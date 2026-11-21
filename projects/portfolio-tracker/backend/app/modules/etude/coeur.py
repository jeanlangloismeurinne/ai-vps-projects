"""Le cœur du déclencheur : mettre à l'étude, passer sur un dossier, lever un arrêt.

Un passage, dans cet ordre (M3 §2 ; arbitrages du 2026-11-21) :

  1. le dossier est-il à l'étude ? sinon rien (K10) ; un autre passage le tient-il ? alors rien ;
  2. RELEVER — sauf si le dossier est en pause de dépense ou terminé : rien de payant ne se lance
     alors (les collectes lancées attendent, les sources rencontrées aussi) ;
       · répondre aux demandes de collecte lancées pour CE dossier (M2) ;
       · faire juger les sources inconnues rencontrées pour CE dossier (M2 → M1) ;
  3. LIRE — mettre en lecture les documents arrivés (M3, code sans modèle, gratuit : même en pause) ;
  4. AVANCER ET RANGER, dans UNE transaction : l'état du dossier (chef de dossier) et ce que ses pas
     ont décidé (les demandes à lancer, la dépense déclarée) sont rangés ensemble ou pas du tout.

Chaque étape écrit dans sa propre transaction ; seule la 4 doit être atomique (elle seule lie l'état
du dossier à ce qu'il lance). Une panne en 2 ou 3 n'empêche pas la 4 : elle se dit dans le passage.

Les besoins de documents ne sont pas écrits ici : chaque module consommateur les déclare dans son
référentiel (M3 §2, point 1) ; le passage les rassemble (le même genre une fois) et en fait le pas de
collecte. Rien ici ne connaît une société, un pays ni un formulaire.
"""
from __future__ import annotations

import asyncio
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Mapping, Sequence

from app.modules.chef_de_dossier import contrat as CD
from app.modules.comptes import contrat as COMPTES
from app.modules.connaissance import contrat as K
from app.modules.emetteurs import contrat as E
from app.modules.recueil import contrat as R

from .contrat import (
    AVANCE,
    DEJA_EN_COURS,
    INTERROMPU,
    NON_ETUDIE,
    RIEN_DE_NEUF,
    VERSION_CONTRAT,
    Etude,
    EtudeLue,
    GesteRefuse,
    Monde,
    Passage,
)

_REFERENTIEL = Path(__file__).resolve().parent / "referentiel.json"


def referentiel() -> Mapping[str, Any]:
    with _REFERENTIEL.open(encoding="utf-8") as f:
        return json.load(f)


# ── Les besoins ──────────────────────────────────────────────────────────────────────────────

def besoins_des_consommateurs() -> dict[str, list[dict[str, Any]]]:
    """Les besoins initiaux déclarés par chaque module consommateur du parcours, lus par son contrat.
    Un module consommateur de plus = une ligne ici (et son pas au parcours, quand il en aura un) ;
    ni la collecte, ni la lecture, ni le chef de dossier, ni le rassemblement ne changent."""
    return {COMPTES.NOM_DU_MODULE: COMPTES.besoins_initiaux()}


def rassembler(besoins: Mapping[str, Sequence[Mapping[str, Any]]], dossier: str) -> list[R.Demande]:
    """Les demandes de collecte d'un dossier : chaque besoin des modules, le même (genre, depuis)
    une seule fois, dans l'ordre où ils sont déclarés. Un besoin mal formé est refusé ici, avant toute
    exécution, avec le module qui l'a déclaré."""
    genres = R.genres()
    demandes: dict[str, R.Demande] = {}
    for module, liste in besoins.items():
        for b in liste:
            inconnus = set(b) - {"genre", "depuis"}
            if inconnus or not str(b.get("genre", "")).strip():
                raise R.DemandeRefusee(f"besoin mal formé déclaré par « {module} » : {dict(b)}")
            genre = genres.get(b["genre"])
            if genre is None:
                raise R.DemandeRefusee(f"« {module} » déclare un genre de document inconnu : {b['genre']!r}")
            if (genre["etendue"] == "depuis") != bool(str(b.get("depuis", "")).strip()):
                raise R.DemandeRefusee(f"« {module} » : le genre {b['genre']!r} s'étend "
                                       f"« {genre['etendue']} », sa date « depuis » ne va pas ({dict(b)})")
            d = R.Demande(genre=b["genre"], emetteur=dossier, depuis=str(b.get("depuis", "")))
            demandes.setdefault(d.cle, d)
    if not demandes:
        raise R.DemandeRefusee("aucun module ne déclare de besoin : rien à collecter")
    return list(demandes.values())


