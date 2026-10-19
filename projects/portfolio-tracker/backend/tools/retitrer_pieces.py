"""Rattrapage des titres (et de la 1ʳᵉ ligne du contenu pour les relevés d'appariement) des pièces
EN VIGUEUR (`superseded_by IS NULL`) touchées par le défaut mesuré le 2026-10-18.

Arbitrage de l'utilisateur (2026-10-18) : « le titre d'une pièce dit ce qu'elle CONTIENT, jamais ce
qu'on lui a demandé ». NVDA ma_1 #1475 a été fondée à tort sur #1429, titrée « … sur les exercices
2022 à 2026 — EXERCICE CLOS LE 2026-01-25 » alors que son expression (offsets `[0]`) ne lisait qu'UN
exercice : le titre affirmait la métrique DEMANDÉE (`libelle` de la ligne de plan), pas ce que
l'expression avait LU. Même défaut, forme « Lecture du collecteur — {titre rédigé par le modèle} » :
une AFFIRMATION du modèle, pas le nom du document lu.

CE QUE CET OUTIL RECALCULE, ET PAR QUELLES FONCTIONS (PAS DE JUMEAU) — détenteurs importés, jamais
réimplémentés :
  · un RELEVÉ D'APPARIEMENT (`content_structured` porte `appariement_statut`, détenteur unique de la
    forme : `app.knowledge.appariement_feed`) → les postes réellement lus
    (`_postes_libelles`) et la ou les périodes réellement lues (`_periode_reellement_lue`),
    reconstruits depuis `content_structured["ingredients"]`/`["period"]` déjà en base — jamais
    recalculés (aucun appel réseau, aucune ré-évaluation de la formule) ;
  · une LECTURE DU COLLECTEUR (`est_lecture_du_collecteur`, #126 : `source_type='agent_synthesis'`
    + tag `lecture_du_collecteur`) → `app.agents.v2.worker.titre_de_fiche(url)`, l'URL étant RELUE
    dans le contenu de la lecture elle-même (seul endroit où le document qu'elle commente est
    encore nommé — `_lecture_du_collecteur` l'y a écrit littéralement : « … du document {url} : »).
Toute autre pièce (socle des comptes, financials_feed, valuation_feed, base_rate_corpus, une fiche à
extraits déjà titrée par `titre_de_fiche`, un aveu `llm_memory`…) N'EST PAS CONCERNÉE : son titre
dépendait déjà uniquement de son contenu — elle n'apparaît ni dans le décompte ni dans les exemples.

MODE PAR DÉFAUT = À BLANC (AUCUNE écriture) : imprime, par pièce retitrée, l'ancien → nouveau titre,
le décompte par producteur, et toute pièce que l'outil n'a pas su retitrer (et pourquoi — jamais un
silence, même geste que le reste du maillon, #25).

`--appliquer` ÉCRIT dans une transaction (ROLLBACK automatique sur toute erreur). Interdit pour ce
lot (la spec qui a commandé cet outil l'interdit explicitement) — ne lancer QUE le mode à blanc.

EMBEDDING : `store_knowledge`/`entry_text` embeddent `title + content + tags`
(`app/knowledge/service.py` l.252, `app/knowledge/embeddings.py` l.67-80) — un titre (et, pour un
relevé, une 1re ligne de contenu) changés SANS ré-embedding laissent un vecteur DÉCALÉ : la
recherche vectorielle rapprocherait la pièce retitrée de requêtes qui correspondaient à son ANCIEN
texte. `--appliquer` ne calcule donc PAS de nouvel embedding (aucun appel API, cf. interdits) : il
met `embedding = NULL` sur chaque pièce retitrée, et c'est `backfill_embeddings`
(`app/knowledge/embeddings.py`, déjà idempotent sur `embedding IS NULL`) qui le rattrape — à lancer
SÉPARÉMENT, explicitement, après relecture du mode à blanc.

    bash tools/retitrer_pieces.sh                    # à blanc, toutes les pièces en vigueur
    bash tools/retitrer_pieces.sh --ticker NVDA       # restreint à un émetteur
    bash tools/retitrer_pieces.sh --exemples 20       # plus d'exemples affichés (défaut 10)
    bash tools/retitrer_pieces.sh --appliquer         # ÉCRIT — n'a volontairement pas été lancé

Codes : 0 = mesure dressée (à blanc) ou écriture faite (`--appliquer`) · 2 = pas mesurable.
"""
from __future__ import annotations

import asyncio
import os
import re
import sys
from types import SimpleNamespace
from typing import Any, Optional

from app.agents.v2.worker import titre_de_fiche
from app.contracts.worker_delegation_schema import est_lecture_du_collecteur
from app.db.database import close_pool, get_db_session, init_pool
from app.knowledge.appariement_feed import (
    PointRetenu,
    _periode_reellement_lue,
    _postes_libelles,
)

L = 78

