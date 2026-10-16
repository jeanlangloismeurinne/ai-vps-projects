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


def _lexical_score_list(chunks: list[Chunk], query: str) -> list[float]:
    """Comme `_lexical_scores`, mais REND les scores au lieu de les écrire sur les chunks — il en
    faut deux listes indépendantes quand un même chunk est noté à la fois contre `query` et contre
    `focus` (sélection par pertinence, §12 du prompt search-worker) : écrire sur `c.score` à deux
    reprises écraserait la première notation.
    """
    terms = {w.lower() for w in _WORD.findall(query)}
    if not terms:
        return [0.0] * len(chunks)
    scores: list[float] = []
    for c in chunks:
        words = [w.lower() for w in _WORD.findall(c.text)]
        if not words:
            scores.append(0.0)
            continue
        hits = sum(1 for w in words if w in terms)
        distinct = len({w for w in words if w in terms})
        scores.append((hits / len(words)) + 0.1 * distinct)
    return scores


def _lexical_scores(chunks: list[Chunk], query: str) -> None:
    """Repli sans embedding : recouvrement de termes, normalisé par la longueur du chunk.

    Volontairement rustique. Ce n'est PAS un co-classement avec le vectoriel (convention #22 : les
    fusionner dégrade le résultat) — c'est ce qui reste quand l'embedding est indisponible, et il
    vaut mieux qu'une troncature en tête, qui elle ne regarde pas la question du tout.
    """
    for c, s in zip(chunks, _lexical_score_list(chunks, query)):
        c.score = s


async def _embed_scores(chunks: list[Chunk], queries: list[str]) -> Optional[list[list[float]]]:
    """Classe les chunks par similarité cosinus avec CHAQUE requête de `queries`.

    Les chunks ne sont embeddés qu'UNE fois quel que soit le nombre de requêtes ; les requêtes partent
    dans leur propre appel, avec l'instruction de requête (`is_query=True`) que certains modèles exigent.

    Rend `None` si l'embedding est indisponible (repli lexical), sinon une matrice
    `[query_idx][chunk_idx]` de scores cosinus.
    """
    if not embeddings.is_configured() or not chunks:
        return None
    sample = chunks[:_MAX_CHUNKS_EMBEDDED]
    try:
        qvecs = await embeddings.embed_texts(list(queries), is_query=True)
        sample_vecs = await embeddings.embed_texts([c.text for c in sample])
    except Exception as e:  # noqa: BLE001
        logger.warning("document_search: embedding indisponible (%s) — repli lexical", e)
        return None
    if len(qvecs) != len(queries) or len(sample_vecs) != len(sample):
        logger.warning("document_search: %d+%d vecteurs pour %d requête(s) et %d chunk(s) — repli lexical",
                       len(qvecs), len(sample_vecs), len(queries), len(sample))
        return None
    pad = [0.0] * (len(chunks) - len(sample))
    return [[_cosine(qv, v) for v in sample_vecs] + pad for qv in qvecs]


