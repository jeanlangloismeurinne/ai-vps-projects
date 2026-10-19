"""Le REGISTRE DU COMITÉ — acquitter / renvoyer, tracés (chantier v3, lot 6 maillon 3, spec §8.2, A7).

DÉTENTEUR UNIQUE (#46) de deux choses :
  · « cette acceptation du comité tient-elle AUJOURD'HUI ? » — `servir_acceptation`, PURE ;
  · l'ÉCRITURE du procès-verbal — `acquitter` / `renvoyer`, les seuls à insérer dans
    `comite_decisions` (migration 048).

CE QUE FERAIT UN VRAI FONDS, ET LES CHOIX QUI EN DÉCOULENT
---------------------------------------------------------
1. Le PV ne se réécrit pas : chaque décision est une ligne NEUVE ; la plus récente sur une question
   est la position du comité (un renvoi après une acceptation la remplace, et inversement).
2. Accepter porte sur UNE réponse précise, la version du dossier que le comité a lue. Si l'analyse
   est refaite, le comité n'a pas lu la nouvelle : l'acceptation tombe (`tombee_reponse_remplacee`).
3. Une acceptation TOMBE sur un fait important publié après elle (arbitrage n°2) — jugé contre
   `ancre_substantielle`, la même ancre que l'actualité et la porte de complétude : un 8-K de pure
   forme ne fait rien tomber.
4. Quand le comité tranche, la recherche en cours sur la question S'ARRÊTE ou est REMPLACÉE : un
   comité qui accepte un trou ne laisse pas l'analyste continuer à dépenser dessus ; un comité qui
   renvoie avec une consigne précise remplace la consigne générique du manager. Le mandat ouvert est
   passé `abandonne` (jamais supprimé) et le PV garde son id (`mandat_remplace_id`).
5. Renvoyer emprunte le MÊME canal que le manager (`persist_mandate`, origine `comite`) : le
   bouclage le consomme comme les autres, aucun chemin de recherche parallèle (#46).
6. RÉINITIALISER (#137, point 17-bis) : le gérant remet à zéro une question ou un chapitre de son
   choix, même accepté. C'est une décision du PV (signée, motivée) ; la recherche en cours s'arrête ;
   la réponse courante est relevée (`answer_id`) mais jamais retirée — elle reste au dossier comme
   archive et ne ferme plus la question (`parcours.manque_de_la_question`). Aucun mandat : la question
   repart par la relance bornée (`tools/executer_chaine.py`). Le chapitre = une ligne par question
   applicable, dans UNE transaction.
7. RÉTABLIR (point 13, 2026-10-18) : sur une révision à la BAISSE (`agents/v2/revision.baisse_a_lire`),
   le comité désigne la PRÉCÉDENTE IMMÉDIATE, signe et motive. Refusé si la réponse désignée n'est pas
   cette précédente, si la courante n'est pas une baisse à lire, si la version de référentiel diffère,
   ou si l'`answer_json` de la précédente ne valide plus contre le contrat (« réinitialiser plutôt »).
   Effet : la précédente est réécrite comme réponse NEUVE (`framework_persist.persist_answer_detail` —
   l'append-only tient : jamais de `superseded_by` remis à NULL, la COPIE supersède la courante
   dégradée, et ferme d'office un mandat ouvert comme toute réponse, point 14 — c'est voulu, un
   second mécanisme ferait doublon avec #46) ; le PV garde `answer_id` = la copie et
   `retablie_depuis_id` = la précédente. Ce n'est PAS une acceptation : la copie repasse les contrôles
   et la fraîcheur comme toute réponse.

⚠️ ATOMICITÉ (#35). `get_db_session()` n'ouvre aucune transaction : `acquitter`/`renvoyer`/`retablir`
ouvrent la leur (abandon du mandat + nouveau mandat/nouvelle réponse + ligne de PV, tout ou rien).
"""
from __future__ import annotations

from typing import Any, Optional
from zoneinfo import ZoneInfo

from app.contracts.comite_schema import (
    AcceptationServie,
    DecisionComite,
    DemandeAcquittement,
    DemandeReinitialisation,
    DemandeRenvoi,
    DemandeRetablissement,
    EtatAncre,
    FaitImportant,
    PositionComite,
)
from app.contracts.framework_answer_schema import FrameworkMandate
from app.contracts.framework_definition_schema import FrameworksFile

