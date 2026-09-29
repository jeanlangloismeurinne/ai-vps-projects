"""La SIGNATURE du modèle de valorisation et sa persistance (roadmap 05 capacité 4 bis, migration 051).

DÉTENTEUR UNIQUE (#46) de trois choses :
  · « quelle version est en attente, laquelle est signée, et tiennent-elles aujourd'hui ? » —
    `servir_atelier`, PURE ;
  · l'écriture des deux registres (051) — `proposer`, `signer`, `ecarter`, les seuls à y insérer ;
  · le dossier contre lequel un modèle se juge — `charger_dossier_valorisation`.

Ce que ferait un vrai fonds, et les choix qui en découlent : docstring du contrat
`contracts/signature_modele_schema.py`. En bref : l'analyste propose une version, le comité la signe ou
l'écarte, motif écrit ; la fourchette signée est au PV ; la plus récente proposition remplace celle qui
attendait ; tant qu'une nouvelle version n'est pas signée, la signée reste affichée (#97, n°6) ; et
tout se rejoue contre le dossier DU JOUR (#53) — signer un modèle qui ne tient plus est refusé, un
modèle signé qui ne tient plus est servi « à revoir ».

⚠️ ATOMICITÉ (#35). `get_db_session()` n'ouvre aucune transaction : `proposer`/`signer`/`ecarter`
ouvrent la leur. Deux signatures concurrentes de la même version : la seconde se heurte à l'unicité
de la décision par version (051) — jamais deux décisions pour une version.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Mapping, Optional

from app.contracts.modele_valorisation_schema import ModeleValorisation, cle_hypothese
from app.contracts.signature_modele_schema import (
    AtelierServi, DecisionModele, DemandeDecisionModele, EcartEntreVersions, Fourchette,
    LigneModifiee, PropositionServie, SigneeServie, VersionModele,
)
from app.valorisation.modele import Evaluation, ModeleRefuse, evaluer_modele, valider_pont_modele

__all__ = [
    "ActeRefuse", "DossierValorisation", "fourchette_de", "ecart_entre", "version_en_attente",
    "derniere_signature", "servir_atelier", "reponses_reprenables", "charger_dossier_valorisation", "lire_atelier",
    "proposer", "signer", "ecarter",
]


class ActeRefuse(ValueError):
    """Le geste n'est pas possible sur CE registre (version remplacée ou déjà décidée, modèle qui ne
    tient plus contre le dossier…). L'endpoint en fait un 409 qui dit pourquoi."""


@dataclass(frozen=True)
class DossierValorisation:
    """Ce contre quoi un modèle se juge (le pont [A]/[B]) : les réponses ACQUITTÉES du titre
    (answer_id → question_id) et les pièces COURANTES de son dossier."""
    ticker_id: str
    reponses_acquittees: Mapping[int, str]
    pieces_du_dossier: frozenset[int]


# ── Règles PURES ───────────────────────────────────────────────────────────────────────────────

def fourchette_de(ev: Evaluation) -> Fourchette:
    return Fourchette(bas=ev.bas, central=ev.central, haut=ev.haut, par_evenement=dict(ev.par_evenement))


def _juger(modele: ModeleValorisation, dossier: DossierValorisation) -> tuple[Optional[Fourchette], Optional[str]]:
    """(fourchette, None) si le modèle tient contre le dossier ; (fourchette du jour si la mécanique
    tourne encore, motif) sinon."""
    try:
        ev = valider_pont_modele(modele, ticker_id=dossier.ticker_id,
                                 reponses_acquittees=dossier.reponses_acquittees,
                                 pieces_du_dossier=set(dossier.pieces_du_dossier))
        return fourchette_de(ev), None
    except ModeleRefuse as refus:
        try:
            ev = evaluer_modele(modele)
            f = fourchette_de(ev) if ev.bas <= ev.central <= ev.haut else None
        except ModeleRefuse:
            f = None
        return f, refus.motif


