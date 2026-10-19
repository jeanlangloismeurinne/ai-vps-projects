"""Le PARCOURS DU COMITÉ — les trois niveaux de drill-down (chantier v3, lot 6 maillon 2, spec §8.1).

  GET /v2/tickers/{ticker_id}/dossier                                   NIVEAU 1 — peut-on décider ?
  GET /v2/tickers/{ticker_id}/frameworks/{framework_id}                 NIVEAU 2 — une méthodologie
  GET /v2/tickers/{ticker_id}/frameworks/{framework_id}/q/{question_id} NIVEAU 3 — la preuve
  POST …/q/{question_id}/acquitter   le comité accepte UNE réponse telle qu'elle est (PV, maillon 3)
  POST …/q/{question_id}/renvoyer    le comité renvoie la question en recherche (PV + mandat)
  POST …/q/{question_id}/reinitialiser   le gérant remet UNE question à zéro, même acceptée (#137)
  POST …/frameworks/{framework_id}/reinitialiser   … ou tout un CHAPITRE (une ligne de PV par question
                                                   applicable) — rend le niveau 2 recalculé
  POST …/q/{question_id}/retablir    le comité RÉTABLIT la précédente immédiate d'une révision à la
                                     baisse (point 13) — PAS une acceptation, la copie repasse les
                                     contrôles et la fraîcheur comme toute réponse
  POST /v2/tickers/{ticker_id}/classement   le comité RECLASSE ou MAINTIENT l'émetteur au vu d'un dépôt
                                            (#139) — rend le niveau 1 recalculé

Ces POST sont les SEULES écritures du parcours ; elles passent par `agents/v2/comite.py`
(détenteur unique du procès-verbal) et rendent le niveau 3 RECALCULÉ — le comité voit tout de suite
l'effet de sa décision, lu au même point de lecture que le reste. Un refus (réponse remplacée
entre-temps, réponse d'une autre question, EDGAR illisible pour une acceptation) est un 409 qui dit
pourquoi, jamais une décision archivée sur un dossier que le comité n'a pas lu.

Aucune règle ici : tout est dressé par `agents/v2/parcours.py` (détenteur unique), recalculé à la
lecture, et RIEN n'est écrit — ni avis, ni mandat, ni note (#53/#54/#77). Un GET qui servirait une
ligne stockée servirait le verdict d'avant le dernier fait important publié.

Un framework ou une question inconnus rendent 404, jamais un niveau vide : un écran vide se lirait
« rien au dossier ». Un titre inconnu aussi — un dossier vide pour un titre qui n'existe pas se lirait
« aucune question applicable ».
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.agents.v2.comite import (
    DecisionRefusee, acquitter, reinitialiser, reinitialiser_chapitre, renvoyer, retablir)
from app.agents.v2.parcours import (
    ReferenceInconnue, charger_etat_dossier, dresser_niveau1, dresser_niveau2, dresser_niveau3)
from app.agents.v2.projection_memo import memo_de_l_etat
from app.contracts.comite_schema import (
    DemandeAcquittement, DemandeClassement, DemandeReinitialisation, DemandeRenvoi,
    DemandeRetablissement)
from app.contracts.parcours_schema import DossierTitre, FrameworkDuDossier, PreuvesQuestion
from app.db.database import get_db_session

router = APIRouter(tags=["parcours-v2"])


async def _etat(ticker_id: str):
    async with get_db_session() as conn:
        existe = await conn.fetchval("SELECT 1 FROM tickers WHERE id = $1", ticker_id)
        if not existe:
            raise HTTPException(status_code=404, detail=f"Titre `{ticker_id}` inconnu.")
        return await charger_etat_dossier(conn, ticker_id)


@router.get("/v2/tickers/{ticker_id}/dossier", response_model=DossierTitre)
async def dossier_niveau1(ticker_id: str) -> DossierTitre:
    etat = await _etat(ticker_id)
    return dresser_niveau1(etat, memo_de_l_etat(etat))


@router.get("/v2/tickers/{ticker_id}/frameworks/{framework_id}", response_model=FrameworkDuDossier)
async def dossier_niveau2(ticker_id: str, framework_id: str) -> FrameworkDuDossier:
    etat = await _etat(ticker_id)
    try:
        return dresser_niveau2(etat, framework_id)
    except ReferenceInconnue as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/v2/tickers/{ticker_id}/frameworks/{framework_id}/q/{question_id}",
            response_model=PreuvesQuestion)
async def dossier_niveau3(ticker_id: str, framework_id: str, question_id: str) -> PreuvesQuestion:
    etat = await _etat(ticker_id)
    try:
        return dresser_niveau3(etat, framework_id, question_id)
    except ReferenceInconnue as e:
        raise HTTPException(status_code=404, detail=str(e))


async def _decider(ticker_id: str, framework_id: str, question_id: str, geste, demande):
    # Import tardif : l'ancre appelle EDGAR, et ce module est importé par des checks hors réseau.
    from app.agents.v2.frameworks import load_frameworks, types_qui_rouvrent
    from app.agents.v2.note_flash import qualifications_de_l_emetteur
    from app.knowledge.evenements import ancre_de_la_question
    from app.knowledge.material_events import ancre_substantielle, material_anchor_for_ticker

    async with get_db_session() as conn:
        if not await conn.fetchval("SELECT 1 FROM tickers WHERE id = $1", ticker_id):
            raise HTTPException(status_code=404, detail=f"Titre `{ticker_id}` inconnu.")
        # La MÊME ancre que celle qui jugera l'acceptation à la lecture (arbitrage n°2) : celle de
        # CETTE question (#89) — le PV cite le dernier fait qui la rouvre, pas le dernier fait venu.
        ancre = ancre_substantielle(await material_anchor_for_ticker(conn, ticker_id))
        fichier = load_frameworks()
        notes = await qualifications_de_l_emetteur(conn, ancre.cik, fichier)
        try:
            ancre = ancre_de_la_question(
                ancre, rouvrent=types_qui_rouvrent(fichier, question_id), qualifications=notes)
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))
        try:
            await geste(conn, ticker_id=ticker_id, framework_id=framework_id,
                        question_id=question_id, demande=demande, ancre=ancre)
        except ReferenceInconnue as e:
            raise HTTPException(status_code=404, detail=str(e))
        except DecisionRefusee as e:
            raise HTTPException(status_code=409, detail=str(e))
    return await dossier_niveau3(ticker_id, framework_id, question_id)


@router.post("/v2/tickers/{ticker_id}/frameworks/{framework_id}/q/{question_id}/acquitter",
             response_model=PreuvesQuestion)
async def comite_acquitter(ticker_id: str, framework_id: str, question_id: str,
                           demande: DemandeAcquittement) -> PreuvesQuestion:
    return await _decider(ticker_id, framework_id, question_id, acquitter, demande)


@router.post("/v2/tickers/{ticker_id}/frameworks/{framework_id}/q/{question_id}/renvoyer",
             response_model=PreuvesQuestion)
async def comite_renvoyer(ticker_id: str, framework_id: str, question_id: str,
                          demande: DemandeRenvoi) -> PreuvesQuestion:
    return await _decider(ticker_id, framework_id, question_id, renvoyer, demande)


@router.post("/v2/tickers/{ticker_id}/frameworks/{framework_id}/q/{question_id}/reinitialiser",
             response_model=PreuvesQuestion)
async def comite_reinitialiser(ticker_id: str, framework_id: str, question_id: str,
                               demande: DemandeReinitialisation) -> PreuvesQuestion:
    return await _decider(ticker_id, framework_id, question_id, reinitialiser, demande)


@router.post("/v2/tickers/{ticker_id}/frameworks/{framework_id}/q/{question_id}/retablir",
             response_model=PreuvesQuestion)
async def comite_retablir(ticker_id: str, framework_id: str, question_id: str,
                          demande: DemandeRetablissement) -> PreuvesQuestion:
    return await _decider(ticker_id, framework_id, question_id, retablir, demande)


@router.post("/v2/tickers/{ticker_id}/frameworks/{framework_id}/reinitialiser",
             response_model=FrameworkDuDossier)
async def comite_reinitialiser_chapitre(ticker_id: str, framework_id: str,
                                        demande: DemandeReinitialisation) -> FrameworkDuDossier:
    """Tout un chapitre remis à zéro : les questions APPLICABLES à l'émetteur, une ligne de PV
    chacune. Émetteur non classé → 409 (on ne sait pas quelles questions s'appliquent). L'ancre
    citée au PV est celle du TITRE : une réinitialisation ne tombe jamais, elle trace seulement le
    dernier fait connu."""
    from app.agents.v2.framework_persist import read_archetype
    from app.agents.v2.frameworks import load_frameworks
    from app.agents.v2.traducteur import questions_applicables
    from app.knowledge.material_events import ancre_substantielle, material_anchor_for_ticker

    fichier = load_frameworks()
    if not any(f.id == framework_id for f in fichier.frameworks):
        raise HTTPException(status_code=404, detail=f"framework `{framework_id}` absent du référentiel")
    async with get_db_session() as conn:
        if not await conn.fetchval("SELECT 1 FROM tickers WHERE id = $1", ticker_id):
            raise HTTPException(status_code=404, detail=f"Titre `{ticker_id}` inconnu.")
        classement = await read_archetype(conn, ticker_id=ticker_id)
        if classement is None:
            raise HTTPException(status_code=409, detail=(
                f"`{ticker_id}` n'est pas classé : on ne sait pas quelles questions de "
                f"`{framework_id}` s'appliquent — classer l'émetteur d'abord"))
        questions = [q.id for q in questions_applicables(fichier, framework_id, classement[0])]
        ancre = ancre_substantielle(await material_anchor_for_ticker(conn, ticker_id))
        try:
            await reinitialiser_chapitre(conn, ticker_id=ticker_id, framework_id=framework_id,
                                         questions=questions, demande=demande, ancre=ancre,
                                         fichier=fichier)
        except DecisionRefusee as e:
            raise HTTPException(status_code=409, detail=str(e))
    return await dossier_niveau2(ticker_id, framework_id)


@router.post("/v2/tickers/{ticker_id}/classement", response_model=DossierTitre)
async def comite_classer(ticker_id: str, demande: DemandeClassement) -> DossierTitre:
    """Le comité reclasse (ou maintient) l'émetteur au vu d'un dépôt (#139). La lecture du dépôt devient
    la pièce du classement, jointe à tous les chapitres. Refus (dépôt hors du fil de l'émetteur,
    archétype inconnu, seconde décision le même jour, lecture impossible) : 409 qui dit pourquoi."""
    from app.agents.v2.classement import ClassementRefuse, decider_classement
    from app.agents.v2.frameworks import load_frameworks
    from app.knowledge.material_events import material_anchor_for_ticker

    fichier = load_frameworks()
    async with get_db_session() as conn:
        if not await conn.fetchval("SELECT 1 FROM tickers WHERE id = $1", ticker_id):
            raise HTTPException(status_code=404, detail=f"Titre `{ticker_id}` inconnu.")
        # Le fil BRUT, pas l'ancre substantielle : la décision cite le dépôt tel que l'émetteur l'a publié.
        ancre = await material_anchor_for_ticker(conn, ticker_id)
        if ancre.status == "unavailable":
            raise HTTPException(status_code=409, detail=(
                f"le fil EDGAR de `{ticker_id}` est injoignable ({ancre.raison}) : le dépôt cité ne "
                "peut pas être vérifié — reprendre plus tard"))
        try:
            await decider_classement(conn, ticker_id=ticker_id, archetype=demande.archetype,
                                     accession=demande.accession, motif=demande.motif,
                                     auteur=demande.auteur, fichier=fichier, ancre=ancre)
        except ClassementRefuse as e:
            raise HTTPException(status_code=409, detail=str(e))
    return await dossier_niveau1(ticker_id)
