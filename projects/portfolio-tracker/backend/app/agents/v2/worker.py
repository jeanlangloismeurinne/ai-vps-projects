"""
search-worker (§5.2, contrat C1) — `WorkerRequest` → `WorkerResponse` d'entries scorées.

C'est le **boundary par lequel la donnée entre dans le système**. Un agent métier dit *quoi* trouver
et *avec quelle exigence de fiabilité* ; l'ouvrier cherche (web_search / fetch_url), vérifie
l'existant (query_knowledge) et rend des `knowledge_entries` **scorées** — jamais de prose (G3).

## Ce que le modèle décide, et ce qu'il ne décide pas

Le modèle décide du **fond** : quoi chercher, quelle source retenir, quel contenu en extraire, ce
qu'il n'a pas trouvé. Tout le reste est **recalculé en Python** par `_apply_deterministic_overrides`,
selon le même principe que `curator._apply_deterministic_overrides` :

  - `reliability_score` / `reliability_tier` / `reliability_note` ← `compute_reliability(source_type)`.
    Laisser un modèle noter la fiabilité de la source qu'il vient de choisir, c'est lui laisser fixer
    son propre score : le plafond de source (§6.3) n'aurait plus de gardien.
  - `source_type` ← déterminé par le **domaine** (`classify_source_type`), pas par la déclaration du
    modèle : un billet de blog ne devient pas `financial_press` parce qu'il parle de résultats, et
    une page `ir.nvidia.com` reste de l'IR officiel même si le modèle la sous-qualifie. Seul l'aveu
    `llm_memory` est honoré tel quel (cf. `_resolve_source_type`).
  - **provenance** ← confrontée au `RetrievalLog` du run (`_verify_provenance`). Interdire au modèle
    de choisir son `source_type` ne suffisait pas : en choisissant l'URL il choisit le domaine, donc
    le source_type, donc le score. Une URL jamais rapportée par un outil ne peut pas fonder une
    citation — elle est ramenée à `llm_memory`.
  - **une entrée = un document** : une entry qui cite plusieurs dépôts sous un seul `source_url` est
    marquée pour revue humaine (`_cited_documents`), l'attribution étant fausse pour au moins un.
  - filtre `reliability_min`, plafond `max_entries`, `covers`, cohérence `status`/`uncovered_fields`,
    et la déclaration d'exécution (modèle, tokens, coût) qui est **mesurée**, jamais déclarée.

Le résultat corrigé est ensuite validé par `WorkerExchange` (invariants croisés requête×réponse). La
validation est donc un **filet**, pas le mécanisme : on ne compte pas sur elle pour faire respecter
des règles qu'on sait imposer soi-même. Un `WorkerExchange` qui échoue signale un bug ici, pas un
modèle désobéissant.

## Recherche web indisponible

`run_search_worker` refuse de démarrer si le backend de recherche n'est pas configuré (sauf
`allow_without_web=True`, mode anti-doublon sur la seule base locale). Motif : un worker sans
recherche rendrait un `not_found` parfaitement bien formé, que le curator lirait comme « cette
information n'existe pas » alors qu'elle n'a pas été cherchée. Mieux vaut une erreur bruyante en
amont qu'un trou de couverture crédible.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
from datetime import date, datetime
from typing import Any, Optional

import asyncpg

from app.agents.providers import get_agent_provider
from app.contracts import (
    SOURCE_RELIABILITY_BASELINE,
    WorkerExchange,
    WorkerRequest,
    WorkerResponse,
)
from app.knowledge.service import compute_reliability, store_knowledge
from app.knowledge.websearch import SearchUnavailable, classify_source_type, search_is_configured

from .runner import run_tool_json_agent
from .tools import RetrievalLog, build_tool_executors

logger = logging.getLogger(__name__)

WORKER_NAME = "search-worker"

_CLOSING_INSTRUCTION = (
    "Termine maintenant. N'appelle plus aucun outil : réponds UNIQUEMENT par l'objet JSON "
    "`WorkerResponse` du contrat, sans texte autour.\n"
    "Rappels : aucune prose (G3) ; ce que tu n'as pas trouvé va dans `uncovered_fields` ; "
    "chaque entry porte `content` (Markdown, autoportant), `source_type`, `source_url`, "
    "`source_date` (ISO) et une `reliability_note` non vide ; n'invente aucune URL — n'utilise que "
    "celles rapportées par les outils. Les champs `reliability_score`/`reliability_tier` sont "
    "recalculés côté serveur d'après la source : donne-les au mieux, mais c'est `source_type` et "
    "`source_url` qui comptent.\n"
    "DEUX RÈGLES DE PROVENANCE, vérifiées côté serveur :\n"
    "1. `source_url` doit être une URL que tu as RÉELLEMENT ouverte avec `fetch_url` pendant ce run. "
    "Une URL que tu connais de mémoire, même exacte, ne compte pas : le serveur compare à la liste "
    "des pages effectivement récupérées et rétrograde en `llm_memory` (score 0.40) tout ce qui n'y "
    "figure pas. Si tu restitues de mémoire, déclare-le : `source_type: llm_memory`, c'est honnête "
    "et ce n'est pas sanctionné.\n"
    "2. Une entrée = UN document. Ne fusionne jamais deux dépôts (un 10-K et un 10-Q, un communiqué "
    "et un article) sous un seul `source_url` : fais-en deux entries, chacune avec son URL et sa "
    "date."
)


# ── hash de requête (§13.5 : reproductibilité) ───────────────────────────────
def request_hash(req: WorkerRequest) -> str:
    """Empreinte stable d'une WorkerRequest (clés triées) — rejouabilité et clé de cache éventuelle."""
    payload = json.dumps(req.model_dump(mode="json"), sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]


