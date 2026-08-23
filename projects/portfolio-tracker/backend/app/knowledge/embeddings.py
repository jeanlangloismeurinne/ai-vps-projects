"""Embeddings de la Knowledge Platform — client DeepInfra, modèle `BAAI/bge-m3` (1024d, multilingue).

Pourquoi bge-m3 et pas bge-base-en-v1.5 (DÉCISION #4 initiale) : le corpus est en FRANÇAIS
(lang='fr' sur toutes les entrées du seed, et les sources EU le resteront), et le modèle anglais
ratait précisément les entrées financières EDGAR Tier A. Bench sur corpus réel (7 requêtes FR,
15 entrées) : hit@3 = 4/7 en bge-base-en-v1.5 contre 7/7 en bge-m3. Justification complète et
chiffrée dans `db/migrations/027_v2_embeddings_1024.sql`.

Provider-agnostic (constitution §5.6) : on passe par l'endpoint OpenAI-compatible déjà utilisé par
`DeepInfraProvider`, avec le modèle dans le body — changer de modèle d'embedding est un changement
de config (+ migration + backfill), jamais un changement d'URL.

Pas de dépendance `pgvector` Python : le vecteur est sérialisé en littéral texte et casté `$n::vector`
côté SQL. Une dépendance de moins à faire vivre sur un VPS contraint, pour ~10 lignes de code.

Sur les échecs : `embed_texts` LÈVE. C'est délibéré — chaque appelant a une stratégie différente
(query_knowledge dégrade vers le texte, store_knowledge écrit NULL et laisse le backfill rattraper),
et masquer l'erreur ici produirait exactement le mode de panne silencieux que la V2 combat (A2).
"""
from __future__ import annotations

import logging
from typing import Any, Optional, Sequence

import asyncpg
import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# Nb de textes par appel HTTP. DeepInfra accepte des batches larges ; 64 borne la taille du payload
# et la casse en cas de retry, sans multiplier les allers-retours (le corpus pilote tient en 1 appel).
_BATCH_SIZE = 64

# Garde-fou de taille. bge-m3 accepte 8192 tokens ; on tronque bien avant, car au-delà de quelques
# milliers de caractères l'entrée devrait de toute façon être découpée en plusieurs knowledge_entries
# (c'est le rôle de l'ingestion-agent, pas de l'embedding de rattraper un chunking absent).
_MAX_CHARS = 6000

# Certaines familles de modèles exigent une instruction en tête des REQUÊTES (asymétrie
# requête/document). bge-m3 n'en veut PAS — en ajouter une dégraderait le score. Table explicite
# pour que le jour où l'on rebascule sur un modèle qui en exige une, ce soit un fait documenté
# et non une régression silencieuse de qualité de recherche.
_QUERY_INSTRUCTION: dict[str, str] = {
    "BAAI/bge-base-en-v1.5": "Represent this sentence for searching relevant passages: ",
    "BAAI/bge-large-en-v1.5": "Represent this sentence for searching relevant passages: ",
    "intfloat/multilingual-e5-large": "query: ",
    # "BAAI/bge-m3": aucune instruction (volontairement absent)
}


class EmbeddingUnavailable(RuntimeError):
    """L'embedding n'a pas pu être calculé (clé absente, API en erreur, timeout)."""


def is_configured() -> bool:
    """Vrai si le service d'embedding est utilisable. Permet aux appelants de dégrader sans exception."""
    return bool(settings.DEEPINFRA_API_KEY)


def _endpoint() -> str:
    base = (settings.DEEPINFRA_API_BASE or "https://api.deepinfra.com/v1/openai").rstrip("/")
    return f"{base}/embeddings"


def entry_text(
    title: Optional[str],
    content: str,
    tags: Optional[Sequence[str]] = None,
) -> str:
    """Texte canonique embeddé pour une knowledge_entry.

    CRITIQUE : cette fonction est la SEULE source de vérité de la composition du texte. Le backfill
    et l'écriture temps réel doivent produire le même texte pour la même entrée, sinon deux entrées
    identiques atterrissent à des endroits différents de l'espace vectoriel et l'anti-doublon du
    search-worker devient inopérant.
    """
    parts = [p for p in (title, content, " ".join(tags or [])) if p and p.strip()]
    return "\n".join(parts).strip()[:_MAX_CHARS]


def to_pgvector(vec: Sequence[float]) -> str:
    """Sérialise un vecteur au format littéral pgvector : '[0.1,0.2,...]' (à caster `$n::vector`)."""
    return "[" + ",".join(f"{float(x):.7g}" for x in vec) + "]"