# ── Le parcours ──────────────────────────────────────────────────────────────────────────────

def parcours(dossier: str, *, fiche: Any, demandes: Sequence[R.Demande], vue_recueil: R.VueTravaux,
             vue_lecture: K.VueLecture, envoi: R.Envoi) -> list[CD.Pas]:
    """Le parcours d'un dossier aujourd'hui : la fiche, la collecte des besoins, le suivi de
    l'évaluation des sources qu'elle rencontre, la mise en lecture. Chaque module accepté y ajoutera
    son pas."""
    noms = referentiel()["pas"]
    return [
        E.pas_fiche(fiche),
        R.pas_collecte(noms["collecte"], list(demandes), vue_recueil, envoi),
        R.pas_evaluation(noms["evaluation"], dossier, vue_recueil, envoi, apres=(noms["collecte"],)),
        K.pas_lecture(noms["lecture"], vue_lecture, apres=(noms["collecte"],)),
    ]


# ── Le passage ───────────────────────────────────────────────────────────────────────────────

async def _fiche(monde: Monde, dossier: str) -> Any:
    """La fiche de l'émetteur, ou None : sans fiche, le pas de la fiche nomme l'acte attendu."""
    try:
        return await E.lire_fiche(monde.emetteurs, dossier)
    except E.FicheAbsente:
        return None


def _payant_suspendu(etat: CD.EtatDossier) -> bool:
    """Rien de payant ne se lance sur un dossier en pause de dépense, ni sur un dossier terminé."""
    return etat.arret is not None and etat.arret.motif in (CD.ARRET_PAUSE_DEPENSE, CD.ARRET_PARCOURS_TERMINE)


async def _peek(monde: Monde, dossier: str) -> CD.EtatDossier:
    return CD.lire_etat(await monde.chef.ouvrir(dossier), dossier)


async def passer(monde: Monde, dossier: str, *, le: str) -> Passage:
    if await monde.etude.etude(dossier) is None:  # non étudié : rien ne se fait
        return Passage(dossier=dossier, le=le, issue=NON_ETUDIE)
    if not await monde.etude.prendre(dossier):
        return Passage(dossier=dossier, le=le, issue=DEJA_EN_COURS)
    try:
        return await _passer(monde, dossier, le=le)
    finally:
        await monde.etude.rendre(dossier)