__all__ = [
    "DecisionRefusee",
    "fait_de_l_ancre",
    "servir_acceptation",
    "position_du_comite",
    "lire_registre",
    "acquitter",
    "renvoyer",
    "reinitialiser",
    "reinitialiser_chapitre",
    "retablir",
]


class DecisionRefusee(ValueError):
    """Le comité ne peut pas prendre CETTE décision sur CE dossier (réponse remplacée entre-temps,
    réponse d'une autre question, faits importants illisibles…). L'endpoint en fait un 409 — jamais
    une décision archivée sur un dossier que le comité n'a pas lu."""


# ── Règles PURES ───────────────────────────────────────────────────────────────────────────────

def fait_de_l_ancre(ancre: Any) -> tuple[EtatAncre, Optional[FaitImportant]]:
    """Le dernier fait important connu, tel que le PV le cite. `ancre` est un `MaterialEventLookup`
    DÉJÀ passé par `ancre_substantielle` (l'appelant le garantit) ; son `status` est rendu tel quel
    (#49)."""
    if ancre.status != "found" or ancre.event is None:
        return ("none" if ancre.status == "none" else "unavailable"), None
    e = ancre.event
    return "found", FaitImportant(publie_le=e.filing_date, accession=e.accession, resume=e.resume())


# Le jour d'une décision se lit dans le fuseau d'EDGAR : une date de dépôt est un jour de New York.
# Lire `decide_le` en UTC ferait passer une décision prise un soir de Paris… au jour suivant d'EDGAR.
_FUSEAU_EDGAR = ZoneInfo("America/New_York")


def _fait_nouveau(decision: DecisionComite, ancre: Any) -> Optional[FaitImportant]:
    """Le fait important publié APRÈS la décision (arbitrage n°2), le plus récent, ou None.

    « Après » se juge au JOUR de dépôt EDGAR (une date, sans heure) :
      · déposé un jour POSTÉRIEUR à la décision → nouveau ;
      · déposé le JOUR MÊME → nouveau, sauf si c'est le fait que le PV cite comme connu : on ne peut
        pas prouver qu'un autre dépôt du jour précédait la séance, et dans le doute la question
        repasse devant le comité (le coût d'une relecture, pas celui d'une décision sur un dossier
        faux) ;
      · déposé AVANT le jour de la décision → il était public quand le comité a tranché : pas
        nouveau, même si notre flux ne l'avait pas montré (c'est « publié après elle » qui fait
        tomber, pas « absent de notre écran »).
    On parcourt TOUS les dépôts substantiels récents, pas seulement le dernier : deux faits du même
    jour ne se départagent pas par l'ordre du flux."""
    if ancre.status != "found":
        return None
    jour = decision.decide_le.astimezone(_FUSEAU_EDGAR).date()
    connu = decision.fait_connu.accession if decision.fait_connu else None
    for e in ancre.recents or ((ancre.event,) if ancre.event else ()):
        if e.filing_date > jour or (e.filing_date == jour and e.accession != connu):
            return FaitImportant(publie_le=e.filing_date, accession=e.accession, resume=e.resume())
    return None


def servir_acceptation(
    decision: DecisionComite, *, reponses_courantes: frozenset[int], ancre: Any,
) -> AcceptationServie:
    """DÉTENTEUR UNIQUE (#46) de « l'acceptation du comité tient-elle aujourd'hui ? ». Pure.

    L'ordre des branches EST la doctrine :
      1. la réponse acceptée n'est plus la réponse courante → le comité a lu un autre dossier ;
      2. les faits importants sont illisibles → on ne SAIT pas (#49), l'acceptation ne fonde rien ;
      3. un fait important publié depuis → elle tombe (arbitrage n°2), et on dit lequel ;
      4. sinon elle est en vigueur.
    """
    if decision.answer_id not in reponses_courantes:
        return AcceptationServie(
            decision=decision, etat="tombee_reponse_remplacee",
            motif_etat="l'analyse a été refaite depuis : le comité avait accepté une version de la "
                       "réponse qui n'est plus celle du dossier")
    if ancre.status not in ("found", "none"):
        return AcceptationServie(
            decision=decision, etat="non_verifiable",
            motif_etat="les dépôts EDGAR n'ont pas pu être lus : on ne peut pas vérifier qu'aucun "
                       "fait important n'a été publié depuis la décision")
    nouveau = _fait_nouveau(decision, ancre)
    if nouveau is not None:
        return AcceptationServie(
            decision=decision, etat="tombee_fait_nouveau", fait_nouveau=nouveau,
            motif_etat=f"un fait important a été publié depuis la décision : {nouveau.resume}")
    return AcceptationServie(
        decision=decision, etat="en_vigueur",
        motif_etat="aucun fait important publié depuis la décision, et la réponse acceptée est "
                   "toujours celle du dossier")