# ── normalisation déterministe ───────────────────────────────────────────────
def _baseline(source_type: str) -> float:
    return SOURCE_RELIABILITY_BASELINE.get(source_type, (None, 0.0))[1]


def _resolve_source_type(declared: Any, url: Optional[str]) -> str:
    """Qualification finale de la source : le **domaine** tranche, sauf aveu de mémoire modèle.

    `source_type` n'est pas un jugement mais un **fait sur la source**, que le domaine détermine
    mieux que le modèle : une page `ir.nvidia.com` EST de l'IR officiel, qu'un modèle distrait la
    qualifie de blog ou d'archive EDGAR. Laisser sa déclaration faire foi, c'est lui laisser fixer
    le score qui en découle (§6.3) — dans les deux sens : la sur-qualification gonfle la fiabilité,
    la sous-qualification fait tomber une bonne source sous le plancher et creuse un faux trou de
    couverture.

    Une seule déclaration à la baisse est honorée : `llm_memory`. Elle ne parle pas de la source mais
    de ce que le modèle a fait — « je n'ai pas lu cette page, je restitue de mémoire ». Aucun domaine
    ne peut contredire cet aveu, et P2 (§6.4) impose derrière revue humaine + cutoff.
    """
    if declared == "llm_memory":
        return "llm_memory"
    return classify_source_type(url)


def _verify_provenance(url: Optional[str], log: Optional[RetrievalLog]) -> tuple[bool, Optional[str]]:
    """`(source_non_vérifiée, note)` — l'URL déclarée a-t-elle vraiment été lue pendant le run ?

    `_resolve_source_type` retire au modèle le choix de son `source_type`, mais pas celui de son
    `source_url` — or l'URL détermine le domaine, donc le source_type, donc le score. Le contournement
    est involontaire mais total : run C sur NVDA (2026-08-23), 5 entrées à `edgar_official` 0.94
    tier A pointant sec.gov, alors qu'aucune URL sec.gov n'avait été récupérée du run. Le modèle
    restituait sa mémoire d'entraînement en l'habillant d'une URL plausible.

    On ne juge pas le contenu — c'est hors de portée d'un contrôle Python. On répond à la seule
    question vérifiable : **ce document est-il passé sous les yeux du modèle ?** Trois cas :
      - jamais rapporté, ou simple lien dans une liste de résultats → la citation n'a aucun support :
        c'est de la mémoire modèle, et P2 (§6.4) s'applique (0.40, revue humaine) ;
      - extrait de tête seul (2 000 car. d'un résultat de recherche) → la source est réelle mais
        n'a pas été lue en entier : le score du domaine reste, la revue humaine est exigée ;
      - document récupéré par `fetch_url` → rien à signaler.
    """
    if log is None or not url:
        return False, None
    depth = log.depth_of(url)
    if depth == "full":
        return False, None
    if depth == "excerpt":
        return False, (
            "source réelle mais lue en extrait seulement (texte de résultat de recherche, "
            "document jamais récupéré en entier) — revue humaine"
        )
    return True, (
        "URL déclarée jamais récupérée pendant le run "
        f"({'aucun outil ne l a rapportée' if depth is None else 'vue en lien de résultat, sans contenu'}) "
        "— provenance non vérifiable, ramenée à llm_memory"
    )


