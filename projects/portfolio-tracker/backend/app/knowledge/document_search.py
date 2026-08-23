"""
Recherche **au sein d'un document** — sélection par pertinence plutôt que troncature en tête.

Ce module ne connaît ni URL ni HTTP : il prend un **texte** et une **question**, et rend les passages
qui répondent à la question. C'est délibéré — le même code doit servir trois entrées :
  - une page récupérée par `fetch_url` (couche 3, search-worker) ;
  - un document **uploadé manuellement** par l'utilisateur (cas des sociétés non cotées, où il n'y a
    ni IR public ni dépôt régulateur : le rapport de gestion arrive par un fichier) ;
  - n'importe quel texte long qu'un agent doit lire sans le repayer intégralement en tokens.

## Pourquoi la troncature en tête est indéfendable

Mesuré sur le 10-K NVDA FY2026 (2026-08-23) : 362 575 caractères de texte, et la concentration
client (« 22% of total revenue ») se trouve à la position 136 069, soit **37,5 % du document**. Un
plafond à 20 000 caractères en capte 5,5 % — la page de garde et le sommaire. Exa `/contents` tronque
en tête lui aussi : interrogé sur la même URL, il rend « Table of Contents / UNITED STATES SECURITIES
AND EXCHANGE COMMISSION ». Aucun des deux chemins n'atteignait le corps du dépôt.

Et le problème n'est pas réservé aux gros documents. Sur l'article CNBC de 12 189 caractères
effectivement utilisé par le worker, les éléments repris dans l'entrée retenue étaient à 44 %
(« Ironwood »), 62 % (« 30 % ») et 71 % (« Maia ») du texte : un plafond à 6 000 en aurait coupé
deux. La raison est structurelle — c'est un **comparatif** (Google, puis AWS, puis Meta, puis
Microsoft), donc l'information est distribuée par construction. Il n'existe pas de taille de
troncature défendable a priori : elle dépend du genre du document, que l'on ne connaît pas d'avance.

## Ce que la sélection par pertinence change

Elle est meilleure sur les **deux** axes à la fois, ce qui est rare et vaut d'être dit : on renvoie
MOINS de caractères (quelques milliers au lieu du plafond) tout en couvrant TOUT le document. Le
plafond arbitraire disparaît de lui-même, et avec lui le compromis pertinence/budget qui avait
conduit à `FETCH_URL_MAX_CHARS`.

## Dégradation

Trois niveaux, toujours **déclarés** dans le champ `mode` du retour (jamais silencieux, cf. #25) :
  `relevance` (embeddings bge-m3, nominal) → `lexical` (recouvrement de termes, si l'embedding est
  indisponible) → `head` (troncature en tête, dernier recours). L'appelant et le modèle savent
  toujours lequel a servi : un extrait `head` ne se lit pas comme un extrait `relevance`.
"""
from __future__ import annotations

import logging
import math
import re
from dataclasses import dataclass
from typing import Optional

from app.knowledge import embeddings

logger = logging.getLogger(__name__)

# Taille de chunk : assez large pour qu'un passage garde son contexte (un facteur de risque, un
# paragraphe de MD&A), assez courte pour que le vecteur reste discriminant. bge-m3 encaisse bien
# plus, mais un chunk trop long dilue le signal — c'est la même raison qui fait chunker un corpus.
_CHUNK_CHARS = 1200
_CHUNK_OVERLAP = 150      # évite qu'une phrase coupée en deux ne soit trouvable dans aucun chunk
_MAX_CHUNKS_EMBEDDED = 400  # garde-fou de coût : ~480 k caractères, au-delà on échantillonne
_MARKER_CHARS = 40          # coût d'un « [… N caractères omis …] », provisionné dans le budget

_SPLIT_PATTERN = re.compile(r"(?<=[.!?])\s+|\n{2,}")
_WORD = re.compile(r"[\w'’-]{3,}", re.UNICODE)