def position_du_comite(
    registre: list[DecisionComite], *, reponses_courantes: frozenset[int], ancre: Any,
) -> Optional[PositionComite]:
    """La position du comité sur UNE question : sa décision la plus récente (le registre est rendu
    le plus récent d'abord), servie si c'est une acceptation."""
    if not registre:
        return None
    derniere = registre[0]
    acc = (servir_acceptation(derniere, reponses_courantes=reponses_courantes, ancre=ancre)
           if derniere.action == "acquitter" else None)
    return PositionComite(derniere=derniere, acceptation=acc)


# ── Lecture du registre ────────────────────────────────────────────────────────────────────────

_COLONNES = ("id, ticker_id, framework_id, framework_version, question_id, action, answer_id, "
             "mandat_id, mandat_remplace_id, retablie_depuis_id, auteur, motif, ancre_etat, "
             "fait_connu_publie_le, fait_connu_accession, fait_connu_resume, decide_le")


def _decision(r) -> DecisionComite:
    fait = (FaitImportant(publie_le=r["fait_connu_publie_le"], accession=r["fait_connu_accession"],
                          resume=r["fait_connu_resume"])
            if r["fait_connu_publie_le"] is not None else None)
    return DecisionComite(
        id=r["id"], ticker_id=r["ticker_id"], framework_id=r["framework_id"],
        framework_version=r["framework_version"], question_id=r["question_id"],
        action=r["action"], answer_id=r["answer_id"], mandat_id=r["mandat_id"],
        mandat_remplace_id=r["mandat_remplace_id"], retablie_depuis_id=r["retablie_depuis_id"],
        auteur=r["auteur"], motif=r["motif"],
        ancre_etat=r["ancre_etat"], fait_connu=fait, decide_le=r["decide_le"])


async def lire_registre(
    conn, *, ticker_id: str, framework_version: str,
) -> dict[tuple[str, str], list[DecisionComite]]:
    """Le PV d'un émetteur pour une version des frameworks : (framework, question) → décisions, la
    plus récente d'abord. L'ordre est celui des `id` (l'identité est monotone) — deux décisions dans
    la même seconde restent ordonnées."""
    rows = await conn.fetch(
        f"SELECT {_COLONNES} FROM comite_decisions "
        "WHERE ticker_id = $1 AND framework_version = $2 ORDER BY id DESC",
        ticker_id, framework_version)
    out: dict[tuple[str, str], list[DecisionComite]] = {}
    for r in rows:
        out.setdefault((r["framework_id"], r["question_id"]), []).append(_decision(r))
    return out


# ── Écriture du procès-verbal ──────────────────────────────────────────────────────────────────

def _question(fichier: FrameworksFile, framework_id: str, question_id: str):
    from app.agents.v2.parcours import ReferenceInconnue

    f = next((f for f in fichier.frameworks if f.id == framework_id), None)
    if f is None:
        raise ReferenceInconnue(f"framework `{framework_id}` absent du référentiel")
    if not any(q.id == question_id for q in f.questions):
        raise ReferenceInconnue(f"question `{question_id}` inconnue du framework `{framework_id}`")


async def _inscrire(conn, *, ticker_id, framework_id, version, question_id, action, answer_id,
                    mandat_id, mandat_remplace_id, auteur, motif, ancre,
                    retablie_depuis_id=None) -> DecisionComite:
    etat, fait = fait_de_l_ancre(ancre)
    row = await conn.fetchrow(
        "INSERT INTO comite_decisions (ticker_id, framework_id, framework_version, question_id, "
        "action, answer_id, mandat_id, mandat_remplace_id, retablie_depuis_id, auteur, motif, "
        "ancre_etat, fait_connu_publie_le, fait_connu_accession, fait_connu_resume) "
        "VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15) "
        f"RETURNING {_COLONNES}",
        ticker_id, framework_id, version, question_id, action, answer_id, mandat_id,
        mandat_remplace_id, retablie_depuis_id, auteur, motif, etat,
        fait.publie_le if fait else None, fait.accession if fait else None,
        fait.resume if fait else None)
    return _decision(row)


