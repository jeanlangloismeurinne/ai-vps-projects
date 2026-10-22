"""La SIGNATURE DE L'ARCHITECTURE et sa persistance (lot M3, roadmap V3 `12-lot-M3-architecte.md`
§6.2, migration 062). Même geste que `app/valorisation/signature.py` (#46) : `servir_architecture`
PURE (rien de stocké n'est un verdict, #53/#77 — `juger` rejoue le pont et [S1]-[S9] contre la
matière DU JOUR), l'écriture des deux registres (061 proposer, 062 signer/ecarter), l'INTERRUPTEUR
`signature_de_l_architecture` qui décide ce qui est EN VIGUEUR.

⚠️ ATOMICITÉ (#35). `get_db_session()` n'ouvre aucune transaction : `signer`/`ecarter` ouvrent la
leur. Deux signatures concurrentes de la même version : la seconde se heurte à l'unicité de la
décision par version (062) — jamais deux décisions pour une version.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable, Optional

from app.contracts.architecture_signature_schema import (
    ArchitectureServie, DecisionArchitecture, DemandeDecisionArchitecture,
    EnVigueurArchitectureServie, PropositionArchitectureServie, SigneeArchitectureServie,
    VersionArchitecture,
)
from app.contracts.modele_entreprise_schema import Architecture

__all__ = [
    "ActeRefuse", "Juger", "version_en_attente", "derniere_signature", "servir_architecture",
    "lire_registre", "signer", "ecarter",
]

Juger = Callable[[Architecture], tuple[bool, str, tuple[str, ...]]]


class ActeRefuse(ValueError):
    """Le geste n'est pas possible sur CE registre (version remplacée ou déjà décidée, architecture
    qui ne tient plus contre le dossier…). L'endpoint en fait un 409 qui dit pourquoi."""


def version_en_attente(versions: list[VersionArchitecture],
                       pv: list[DecisionArchitecture]) -> Optional[VersionArchitecture]:
    """La version que le comité peut décider : la PLUS RÉCENTE proposée, si elle n'a pas encore été
    décidée. Une proposition plus ancienne non décidée est REMPLACÉE, jamais en attente (#98)."""
    if not versions:
        return None
    derniere = max(versions, key=lambda v: v.version)
    return None if any(d.architecture_id == derniere.id for d in pv) else derniere


def derniere_signature(pv: list[DecisionArchitecture]) -> Optional[DecisionArchitecture]:
    signees = [d for d in pv if d.action == "signer"]
    return max(signees, key=lambda d: d.id) if signees else None


def servir_architecture(
    ticker_id: str, versions: list[VersionArchitecture], pv: list[DecisionArchitecture], *,
    juger: Juger, interrupteur: bool, genere_le: Optional[datetime] = None,
) -> ArchitectureServie:
    """DÉTENTEUR UNIQUE de ce que le comité voit de l'architecture d'un titre. Pure, sans modèle de
    langage : tout est rejoué contre la matière du jour via `juger`.

    ⚠️ Écart assumé à la spec (§6.2) : `ticker_id` est un paramètre EXPLICITE, pas déduit de
    `versions`/`pv` — sans lui, un titre sans AUCUNE architecture proposée (`versions == []`,
    `pv == []`) ne pourrait pas être nommé dans la réponse servie.

    `interrupteur` = `ReferentielModele.signature_de_l_architecture` (§2.1/§6.2) : `true` → la
    SIGNÉE si elle tient, sinon aucune (les relances M4 attendent une nouvelle signature) ; `false`
    → la dernière PROPOSÉE qui tient, signée ou non (cible : une seule signature, celle du
    classeur)."""
    par_id = {v.id: v for v in versions}
    signature = derniere_signature(pv)
    signee: Optional[SigneeArchitectureServie] = None
    if signature is not None:
        v = par_id[signature.architecture_id]
        tient, motif, signaux = juger(v.architecture)
        signee = SigneeArchitectureServie(
            version=v, signature=signature, etat="tient" if tient else "a_revoir",
            motif_etat=("l'architecture signée tient contre le dossier du jour" if tient else
                        f"l'architecture signée ne tient plus contre le dossier du jour : {motif} — "
                        "elle reste affichée jusqu'à ce qu'une version mise à jour soit signée"),
            signaux_du_jour=list(signaux))

    attente = version_en_attente(versions, pv)
    proposition: Optional[PropositionArchitectureServie] = None
    if attente is not None:
        tient, motif, signaux = juger(attente.architecture)
        proposition = PropositionArchitectureServie(
            version=attente, signable=tient, motif_refus=None if tient else motif,
            signaux=list(signaux) if tient else [])

    etat = {(False, False): "aucune_proposee" if not versions else "aucune_signee",
            (False, True): "en_attente_de_signature",
            (True, False): "signee",
            (True, True): "signee_nouvelle_version_en_attente"}[(signee is not None, proposition is not None)]

    if interrupteur:
        if signee is not None and signee.etat == "tient":
            en_vigueur = EnVigueurArchitectureServie(
                version=signee.version,
                motif="architecture signée, tient contre le dossier du jour")
        elif signee is not None:
            en_vigueur = EnVigueurArchitectureServie(
                version=None,
                motif=f"l'architecture signée ne tient plus ({signee.motif_etat}) — les relances "
                     "ciblées (M4) attendent une nouvelle signature")
        else:
            en_vigueur = EnVigueurArchitectureServie(
                version=None, motif="aucune architecture signée — les relances ciblées (M4) "
                "attendent la première signature")
    else:
        candidate: Optional[VersionArchitecture] = None
        for v in sorted(versions, key=lambda v: v.version, reverse=True):
            tient, _motif, _signaux = juger(v.architecture)
            if tient:
                candidate = v
                break
        en_vigueur = EnVigueurArchitectureServie(
            version=candidate,
            motif=("la dernière architecture proposée qui tient aujourd'hui (signature non "
                  f"exigée, v{candidate.version})" if candidate is not None else
                  "aucune architecture proposée ne tient aujourd'hui (signature non exigée)"))

    return ArchitectureServie(
        ticker_id=ticker_id,
        etat=etat, signee=signee, en_attente=proposition, en_vigueur=en_vigueur,
        versions_proposees=len(versions),
        proces_verbal=sorted(pv, key=lambda d: d.id, reverse=True),
        genere_le=genere_le or datetime.now(timezone.utc))