def _allouer_par_classements(
    rankings: list[tuple[str, list[tuple[Chunk, float]]]],
    *,
    max_chars: int,
    min_score: float,
) -> tuple[list[Chunk], dict[int, str], dict[int, float]]:
    """Alloue le budget en ALTERNANT entre les classements — jamais en fusionnant leurs scores en un
    seul (#22 : un co-classement dégrade le résultat mesuré). À chaque tour, chaque classement actif
    cède son prochain chunk NON ENCORE retenu qui rentre dans le budget restant ; un chunk sous
    `min_score` désactive SON classement, pas les autres (chaque file a sa propre pertinence) ; le
    budget global s'arrête comme la sélection à un seul classement (`_CHUNK_CHARS // 2`).

    `rankings` : `[(label, chunks_triés_par_score_desc), …]`. Rend les chunks retenus, et pour
    chacun (par `id()`) le label du classement qui l'a pris et le score associé.
    """
    budget = max_chars
    selected: list[Chunk] = []
    taken: set[int] = set()
    origine_de: dict[int, str] = {}
    score_de: dict[int, float] = {}
    pos = [0] * len(rankings)
    active = [True] * len(rankings)

    def essaie(i: int) -> bool:
        nonlocal budget
        label, ordered = rankings[i]
        while pos[i] < len(ordered):
            c, s = ordered[pos[i]]
            pos[i] += 1
            if id(c) in taken:
                continue  # déjà pris par l'autre classement — pas de double compte dans le budget
            if s <= min_score and selected:
                active[i] = False
                return False
            cost = len(c.text) + _MARKER_CHARS
            if cost > budget:
                continue  # ne rentre pas : on essaie le candidat suivant du MÊME classement
            selected.append(c)
            taken.add(id(c))
            origine_de[id(c)] = label
            score_de[id(c)] = s
            budget -= cost
            return True
        active[i] = False
        return False

    while any(active) and budget >= _CHUNK_CHARS // 2:
        progres = False
        for i in range(len(rankings)):
            if not active[i] or budget < _CHUNK_CHARS // 2:
                continue
            if essaie(i):
                progres = True
        if not progres:
            break  # aucun classement n'a pu placer de chunk ce tour-ci : on n'avancera plus
    return selected, origine_de, score_de


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
    focus: Optional[str] = None,
) -> dict[str, object]:
    """Rend les passages de `text` qui répondent à `query`, dans la limite de `max_chars`.

    `focus` (facultatif) est ce que l'APPELANT dit chercher DANS le document, dans les mots du
    document (un intitulé de section, un titre de tableau) — complément de `query`, jamais un
    remplacement. Raison d'être : une ligne de tableau (noms, chiffres) n'a presque aucune sémantique
    propre, seul l'intitulé qui la précède la rend trouvable par similarité — mesuré sur la table
    d'actionnariat NVIDIA, rang 126/288 sur le mandat, rang 4 sur le titre de section. Avec `focus`,
    deux classements (par `query`, par `focus`) se PARTAGENT le budget en alternance (#22 : jamais
    fusionnés en un score unique) plutôt que de se faire concurrence dans un seul tri.

    `focus` None/vide : comportement STRICTEMENT inchangé (aucune clé ajoutée au retour). `focus`
    donné : le retour ajoute `"focus"` et chaque span porte `"origine"` (`"question"` ou
    `"chercher"`), le score étant celui du classement qui l'a retenu.

    Retour : `{mode, text, chars_total, chars_returned, chunks_total, chunks_selected, spans[, focus]}`.
    `mode` ∈ `relevance` | `lexical` | `head` | `whole` — toujours renseigné, pour que l'appelant et
    le modèle sachent comment le texte a été obtenu.
    """
    text = text or ""
    total = len(text)
    query_clean = (query or "").strip()
    focus_clean = (focus or "").strip() or None

    if total <= max_chars:
        return {
            "mode": "whole", "text": text, "chars_total": total, "chars_returned": total,
            "chunks_total": 1, "chunks_selected": 1, "spans": [{"start": 0, "end": total}],
        }

    if not query_clean and not focus_clean:
        # Ni question ni consigne de recherche : pas de pertinence à mesurer, la tête est le seul
        # choix honnête.
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

    if focus_clean:
        return await _select_relevant_avec_focus(
            chunks, query_clean, focus_clean, text=text, total=total,
            max_chars=max_chars, min_score=min_score,
        )

    matrice = await _embed_scores(chunks, [query_clean])
    if matrice is not None:
        mode = "relevance"
        for c, s in zip(chunks, matrice[0]):
            c.score = s
    else:
        mode = "lexical"
        _lexical_scores(chunks, query_clean)

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


async def _select_relevant_avec_focus(
    chunks: list[Chunk],
    query_clean: str,
    focus_clean: str,
    *,
    text: str,
    total: int,
    max_chars: int,
    min_score: float,
) -> dict[str, object]:
    """Branche `focus` de `select_relevant` — deux classements, budget alloué en alternance.

    Séparée pour ne pas alourdir le chemin sans `focus` (qui doit rester identique bit à bit à avant
    son introduction) ; `query_clean` vide = « chercher seul » (un seul classement), cf. docstring de
    `select_relevant`.
    """
    requetes: list[tuple[str, str]] = []
    if query_clean:
        requetes.append(("question", query_clean))
    requetes.append(("chercher", focus_clean))

    matrice = await _embed_scores(chunks, [q for _, q in requetes])
    if matrice is not None:
        mode = "relevance"
        listes_scores = matrice
    else:
        mode = "lexical"
        listes_scores = [_lexical_score_list(chunks, q) for _, q in requetes]

    rankings = [
        (label, sorted(zip(chunks, scores), key=lambda t: t[1], reverse=True))
        for (label, _), scores in zip(requetes, listes_scores)
    ]
    selected, origine_de, score_de = _allouer_par_classements(
        rankings, max_chars=max_chars, min_score=min_score
    )

    if not selected:  # tous les chunks dépassent le budget : on rabat sur la tête, en le disant
        return {
            "mode": "head", "text": text[:max_chars], "chars_total": total,
            "chars_returned": max_chars, "chunks_total": len(chunks), "chunks_selected": 0,
            "spans": [{"start": 0, "end": max_chars}], "focus": focus_clean,
        }

    assembled = _assemble(selected, total)
    logger.info(
        "document_search[%s]: %d car. → %d chunk(s) sur %d, %d car. rendus (focus=%r)",
        mode, total, len(selected), len(chunks), len(assembled), focus_clean[:60],
    )
    return {
        "mode": mode,
        "text": assembled,
        "chars_total": total,
        "chars_returned": len(assembled),
        "chunks_total": len(chunks),
        "chunks_selected": len(selected),
        "focus": focus_clean,
        "spans": [
            {
                "start": c.start, "end": c.end,
                "score": round(score_de[id(c)], 4),
                "origine": origine_de[id(c)],
            }
            for c in sorted(selected, key=lambda c: c.start)
        ],
    }
