"""Le BOUCLAGE comité → collecte (chantier v3, lot 5) — ce qui ferme la figure #71.

LE TROU QUE CE MODULE COMBLE
----------------------------
Le manager RENVOIE une réponse insuffisante et `persist_review` écrit un `framework_mandate` OUVERT
(§3.1). Jusqu'ici, PERSONNE ne le relisait en production : `read_open_mandates`/`serve_mandate`
n'avaient d'appelant que dans l'outil d'acceptation (mesuré le 2026-09-25 : 0 appelant dans `app/`).
Un décideur sans producteur ne décide jamais — la boucle que toute la v3 devait fermer restait
ouverte. Ce module est le producteur.

CE QU'IL FAIT, ET L'ARBITRAGE UTILISATEUR QUI LE GOUVERNE (2026-09-25)
---------------------------------------------------------------------
Un fonds ne reste pas en salle de comité pendant que l'analyste cherche : il RECONVOQUE. Donc le
bouclage est un PASSAGE (cadence « cycle suivant »), pas une boucle interne — il produit une note
ARRÊTÉE où l'utilisateur peut intervenir en connaissance des forces ET des limites du dossier.

Et l'analyste refait les recherches manquantes PAR LE MÊME PROCESSUS que l'analyse initiale, restreint
aux questions renvoyées : « il faut utiliser le même processus que l'analyse initiale avec les
nouvelles questions pour éviter de créer des chemins de recherche parallèles » (#46). D'où
`executer_collecte_framework(..., questions=scope)` — le traducteur, le pont et la collecte sont les
mêmes, scopés. AUCUN nouveau chemin de collecte, AUCUN nouvel input du search-worker (le mandat
re-rentre par le traducteur, pas par un prompt élargi — les #19/#39 ne sont donc PAS touchés).

LA NOTE HONNÊTE — QUATRE SORTS (voir `contracts/bouclage_schema.py`)
-------------------------------------------------------------------
Après le passage, chaque renvoi rejoué reçoit son SORT, DÉRIVÉ (aucun appel de modèle) :
`acquis` / `collecte_insuffisante` / `mandat_non_executable` / `classe_sans_suite`. La distinction
`collecte_insuffisante` (on a su où chercher, la source a déçu) vs `mandat_non_executable` (le
traducteur n'a même pas su en faire une ligne) est celle que l'utilisateur a exigée : « distinguer si
la collecte est insuffisante ou si le mandat n'était pas clair ». Elle se lit sur l'origine des
mandats du collecteur (`echec_collecte` vs `inobtenable`), pas sur un jugement.

⚠️ ATOMICITÉ (#35). Comme la chaîne (`executer_chaine`), chaque écriture liée est enveloppée dans sa
propre transaction ; un bouclage interrompu laisse un mandat encore ouvert, qu'un passage suivant
re-sert (idempotence de `id_du_mandat_ouvert`).
"""
from __future__ import annotations

from typing import Any, Optional

import asyncpg

from app.agents.v2.analyste import repondre
from app.agents.v2.collecte_executor import executer_collecte_framework
from app.agents.v2.dossier import charger_dossier
from app.agents.v2.framework_persist import persist_answer, read_dispenses
from app.agents.v2.frameworks import load_frameworks
from app.agents.v2.manager_persist import (
    id_du_mandat_ouvert,
    read_open_mandates,
    serve_mandate,
)
from app.contracts.bouclage_schema import CompteRenduBouclage, MandatBoucle, SortBouclage
from app.contracts.framework_answer_schema import Statut
from app.db.database import get_db_session

__all__ = ["classer_sort", "boucler_renvois", "PLAFOND_DOSSIER"]

# Même plafond que la chaîne et l'acceptation analyste — et pour la même raison (un dossier entier
# ferait un prompt de plusieurs centaines de milliers de tokens). La troncature est DITE (bilan du
# dossier).
PLAFOND_DOSSIER = 40