# ── Lecture ───────────────────────────────────────────────────────────────────────────────────────

_COL_VERSIONS = "id, ticker_id, version, auteur, propose_le, contenu"
_COL_PV = ("d.id, d.architecture_id, m.ticker_id, m.version, d.action, d.auteur, d.motif, "
           "d.signaux, d.decide_le")


def _version(r) -> VersionArchitecture:
    return VersionArchitecture(id=r["id"], ticker_id=r["ticker_id"], version=r["version"],
                               auteur=r["auteur"], propose_le=r["propose_le"],
                               architecture=Architecture.model_validate(r["contenu"]))


def _decision(r) -> DecisionArchitecture:
    return DecisionArchitecture(id=r["id"], architecture_id=r["architecture_id"],
                                ticker_id=r["ticker_id"], version=r["version"], action=r["action"],
                                auteur=r["auteur"], motif=r["motif"], signaux=list(r["signaux"] or []),
                                decide_le=r["decide_le"])


async def lire_registre(conn, ticker_id: str) -> tuple[list[VersionArchitecture], list[DecisionArchitecture]]:
    versions = [_version(r) for r in await conn.fetch(
        f"SELECT {_COL_VERSIONS} FROM architectures_modele WHERE ticker_id = $1 ORDER BY version",
        ticker_id)]
    pv = [_decision(r) for r in await conn.fetch(
        f"SELECT {_COL_PV} FROM architectures_modele_decisions d "
        "JOIN architectures_modele m ON m.id = d.architecture_id WHERE m.ticker_id = $1 "
        "ORDER BY d.id DESC", ticker_id)]
    return versions, pv


# ── Écriture ────────────────────────────────────────────────────────────────────────────────────

async def _en_attente(conn, ticker_id: str, version: int) -> VersionArchitecture:
    versions, pv = await lire_registre(conn, ticker_id)
    visee = next((v for v in versions if v.version == version), None)
    if visee is None:
        raise LookupError(f"aucune version {version} proposée pour `{ticker_id}`")
    attente = version_en_attente(versions, pv)
    if attente is None or attente.id != visee.id:
        decidee = next((d for d in pv if d.architecture_id == visee.id), None)
        raise ActeRefuse(
            f"la v{version} a déjà été {'signée' if decidee.action == 'signer' else 'écartée'} "
            f"le {decidee.decide_le:%Y-%m-%d} ({decidee.auteur})" if decidee is not None else
            f"la v{version} a été remplacée par une proposition plus récente "
            f"(v{attente.version if attente else '?'}) — le comité décide la version en attente")
    return visee


async def _inscrire(conn, visee: VersionArchitecture, action: str,
                    demande: DemandeDecisionArchitecture, signaux: list[str]) -> DecisionArchitecture:
    r = await conn.fetchrow(
        "INSERT INTO architectures_modele_decisions (architecture_id, action, auteur, motif, signaux) "
        "VALUES ($1, $2, $3, $4, $5) RETURNING id",
        visee.id, action, demande.auteur, demande.motif, signaux)
    row = await conn.fetchrow(
        f"SELECT {_COL_PV} FROM architectures_modele_decisions d "
        "JOIN architectures_modele m ON m.id = d.architecture_id WHERE d.id = $1", r["id"])
    return _decision(row)


async def signer(conn, *, ticker_id: str, version: int, demande: DemandeDecisionArchitecture,
                 juger: Juger) -> DecisionArchitecture:
    """Le comité SIGNE la version en attente. Le pont + [S1]-[S9] sont rejoués contre la matière du
    jour : le comité signe ce qu'il voit, et les signaux qu'il voit sont inscrits au PV."""
    async with conn.transaction():
        visee = await _en_attente(conn, ticker_id, version)
        tient, motif, signaux = juger(visee.architecture)
        if not tient:
            raise ActeRefuse(f"la v{version} ne tient plus contre le dossier du jour : {motif} — "
                             "elle ne peut pas être signée en l'état")
        return await _inscrire(conn, visee, "signer", demande, list(signaux))


async def ecarter(conn, *, ticker_id: str, version: int,
                  demande: DemandeDecisionArchitecture) -> DecisionArchitecture:
    """Le comité ÉCARTE la version en attente, motif écrit ; la signée, s'il y en a une, reste la
    référence (sous l'interrupteur `true`)."""
    async with conn.transaction():
        visee = await _en_attente(conn, ticker_id, version)
        return await _inscrire(conn, visee, "ecarter", demande, [])
