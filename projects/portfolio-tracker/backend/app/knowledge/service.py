"""
Service Knowledge Platform (couche 3) — store / query / snapshot des `knowledge_entries`.

Substrat commun de tous les agents V2. Trois opérations du LLM Wiki Pattern (§6.1) :
  - **store_knowledge** : crée une entrée APPEND-ONLY versionnée (A1) — on ne mute JAMAIS, on
    supersede. Le score de fiabilité est calculé ici (§6.3), pas déclaré par l'agent.
  - **query_knowledge** : recherche sur la version COURANTE des entrées (superseded_by IS NULL AND
    NOT is_deleted). Recherche VECTORIELLE (`embedding <=> $vec`, bge-m3 1024d, index HNSW
    vector_cosine_ops), avec repli TEXTE (ILIKE multi-termes) dans deux cas seulement : embeddings
    indisponibles (clé absente / API en erreur), et entrées pas encore embeddées.

    Le repli texte est un FALLBACK STRICT, jamais une fusion. Mesuré sur le corpus réel : le signal
    lexical est si faible en français (MRR 0.352) que le fusionner (RRF) DÉGRADE le classement
    vectoriel — 0.905 → 0.655. Ne pas « améliorer » ceci en hybride sans re-mesurer.
  - **snapshot_refs** : fige (analysis_id, analysis_kind, entry_id@version, content) dans
    analysis_knowledge_refs (A1/A2) — le P0 d'auditabilité, jamais un INT[] mutable.

Conventions DB projet : asyncpg $1 (pas %s) ; JSONB auto-décodé (pas de json.dumps) ; les fonctions
prennent une connexion `conn` explicite → l'appelant maîtrise la transaction (atomicité store+supersede
et batch de snapshot). Ouvrir via `async with get_db_session() as conn`.
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Any, Optional, Sequence

import asyncpg

from .embeddings import (
    EmbeddingUnavailable,
    embed_one,
    entry_text,
    is_configured as embeddings_configured,
    to_pgvector,
)

logger = logging.getLogger(__name__)


# ── Framework de fiabilité (§6.3 / KP §3.3) ──────────────────────────────────
# source_type -> (tier, score de base). Le tier est fixé par la source ; le score est modulé
# (âge / cross-validation / contradiction) puis borné [0,1]. Le tier NE change pas à la modulation
# (il qualifie la NATURE de la source, pas son actualité).
RELIABILITY_TABLE: dict[str, tuple[str, float]] = {
    "edgar_official":               ("A",  0.95),
    "company_ir_official":          ("A",  0.90),
    "earnings_transcript_official": ("A-", 0.85),
    "regulator_filing_eu":          ("A-", 0.85),
    # yfinance/fmp : fournisseurs de données de marché structurées (§6.5/§17). Alignés sur
    # SOURCE_RELIABILITY_BASELINE du contrat C1 — les deux tables doivent coïncider, sinon une
    # entrée serait scorée ici et plafonnée là-bas selon des baselines différentes.
    "yfinance":                     ("B+", 0.75),
    "fmp":                          ("B+", 0.75),
    "financial_press":              ("B+", 0.75),
    "user_provided_confidential":   ("B+", 0.80),
    "web_search_reputable":         ("B",  0.65),
    "user_provided":                ("B",  0.70),
    "agent_synthesis":              ("B-", 0.60),
    "web_search_generic":           ("C+", 0.50),
    "llm_memory":                   ("C",  0.40),
}
_FALLBACK_RELIABILITY = ("C", 0.40)  # source inconnue = prudence (traité comme mémoire modèle)

# entry_types dont le score se dégrade au rythme "financier" (−0.05/an) vs "qualitatif" (−0.02/an).
_FINANCIAL_ENTRY_TYPES = {"fact_financial"}

# source_types qui exigent une revue humaine (P2 : mémoire modèle non vérifiée).
_REQUIRES_REVIEW_SOURCES = {"llm_memory"}


def compute_reliability(
    source_type: str,
    *,
    entry_type: Optional[str] = None,
    source_date: Optional[date] = None,
    today: Optional[date] = None,
    cross_validated: bool = False,
    has_conflict: bool = False,
) -> tuple[float, str, str]:
    """Renvoie (score, tier, note explicative). Modulations §6.3 : âge, cross-validation, conflit."""
    tier, base = RELIABILITY_TABLE.get(source_type, _FALLBACK_RELIABILITY)
    score = base
    notes: list[str] = [f"base {source_type}={base:.2f} (tier {tier})"]

    if source_date is not None:
        ref = today or date.today()
        years = max(0.0, (ref - source_date).days / 365.25)
        decay = 0.05 if entry_type in _FINANCIAL_ENTRY_TYPES else 0.02
        penalty = round(years * decay, 3)
        if penalty:
            score -= penalty
            notes.append(f"âge {years:.1f}a −{penalty:.2f}")
    if cross_validated:
        score += 0.10
        notes.append("cross-validé +0.10")
    if has_conflict:
        score -= 0.20
        notes.append("contradiction −0.20")

    score = round(min(1.0, max(0.0, score)), 3)
    return score, tier, " ; ".join(notes)


# ── STORE (append-only, A1) ──────────────────────────────────────────────────
async def store_knowledge(
    conn: asyncpg.Connection,
    *,
    ticker_id: Optional[str],
    entry_type: str,
    content: str,
    source_type: str,
    title: Optional[str] = None,
    content_structured: Optional[dict] = None,
    tags: Optional[Sequence[str]] = None,
    lang: str = "en",
    source_url: Optional[str] = None,
    source_date: Optional[date] = None,
    fiscal_period: Optional[str] = None,
    document_id: Optional[int] = None,
    model_cutoff: Optional[str] = None,
    cross_validated: bool = False,
    has_conflict: bool = False,
    conflict_entry_id: Optional[int] = None,
    supersedes_entry_id: Optional[int] = None,
    embed: bool = True,
    embedding: Optional[Sequence[float]] = None,
    requires_human_review: bool = False,
    derived_reliability: Optional[tuple[float, str, str]] = None,
) -> dict[str, Any]:
    """Crée une knowledge_entry. Le score/tier sont CALCULÉS (§6.3), jamais fournis par l'appelant.

    Versionnement A1 : si `supersedes_entry_id` est donné, l'ancienne entrée est marquée
    `superseded_by = <nouvelle>` (jamais mutée sur le fond) et la nouvelle porte `version+1`.

    `derived_reliability=(score, tier, note)` court-circuite `compute_reliability` — réservé aux
    fondations DÉTERMINISTES qui dérivent le tier d'intrants déjà scorés en base (ex. synthesis_feed :
    un cran sous la plus faible entry citée). Ce n'est PAS l'agent qui déclare son score (#24) : c'est
    un calcul Python à partir de tiers vérifiés en base. Le `note` DOIT expliquer la dérivation.
    `requires_human_review=True` force le flag (en plus des source_types qui l'exigent d'office, P2).

    Embedding : calculé ICI par défaut (`embed=True`) pour qu'une entrée naisse immédiatement
    trouvable — sinon le backlog d'entrées `embedding IS NULL` grossit et l'anti-doublon du
    search-worker rate des entrées qui existent déjà. L'échec n'est PAS fatal : on écrit NULL, on
    loggue, et `backfill_embeddings` rattrape. Perdre une entrée parce que l'API d'embedding tousse
    serait un bien pire résultat que la retrouver plus tard.

    Deux échappatoires pour l'ingestion de masse (ingestion-agent, Batch API) : `embedding=[...]`
    fournit un vecteur déjà calculé en lot, et `embed=False` diffère au backfill. Elles évitent
    N appels HTTP unitaires à l'intérieur d'une transaction.
    """
    if derived_reliability is not None:
        score, tier, note = derived_reliability
    else:
        score, tier, note = compute_reliability(
            source_type, entry_type=entry_type, source_date=source_date,
            cross_validated=cross_validated, has_conflict=has_conflict,
        )
    requires_review = requires_human_review or source_type in _REQUIRES_REVIEW_SOURCES

    version = 1
    if supersedes_entry_id is not None:
        prev = await conn.fetchrow(
            "SELECT version FROM knowledge_entries WHERE id = $1", supersedes_entry_id
        )
        if prev is None:
            raise ValueError(f"supersedes_entry_id introuvable : {supersedes_entry_id}")
        version = prev["version"] + 1

    vec_literal: Optional[str] = None
    if embedding is not None:
        vec_literal = to_pgvector(embedding)
    elif embed and embeddings_configured():
        try:
            vec_literal = to_pgvector(
                await embed_one(entry_text(title, content, tags))
            )
        except EmbeddingUnavailable as e:
            logger.warning(
                "store_knowledge: embedding indisponible (%s) — entrée écrite avec embedding NULL, "
                "rattrapable par backfill_embeddings", e,
            )

    row = await conn.fetchrow(
        """
        INSERT INTO knowledge_entries (
            ticker_id, document_id, entry_type, title, content, content_structured,
            tags, lang, source_type, source_url, source_date, fiscal_period,
            reliability_score, reliability_tier, reliability_note,
            has_conflict, conflict_entry_id, requires_human_review, model_cutoff, version,
            embedding
        ) VALUES (
            $1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18,$19,$20,$21::vector
        )
        RETURNING id, version, reliability_score, reliability_tier
        """,
        ticker_id, document_id, entry_type, title, content, content_structured,
        list(tags or []), lang, source_type, source_url, source_date, fiscal_period,
        score, tier, note, has_conflict, conflict_entry_id, requires_review, model_cutoff, version,
        vec_literal,
    )

    if supersedes_entry_id is not None:
        await conn.execute(
            "UPDATE knowledge_entries SET superseded_by = $1, is_outdated = TRUE, updated_at = NOW() "
            "WHERE id = $2",
            row["id"], supersedes_entry_id,
        )

    return dict(row)


# ── QUERY (version courante) ─────────────────────────────────────────────────
_CURRENT = "superseded_by IS NULL AND is_deleted = FALSE"


async def get_current_entries(
    conn: asyncpg.Connection,
    ticker_id: Optional[str],
    *,
    entry_types: Optional[Sequence[str]] = None,
    min_reliability: float = 0.0,
    include_sector: bool = True,
    limit: int = 500,
) -> list[dict[str, Any]]:
    """Toutes les entrées COURANTES d'un ticker (base du readiness / context_pack).

    `include_sector` ajoute les entrées transverses (ticker_id IS NULL = sectoriel/macro) réutilisables
    entre titres d'un même secteur (§6.6, wiki cumulatif).
    """
    clauses = [_CURRENT, "reliability_score >= $2"]
    params: list[Any] = [ticker_id, min_reliability]
    if include_sector:
        clauses.append("(ticker_id = $1 OR ticker_id IS NULL)")
    else:
        clauses.append("ticker_id = $1")
    if entry_types:
        params.append(list(entry_types))
        clauses.append(f"entry_type = ANY(${len(params)})")
    params.append(limit)
    sql = f"""
        SELECT id, ticker_id, entry_type, title, content, content_structured, tags,
               source_type, source_url, source_date, fiscal_period, reliability_score, reliability_tier,
               requires_human_review, has_conflict, version
        FROM knowledge_entries
        WHERE {' AND '.join(clauses)}
        ORDER BY reliability_score DESC, source_date DESC NULLS LAST, id
        LIMIT ${len(params)}
    """
    return [dict(r) for r in await conn.fetch(sql, *params)]


# Nb de places réservées, dans le budget `limit`, aux entrées non encore embeddées (invisibles au
# vectoriel). Borne volontairement basse : c'est un filet pour un état transitoire, pas un
# co-classement — le signal lexical est faible et ne doit pas évincer le vectoriel.
_RESCUE_QUOTA = 3

_SELECT_COLS = """id, ticker_id, entry_type, title, content, content_structured, tags,
               source_type, source_date, fiscal_period, reliability_score, reliability_tier,
               requires_human_review, has_conflict, version"""


async def _vector_search(
    conn: asyncpg.Connection,
    *,
    vec_literal: str,
    ticker_id: Optional[str],
    entry_types: Optional[Sequence[str]],
    min_reliability: float,
    include_sector: bool,
    limit: int,
) -> list[dict[str, Any]]:
    """Plus proches voisins cosinus parmi les entrées COURANTES et DÉJÀ embeddées.

    Le classement est purement sémantique : la fiabilité n'entre PAS dans le tri (elle reste un
    filtre via `min_reliability` et un champ retourné). C'est l'invariant A3 — qualité de
    l'information et pertinence sont des axes séparés, jamais fusionnés en un score unique.
    """
    params: list[Any] = [ticker_id, min_reliability, vec_literal]
    scope = "(ticker_id = $1 OR ticker_id IS NULL)" if include_sector else "ticker_id = $1"
    type_clause = ""
    if entry_types:
        params.append(list(entry_types))
        type_clause = f" AND entry_type = ANY(${len(params)})"
    params.append(limit)
    sql = f"""
        SELECT {_SELECT_COLS},
               1 - (embedding <=> $3::vector) AS similarity
        FROM knowledge_entries
        WHERE {_CURRENT} AND {scope} AND reliability_score >= $2
              AND embedding IS NOT NULL{type_clause}
        ORDER BY embedding <=> $3::vector
        LIMIT ${len(params)}
    """
    rows = [dict(r) for r in await conn.fetch(sql, *params)]
    for r in rows:
        r["match_mode"] = "vector"
    return rows


async def _text_search(
    conn: asyncpg.Connection,
    *,
    query: str,
    ticker_id: Optional[str],
    entry_types: Optional[Sequence[str]],
    min_reliability: float,
    include_sector: bool,
    limit: int,
    only_unembedded: bool = False,
) -> list[dict[str, Any]]:
    """Repli lexical : nb de termes (>2 chars) présents dans content|title|tags, puis fiabilité.

    Signal faible en français (MRR mesuré 0.352) — d'où son statut de repli et non de co-classement.
    `only_unembedded` le restreint aux entrées que le vectoriel ne peut PAS voir.
    """
    terms = [t for t in query.replace(",", " ").split() if len(t) > 2][:12]
    if not terms:
        return []

    params: list[Any] = [ticker_id, min_reliability]
    scope = "(ticker_id = $1 OR ticker_id IS NULL)" if include_sector else "ticker_id = $1"
    type_clause = ""
    if entry_types:
        params.append(list(entry_types))
        type_clause = f" AND entry_type = ANY(${len(params)})"

    hit_exprs: list[str] = []
    for term in terms:
        params.append(f"%{term}%")
        i = len(params)
        hit_exprs.append(
            f"(CASE WHEN (content ILIKE ${i} OR COALESCE(title,'') ILIKE ${i} "
            f"OR array_to_string(tags,' ') ILIKE ${i}) THEN 1 ELSE 0 END)"
        )
    relevance = " + ".join(hit_exprs)
    emb_clause = " AND embedding IS NULL" if only_unembedded else ""
    params.append(limit)
    sql = f"""
        SELECT {_SELECT_COLS},
               ({relevance}) AS relevance
        FROM knowledge_entries
        WHERE {_CURRENT} AND {scope} AND reliability_score >= $2{type_clause}{emb_clause}
        ORDER BY relevance DESC, reliability_score DESC, source_date DESC NULLS LAST
        LIMIT ${len(params)}
    """
    rows = [dict(r) for r in await conn.fetch(sql, *params)]
    for r in rows:
        r["match_mode"] = "text"
    hits = [r for r in rows if r.get("relevance", 0) > 0]
    # Sans aucun terme trouvé, on ne renvoie rien en mode « rattrapage » (ce serait du bruit) ;
    # en mode repli complet on rend quand même les entrées les plus fiables, faute de mieux.
    return hits if (hits or only_unembedded) else rows


async def query_knowledge(
    conn: asyncpg.Connection,
    *,
    ticker_id: Optional[str],
    query: Optional[str] = None,
    entry_types: Optional[Sequence[str]] = None,
    min_reliability: float = 0.0,
    include_sector: bool = True,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Recherche sur les entrées courantes. Sans `query` → get_current_entries (tronqué à `limit`).

    Avec `query`, chemin nominal = VECTORIEL (bge-m3, index HNSW). Deux replis, tous deux traçés
    dans le champ `match_mode` de chaque ligne :

      - embeddings indisponibles (clé absente / API en erreur) → repli texte intégral ;
      - entrées non encore embeddées → elles sont invisibles au vectoriel, donc rattrapées par une
        passe texte restreinte à `embedding IS NULL` et concaténées APRÈS les résultats vectoriels.

    Ce rattrapage n'est pas cosmétique : l'anti-doublon du search-worker (`query_knowledge` avant
    `store_knowledge`) doit voir une entrée fraîchement écrite même si son embedding a échoué,
    sinon il recrée un doublon.

    Les deux signaux ne sont JAMAIS fusionnés (cf. docstring module : la fusion RRF dégrade).
    """
    if not query or not query.strip():
        return await get_current_entries(
            conn, ticker_id, entry_types=entry_types, min_reliability=min_reliability,
            include_sector=include_sector, limit=limit,
        )

    common = dict(
        ticker_id=ticker_id, entry_types=entry_types, min_reliability=min_reliability,
        include_sector=include_sector,
    )

    vec_literal: Optional[str] = None
    if embeddings_configured():
        try:
            vec_literal = to_pgvector(await embed_one(query, is_query=True))
        except EmbeddingUnavailable as e:
            logger.warning("query_knowledge: vectoriel indisponible (%s) — repli texte", e)
    else:
        logger.debug("query_knowledge: DEEPINFRA_API_KEY absente — repli texte")

    if vec_literal is None:
        return await _text_search(conn, query=query, limit=limit, **common)

    rows = await _vector_search(conn, vec_literal=vec_literal, limit=limit, **common)

    # Le rattrapage tourne TOUJOURS, avec un quota réservé. Ne le conditionner pas à `limit -
    # len(rows) > 0` : dès que le corpus dépasse `limit` entrées embeddées, le vectoriel remplit le
    # budget et le rattrapage ne s'exécuterait jamais — donc jamais quand il sert.
    rescued = await _text_search(
        conn, query=query, limit=min(_RESCUE_QUOTA, limit), only_unembedded=True, **common
    )
    if rescued:
        logger.warning(
            "query_knowledge: %d entrée(s) non embeddée(s) rattrapée(s) en texte — "
            "état transitoire anormal, lancer backfill_embeddings", len(rescued),
        )
        # On tronque les résultats vectoriels les PLUS FAIBLES pour tenir le contrat `limit`.
        rows = rows[:max(0, limit - len(rescued))] + rescued
    return rows