_SQL = """
    SELECT ke.id, ke.ticker_id, t.ticker_symbol AS symbole, ke.source_type,
           ke.title, ke.content, ke.content_structured, ke.source_url, ke.tags
    FROM knowledge_entries ke
    JOIN tickers t ON t.id = ke.ticker_id
    WHERE ke.superseded_by IS NULL
    {filtre}
    ORDER BY ke.id
"""

# Motif ÉCRIT par `_lecture_du_collecteur` (app/agents/v2/worker.py) — littéral, pas deviné : c'est
# le seul endroit où le document commenté par une lecture est encore nommé.
_RE_DOCUMENT = re.compile(r"du document (\S+) :")


def _point_depuis_ingredient(ing: dict[str, Any]) -> PointRetenu:
    """Un `PointRetenu` reconstruit depuis UN ingrédient du `content_structured` déjà en base.

    `duree_jours` et `filed` ne sont pas portés par le structuré (ils ne servaient qu'à la ligne de
    détail, pas au titre) : `None`, sans conséquence — `_postes_libelles`/`_periode_reellement_lue`
    ne lisent que `concept`, `offset`, `end`, `cadrage`.
    """
    return PointRetenu(
        concept=str(ing["concept"]), valeur=float(ing["value"]), unite=str(ing["unit"]),
        end=str(ing["end"]), cadrage=str(ing["cadrage"]), duree_jours=None,
        form=ing.get("form"), accn=ing.get("accn"), offset=ing.get("offset", 0),
    )


def _retitrer_appariement(row) -> Optional[tuple[str, str]]:
    """(nouveau_titre, nouveau_contenu) pour un relevé d'appariement — ou None si la forme stockée
    est illisible (jamais une exception qui tue le lot : un refus NOMMÉ, même geste que le
    producteur, #25)."""
    cs = row["content_structured"] or {}
    ingredients = cs.get("ingredients")
    periode = cs.get("period")
    if not ingredients or periode is None:
        return None
    try:
        points = {
            (str(ing["concept"]), ing.get("offset", 0)): _point_depuis_ingredient(ing)
            for ing in ingredients
        }
    except (KeyError, TypeError, ValueError):
        return None

    postes = _postes_libelles(points)
    periode_titre = _periode_reellement_lue(points, str(periode))
    symbole = row["symbole"] or row["ticker_id"]
    nouveau_titre = f"{postes} — {periode_titre} ({symbole})"

    ancien_contenu = row["content"] or ""
    premiere, sep_ligne, reste = ancien_contenu.partition("\n")
    _prefixe, sep_valeur, valeur_part = premiere.partition(" : ")
    if not sep_valeur:
        # La 1re ligne n'a pas la forme attendue (`{libelle} — … : {valeur}.`) : on retitre quand
        # même la pièce (le titre, lui, est toujours reconstructible), mais le contenu est laissé
        # intact plutôt que d'y écrire un prefixe hors forme — nommé dans le rapport, pas un silence.
        return nouveau_titre, ancien_contenu
    nouvelle_tete = f"{postes} — {row['ticker_id']} ({symbole}), {periode_titre} : {valeur_part}"
    nouveau_contenu = nouvelle_tete + (("\n" + reste) if sep_ligne else "")
    return nouveau_titre, nouveau_contenu


def _retitrer_lecture(row) -> Optional[str]:
    """Le nouveau titre d'une lecture du collecteur — ou None si le document n'est pas relisible
    dans son propre contenu (forme inattendue, jamais un silence)."""
    m = _RE_DOCUMENT.search(row["content"] or "")
    if not m:
        return None
    url = m.group(1)
    if url in ("None", ""):
        url = None
    return f"Lecture du collecteur — {titre_de_fiche(url)}"