async def _passer(monde: Monde, dossier: str, *, le: str) -> Passage:
    pannes: list[str] = []
    collectes: list[Mapping[str, Any]] = []
    sources: list[Mapping[str, Any]] = []
    lectures: list[Mapping[str, Any]] = []

    # 2. Relever (payant).
    suspendu = _payant_suspendu(await _peek(monde, dossier))
    if not suspendu:
        if monde.outils is None:
            if any(t["statut"] == R.LANCEE for t in await monde.recueil.travaux(dossier)):
                pannes.append("collecte : aucun outil de collecte donné à ce passage")
        else:
            try:
                async with monde.transaction():
                    collectes = await R.traiter_les_travaux(depot=monde.recueil, emetteurs_depot=monde.emetteurs,
                                                            outils=monde.outils, le=le, emetteur=dossier)
            except Exception as exc:  # noqa: BLE001 — une panne se dit dans le passage, la suite continue
                pannes.append(f"collecte : {type(exc).__name__}: {exc}")
        if monde.evaluateur is not None:
            try:
                async with monde.transaction():
                    sources = await R.evaluer_les_sources_rencontrees(
                        depot=monde.recueil, emetteurs_depot=monde.emetteurs, evaluateur=monde.evaluateur,
                        le=le, emetteur=dossier)
            except Exception as exc:  # noqa: BLE001
                pannes.append(f"évaluation des sources : {type(exc).__name__}: {exc}")

    # 3. Lire (gratuit).
    try:
        async with monde.transaction():
            lectures = await K.lire_documents(monde.connaissance, recueil_depot=monde.recueil,
                                              emetteur=dossier, le=le)
    except Exception as exc:  # noqa: BLE001
        pannes.append(f"mise en lecture : {type(exc).__name__}: {exc}")

    # 4. Avancer et ranger, ensemble ou pas du tout.
    avant = apres = None
    try:
        async with monde.transaction():  # ensemble ou pas du tout
            depot = await monde.chef.ouvrir(dossier)
            avant = CD.lire_etat(depot, dossier)
            envoi = R.Envoi()
            fiche = await _fiche(monde, dossier)
            demandes = rassembler(besoins_des_consommateurs(), dossier)
            pas = parcours(dossier, fiche=fiche, demandes=demandes,
                           vue_recueil=await R.vue_travaux(monde.recueil, dossier),
                           vue_lecture=await K.vue_lecture(monde.connaissance, recueil_depot=monde.recueil,
                                                          emetteur=dossier),
                           envoi=envoi)
            apres = CD.avancer(avant, pas, lecture_humaine=referentiel()["lecture_humaine"])
            depot.ranger(dossier, apres.vers_dict())
            await R.ranger_envoi(monde.recueil, envoi)
            await monde.chef.refermer(dossier, depot)
    except Exception as exc:  # noqa: BLE001 — rien n'est rangé ; le passage suivant reprendra
        pannes.append(f"avancement du dossier : {type(exc).__name__}: {exc}")
        apres = None

    nouveaux = () if apres is None or avant is None else tuple(
        f"{l.pas or '—'} : {l.evenement}" + (f" ({l.detail})" if l.detail else "")
        for l in apres.journal[len(avant.journal):])
    a_bouge = bool(collectes or sources or lectures or nouveaux or pannes)
    final = apres if apres is not None else avant
    passage = Passage(
        dossier=dossier, le=le, issue=AVANCE if a_bouge else RIEN_DE_NEUF,
        collectes=tuple(collectes), sources=tuple(sources),
        lectures=tuple({k: l[k] for k in ("empreinte", "statut", "lignes", "raison")} for l in lectures),
        evenements=nouveaux, arret="" if final is None or final.arret is None else final.arret.motif,
        payant_suspendu=suspendu, detail=" ; ".join(pannes))
    if a_bouge:
        await monde.etude.noter_passage(asdict(passage))
    return passage


async def traiter_les_dossiers(monde: Monde, *, le: str, delai_par_dossier_s: float | None = None) -> list[Passage]:
    delai = referentiel()["passage"]["delai_par_dossier_s"] if delai_par_dossier_s is None else delai_par_dossier_s
    rendus = []
    for e in await monde.etude.etudes():
        try:
            rendus.append(await asyncio.wait_for(passer(monde, e["dossier"], le=le), timeout=delai))
        except asyncio.TimeoutError:
            # Arrêté en route : ce qui était en transaction est annulé, le verrou rendu (`passer`) ;
            # le passage suivant reprend. Noté, pour qu'un dossier qui bloque à chaque fois se voie.
            p = Passage(dossier=e["dossier"], le=le, issue=INTERROMPU,
                        detail=f"passage arrêté après {delai:g} s : le dossier reprendra au passage suivant")
            await monde.etude.noter_passage(asdict(p))
            rendus.append(p)
    return rendus


# ── Les gestes ────────────────────────────────────────────────────────────────────────────────