def classer_sort(
    statut_avant: Statut,
    statut_apres: Statut,
    *,
    a_tente_collecte: bool,
    dispensee: bool,
) -> SortBouclage:
    """DÉTENTEUR UNIQUE (#46) du SORT d'un renvoi rejoué. Aucun appel de modèle : une fonction pure
    des faits déjà mesurés (le statut avant/après `serve_mandate`, l'origine de la collecte, la
    présence d'une dispense).

    L'ordre des branches EST la doctrine :
      1. la question est FONDÉE (statut_apres ≠ non_fondable) → `acquis`, quoi qu'il ait fallu — savoir
         qu'une question est `sans_objet` répond aussi au renvoi.
      2. le comité a ACCEPTÉ le trou (dispense) → `classe_sans_suite`, même si la collecte a tenté :
         c'est une décision de comité, elle prime sur le résultat de la recherche.
      3. on a TENTÉ la collecte (un lien produit, ou une source qui a déçu) → `collecte_insuffisante` :
         « cherché, la donnée n'est pas publiée ».
      4. sinon → `mandat_non_executable` : le traducteur n'a pas su en faire une ligne de plan, le
         problème est la QUESTION, pas la recherche.
    """
    if statut_apres != "non_fondable":
        return "acquis"
    if dispensee:
        return "classe_sans_suite"
    if a_tente_collecte:
        return "collecte_insuffisante"
    return "mandat_non_executable"


# Le motif de chaque sort — la moitié « honnête » de la note. Un par sort, DISTINCTS (un lecteur
# doit pouvoir dire POURQUOI, #25). Ils vivent à côté de `classer_sort`, leur unique producteur.
_MOTIF_DU_SORT: dict[SortBouclage, str] = {
    "acquis": "la re-collecte a fondé la question (statut passé au-dessus de non_fondable)",
    "collecte_insuffisante": "recherche menée par le processus normal, mais la donnée n'est pas "
                             "publiée (source pressentie décevante) : limite du monde, pas de l'outil",
    "mandat_non_executable": "aucune source connue ne produit cet ingrédient pour cet émetteur : "
                             "c'est la QUESTION qu'il faut réécrire, pas la recherche à relancer",
    "classe_sans_suite": "le comité a accepté le trou — une dispense active couvre la question",
}


def _a_tente_collecte_par_question(rapport: dict[str, Any]) -> dict[str, bool]:
    """Par question renvoyée : la re-collecte a-t-elle TENTÉ quelque chose d'exécutable ?

    OUI si un lien a été produit (une entry écrite) OU si un mandat `echec_collecte` a été ouvert (une
    source pressentie qui a déçu — on a su où chercher). NON si la question n'a que des mandats
    `inobtenable` : le traducteur n'a même pas su en faire une ligne. C'est le discriminant #54
    (`collecte_insuffisante` vs `mandat_non_executable`).
    """
    tente: dict[str, bool] = {}
    for lien in rapport["liens"]:
        tente[lien["question_id"]] = True
    for mandat in rapport["mandats"]:
        qid = mandat["question_id"]
        if mandat["origine"] == "echec_collecte":
            tente[qid] = True
        else:  # inobtenable
            tente.setdefault(qid, False)
    return tente


async def _statuts_avant(
    conn: asyncpg.Connection, *, ticker_id: str, framework_version: str, analyste: str,
    questions: frozenset[str],
) -> dict[str, Statut]:
    """Le statut COURANT de la réponse de cet analyste, question par question, AVANT le bouclage.

    Une question jamais répondue (mandat « question applicable sans réponse ») n'a pas de ligne : son
    statut avant est `non_fondable` — elle n'était pas fondée, et le dire est plus honnête que de
    prétendre un état inexistant. La sélection `superseded_by IS NULL` appartient à la table (A1)."""
    rows = await conn.fetch(
        "SELECT question_id, statut FROM framework_answers "
        "WHERE ticker_id = $1 AND framework_version = $2 AND analyste = $3 "
        "AND superseded_by IS NULL AND question_id = ANY($4::text[])",
        ticker_id, framework_version, analyste, list(questions))
    return {row["question_id"]: row["statut"] for row in rows}