async def main() -> int:
    appliquer = "--appliquer" in sys.argv
    ticker = None
    if "--ticker" in sys.argv:
        ticker = sys.argv[sys.argv.index("--ticker") + 1]
    n_exemples = 10
    if "--exemples" in sys.argv:
        n_exemples = int(sys.argv[sys.argv.index("--exemples") + 1])

    if not os.environ.get("DATABASE_URL"):
        print("DATABASE_URL manquante", file=sys.stderr)
        return 2

    await init_pool(os.environ["DATABASE_URL"])
    try:
        async with get_db_session() as conn:
            filtre = "AND ke.ticker_id = $1" if ticker else ""
            sql = _SQL.format(filtre=filtre)
            rows = await conn.fetch(sql, *([ticker] if ticker else []))
    except Exception:
        import traceback
        traceback.print_exc()
        await close_pool()
        return 2

    decompte: dict[str, int] = {}
    non_retitrees: list[str] = []
    a_ecrire: list[tuple[int, str, Optional[str]]] = []
    exemples: list[str] = []
    exemple_1429: Optional[str] = None

    for row in rows:
        cs = row["content_structured"]
        if isinstance(cs, dict) and "appariement_statut" in cs:
            producteur = "appariement_feed (relevé)"
            res = _retitrer_appariement(row)
            if res is None:
                non_retitrees.append(
                    f"#{row['id']} ({row['ticker_id']}) [{producteur}] — content_structured "
                    "sans `ingredients`/`period` lisibles")
                continue
            nouveau_titre, nouveau_contenu = res
            if nouveau_titre == row["title"] and nouveau_contenu == (row["content"] or ""):
                continue  # déjà au nouveau format — idempotent
            decompte[producteur] = decompte.get(producteur, 0) + 1
            ligne = (f"#{row['id']} ({row['ticker_id']}) [{producteur}]\n"
                     f"    ancien  → {row['title']!r}\n"
                     f"    nouveau → {nouveau_titre!r}")
            if row["id"] == 1429:
                exemple_1429 = ligne
            elif len(exemples) < n_exemples:
                exemples.append(ligne)
            a_ecrire.append((row["id"], nouveau_titre, nouveau_contenu))
            continue

        if est_lecture_du_collecteur(SimpleNamespace(source_type=row["source_type"], tags=row["tags"])):
            producteur = "worker._lecture_du_collecteur"
            nouveau_titre = _retitrer_lecture(row)
            if nouveau_titre is None:
                non_retitrees.append(
                    f"#{row['id']} ({row['ticker_id']}) [{producteur}] — le document commenté "
                    "n'est pas relisible dans le contenu de la lecture")
                continue
            if nouveau_titre == row["title"]:
                continue  # déjà au nouveau format
            decompte[producteur] = decompte.get(producteur, 0) + 1
            if len(exemples) < n_exemples:
                exemples.append(f"#{row['id']} ({row['ticker_id']}) [{producteur}]\n"
                                 f"    ancien  → {row['title']!r}\n"
                                 f"    nouveau → {nouveau_titre!r}")
            a_ecrire.append((row["id"], nouveau_titre, None))
        # sinon : pas concerné (socle/financials/valuation/base_rate_corpus/fiche à extraits/aveu
        # llm_memory…) — son titre est déjà composé depuis son contenu, inchangé.

    print(f"\n{'─' * L}\nRATTRAPAGE DES TITRES — {len(rows)} pièce(s) EN VIGUEUR examinée(s)"
          + (f" (ticker={ticker})" if ticker else "") + f"\n{'─' * L}")
    print(f"  à retitrer : {len(a_ecrire)}")
    for p in sorted(decompte):
        print(f"    {p:<32} {decompte[p]}")
    print(f"  non concernées (titre déjà composé depuis le contenu) : "
          f"{len(rows) - len(a_ecrire) - len(non_retitrees)}")
    if non_retitrees:
        print(f"  NON RETITRÉES (motif) : {len(non_retitrees)}")
        for m in non_retitrees:
            print(f"    - {m}")

    print(f"\n{'─' * L}\n#1429 (NVDA, le cas qui a motivé ce lot)\n{'─' * L}")
    print(exemple_1429 if exemple_1429 is not None else "  #1429 absente du périmètre interrogé"
          + (" (filtrée par --ticker)" if ticker and ticker != "NVDA" else " ou déjà au nouveau format"))

    print(f"\n{'─' * L}\nEXEMPLES ({len(exemples)})\n{'─' * L}")
    for e in exemples:
        print(e)

    if not appliquer:
        print(f"\n{'─' * L}\nMode À BLANC — RIEN n'a été écrit.\n{'─' * L}")
        await close_pool()
        return 0

    print(f"\n{'─' * L}\n--appliquer : écriture de {len(a_ecrire)} pièce(s) en transaction…\n{'─' * L}")
    try:
        async with get_db_session() as conn:
            async with conn.transaction():
                for entry_id, nouveau_titre, nouveau_contenu in a_ecrire:
                    # `embedding = NULL` : `store_knowledge`/`entry_text` embeddent `title + content
                    # + tags` (app/knowledge/service.py:252, app/knowledge/embeddings.py:67-80). Un
                    # titre/contenu changé sans ré-embedding laisse un vecteur DÉCALÉ — on ne le
                    # recalcule PAS ici (aucun appel API, cf. interdits) : on le met à NULL, et
                    # `backfill_embeddings` (déjà idempotent sur `embedding IS NULL`) le rattrape
                    # dans un second passage, explicitement lancé, hors de cet outil.
                    if nouveau_contenu is not None:
                        await conn.execute(
                            "UPDATE knowledge_entries SET title=$1, content=$2, embedding=NULL "
                            "WHERE id=$3",
                            nouveau_titre, nouveau_contenu, entry_id)
                    else:
                        await conn.execute(
                            "UPDATE knowledge_entries SET title=$1, embedding=NULL WHERE id=$2",
                            nouveau_titre, entry_id)
        print(f"{len(a_ecrire)} pièce(s) retitrée(s) ; leur embedding est à NULL — lancer "
              f"`backfill_embeddings` séparément pour le recalculer.")
    finally:
        await close_pool()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