async def mettre_a_l_etude(monde: Monde, dossier: str, *, par: str, motif: str, le: str) -> Etude:
    if not par.strip() or not motif.strip():
        raise GesteRefuse("une mise à l'étude dit qui la décide et pourquoi")
    if await _fiche(monde, dossier) is None:
        raise GesteRefuse(f"aucune fiche n'existe pour « {dossier} » : établissez-la avant de mettre la "
                          "société à l'étude")
    etude = Etude(dossier=dossier, mise_le=le, par=par.strip(), motif=motif.strip())
    if not await monde.etude.ajouter_etude(asdict(etude)):   # déjà à l'étude : l'étude d'origine
        return Etude(**(await monde.etude.etude(dossier)))
    return etude


async def geste(monde: Monde, dossier: str, quoi: str, *, le: str, cle: str = "",
                pas: str | None = None) -> str:
    """Un geste qui lève un arrêt du dossier : appliqué à l'état rangé et rangé à son tour (refusé si
    un passage a rangé entre-temps — rien n'est écrasé ; il suffit de refaire le geste)."""
    if await monde.etude.etude(dossier) is None:
        raise GesteRefuse(f"« {dossier} » n'est pas à l'étude")
    async with monde.transaction():
        depot = await monde.chef.ouvrir(dossier)
        etat = CD.lire_etat(depot, dossier)
        try:
            if quoi == "acte":
                etat = CD.enregistrer_acte(etat, cle)
            elif quoi == "pause":
                etat = CD.lever_pause(etat)
            elif quoi == "relance":
                etat = CD.relancer(etat, pas)
            else:
                raise GesteRefuse(f"geste inconnu : {quoi!r}")
        except CD.GesteRefuse as exc:
            raise GesteRefuse(str(exc)) from exc
        depot.ranger(dossier, etat.vers_dict())
        await monde.chef.refermer(dossier, depot)
    return CD.afficher(etat)


# ── La lecture ───────────────────────────────────────────────────────────────────────────────

def _passage(p: Mapping[str, Any]) -> Passage:
    return Passage(**{**p, **{k: tuple(p[k]) for k in ("collectes", "sources", "lectures", "evenements")}})


async def lire_etudes(monde: Monde) -> list[EtudeLue]:
    rendus = []
    for e in await monde.etude.etudes():
        passages = await monde.etude.passages(e["dossier"])
        etat = await _peek(monde, e["dossier"])
        rendus.append(EtudeLue(etude=Etude(**e), dernier_passage=_passage(passages[-1]) if passages else None,
                               dossier_en_clair=CD.afficher(etat)))
    return rendus


# ── L'écran ──────────────────────────────────────────────────────────────────────────────────

def libelle_acte(cle: str, acte: str) -> str:
    """L'acte en mots de gérant (référentiel) ; une clé absente garde le libellé du chef de dossier."""
    return referentiel()["libelles_actes"].get(cle) or acte


async def vue_ecran(monde: Monde, dossier: str) -> dict[str, Any]:
    etude = await monde.etude.etude(dossier)
    etat = await _peek(monde, dossier)
    d = etat.vers_dict()
    if d["arret"] is not None:
        a = d["arret"]
        a["libelle"] = libelle_acte(a["cle"], a["acte"]) if a["acte"] else ""
        for x in a["attentes"]:
            x["libelle"] = libelle_acte(x["cle"], x["acte"]) if x["acte"] else ""
    passages = list(await monde.etude.passages(dossier)) if etude is not None else []
    return {
        "version_contrat": VERSION_CONTRAT,
        "dossier": dossier,
        "etude": etude,
        "passages": list(reversed(passages))[:int(referentiel()["passages_a_l_ecran"])],
        "etat": d,
        "en_clair": CD.afficher(etat),
        "intervalle_min": int(referentiel()["passage"]["intervalle_min"]),
        "lecture_humaine": dict(referentiel()["lecture_humaine"]),
    }