def ecart_entre(signee: ModeleValorisation, proposee: ModeleValorisation) -> EcartEntreVersions:
    """Ce qui a changé d'une version à l'autre, ligne par ligne — ce que le comité relit d'abord."""
    avant = {cle_hypothese(h): h for h in signee.hypotheses}
    apres = {cle_hypothese(h): h for h in proposee.hypotheses}
    communes = sorted(set(avant) & set(apres))
    seg_avant = {s.id for s in signee.segments}
    seg_apres = {s.id for s in proposee.segments}
    return EcartEntreVersions(
        hypotheses_modifiees=[LigneModifiee(cle=c, avant=avant[c].valeur, apres=apres[c].valeur)
                              for c in communes if avant[c].valeur != apres[c].valeur],
        hypotheses_ajoutees=sorted(set(apres) - set(avant)),
        hypotheses_retirees=sorted(set(avant) - set(apres)),
        origines_changees=[c for c in communes if avant[c].origine != apres[c].origine],
        segments_ajoutes=sorted(seg_apres - seg_avant),
        segments_retires=sorted(seg_avant - seg_apres),
        mecanique_changee=signee.mecanique != proposee.mecanique,
        forme_changee=signee.fourchette != proposee.fourchette,
    )


def version_en_attente(versions: list[VersionModele], pv: list[DecisionModele]) -> Optional[VersionModele]:
    """La version que le comité peut décider : la PLUS RÉCENTE proposée, si elle n'a pas encore été
    décidée. Une proposition plus ancienne non décidée est REMPLACÉE, jamais en attente."""
    if not versions:
        return None
    derniere = max(versions, key=lambda v: v.version)
    return None if any(d.modele_id == derniere.id for d in pv) else derniere


def derniere_signature(pv: list[DecisionModele]) -> Optional[DecisionModele]:
    """La signature en vigueur : la plus récente au PV (ordre des `id`, monotone)."""
    signees = [d for d in pv if d.action == "signer"]
    return max(signees, key=lambda d: d.id) if signees else None


def servir_atelier(
    versions: list[VersionModele], pv: list[DecisionModele], dossier: DossierValorisation,
    *, genere_le: Optional[datetime] = None,
) -> AtelierServi:
    """DÉTENTEUR UNIQUE de ce que le comité voit du modèle d'un titre. Pure, déterministe, sans modèle
    de langage : tout est rejoué contre le dossier du jour."""
    par_id = {v.id: v for v in versions}
    signature = derniere_signature(pv)
    signee: Optional[SigneeServie] = None
    if signature is not None:
        v = par_id[signature.modele_id]
        f, motif = _juger(v.modele, dossier)
        signee = SigneeServie(
            version=v, signature=signature, fourchette_du_jour=f,
            etat="tient" if motif is None else "a_revoir",
            motif_etat=("le modèle signé tient contre le dossier du jour" if motif is None else
                        f"le modèle signé ne tient plus contre le dossier du jour : {motif} — la "
                        "fourchette signée reste la référence jusqu'à ce qu'une version mise à jour "
                        "soit signée"))
    attente = version_en_attente(versions, pv)
    proposition: Optional[PropositionServie] = None
    if attente is not None:
        f, motif = _juger(attente.modele, dossier)
        proposition = PropositionServie(
            version=attente, signable=motif is None, motif_refus=motif,
            fourchette=f if motif is None else None,
            ecart=ecart_entre(signee.version.modele, attente.modele) if signee is not None else None)
    etat = {(False, False): "aucun_modele_propose" if not versions else "aucun_modele_signe",
            (False, True): "en_attente_de_signature",
            (True, False): "signe",
            (True, True): "signe_nouvelle_version_en_attente"}[(signee is not None, proposition is not None)]
    return AtelierServi(
        ticker_id=dossier.ticker_id, etat=etat, signee=signee, en_attente=proposition,
        versions_proposees=len(versions),
        proces_verbal=sorted(pv, key=lambda d: d.id, reverse=True),
        genere_le=genere_le or datetime.now(timezone.utc))


# ── Lecture ───────────────────────────────────────────────────────────────────────────────────