async def embed_texts(
    texts: Sequence[str],
    *,
    is_query: bool = False,
    timeout: int = 120,
) -> list[list[float]]:
    """Embedde une liste de textes. Renvoie les vecteurs DANS L'ORDRE d'entrée.

    `is_query=True` applique l'instruction de requête du modèle si celui-ci en attend une (§ table
    `_QUERY_INSTRUCTION`). Lève `EmbeddingUnavailable` si la clé manque ou si l'API échoue.
    """
    if not texts:
        return []
    if not is_configured():
        raise EmbeddingUnavailable(
            "DEEPINFRA_API_KEY absente — embeddings indisponibles (configure-la dans Coolify)."
        )

    model = settings.EMBEDDING_MODEL
    prefix = _QUERY_INSTRUCTION.get(model, "") if is_query else ""
    payload_texts = [prefix + (t or "").strip()[:_MAX_CHARS] for t in texts]

    out: list[list[float]] = []
    headers = {
        "Authorization": f"Bearer {settings.DEEPINFRA_API_KEY}",
        "Content-Type": "application/json",
    }
    total_tokens = 0

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            for start in range(0, len(payload_texts), _BATCH_SIZE):
                batch = payload_texts[start:start + _BATCH_SIZE]
                r = await client.post(
                    _endpoint(), headers=headers, json={"model": model, "input": batch}
                )
                if r.status_code >= 400:
                    logger.error("DeepInfra embeddings %s: %s", r.status_code, r.text[:400])
                r.raise_for_status()
                data = r.json()
                # L'API peut renvoyer les items dans le désordre : on réordonne sur `index`.
                items = sorted(data.get("data", []), key=lambda d: d.get("index", 0))
                if len(items) != len(batch):
                    raise EmbeddingUnavailable(
                        f"DeepInfra a renvoyé {len(items)} vecteurs pour {len(batch)} textes"
                    )
                out.extend(item["embedding"] for item in items)
                total_tokens += (data.get("usage") or {}).get("total_tokens", 0) or 0
    except httpx.HTTPStatusError as e:
        raise EmbeddingUnavailable(
            f"DeepInfra embeddings a retourné {e.response.status_code} — relance possible sans risque"
        ) from e
    except httpx.TimeoutException as e:
        raise EmbeddingUnavailable(
            "DeepInfra embeddings n'a pas répondu dans le délai imparti — relance possible"
        ) from e

    # Garde-fou de dimension : une incohérence modèle/colonne casserait l'INSERT plus loin avec une
    # erreur Postgres opaque. On échoue ici, avec le diagnostic exact.
    expected = settings.EMBEDDING_DIM
    if out and len(out[0]) != expected:
        raise EmbeddingUnavailable(
            f"dimension inattendue : le modèle {model} renvoie {len(out[0])}d, "
            f"or knowledge_entries.embedding est en vector({expected}). "
            f"Changer de modèle impose une migration + un backfill complet."
        )

    logger.info(
        "embeddings: %d texte(s), modèle=%s, %d tokens facturés", len(out), model, total_tokens
    )
    return out


async def embed_one(text: str, *, is_query: bool = False, timeout: int = 120) -> list[float]:
    """Embedde un texte unique. Sucre sur `embed_texts`."""
    vecs = await embed_texts([text], is_query=is_query, timeout=timeout)
    return vecs[0]


# ── Backfill ─────────────────────────────────────────────────────────────────
async def backfill_embeddings(
    conn: asyncpg.Connection,
    *,
    ticker_id: Optional[str] = None,
    batch_size: int = _BATCH_SIZE,
    limit: Optional[int] = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Calcule et écrit l'embedding des entrées où il manque (`embedding IS NULL`).

    Idempotent : ne touche que les lignes NULL, donc relançable sans risque après un échec partiel.
    Porte sur les entrées COURANTES comme sur les superseded — une entrée superseded reste citée par
    `analysis_knowledge_refs` et doit rester retrouvable.

    Renvoie un compte-rendu {candidats, embeddees, echecs, tokens_estimes}.
    """
    where = ["embedding IS NULL", "is_deleted = FALSE"]
    params: list[Any] = []
    if ticker_id is not None:
        params.append(ticker_id)
        where.append(f"ticker_id = ${len(params)}")
    sql = f"SELECT id, title, content, tags FROM knowledge_entries WHERE {' AND '.join(where)} ORDER BY id"
    if limit is not None:
        params.append(limit)
        sql += f" LIMIT ${len(params)}"

    rows = await conn.fetch(sql, *params)
    report: dict[str, Any] = {
        "candidats": len(rows),
        "embeddees": 0,
        "echecs": 0,
        "modele": settings.EMBEDDING_MODEL,
        "dry_run": dry_run,
    }
    if not rows:
        logger.info("backfill_embeddings: rien à faire (aucune entrée à embedding NULL)")
        return report
    if dry_run:
        logger.info("backfill_embeddings (dry-run): %d entrée(s) candidates", len(rows))
        return report

    for start in range(0, len(rows), batch_size):
        chunk = rows[start:start + batch_size]
        texts = [entry_text(r["title"], r["content"], r["tags"]) for r in chunk]
        try:
            vecs = await embed_texts(texts)
        except EmbeddingUnavailable as e:
            logger.error("backfill_embeddings: lot %d-%d échoué — %s", start, start + len(chunk), e)
            report["echecs"] += len(chunk)
            continue
        # Écriture ligne à ligne : le volume est faible et cela isole l'échec d'une ligne.
        for row, vec in zip(chunk, vecs):
            await conn.execute(
                "UPDATE knowledge_entries SET embedding = $1::vector WHERE id = $2",
                to_pgvector(vec), row["id"],
            )
            report["embeddees"] += 1

    logger.info(
        "backfill_embeddings: %d/%d entrée(s) embeddée(s), %d échec(s)",
        report["embeddees"], report["candidats"], report["echecs"],
    )
    return report