async def boucler_renvois(
    ticker_id: str,
    framework_id: str,
    archetype: str,
    *,
    analyste: str,
    fichier=None,
    plafond: int = PLAFOND_DOSSIER,
) -> CompteRenduBouclage:
    """UN passage de bouclage : lire les renvois ouverts, refaire la recherche PAR LE MÊME PROCESSUS
    (scopé), re-répondre, servir les mandats, rendre la note honnête.

    ⚠️ DÉPENSE et ÉCRIT en prod (collecte scopée, réponses persistées, mandats servis). Ne PAS jouer
    dans `portfolio-backend` (il porte le code déployé). Rend un `CompteRenduBouclage` NON persisté
    (assemblé au run, recalculable — #53/#77).
    """
    fichier = fichier or load_frameworks()
    version = fichier.schema_version

    # 1. LIRE les renvois ouverts. Rien à boucler → note vide honnête (0 lu), aucune dépense (#40).
    async with get_db_session() as conn:
        ouverts = await read_open_mandates(
            conn, ticker_id=ticker_id, framework_id=framework_id, framework_version=version)
    if not ouverts:
        return CompteRenduBouclage(
            ticker_id=ticker_id, framework_id=framework_id, framework_version=version,
            mandats_lus=0, boucles=[])

    scope = frozenset(m.question_id for m in ouverts)

    async with get_db_session() as conn:
        statuts_avant = await _statuts_avant(
            conn, ticker_id=ticker_id, framework_version=version, analyste=analyste, questions=scope)

    # 2. RE-COLLECTE scopée — le MÊME processus, restreint aux questions renvoyées (arbitrage 2026-09-25).
    rapport = await executer_collecte_framework(
        ticker_id, framework_id, archetype, questions=scope)
    tente = _a_tente_collecte_par_question(rapport)

    # 3. RE-ANALYSE sur le dossier ENRICHI. `repondre` répond à tout ; on ne retient QUE les questions
    #    renvoyées — les réponses sont indépendantes par question, re-calculer les autres ne les change
    #    pas et on ne les re-persiste pas (le comité n'a renvoyé qu'elles).
    async with get_db_session() as conn:
        dossier = await charger_dossier(
            conn, ticker_id=ticker_id, framework_id=framework_id,
            framework_version=version, plafond=plafond)
    resultat = await repondre(
        ticker_id, framework_id, archetype,
        analyste=analyste, entries=dossier.entries, fichier=fichier)
    reponses = {a.question_id: a for a in resultat.answers if a.question_id in scope}

    # 4. Persister les réponses renvoyées + lire les dispenses (le comité a-t-il classé sans suite ?).
    async with get_db_session() as conn:
        dispenses = await read_dispenses(
            conn, ticker_id=ticker_id, framework_id=framework_id, framework_version=version)
        async with conn.transaction():
            for a in reponses.values():
                await persist_answer(conn, a)

    # 5. SERVIR chaque mandat et ASSEMBLER la note honnête, sort par sort.
    boucles: list[MandatBoucle] = []
    async with get_db_session() as conn:
        for m in ouverts:
            qid = m.question_id
            a = reponses.get(qid)
            if a is None:
                # La question n'est plus applicable / pas re-répondue : hors compte rendu. Servir sur
                # rien serait un faux vert (#54) — on préfère la dire absente en la taisant.
                continue
            mandat_id = await id_du_mandat_ouvert(
                conn, ticker_id=ticker_id, framework_id=framework_id,
                framework_version=version, question_id=qid)
            if mandat_id is None:
                continue  # servi entre-temps par un autre passage
            statut_avant = statuts_avant.get(qid, "non_fondable")
            statut_apres: Statut = a.statut
            entry_ids = sorted({lien["entry_id"] for lien in rapport["liens"]
                                if lien["question_id"] == qid})
            async with conn.transaction():
                await serve_mandate(
                    conn, mandat_id, statut_avant=statut_avant, statut_apres=statut_apres,
                    entry_ids_produits=entry_ids)
            sort = classer_sort(
                statut_avant, statut_apres,
                a_tente_collecte=tente.get(qid, False), dispensee=qid in dispenses)
            boucles.append(MandatBoucle(
                question_id=qid, mandat_id=mandat_id, sort=sort,
                statut_avant=statut_avant, statut_apres=statut_apres,
                entry_ids_produits=entry_ids, motif=_MOTIF_DU_SORT[sort]))

    return CompteRenduBouclage(
        ticker_id=ticker_id, framework_id=framework_id, framework_version=version,
        mandats_lus=len(ouverts), boucles=boucles)