# Les pièces COURANTES d'un titre : même périmètre que le corpus de l'analyste (`dossier._SQL_ENTRIES`).
_SQL_PIECES = "SELECT id FROM knowledge_entries WHERE ticker_id = $1 AND superseded_by IS NULL"


def reponses_reprenables(reponses) -> dict[int, str]:
    """answer_id → question_id des réponses dont la valorisation peut reprendre le chiffre : celles qui
    TIENNENT aujourd'hui (`parcours.reponse_tient`, détenteur unique — acquittées ET courantes) et qui
    portent un chiffre (pas un hors-sujet). Un fonds ne reprend pas dans sa valorisation un chiffre que
    son propre dossier marque périmé par un fait publié depuis. ⚠️ Une réponse seulement RETENUE par
    le comité malgré sa faiblesse (#85) n'est pas reprenable : un chiffre de la valorisation doit
    avoir passé le contrôle."""
    from app.agents.v2.parcours import reponse_tient

    return {r.answer_id: r.servie.question_id for r in reponses
            if reponse_tient(r) and r.servie.statut != "sans_objet"}


async def charger_dossier_valorisation(conn, ticker_id: str) -> DossierValorisation:
    """Le dossier du jour : les réponses reprenables (`reponses_reprenables`) et les pièces courantes."""
    from app.agents.v2.parcours import charger_etat_dossier

    etat = await charger_etat_dossier(conn, ticker_id)
    acquittees = reponses_reprenables(etat.reponses)
    pieces = frozenset(r["id"] for r in await conn.fetch(_SQL_PIECES, ticker_id))
    return DossierValorisation(ticker_id=ticker_id, reponses_acquittees=acquittees, pieces_du_dossier=pieces)


_COL_VERSIONS = "id, ticker_id, version, auteur, propose_le, contenu"
_COL_PV = ("d.id, d.modele_id, m.ticker_id, m.version, d.action, d.auteur, d.motif, d.fourchette_bas, "
           "d.fourchette_central, d.fourchette_haut, d.par_evenement, d.decide_le")


def _version(r) -> VersionModele:
    return VersionModele(id=r["id"], ticker_id=r["ticker_id"], version=r["version"], auteur=r["auteur"],
                         propose_le=r["propose_le"], modele=ModeleValorisation.model_validate(r["contenu"]))


def _decision(r) -> DecisionModele:
    f = (Fourchette(bas=r["fourchette_bas"], central=r["fourchette_central"], haut=r["fourchette_haut"],
                    par_evenement={k: tuple(v) for k, v in (r["par_evenement"] or {}).items()})
         if r["action"] == "signer" else None)
    return DecisionModele(id=r["id"], modele_id=r["modele_id"], ticker_id=r["ticker_id"],
                          version=r["version"], action=r["action"], auteur=r["auteur"],
                          motif=r["motif"], fourchette=f, decide_le=r["decide_le"])


async def lire_atelier(conn, ticker_id: str) -> tuple[list[VersionModele], list[DecisionModele]]:
    versions = [_version(r) for r in await conn.fetch(
        f"SELECT {_COL_VERSIONS} FROM modeles_valorisation WHERE ticker_id = $1 ORDER BY version",
        ticker_id)]
    pv = [_decision(r) for r in await conn.fetch(
        f"SELECT {_COL_PV} FROM modeles_valorisation_decisions d "
        "JOIN modeles_valorisation m ON m.id = d.modele_id WHERE m.ticker_id = $1 ORDER BY d.id DESC",
        ticker_id)]
    return versions, pv


# ── Écriture ──────────────────────────────────────────────────────────────────────────────────