async def _arreter_la_recherche_en_cours(conn, *, ticker_id, framework_id, version, question_id):
    from app.agents.v2.manager_persist import abandonner_mandat, id_du_mandat_ouvert

    ouvert = await id_du_mandat_ouvert(
        conn, ticker_id=ticker_id, framework_id=framework_id, framework_version=version,
        question_id=question_id)
    if ouvert is not None:
        await abandonner_mandat(conn, ouvert)
    return ouvert


async def acquitter(
    conn, *, ticker_id: str, framework_id: str, question_id: str,
    demande: DemandeAcquittement, ancre: Any, fichier: Optional[FrameworksFile] = None,
) -> DecisionComite:
    """Le comité accepte UNE réponse telle qu'elle est. Refuse (`DecisionRefusee`) si la réponse
    n'est pas la réponse COURANTE de cette question, ou si les faits importants sont illisibles (on
    ne pourrait jamais la faire tomber). `ancre` : déjà passée par `ancre_substantielle`."""
    from app.agents.v2.frameworks import load_frameworks

    fichier = fichier or load_frameworks()
    version = fichier.schema_version
    _question(fichier, framework_id, question_id)
    if fait_de_l_ancre(ancre)[0] == "unavailable":
        raise DecisionRefusee(
            "les dépôts EDGAR sont illisibles en ce moment : sans savoir quel fait important est "
            "déjà connu, l'acceptation ne pourrait jamais tomber (arbitrage n°2). Réessayer plus tard.")
    rep = await conn.fetchrow(
        "SELECT ticker_id, framework, framework_version, question_id, superseded_by "
        "FROM framework_answers WHERE id = $1", demande.answer_id)
    if rep is None:
        raise DecisionRefusee(f"réponse #{demande.answer_id} introuvable")
    if (rep["ticker_id"], rep["framework"], rep["framework_version"], rep["question_id"]) != (
            ticker_id, framework_id, version, question_id):
        raise DecisionRefusee(f"la réponse #{demande.answer_id} n'est pas une réponse de "
                              f"{ticker_id} · {framework_id} {version} · {question_id}")
    if rep["superseded_by"] is not None:
        raise DecisionRefusee(f"la réponse #{demande.answer_id} a été remplacée par "
                              f"#{rep['superseded_by']} : le comité doit lire la réponse courante")
    async with conn.transaction():
        arrete = await _arreter_la_recherche_en_cours(
            conn, ticker_id=ticker_id, framework_id=framework_id, version=version,
            question_id=question_id)
        return await _inscrire(
            conn, ticker_id=ticker_id, framework_id=framework_id, version=version,
            question_id=question_id, action="acquitter", answer_id=demande.answer_id,
            mandat_id=None, mandat_remplace_id=arrete, auteur=demande.auteur,
            motif=demande.motif, ancre=ancre)


async def renvoyer(
    conn, *, ticker_id: str, framework_id: str, question_id: str,
    demande: DemandeRenvoi, ancre: Any, fichier: Optional[FrameworksFile] = None,
) -> DecisionComite:
    """Le comité renvoie la question en recherche : un mandat `comite` OUVERT par le canal du manager
    (`persist_mandate`), la recherche en cours remplacée, le PV inscrit — tout ou rien."""
    from app.agents.v2.frameworks import load_frameworks
    from app.agents.v2.manager_persist import persist_mandate

    fichier = fichier or load_frameworks()
    version = fichier.schema_version
    _question(fichier, framework_id, question_id)
    if demande.answer_id is not None:
        rep = await conn.fetchrow(
            "SELECT ticker_id, framework, framework_version, question_id FROM framework_answers "
            "WHERE id = $1", demande.answer_id)
        if rep is None or tuple(rep.values()) != (ticker_id, framework_id, version, question_id):
            raise DecisionRefusee(f"la réponse #{demande.answer_id} n'est pas une réponse de "
                                  f"{ticker_id} · {framework_id} {version} · {question_id}")
    mandat = FrameworkMandate(
        framework_id=framework_id, question_id=question_id, ticker_id=ticker_id,
        origine="comite", motif=f"renvoi du comité ({demande.auteur}) : {demande.motif}",
        mandat=demande.mandat, etat="ouvert")
    async with conn.transaction():
        remplace = await _arreter_la_recherche_en_cours(
            conn, ticker_id=ticker_id, framework_id=framework_id, version=version,
            question_id=question_id)
        mandat_id = await persist_mandate(conn, mandat, framework_version=version)
        return await _inscrire(
            conn, ticker_id=ticker_id, framework_id=framework_id, version=version,
            question_id=question_id, action="renvoyer", answer_id=demande.answer_id,
            mandat_id=mandat_id, mandat_remplace_id=remplace, auteur=demande.auteur,
            motif=demande.motif, ancre=ancre)