# Désignations de dépôts réglementaires. Une entry qui en cite plusieurs parle de plusieurs
# documents, alors qu'elle ne porte qu'un `source_url`.
_FILING_FORMS = re.compile(r"\b(10-K|10-Q|8-K|20-F|40-F|6-K|S-1|DEF\s*14A)\b", re.IGNORECASE)


def _cited_documents(content: str) -> list[str]:
    """Désignations distinctes de dépôts citées dans le contenu (`10-K`, `10-Q`, …)."""
    return sorted({re.sub(r"\s+", " ", m.group(1)).upper() for m in _FILING_FORMS.finditer(content)})


def _parse_iso_date(value: Any) -> Optional[date]:
    """Date ISO stricte. Une date non reconnue est écartée plutôt que devinée : elle pilote la
    décote d'âge du score (§6.3), donc une valeur inventée fausserait la fiabilité en silence."""
    if isinstance(value, date):
        return value
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return datetime.strptime(value.strip()[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def _normalise_entry(
    raw: Any, req: WorkerRequest, log: Optional[RetrievalLog] = None
) -> Optional[dict[str, Any]]:
    """Corrige une entry brute du modèle, ou None si elle est irrécupérable (rejet tracé)."""
    if not isinstance(raw, dict):
        return None
    content = (raw.get("content") or "").strip()
    if not content:
        return None  # une entry sans contenu n'est pas une donnée

    want = req.output_schema.entry_type
    if raw.get("entry_type") != want:
        # On REJETTE au lieu de forcer : une entry du mauvais type répond à une autre question que
        # celle posée. La corriger d'office ferait entrer une donnée hors mandat.
        logger.info("search-worker: entry rejetée (type %r ≠ %r)", raw.get("entry_type"), want)
        return None

    url = (raw.get("source_url") or "").strip() or None
    source_type = _resolve_source_type(raw.get("source_type"), url)
    source_date = _parse_iso_date(raw.get("source_date"))

    caveats: list[str] = []
    unverified, provenance_note = _verify_provenance(url, log)
    if provenance_note:
        caveats.append(provenance_note)
    if unverified and source_type != "llm_memory":
        logger.info(
            "search-worker: provenance non vérifiée pour %s — %s → llm_memory",
            url, source_type,
        )
        source_type = "llm_memory"

    # Une entrée = un document. Une entry qui cite un 10-K ET un 10-Q sous un seul `source_url`
    # attribue au document cité les propos de l'autre — et lui prête son score. Constaté en run C :
    # une citation du 10-Q du 20/05/2026 archivée sous l'URL du 10-K, à 0.94 tier A. On ne peut pas
    # scinder l'entry sans réécrire son contenu (ce que le worker n'a pas le droit de faire, G3),
    # donc on la laisse entrer en la marquant : la base est append-only, une provenance douteuse
    # tracée vaut mieux qu'une provenance douteuse muette.
    cited = _cited_documents(content)
    if len(cited) > 1:
        caveats.append(
            f"contenu adossé à plusieurs documents ({', '.join(cited)}) pour un seul source_url "
            "— attribution à vérifier, une entrée devrait porter un seul document"
        )
        logger.info("search-worker: entry multi-documents (%s) sous %s", ", ".join(cited), url)

    score, tier, note = compute_reliability(
        source_type, entry_type=want, source_date=source_date,
    )
    declared_note = (raw.get("reliability_note") or "").strip()
    if declared_note:
        note = f"{note} | agent : {declared_note[:300]}"
    if caveats:
        note = f"{note} | provenance : {' ; '.join(caveats)}"

    entry: dict[str, Any] = {
        "entry_type": want,
        "title": (raw.get("title") or "").strip() or None,
        "content": content,
        "content_structured": raw.get("content_structured") if isinstance(raw.get("content_structured"), dict) else None,
        "tags": [str(t)[:60] for t in (raw.get("tags") or []) if str(t).strip()][:12],
        "lang": (raw.get("lang") or "fr")[:8],
        "source_type": source_type,
        "source_url": url,
        "source_date": source_date.isoformat() if source_date else None,
        "fiscal_period": raw.get("fiscal_period") or req.output_schema.fiscal_period,
        "reliability_score": score,
        "reliability_tier": tier,
        "reliability_note": note,
        "requires_human_review": bool(raw.get("requires_human_review")) or bool(caveats),
        "model_cutoff": raw.get("model_cutoff"),
        "covers": req.output_schema.field_path or raw.get("covers"),
        "question_status": raw.get("question_status"),
    }

    if source_type == "llm_memory":
        # P2 (§6.4) : la mémoire modèle entre sous condition de traçabilité, jamais discrètement.
        entry["requires_human_review"] = True
        entry["model_cutoff"] = entry.get("model_cutoff") or "inconnu"
    return entry


def _apply_deterministic_overrides(
    data: dict[str, Any],
    req: WorkerRequest,
    *,
    model_used: str,
    tokens_in: int,
    tokens_out: int,
    cost_usd: float,
    log: Optional[RetrievalLog] = None,
) -> dict[str, Any]:
    """Recalcule tout ce qui est dérivable de la requête et des sources. Cf. docstring du module."""
    raw_entries = data.get("entries") if isinstance(data.get("entries"), list) else []

    kept: list[dict[str, Any]] = []
    seen: set[tuple[Optional[str], str]] = set()
    n_rejected = n_below_floor = n_dup = 0

    for raw in raw_entries:
        entry = _normalise_entry(raw, req, log)
        if entry is None:
            n_rejected += 1
            continue
        if entry["reliability_score"] < req.reliability_min:
            # Le plancher est un refus d'entrée, pas une préférence de tri : sous le seuil, le métier
            # a dit que la donnée ne l'intéressait pas — elle devient un champ non couvert.
            n_below_floor += 1
            continue
        key = (entry["source_url"], (entry["title"] or entry["content"][:120]).lower())
        if key in seen:
            n_dup += 1
            continue
        seen.add(key)
        kept.append(entry)

    # Arrêt de Pareto : on garde les mieux notées, pas les premières venues.
    kept.sort(key=lambda e: e["reliability_score"], reverse=True)
    n_truncated = max(0, len(kept) - req.max_entries)
    kept = kept[: req.max_entries]

    uncovered = [str(u) for u in (data.get("uncovered_fields") or []) if str(u).strip()]
    target = req.output_schema.field_path or req.output_schema.dimension or req.query[:120]

    if not kept and target not in uncovered:
        # Rien n'entre : le champ visé est non couvert, et il doit être DIT (A6 l'exige même pour un
        # mandat divergent qui ne trouve pas de contre-preuve).
        uncovered.append(target)

    status = "found" if kept and not uncovered else ("partial" if kept else "not_found")

    if n_rejected or n_below_floor or n_dup or n_truncated:
        logger.info(
            "search-worker[%s]: %d entrée(s) retenue(s) — rejetées:%d sous-plancher:%d doublons:%d "
            "tronquées:%d (reliability_min=%.2f, max_entries=%d)",
            req.output_schema.field_path or req.query[:40],
            len(kept), n_rejected, n_below_floor, n_dup, n_truncated,
            req.reliability_min, req.max_entries,
        )

    return {
        "request_hash": data.get("request_hash") or request_hash(req),
        "worker": WORKER_NAME,
        "status": status,
        "entries": kept,
        "uncovered_fields": uncovered,
        # §5.3 : l'exécution est MESURÉE côté serveur. Le modèle n'a aucun moyen de connaître son
        # propre coût, et le lui demander revient à archiver une estimation dans un champ d'audit.
        "execution": {
            "tier": "ouvrier",
            "model_used": model_used,
            "batch": False,
            "cache_hit": False,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "cost_usd": round(cost_usd, 6),
        },
    }


# ── exécution ────────────────────────────────────────────────────────────────
def _build_user_message(req: WorkerRequest) -> str:
    """La requête part telle quelle (JSON) : le prompt du worker est écrit contre ce contrat."""
    lignes = [
        "WorkerRequest à traiter :",
        "```json",
        json.dumps(req.model_dump(mode="json"), ensure_ascii=False, indent=2),
        "```",
        "",
        f"Commence par `query_knowledge` (anti-doublon) : {req.check_existing_first}.",
        f"Plancher de fiabilité : {req.reliability_min:.2f} — sous ce seuil, ne retourne rien, "
        f"déclare le champ non couvert.",
        f"Plafond : {req.max_entries} entries maximum.",
    ]
    if req.divergent:
        lignes.append(
            "MANDAT DIVERGENT (A6) : tu cherches ce qui CONTREDIT la thèse dominante. Si tu ne "
            "trouves aucune contre-preuve, dis-le explicitement dans `uncovered_fields` — "
            "l'absence de contre-preuve est elle-même une information."
        )
    return "\n".join(lignes)


async def run_search_worker(
    req: WorkerRequest,
    *,
    allow_without_web: bool = False,
    max_iterations: int = 6,
    timeout: int = 720,
) -> WorkerExchange:
    """Exécute le search-worker et renvoie l'échange complet (requête + réponse validées).

    Lève `SearchUnavailable` si la recherche web n'est pas configurée (voir docstring du module),
    `AgentNotFoundError` si l'agent n'est pas en DB, `RuntimeError` si la sortie reste non conforme
    après réparation.
    """
    if req.worker != WORKER_NAME:
        raise ValueError(f"run_search_worker appelé pour worker={req.worker!r}")
    if not allow_without_web and not search_is_configured():
        raise SearchUnavailable(
            "search-worker refusé : aucun backend de recherche web configuré. Un run sans recherche "
            "produirait un 'not_found' indiscernable d'une absence réelle de source."
        )

    agent = await get_agent_provider(WORKER_NAME, "v2")
    # Le journal est propre à CE run : une URL récupérée lors d'un run précédent ne justifie pas une
    # citation dans celui-ci, et le worker doit pouvoir tourner en parallèle sans état partagé.
    retrieval_log = RetrievalLog()
    executors = build_tool_executors(
        ticker_id=req.ticker_id, query=req.query, log=retrieval_log
    )

    result = await run_tool_json_agent(
        agent,
        [{"role": "user", "content": _build_user_message(req)}],
        executors,
        WorkerResponse,
        closing_instruction=_CLOSING_INSTRUCTION,
        max_iterations=max_iterations,
        temperature=0.2,
        timeout=timeout,
    )

    corrected = _apply_deterministic_overrides(
        result.data,
        req,
        model_used=agent.model or result.completion.model,
        tokens_in=result.tokens_in,
        tokens_out=result.tokens_out,
        cost_usd=result.cost_usd,
        log=retrieval_log,
    )
    logger.info(
        "search-worker[%s]: %d URL rapportée(s) par les outils (%s)",
        req.output_schema.field_path or req.query[:40],
        len(retrieval_log.seen),
        ", ".join(f"{u}:{d}" for u, d in list(retrieval_log.seen.items())[:8]) or "aucune",
    )
    response = WorkerResponse.model_validate(corrected)
    return WorkerExchange(request=req, response=response)


# ── persistance ──────────────────────────────────────────────────────────────
async def persist_worker_entries(
    conn: asyncpg.Connection,
    exchange: WorkerExchange,
) -> list[dict[str, Any]]:
    """Écrit les entries retenues en base (append-only A1) et renvoie les lignes créées.

    Séparé de `run_search_worker` à dessein : l'appelant maîtrise la transaction (§ conventions DB)
    et peut inspecter, voire refuser, un échange avant de le rendre persistant. Le score écrit est
    **recalculé une seconde fois** par `store_knowledge` à partir du `source_type` — c'est la même
    fonction, donc le même résultat, et c'est cette table-là qui fait foi en base.
    """
    created: list[dict[str, Any]] = []
    for entry in exchange.response.entries:
        row = await store_knowledge(
            conn,
            ticker_id=exchange.request.ticker_id,
            entry_type=entry.entry_type,
            content=entry.content,
            source_type=entry.source_type,
            title=entry.title,
            content_structured=entry.content_structured,
            tags=entry.tags,
            lang=entry.lang,
            source_url=entry.source_url,
            source_date=_parse_iso_date(entry.source_date),
            fiscal_period=entry.fiscal_period,
            model_cutoff=entry.model_cutoff,
            covers=(entry.covers.split(".")[-1] if entry.covers else None),
        )
        created.append(dict(row))
    logger.info(
        "search-worker: %d entrée(s) persistée(s) pour %s (%s)",
        len(created), exchange.request.ticker_id, exchange.request.output_schema.field_path,
    )
    return created