async def proposer(conn, modele: ModeleValorisation, *, auteur: str, dossier: DossierValorisation) -> VersionModele:
    """Inscrit une version PROPOSÉE. Refuse (`ActeRefuse`) un modèle qui ne tient pas contre le
    dossier — le comité ne voit jamais une proposition qu'il ne pourrait pas signer le jour même — et
    une numérotation qui ne suit pas le registre (la version N+1 et aucune autre)."""
    if modele.ticker_id != dossier.ticker_id:
        raise ActeRefuse(f"modèle de `{modele.ticker_id}` proposé au dossier de `{dossier.ticker_id}`")
    _f, motif = _juger(modele, dossier)
    if motif is not None:
        raise ActeRefuse(f"le modèle ne tient pas contre le dossier : {motif}")
    if not auteur.strip():
        raise ActeRefuse("une proposition dit qui la fait")
    async with conn.transaction():
        derniere = await conn.fetchval(
            "SELECT coalesce(max(version), 0) FROM modeles_valorisation WHERE ticker_id = $1",
            modele.ticker_id)
        if modele.version != derniere + 1:
            raise ActeRefuse(f"la prochaine version de `{modele.ticker_id}` est la v{derniere + 1}, "
                             f"pas la v{modele.version}")
        r = await conn.fetchrow(
            "INSERT INTO modeles_valorisation (ticker_id, version, schema_version, auteur, contenu) "
            f"VALUES ($1, $2, $3, $4, $5) RETURNING {_COL_VERSIONS}",
            modele.ticker_id, modele.version, modele.schema_version, auteur.strip(),
            modele.model_dump(mode="json"))
    return _version(r)


async def _en_attente(conn, ticker_id: str, version: int) -> VersionModele:
    versions, pv = await lire_atelier(conn, ticker_id)
    visee = next((v for v in versions if v.version == version), None)
    if visee is None:
        raise LookupError(f"aucune version {version} proposée pour `{ticker_id}`")
    attente = version_en_attente(versions, pv)
    if attente is None or attente.id != visee.id:
        decidee = next((d for d in pv if d.modele_id == visee.id), None)
        raise ActeRefuse(
            f"la v{version} a déjà été {'signée' if decidee.action == 'signer' else 'écartée'} "
            f"le {decidee.decide_le:%Y-%m-%d} ({decidee.auteur})" if decidee is not None else
            f"la v{version} a été remplacée par une proposition plus récente (v{attente.version if attente else '?'}) "
            "— le comité décide la version en attente")
    return visee


async def _inscrire(conn, visee: VersionModele, action: str, demande: DemandeDecisionModele,
                    fourchette: Optional[Fourchette]) -> DecisionModele:
    r = await conn.fetchrow(
        "INSERT INTO modeles_valorisation_decisions (modele_id, action, auteur, motif, fourchette_bas, "
        "fourchette_central, fourchette_haut, par_evenement) VALUES ($1, $2, $3, $4, $5, $6, $7, $8) "
        "RETURNING id",
        visee.id, action, demande.auteur, demande.motif,
        fourchette.bas if fourchette else None, fourchette.central if fourchette else None,
        fourchette.haut if fourchette else None,
        ({k: list(v) for k, v in fourchette.par_evenement.items()} if fourchette else None))
    row = await conn.fetchrow(
        f"SELECT {_COL_PV} FROM modeles_valorisation_decisions d "
        "JOIN modeles_valorisation m ON m.id = d.modele_id WHERE d.id = $1", r["id"])
    return _decision(row)


async def signer(conn, *, ticker_id: str, version: int, demande: DemandeDecisionModele,
                 dossier: DossierValorisation) -> DecisionModele:
    """Le comité SIGNE la version en attente. Le pont est rejoué contre le dossier du jour : il signe
    ce qu'il voit, et la fourchette qu'il voit est inscrite au PV."""
    async with conn.transaction():
        visee = await _en_attente(conn, ticker_id, version)
        f, motif = _juger(visee.modele, dossier)
        if motif is not None:
            raise ActeRefuse(f"la v{version} ne tient plus contre le dossier du jour : {motif} — "
                             "elle ne peut pas être signée en l'état")
        return await _inscrire(conn, visee, "signer", demande, f)


async def ecarter(conn, *, ticker_id: str, version: int, demande: DemandeDecisionModele) -> DecisionModele:
    """Le comité ÉCARTE la version en attente, motif écrit ; la version signée, s'il y en a une, reste
    la référence."""
    async with conn.transaction():
        visee = await _en_attente(conn, ticker_id, version)
        return await _inscrire(conn, visee, "ecarter", demande, None)