async def _reponse_courante(conn, *, ticker_id, framework_id, version, question_id) -> Optional[int]:
    return await conn.fetchval(
        "SELECT max(id) FROM framework_answers WHERE ticker_id = $1 AND framework = $2 "
        "AND framework_version = $3 AND question_id = $4 AND superseded_by IS NULL",
        ticker_id, framework_id, version, question_id)


async def _reinitialiser_une(conn, *, ticker_id, framework_id, version, question_id, demande, ancre):
    arrete = await _arreter_la_recherche_en_cours(  # remise à zéro : la recherche en cours s'arrête
        conn, ticker_id=ticker_id, framework_id=framework_id, version=version,
        question_id=question_id)
    courante = await _reponse_courante(
        conn, ticker_id=ticker_id, framework_id=framework_id, version=version,
        question_id=question_id)
    return await _inscrire(
        conn, ticker_id=ticker_id, framework_id=framework_id, version=version,
        question_id=question_id, action="reinitialiser", answer_id=courante,
        mandat_id=None, mandat_remplace_id=arrete, auteur=demande.auteur,
        motif=demande.motif, ancre=ancre)


async def reinitialiser(
    conn, *, ticker_id: str, framework_id: str, question_id: str,
    demande: DemandeReinitialisation, ancre: Any, fichier: Optional[FrameworksFile] = None,
) -> DecisionComite:
    """Le gérant remet UNE question à zéro (#137, point 17-bis) : la recherche en cours s'arrête, le
    PV relève la réponse courante qu'il met de côté — tout ou rien. Les faits illisibles n'empêchent
    pas de réinitialiser (rien ne doit « tomber » ensuite : la question est déjà rouverte)."""
    from app.agents.v2.frameworks import load_frameworks

    fichier = fichier or load_frameworks()
    version = fichier.schema_version
    _question(fichier, framework_id, question_id)
    async with conn.transaction():
        return await _reinitialiser_une(
            conn, ticker_id=ticker_id, framework_id=framework_id, version=version,
            question_id=question_id, demande=demande, ancre=ancre)


async def reinitialiser_chapitre(
    conn, *, ticker_id: str, framework_id: str, questions: list[str],
    demande: DemandeReinitialisation, ancre: Any, fichier: Optional[FrameworksFile] = None,
) -> list[DecisionComite]:
    """Le gérant remet un CHAPITRE à zéro : une ligne de PV par question (le PV est par question),
    dans UNE transaction. `questions` = les questions APPLICABLES à l'émetteur, fournies par
    l'appelant (une ligne de PV sur une question hors sujet serait du bruit indélébile). Une liste
    vide est REFUSÉE : un geste qui n'inscrit rien laisserait croire au gérant qu'il a agi."""
    from app.agents.v2.frameworks import load_frameworks

    fichier = fichier or load_frameworks()
    version = fichier.schema_version
    if not questions:
        raise DecisionRefusee(f"aucune question applicable dans `{framework_id}` : rien à réinitialiser")
    for qid in questions:
        _question(fichier, framework_id, qid)
    async with conn.transaction():
        return [await _reinitialiser_une(
            conn, ticker_id=ticker_id, framework_id=framework_id, version=version,
            question_id=qid, demande=demande, ancre=ancre) for qid in questions]