@dataclass
class Chunk:
    """Fragment de document, avec sa position — la position est rendue au modèle pour qu'il puisse
    dire *où* dans le document il a lu ce qu'il avance."""
    text: str
    start: int
    end: int
    score: float = 0.0


def chunk_text(text: str, *, target_chars: int = _CHUNK_CHARS, overlap: int = _CHUNK_OVERLAP) -> list[Chunk]:
    """Découpe en fragments qui respectent les frontières de phrase/paragraphe quand c'est possible.

    On ne coupe pas au caractère près : un chunk qui commence au milieu d'une phrase perd le sujet de
    cette phrase, et le vecteur qui en résulte parle d'autre chose que le passage réel.
    """
    text = text or ""
    if not text.strip():
        return []
    if len(text) <= target_chars:
        return [Chunk(text=text, start=0, end=len(text))]

    # Frontières candidates (fin de phrase, saut de paragraphe), positions absolues.
    bounds = [0] + [m.end() for m in _SPLIT_PATTERN.finditer(text)] + [len(text)]
    chunks: list[Chunk] = []
    start = 0
    while start < len(text):
        hard_end = min(start + target_chars, len(text))
        # Dernière frontière avant la limite dure ; à défaut, la limite dure elle-même.
        candidates = [b for b in bounds if start + target_chars // 3 < b <= hard_end]
        end = candidates[-1] if candidates else hard_end
        fragment = text[start:end].strip()
        if fragment:
            chunks.append(Chunk(text=fragment, start=start, end=end))
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return chunks


def _cosine(a: list[float], b: list[float]) -> float:
    """Cosinus en Python pur — 1024 dimensions sur quelques centaines de chunks, c'est négligeable,
    et cela évite d'ajouter numpy aux dépendances de l'image (VPS contraint)."""
    num = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return num / (na * nb) if na and nb else 0.0


def _lexical_scores(chunks: list[Chunk], query: str) -> None:
    """Repli sans embedding : recouvrement de termes, normalisé par la longueur du chunk.

    Volontairement rustique. Ce n'est PAS un co-classement avec le vectoriel (convention #22 : les
    fusionner dégrade le résultat) — c'est ce qui reste quand l'embedding est indisponible, et il
    vaut mieux qu'une troncature en tête, qui elle ne regarde pas la question du tout.
    """
    terms = {w.lower() for w in _WORD.findall(query)}
    if not terms:
        for c in chunks:
            c.score = 0.0
        return
    for c in chunks:
        words = [w.lower() for w in _WORD.findall(c.text)]
        if not words:
            c.score = 0.0
            continue
        hits = sum(1 for w in words if w in terms)
        distinct = len({w for w in words if w in terms})
        c.score = (hits / len(words)) + 0.1 * distinct


async def _embed_scores(chunks: list[Chunk], query: str) -> bool:
    """Classe les chunks par similarité cosinus avec la question. Rend False si indisponible."""
    if not embeddings.is_configured() or not chunks:
        return False
    sample = chunks[:_MAX_CHUNKS_EMBEDDED]
    try:
        qvec = await embeddings.embed_one(query, is_query=True)
        vecs = await embeddings.embed_texts([c.text for c in sample])
    except Exception as e:  # noqa: BLE001
        logger.warning("document_search: embedding indisponible (%s) — repli lexical", e)
        return False
    if len(vecs) != len(sample):
        logger.warning("document_search: %d vecteurs pour %d chunks — repli lexical", len(vecs), len(sample))
        return False
    for c, v in zip(sample, vecs):
        c.score = _cosine(qvec, v)
    for c in chunks[_MAX_CHUNKS_EMBEDDED:]:
        c.score = 0.0
    return True


def _assemble(selected: list[Chunk], total_chars: int) -> str:
    """Recompose les passages retenus **dans l'ordre du document**, avec des marqueurs de coupure.

    L'ordre du document, pas celui des scores : un extrait remonté par pertinence mais lu dans le
    désordre suggère une continuité qui n'existe pas. Les marqueurs `[…]` disent explicitement qu'il
    manque du texte entre deux passages — sans quoi le modèle lirait deux paragraphes distants comme
    s'ils se suivaient, et en tirerait des rapprochements que le document ne fait pas.
    """
    ordered = sorted(selected, key=lambda c: c.start)
    parts: list[str] = []
    cursor = 0
    for c in ordered:
        if c.start > cursor:
            parts.append(f"\n\n[… {c.start - cursor:,} caractères omis …]\n\n".replace(",", " "))
        parts.append(c.text)
        cursor = c.end
    if cursor < total_chars:
        parts.append(f"\n\n[… {total_chars - cursor:,} caractères omis …]".replace(",", " "))
    return "".join(parts).strip()


async def select_relevant(
    text: str,
    query: Optional[str],
    *,
    max_chars: int,
    min_score: float = 0.0,
) -> dict[str, object]:
    """Rend les passages de `text` qui répondent à `query`, dans la limite de `max_chars`.

    Retour : `{mode, text, chars_total, chars_returned, chunks_total, chunks_selected, spans}`.
    `mode` ∈ `relevance` | `lexical` | `head` | `whole` — toujours renseigné, pour que l'appelant et
    le modèle sachent comment le texte a été obtenu.
    """
    text = text or ""
    total = len(text)
    if total <= max_chars:
        return {
            "mode": "whole", "text": text, "chars_total": total, "chars_returned": total,
            "chunks_total": 1, "chunks_selected": 1, "spans": [{"start": 0, "end": total}],
        }

    if not (query or "").strip():
        # Sans question, il n'y a pas de pertinence à mesurer : la tête est le seul choix honnête.
        return {
            "mode": "head", "text": text[:max_chars], "chars_total": total,
            "chars_returned": max_chars, "chunks_total": 1, "chunks_selected": 1,
            "spans": [{"start": 0, "end": max_chars}],
        }

    chunks = chunk_text(text)
    if not chunks:
        return {
            "mode": "head", "text": text[:max_chars], "chars_total": total,
            "chars_returned": min(total, max_chars), "chunks_total": 0, "chunks_selected": 0,
            "spans": [],
        }

    mode = "relevance" if await _embed_scores(chunks, query) else "lexical"
    if mode == "lexical":
        _lexical_scores(chunks, query)

    # Chaque passage retenu coûte, en plus de son texte, un marqueur de coupure. On le provisionne,
    # sinon le texte assemblé dépasse le budget annoncé — mesuré : 20 333 caractères rendus pour un
    # plafond de 20 000 sur le 10-K NVDA (19 passages × ~35 car. de marqueur).
    budget, selected = max_chars, []
    for c in sorted(chunks, key=lambda c: c.score, reverse=True):
        if c.score <= min_score and selected:
            break
        cost = len(c.text) + _MARKER_CHARS
        if cost > budget:
            continue
        selected.append(c)
        budget -= cost
        if budget < _CHUNK_CHARS // 2:
            break

    if not selected:  # tous les chunks dépassent le budget : on rabat sur la tête, en le disant
        return {
            "mode": "head", "text": text[:max_chars], "chars_total": total,
            "chars_returned": max_chars, "chunks_total": len(chunks), "chunks_selected": 0,
            "spans": [{"start": 0, "end": max_chars}],
        }

    assembled = _assemble(selected, total)
    logger.info(
        "document_search[%s]: %d car. → %d chunk(s) sur %d, %d car. rendus (meilleur score %.3f)",
        mode, total, len(selected), len(chunks), len(assembled),
        max(c.score for c in selected),
    )
    return {
        "mode": mode,
        "text": assembled,
        "chars_total": total,
        "chars_returned": len(assembled),
        "chunks_total": len(chunks),
        "chunks_selected": len(selected),
        "spans": [
            {"start": c.start, "end": c.end, "score": round(c.score, 4)}
            for c in sorted(selected, key=lambda c: c.start)
        ],
    }
