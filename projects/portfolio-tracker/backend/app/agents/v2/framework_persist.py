"""Persistance de la RÉPONSE et de la DISPENSE (chantier v3, lot 3 maillon 2 — migration 040).

L'ANALYSTE (`agents/v2/analyste.py`) et le pont (`agents/v2/frameworks.py:valider_pont_framework_answer`)
ont déjà jugé l'objet ; ici on l'écrit, sans re-juger. Deux destinations :
  · `framework_answers` — append-only + versionnée (A1, comme `knowledge_entries`, migration 024) :
    une réponse corrigée ne se met pas à jour, elle SUPERSÈDE. La lignée qui décide de ce qu'une
    nouvelle ligne remplace est `(ticker_id, framework, framework_version, question_id, analyste)` —
    PAS sans `analyste` : deux analystes distincts (§3.4, N ≥ 1) ne se supersèdent jamais l'un
    l'autre, seule une correction du MÊME analyste ferme la ligne précédente ;
  · `framework_dispenses` — remplace `DECLARED_NONBLOCKING_GAPS` (dict codé en dur). Idempotente par
    construction (`ON CONFLICT ... DO UPDATE`) : redéclarer la même dispense en met à jour le motif,
    jamais n'en duplique la ligne.

⚠️ ATOMICITÉ EXPLICITE (#35). `get_db_session()` n'ouvre AUCUNE transaction : chaque `execute` part
en autocommit. `persist_answer` fait PLUSIEURS écritures liées (l'INSERT neuf, l'UPDATE qui ferme
l'ancienne ligne, et désormais le SERVICE du mandat de sa lignée, §14 ci-dessous) : l'appelant DOIT
les envelopper dans `async with conn.transaction():`, sinon une panne entre deux laisserait deux
lignes courantes actives sur la même lignée, ou un mandat fermé sans réponse écrite.

UNE DEMANDE DE RECHERCHE SE FERME QUAND LA RÉPONSE EST LIVRÉE (règle d'un fonds, point 14, séance du
2026-10-18). Diagnostic qui a motivé ce §14 : les mandats manager/comité (`origine IN
('manager_renvoi','comite')`) n'étaient servis QUE par le bouclage (`bouclage.py`), jamais par la
chaîne (`tools/executer_chaine.py`), qui est pourtant le chemin réel de TOUTES les réponses — 0 ligne
`servi`/`abandonne` en base avant correctif, et un dossier qui affichait « repartie en recherche »
sur un mandat dont le motif était déjà périmé (`persist_review` étant idempotent PAR QUESTION, un
nouveau renvoi du manager se serait absorbé dans l'ancien mandat sans jamais réapparaître).

Donc : `persist_answer` est désormais le DÉTENTEUR UNIQUE (#46) de la clôture d'un mandat manager/
comité — dans la MÊME transaction que l'écriture de la réponse. Une demande de recherche du gérant/
comité est CLOSE dès qu'une réponse (de N'IMPORTE QUEL analyste — un mandat est PAR QUESTION, pas
rattaché à un analyste, §3.4) est écrite pour sa question, quelle qu'en soit l'issue (`repondu` comme
`non_fondable`) : si la réponse ne satisfait pas, c'est le manager (`persist_review`) qui rouvrira
une demande NEUVE, avec son propre motif — jamais l'ancienne qui ressert. Le bouclage (`bouclage.py`)
ne sert donc plus lui-même (un seul chemin de clôture) : il récupère l'id du mandat ouvert AVANT
d'appeler `persist_answer`, pour pouvoir nommer le mandat dans sa note.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Optional

import asyncpg

from app.contracts.framework_answer_schema import COLONNES_DENORMALISEES, FrameworkAnswer, Statut

__all__ = ["AnswerPersistee", "Classement", "persist_answer", "persist_answer_detail",
           "persist_archetype", "persist_dispense", "read_answers_courantes", "read_archetype",
           "read_classement", "read_dispenses"]


def _lire_chemin(answer: FrameworkAnswer, chemin: str) -> Any:
    """Résout un chemin du contrat (`fondation.rang_derive`) sur l'objet. `None` si le bloc que le
    chemin traverse est absent — c'est le cas normal : un `non_fondable` n'a pas de `fondation`."""
    obj: Any = answer
    for part in chemin.split("."):
        if obj is None:
            return None
        obj = getattr(obj, part)
    return obj


@dataclass(frozen=True)
class AnswerPersistee:
    """Le résultat COMPLET d'une écriture de réponse (§14) : l'`id` neuf, et l'éventuel mandat
    manager/comité SERVI comme EFFET de cette écriture — `None` si aucun mandat n'était ouvert sur
    la lignée (le cas courant : la plupart des réponses ne répondent à aucun renvoi)."""
    id: int
    mandat_servi_id: Optional[int]


async def persist_answer_detail(
    conn: asyncpg.Connection,
    answer: FrameworkAnswer,
    *,
    entry_ids_produits: Optional[list[int]] = None,
) -> AnswerPersistee:
    """Écrit une réponse, supersède l'éventuelle ligne courante de la MÊME lignée, et SERT le mandat
    manager/comité ouvert sur sa question (§14 ci-dessus) — DÉTENTEUR UNIQUE de cette fermeture.
    Rend `AnswerPersistee(id, mandat_servi_id)`.

    À appeler DANS une transaction (#35). Les colonnes dénormalisées sont lues par le CHEMIN DU
    CONTRAT (`COLONNES_DENORMALISEES`, détenteur unique, #46) — jamais recopiées ici : le jour où
    le contrat gagne un bloc, cette fonction n'a rien à savoir de son existence.

    `entry_ids_produits` (mot-clé, optionnel) — les entries à inscrire sur le mandat servi (T8) :
    par défaut, les `cited_entry_ids` de LA RÉPONSE (ou `[]` si la réponse n'en cite aucune, ex. un
    `non_fondable`). Un appelant qui connaît de MEILLEURES entries pour la trace du mandat (le
    bouclage, qui sait ce que sa re-collecte a produit, distinct de ce que l'analyste a cité) les
    passe explicitement.
    """
    valeurs = {colonne: _lire_chemin(answer, chemin)
               for colonne, chemin in COLONNES_DENORMALISEES.items()}

    ancien = await conn.fetchrow(
        "SELECT id, statut FROM framework_answers "
        "WHERE ticker_id = $1 AND framework = $2 AND framework_version = $3 "
        "AND question_id = $4 AND analyste = $5 AND superseded_by IS NULL",
        valeurs["ticker_id"], valeurs["framework"], answer.framework_version,
        valeurs["question_id"], valeurs["analyste"])
    ancien_id = ancien["id"] if ancien is not None else None
    # Même convention que `bouclage._statuts_avant` : une question jamais répondue (par CET
    # analyste) n'a pas de ligne antérieure, et son statut avant est `non_fondable` — elle n'était
    # pas fondée, et c'est plus honnête que de prétendre un état inexistant.
    statut_avant_ligne: Statut = ancien["statut"] if ancien is not None else "non_fondable"

    nouveau_id = await conn.fetchval(
        "INSERT INTO framework_answers "
        "(framework, framework_version, question_id, ticker_id, analyste, statut, answer_json, "
        " cited_entry_ids, rang_degrade, methode_approximation, ingredients, motif) "
        "VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12) RETURNING id",
        valeurs["framework"], answer.framework_version, valeurs["question_id"],
        valeurs["ticker_id"], valeurs["analyste"], valeurs["statut"],
        answer.model_dump(mode="json"), valeurs["cited_entry_ids"], valeurs["rang_degrade"],
        valeurs["methode_approximation"], valeurs["ingredients"], valeurs["motif"])

    if ancien_id is not None:
        await conn.execute(
            "UPDATE framework_answers SET superseded_by = $1 WHERE id = $2",
            nouveau_id, ancien_id)

    # §14 : une réponse ÉCRITE ferme toute demande de recherche manager/comité ouverte sur CETTE
    # question — quel que soit l'analyste qui répond (le mandat n'est pas rattaché à un analyste,
    # il est PAR QUESTION). Import LOCAL : cycle potentiel avec `manager_persist` (import de
    # `manager`, qui importe `frameworks`/`traducteur` — aucun des deux n'importe ce module
    # aujourd'hui, mais la prudence déjà en vigueur dans `read_classement` ci-dessous s'applique
    # pareillement ici).
    from app.agents.v2.manager_persist import id_du_mandat_ouvert, serve_mandate

    mandat_id = await id_du_mandat_ouvert(
        conn, ticker_id=valeurs["ticker_id"], framework_id=valeurs["framework"],
        framework_version=answer.framework_version, question_id=valeurs["question_id"])
    mandat_servi_id: Optional[int] = None
    if mandat_id is not None:
        entries = (entry_ids_produits if entry_ids_produits is not None
                   else list(valeurs["cited_entry_ids"] or []))
        servi = await serve_mandate(
            conn, mandat_id, statut_avant=statut_avant_ligne, statut_apres=valeurs["statut"],
            entry_ids_produits=entries)
        if servi:
            mandat_servi_id = mandat_id

    return AnswerPersistee(id=nouveau_id, mandat_servi_id=mandat_servi_id)


async def persist_answer(
    conn: asyncpg.Connection,
    answer: FrameworkAnswer,
    *,
    entry_ids_produits: Optional[list[int]] = None,
) -> int:
    """Écrit une réponse (voir `persist_answer_detail`) ; rend SEULEMENT l'`id` neuf — compatibilité
    ascendante des appelants existants. Un appelant qui a besoin de savoir quel mandat a été SERVI
    comme effet de cette écriture (ex. l'inventaire imprimé par `tools/executer_chaine.py`) appelle
    `persist_answer_detail` à la place."""
    return (await persist_answer_detail(
        conn, answer, entry_ids_produits=entry_ids_produits)).id


async def read_answers_courantes(
    conn: asyncpg.Connection,
    *,
    ticker_id: str,
    framework_version: str,
) -> list[tuple[int, FrameworkAnswer]]:
    """Les réponses COURANTES d'un émetteur, pour une version de référentiel. Rend `(id, réponse)`.

    « Courante » = `superseded_by IS NULL`, et cette sélection appartient à la table : la lignée est
    fermée par `persist_answer`, pas re-déduite par le lecteur. La refaire côté appelant en ferait
    un jumeau, divergent le jour où la règle de supersession changera (#46).

    `framework_version` est un paramètre REQUIS, jamais un filtre optionnel : sans lui, le lecteur
    rendrait aussi les réponses écrites contre un énoncé qui a changé, et le projecteur les
    publierait comme si elles répondaient à la question actuelle (écart V10). Un appelant qui veut
    « tout » doit le dire version par version, donc savoir qu'il le fait.

    `answer_json` est de type JSONB : asyncpg le décode déjà. Le revalider par le contrat n'est pas
    redondant — une ligne écrite par une version antérieure du contrat doit LEVER ici, pas se
    charger à moitié.
    """
    rows = await conn.fetch(
        "SELECT id, answer_json FROM framework_answers "
        "WHERE ticker_id = $1 AND framework_version = $2 AND superseded_by IS NULL "
        "ORDER BY id",
        ticker_id, framework_version)
    return [(row["id"], FrameworkAnswer.model_validate(row["answer_json"])) for row in rows]


@dataclass(frozen=True)
class Classement:
    """Le classement EN VIGUEUR d'un émetteur, tel qu'on le relit (migrations 046, 059).

    `piece_id` / `auteur` / `declencheur_accession` : présents ensemble quand le classement est une
    DÉCISION du comité (#139) — la pièce suit alors tous les chapitres ; absents ensemble pour les
    classements d'origine (contrainte `ticker_archetypes_decision`)."""
    archetype: str
    motif: str
    effective_from: date
    piece_id: Optional[int] = None
    auteur: Optional[str] = None
    declencheur_accession: Optional[str] = None


async def read_archetype(
    conn: asyncpg.Connection,
    *,
    ticker_id: str,
    a_la_date: Optional[date] = None,
) -> Optional[tuple[str, str]]:
    """L'archétype EN VIGUEUR d'un émetteur (migration 046). Rend `(archetype, motif)` ou `None`.

    `None` = **l'émetteur n'est pas classé**, et c'est un troisième état, pas un défaut de lecture :
    il se distingue de « classé rentable » comme de « classé pré-revenus ». Retomber sur un
    archétype par défaut ferait répondre des questions hors-sujet et fabriquerait exactement le
    défaut T4 / entry #190 (un ROIC pour une société sans revenus). L'ignorance se DIT (#25/#44).

    « En vigueur » = la date d'effet la plus récente qui ne soit pas dans le futur. `created_at`
    n'entre pas dans le tri : une saisie tardive ne doit pas prendre le pas sur un classement dont
    l'effet est antérieur.

    ⚠️ LE VOCABULAIRE EST CONFRONTÉ À SON DÉTENTEUR, PAS À UN CHECK SQL. Un archétype stocké qui ne
    figure plus dans `frameworks.yaml` LÈVE : sauté, il rendrait `None` et l'émetteur paraîtrait
    non classé alors qu'il l'est — un contrôle qui dégrade en sortant à zéro est un vert
    (`feedback_check_degrade_en_sortant_a_zero`).
    """
    c = await read_classement(conn, ticker_id=ticker_id, a_la_date=a_la_date)
    return None if c is None else (c.archetype, c.motif)


async def read_classement(
    conn: asyncpg.Connection,
    *,
    ticker_id: str,
    a_la_date: Optional[date] = None,
) -> Optional[Classement]:
    """Le classement entier — DÉTENTEUR UNIQUE de la lecture (`read_archetype` en est la projection).
    Même règle d'« en vigueur » et même confrontation au référentiel que décrites ci-dessus."""
    row = await conn.fetchrow(
        "SELECT archetype, motif, effective_from, piece_id, auteur, declencheur_accession "
        "FROM ticker_archetypes "
        "WHERE ticker_id = $1 AND effective_from <= $2 "
        "ORDER BY effective_from DESC LIMIT 1",
        ticker_id, a_la_date or date.today())
    if row is None:
        return None

    # Import local : `framework_persist` est importé par des checks sans référentiel monté.
    from app.agents.v2.frameworks import FrameworkDefinitionRefused, load_frameworks

    declares = load_frameworks().archetypes
    if row["archetype"] not in declares:
        raise FrameworkDefinitionRefused(
            f"`{ticker_id}` est classé `{row['archetype']}`, qui n'est plus un archétype déclaré "
            f"({sorted(declares)}) — un classement périmé rendrait hors-sujet des questions qui "
            "s'appliquent, et le manager acquitterait des `sans_objet` fabriqués")
    return Classement(archetype=row["archetype"], motif=row["motif"],
                      effective_from=row["effective_from"], piece_id=row["piece_id"],
                      auteur=row["auteur"], declencheur_accession=row["declencheur_accession"])


async def persist_archetype(
    conn: asyncpg.Connection,
    *,
    ticker_id: str,
    archetype: str,
    motif: str,
    effective_from: Optional[date] = None,
    piece_id: Optional[int] = None,
    auteur: Optional[str] = None,
    declencheur_accession: Optional[str] = None,
) -> int:
    """Classe un émetteur à une date d'effet. APPEND-ONLY : ne met jamais à jour la ligne courante.

    Un reclassement est un FAIT DATÉ (« la société est devenue rentable au T3 »), pas une
    correction : l'écraser perdrait la raison pour laquelle les notes antérieures posaient d'autres
    questions. C'est l'arbitrage du 2026-09-22 — on n'écrase pas, on empile.

    Rejouer le MÊME jour d'effet met à jour le classement de ce jour (`ON CONFLICT`) : c'est une
    correction de saisie, pas un empilement, et l'index unique la rend explicite.

    Une DÉCISION du comité (#139) porte `piece_id`, `auteur` et `declencheur_accession` ensemble — la
    base refuse un mélange (`ticker_archetypes_decision`) ; le geste vit dans `agents/v2/classement.py`.
    """
    return await conn.fetchval(
        "INSERT INTO ticker_archetypes (ticker_id, archetype, effective_from, motif, piece_id, auteur, "
        "declencheur_accession) VALUES ($1, $2, $3, $4, $5, $6, $7) "
        "ON CONFLICT (ticker_id, effective_from) "
        "DO UPDATE SET archetype = EXCLUDED.archetype, motif = EXCLUDED.motif, "
        "piece_id = EXCLUDED.piece_id, auteur = EXCLUDED.auteur, "
        "declencheur_accession = EXCLUDED.declencheur_accession "
        "RETURNING id",
        ticker_id, archetype, effective_from or date.today(), motif, piece_id, auteur,
        declencheur_accession)


async def read_dispenses(
    conn: asyncpg.Connection,
    *,
    ticker_id: str,
    framework_id: str,
    framework_version: str,
) -> dict[str, str]:
    """Dispenses actives pour un émetteur + version de framework donnés.

    Rend `{question_id: motif}` — même forme que l'ancienne `nonblocking_gaps_for`, mais keyé
    par question_id (not MVDD field path). Consommé par le manager en lot 4."""
    rows = await conn.fetch(
        "SELECT question_id, motif FROM framework_dispenses "
        "WHERE ticker_id = $1 AND framework_id = $2 AND framework_version = $3",
        ticker_id, framework_id, framework_version)
    return {row["question_id"]: row["motif"] for row in rows}


async def persist_dispense(
    conn: asyncpg.Connection,
    *,
    ticker_id: str,
    framework_id: str,
    framework_version: str,
    question_id: str,
    motif: str,
) -> None:
    """Écrit une dispense — remplace `DECLARED_NONBLOCKING_GAPS`. Idempotente : redéclarer la même
    dispense met à jour son motif plutôt que de dupliquer la ligne."""
    await conn.execute(
        "INSERT INTO framework_dispenses "
        "(ticker_id, framework_id, framework_version, question_id, motif) "
        "VALUES ($1, $2, $3, $4, $5) "
        "ON CONFLICT (ticker_id, framework_id, framework_version, question_id) "
        "DO UPDATE SET motif = EXCLUDED.motif",
        ticker_id, framework_id, framework_version, question_id, motif)