async def retablir(
    conn, *, ticker_id: str, framework_id: str, question_id: str,
    demande: DemandeRetablissement, ancre: Any, fichier: Optional[FrameworksFile] = None,
) -> DecisionComite:
    """Le comité RÉTABLIT la précédente immédiate d'une révision à la BAISSE (point 13, 2026-10-18).

    Refuse (`DecisionRefusee`) si : aucune réponse courante n'existe pour cette question ; la
    réponse désignée est introuvable, n'est pas une réponse de CE dossier (ticker/framework/version/
    question — couvre « la version de référentiel diffère ») ou n'est pas la PRÉCÉDENTE IMMÉDIATE de
    la courante ; la courante n'est pas une baisse à lire (`revision.baisse_a_lire`) ; l'`answer_json`
    de la précédente ne valide plus contre le contrat EN VIGUEUR.

    Effet, dans UNE transaction : la précédente est réécrite comme réponse NEUVE
    (`framework_persist.persist_answer_detail` — append-only, jamais de `superseded_by` remis à
    NULL ; la copie supersède la courante dégradée ; elle ferme d'office un mandat ouvert comme
    toute réponse écrite, §14 — voulu, pas dupliqué ici) ; le PV inscrit `answer_id` = la copie,
    `retablie_depuis_id` = la précédente rétablie. Ce n'est PAS une acceptation."""
    from app.agents.v2.framework_persist import persist_answer_detail
    from app.agents.v2.frameworks import load_frameworks
    from app.agents.v2.revision import ReponsePourBaisse, baisse_a_lire, precedente_validee
    from app.contracts.framework_answer_schema import FrameworkAnswer

    fichier = fichier or load_frameworks()
    version = fichier.schema_version
    _question(fichier, framework_id, question_id)

    # §3.4 — N analystes peuvent chacun porter une réponse courante à la MÊME question (deux
    # réponses ne se moyennent jamais) : `max(id)` départage comme `_reponse_courante`
    # (réinitialisation, #137) plutôt qu'une ligne arbitraire — déterministe, jamais un couple au
    # hasard parmi plusieurs lignes `superseded_by IS NULL`.
    precedente_row = await conn.fetchrow(
        "SELECT id, statut, answer_json, created_at, ticker_id, framework, framework_version, "
        "question_id, superseded_by FROM framework_answers WHERE id = $1", demande.answer_id)
    if precedente_row is None:
        raise DecisionRefusee(f"réponse #{demande.answer_id} introuvable")
    if (precedente_row["ticker_id"], precedente_row["framework"], precedente_row["framework_version"],
        precedente_row["question_id"]) != (ticker_id, framework_id, version, question_id):
        raise DecisionRefusee(f"la réponse #{demande.answer_id} n'est pas une réponse de "
                              f"{ticker_id} · {framework_id} {version} · {question_id} (la version "
                              "de référentiel ou la question diffère)")
    # La courante se lit DEPUIS la précédente (`superseded_by`) : avec plusieurs analystes sur la
    # question, « la dernière ligne en vigueur » ne serait pas forcément celle de SA lignée.
    # (une précédente encore en vigueur a `superseded_by` NULL : `id = NULL` ne rend aucune ligne).
    courante_row = await conn.fetchrow(
        "SELECT id, statut, answer_json, created_at FROM framework_answers "
        "WHERE id = $1 AND superseded_by IS NULL", precedente_row["superseded_by"])
    if courante_row is None:
        raise DecisionRefusee(f"la réponse #{demande.answer_id} n'est pas la PRÉCÉDENTE IMMÉDIATE "
                              "d'une réponse courante de cette question")

    registre_question = await conn.fetch(
        f"SELECT {_COLONNES} FROM comite_decisions WHERE ticker_id = $1 AND framework_id = $2 "
        "AND framework_version = $3 AND question_id = $4 ORDER BY id DESC",
        ticker_id, framework_id, version, question_id)
    decisions_q = [_decision(r) for r in registre_question]
    courante_rpb = ReponsePourBaisse(
        answer_id=courante_row["id"], cree_le=courante_row["created_at"],
        statut_brut=courante_row["statut"],
        answer=FrameworkAnswer.model_validate(courante_row["answer_json"]))
    precedente_rpb = ReponsePourBaisse(
        answer_id=precedente_row["id"], cree_le=precedente_row["created_at"],
        statut_brut=precedente_row["statut"],
        answer=precedente_validee(precedente_row["statut"], precedente_row["answer_json"]))
    if baisse_a_lire(courante_rpb, precedente_rpb, decisions_q) is None:
        raise DecisionRefusee(f"la réponse courante #{courante_row['id']} n'est pas une baisse à "
                              "lire : rien à rétablir")
    if precedente_rpb.answer is None:
        raise DecisionRefusee(
            f"la réponse #{demande.answer_id} est écrite sous un contrat antérieur, ne peut être "
            "rétablie telle quelle — réinitialiser plutôt")

    async with conn.transaction():
        copie = await persist_answer_detail(conn, precedente_rpb.answer)
        return await _inscrire(
            conn, ticker_id=ticker_id, framework_id=framework_id, version=version,
            question_id=question_id, action="retablir", answer_id=copie.id,
            mandat_id=None, mandat_remplace_id=None, retablie_depuis_id=precedente_row["id"],
            auteur=demande.auteur, motif=demande.motif, ancre=ancre)