# ── SNAPSHOT (auditabilité A1/A2) ────────────────────────────────────────────
async def snapshot_refs(
    conn: asyncpg.Connection,
    *,
    analysis_id: int,
    analysis_kind: str,
    refs: Sequence[dict[str, Any]],
    field_path: Optional[str] = None,
) -> int:
    """Fige les entrées citées (source_entry_refs) dans analysis_knowledge_refs.

    `refs` = liste de {entry_id, version} (SourceEntryRef Pydantic sérialisé). Pour chaque ref on
    copie le CONTENU immuable à cette version + le reliability_score au moment de l'usage. Idempotent
    via ON CONFLICT (UNIQUE analysis_id, analysis_kind, entry_id, field_path). Renvoie le nb figé.
    """
    n = 0
    for ref in refs:
        entry_id = ref["entry_id"]
        version = ref.get("version", 1)
        # version exacte si elle existe encore, sinon la courante de la lignée (le contenu figé
        # protège de toute mutation ultérieure).
        src = await conn.fetchrow(
            "SELECT content, reliability_score FROM knowledge_entries WHERE id = $1 AND version = $2",
            entry_id, version,
        ) or await conn.fetchrow(
            "SELECT content, reliability_score FROM knowledge_entries WHERE id = $1", entry_id
        )
        if src is None:
            logger.warning("snapshot_refs: entry_id %s introuvable — ref ignorée", entry_id)
            continue
        await conn.execute(
            """
            INSERT INTO analysis_knowledge_refs
                (analysis_id, analysis_kind, entry_id, entry_version, content_snapshot,
                 reliability_at_use, field_path)
            VALUES ($1,$2,$3,$4,$5,$6,$7)
            ON CONFLICT (analysis_id, analysis_kind, entry_id, field_path) DO NOTHING
            """,
            analysis_id, analysis_kind, entry_id, version,
            src["content"], src["reliability_score"], field_path,
        )
        n += 1
    return n


def collect_refs(obj: Any) -> list[dict[str, int]]:
    """Extrait récursivement tous les `source_entry_refs` d'un dict/JSON d'analyse (dé-dupliqués).

    Sert à alimenter snapshot_refs depuis un result_json validé sans énumérer chaque champ à la main.
    """
    seen: set[tuple[int, int]] = set()
    out: list[dict[str, int]] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for k, v in node.items():
                if k == "source_entry_refs" and isinstance(v, list):
                    for ref in v:
                        if isinstance(ref, dict) and "entry_id" in ref:
                            key = (ref["entry_id"], ref.get("version", 1))
                            if key not in seen:
                                seen.add(key)
                                out.append({"entry_id": key[0], "version": key[1]})
                else:
                    walk(v)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(obj)
    return out
