"""Les règles de la fiche et du registre des sources — l'intérieur du module (rien d'ici ne
s'importe du dehors : on passe par `contrat.py`).

Trois familles :
  · la FICHE : ce qu'une fiche valide contient, et comment une correction devient une révision ;
  · le JOURNAL DES SOURCES : ce qu'un acte d'admission, de révocation ou de mise en suspens doit
    porter, qui a le droit de le faire, et l'état en vigueur reconstruit en relisant le journal ;
  · l'ÉVALUATION d'une source inconnue : la note calculée sur les réponses de l'évaluateur, et la
    décision (admise / en suspens) prise par le code contre le seuil du référentiel ;
  · la QUALIFICATION : ce que vaut une adresse pour une nature d'information, sur un émetteur.

Aucune horloge : la date d'un acte est donnée par celui qui le fait. Aucun réseau, aucun modèle.
Tout vocabulaire (natures, niveaux, genres de lieu, critères, rôles) vient de `referentiel.json`.
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.parse import urlsplit

from .contrat import (
    ADMETTRE,
    AUTEUR_PAGES_INVESTISSEURS,
    CRITERE_PAGES_INVESTISSEURS,
    PORTEE_GENERALE,
    PREFIXE_PORTEE_EMETTEUR,
    PREFIXE_PORTEE_SPECIALITE,
    PREFIXE_SYSTEME,
    REVOQUER,
    SUSPENDRE,
    UTILISATEUR,
    VERSION_CONTRAT,
    ActeRefuse,
    Cotation,
    Depot,
    Evaluation,
    Fiche,
    FicheAbsente,
    Lieu,
    Origine,
    Qualification,
    Reference,
    Signalement,
    SourceAdmise,
    SourceEnSuspens,
    SourceRevoquee,
)

_IDENTIFIANT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,39}$")
_NOM = re.compile(r"^[a-z][a-z0-9_]{0,39}$")
_PAYS = re.compile(r"^[A-Z]{2}$")
_DOMAINE = re.compile(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)+$")


# ── Le référentiel (donnée) ──────────────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def referentiel() -> Mapping[str, Any]:
    """Le vocabulaire et les critères d'admission, lus dans `referentiel.json`. Un référentiel
    incohérent se refuse au chargement : il ne sert jamais « au mieux »."""
    ref = json.loads((Path(__file__).with_name("referentiel.json")).read_text(encoding="utf-8"))
    niveaux, natures = ref["niveaux"], ref["natures"]
    defauts: list[str] = []
    if not str(ref.get("version", "")).strip():
        defauts.append("version absente")
    if len(set(niveaux)) != len(niveaux) or not niveaux:
        defauts.append("niveaux vides ou en double")
    if len(set(natures)) != len(natures) or not natures:
        defauts.append("natures vides ou en double")
    for cle in ("niveau_sans_admission", "niveau_adresse_illisible"):
        if ref.get(cle) not in niveaux:
            defauts.append(f"{cle} hors de l'échelle")
    for genre, g in ref["genres_de_lieu"].items():
        if g["niveau"] not in niveaux:
            defauts.append(f"genre de lieu « {genre} » : niveau hors de l'échelle")
    prefixes = ref.get("prefixes_relations_investisseurs") or []
    if not prefixes or any(not _NOM.match(x) for x in prefixes):
        defauts.append("préfixes des pages de relations investisseurs vides ou mal formés")
    if CRITERE_PAGES_INVESTISSEURS not in ref["criteres"]:
        defauts.append(f"critère « {CRITERE_PAGES_INVESTISSEURS} » absent")
    for nom, c in ref["criteres"].items():
        if c["niveau_max"] not in niveaux or not c["natures"] or not set(c["natures"]) <= set(natures) \
                or not str(c.get("texte", "")).strip():
            defauts.append(f"critère « {nom} » mal formé")
    ev = ref.get("evaluation_des_sources") or {}
    seuil, minimum, questions = ev.get("seuil"), ev.get("exemples_min"), ev.get("questions") or {}
    if not isinstance(seuil, (int, float)) or isinstance(seuil, bool) or not 0 < seuil <= 1:
        defauts.append("évaluation des sources : seuil hors de ]0, 1]")
    if not isinstance(minimum, int) or isinstance(minimum, bool) or minimum < 1:
        defauts.append("évaluation des sources : nombre minimal de publications lues < 1")
    if not questions or any(not _NOM.match(q) or not str(t).strip() for q, t in questions.items()):
        defauts.append("évaluation des sources : questions vides ou mal formées")
    if defauts:
        raise ValueError("référentiel des émetteurs incohérent : " + " ; ".join(defauts))
    return ref


def _rang_niveau(niveau: str) -> int:
    """0 = le plus fiable. Un niveau hors de l'échelle n'a pas de rang : il se refuse."""
    return referentiel()["niveaux"].index(niveau)


# ── Petites validations communes ─────────────────────────────────────────────────────────────

def _texte(valeur: str, quoi: str) -> str:
    v = (valeur or "").strip()
    if not v:
        raise ActeRefuse(f"{quoi} : obligatoire")
    return v


def _date(le: str) -> str:
    try:
        return date.fromisoformat((le or "").strip()).isoformat()
    except ValueError:
        raise ActeRefuse(f"un acte se date (AAAA-MM-JJ) ; reçu : {le!r}") from None


def _auteur(auteur: str) -> str:
    """« utilisateur », ou « systeme:<rôle> ». Rend l'auteur tel qu'il s'écrit au journal."""
    a = (auteur or "").strip()
    if a == UTILISATEUR:
        return a
    if a.startswith(PREFIXE_SYSTEME) and _NOM.match(a[len(PREFIXE_SYSTEME):]):
        return a
    raise ActeRefuse(f"un acte se signe : « {UTILISATEUR} » ou « {PREFIXE_SYSTEME}<rôle> » ; reçu : {auteur!r}")


def _est_systeme(auteur: str) -> bool:
    return auteur.startswith(PREFIXE_SYSTEME)


def _hote_et_chemin(adresse: str) -> tuple[str, str] | None:
    """Le domaine (sans « www. ») et le chemin d'une adresse, avec ou sans protocole. `None` si
    l'adresse ne désigne pas un domaine lisible : dans le doute, on ne reconnaît rien."""
    brut = (adresse or "").strip()
    if not brut:
        return None
    try:
        morceaux = urlsplit(brut if "//" in brut else "//" + brut)
        hote = (morceaux.hostname or "").lower().rstrip(".")
    except ValueError:
        return None
    if hote.startswith("www."):
        hote = hote[4:]
    if not _DOMAINE.match(hote):
        return None
    chemin = morceaux.path.rstrip("/")
    return hote, chemin


def _couvre(domaine: str, hote: str) -> bool:
    """Un domaine couvre ses sous-domaines — jamais un domaine qui lui ressemble."""
    return hote == domaine or hote.endswith("." + domaine)


def _sous_chemin(chemin_lieu: str, chemin: str) -> bool:
    return not chemin_lieu or chemin == chemin_lieu or chemin.startswith(chemin_lieu + "/")


# ── La fiche ─────────────────────────────────────────────────────────────────────────────────

def _contenu_declare(*, emetteur: str, raison_sociale: str, pays: str,
                     cotations: Sequence[tuple[str, str]], references: Sequence[tuple[str, str]],
                     lieux: Sequence[tuple[str, str]], specialite: str) -> dict[str, Any]:
    """Valide ce que l'auteur déclare et le rend sous sa forme rangée (ordre stable)."""
    ref = referentiel()
    if not _IDENTIFIANT.match(emetteur or ""):
        raise ActeRefuse(f"identifiant maison invalide : {emetteur!r} (lettres, chiffres, . _ -, 40 au plus)")
    pays = (pays or "").strip()
    if pays and not _PAYS.match(pays):
        raise ActeRefuse(f"pays : code à deux lettres majuscules, ou rien ; reçu : {pays!r}")
    specialite = (specialite or "").strip()
    if specialite and not _NOM.match(specialite):
        raise ActeRefuse(f"spécialité : un nom en minuscules sans espace, ou rien ; reçu : {specialite!r}")

    cots: list[list[str]] = []
    for place, symbole in cotations:
        cots.append([_texte(place, "cotation — place"), _texte(symbole, "cotation — symbole")])
    if len({tuple(c) for c in cots}) != len(cots):
        raise ActeRefuse("une cotation est déclarée deux fois")

    refs: list[list[str]] = []
    for registre, valeur in references:
        registre = (registre or "").strip()
        if not _NOM.match(registre):
            raise ActeRefuse(f"référence externe : nom de registre invalide ({registre!r})")
        refs.append([registre, _texte(valeur, f"référence « {registre} »")])
    if len({r[0] for r in refs}) != len(refs):
        raise ActeRefuse("deux références externes portent le même registre")

    lx: list[list[str]] = []
    for genre, adresse in lieux:
        if genre not in ref["genres_de_lieu"]:
            raise ActeRefuse(f"lieu de publication : genre inconnu ({genre!r}) ; "
                             f"connus : {', '.join(ref['genres_de_lieu'])}")
        hc = _hote_et_chemin(adresse)
        if hc is None:
            raise ActeRefuse(f"lieu de publication : adresse illisible ({adresse!r})")
        lx.append([genre, hc[0] + hc[1]])
    if len({l[1] for l in lx}) != len(lx):
        raise ActeRefuse("une même adresse est déclarée deux fois comme lieu de publication")

    return {
        "emetteur": emetteur,
        "raison_sociale": _texte(raison_sociale, "raison sociale"),
        "pays": pays,
        "cotations": sorted(cots),
        "references": sorted(refs),
        "lieux": sorted(lx),
        "specialite": specialite,
    }


async def etablir_fiche(depot: Depot, emetteur: str, *, raison_sociale: str, auteur: str, motif: str,
                        le: str, pays: str, cotations: Sequence[tuple[str, str]],
                        references: Sequence[tuple[str, str]], lieux: Sequence[tuple[str, str]],
                        specialite: str) -> Fiche:
    declare = _contenu_declare(emetteur=emetteur, raison_sociale=raison_sociale, pays=pays,
                               cotations=cotations, references=references, lieux=lieux,
                               specialite=specialite)
    signature = {"auteur": _auteur(auteur), "motif": _texte(motif, "motif"), "le": _date(le)}
    rangees = list(await depot.fiches(emetteur))
    if rangees and all(rangees[-1].get(k) == v for k, v in declare.items()):
        raise ActeRefuse(f"la fiche de « {emetteur} » dit déjà exactement cela : aucune révision à ajouter")
    revision = len(rangees) + 1
    contenu = {"version_contrat": VERSION_CONTRAT, "version_referentiel": referentiel()["version"],
               "revision": revision, **declare, **signature}
    await depot.ajouter_fiche(emetteur, revision, contenu)
    return await lire_fiche(depot, emetteur)


def _fiche_depuis(contenu: Mapping[str, Any], sources: tuple[SourceAdmise, ...] = (),
                  revocations: tuple[SourceRevoquee, ...] = (),
                  en_suspens: tuple[SourceEnSuspens, ...] = ()) -> Fiche:
    version = contenu.get("version_contrat")
    if version != VERSION_CONTRAT:
        # Une fiche d'une autre version ne se lit pas « au mieux » : elle se refuse, nommément.
        raise ValueError(f"fiche en version {version!r}, attendu {VERSION_CONTRAT!r}")
    return Fiche(
        emetteur=contenu["emetteur"],
        raison_sociale=contenu["raison_sociale"],
        pays=contenu["pays"],
        cotations=tuple(Cotation(p, s) for p, s in contenu["cotations"]),
        references=tuple(Reference(r, v) for r, v in contenu["references"]),
        lieux=tuple(Lieu(g, a) for g, a in contenu["lieux"]),
        specialite=contenu["specialite"],
        revision=int(contenu["revision"]),
        auteur=contenu["auteur"],
        motif=contenu["motif"],
        le=contenu["le"],
        sources=sources,
        revocations=revocations,
        en_suspens=en_suspens,
        version_referentiel=contenu["version_referentiel"],
    )


def _portees_de(contenu: Mapping[str, Any]) -> set[str]:
    """Les portées qui valent pour un émetteur : la générale, la sienne, et celle de sa spécialité
    s'il en a une. Sans spécialité, rien ne manque : c'est le parcours généraliste."""
    portees = {PORTEE_GENERALE, PREFIXE_PORTEE_EMETTEUR + contenu["emetteur"]}
    if contenu["specialite"]:
        portees.add(PREFIXE_PORTEE_SPECIALITE + contenu["specialite"])
    return portees


async def lire_fiche(depot: Depot, emetteur: str) -> Fiche:
    rangees = list(await depot.fiches(emetteur))
    if not rangees:
        raise FicheAbsente(f"aucune fiche n'est établie pour « {emetteur} »")
    contenu = rangees[-1]
    admises, revoquees, _, suspendues = etat_des_sources(await depot.actes())
    portees = _portees_de(contenu)
    return _fiche_depuis(
        contenu,
        sources=tuple(s for s in admises.values() if s.portee in portees),
        revocations=tuple(r for r in revoquees.values() if r.portee in portees),
        en_suspens=tuple(x for x in suspendues.values() if x.portee in portees),
    )


# ── Le journal des sources ───────────────────────────────────────────────────────────────────

Cle = tuple[str, str]  # (source, portée)


def etat_des_sources(actes: Sequence[Mapping[str, Any]]) -> tuple[
        dict[Cle, SourceAdmise], dict[Cle, SourceRevoquee], dict[Cle, str], dict[Cle, SourceEnSuspens]]:
    """L'état en vigueur, reconstruit en relisant le journal dans l'ordre : ce qui est admis, ce
    qui est révoqué (avec les natures que la révocation a retirées), qui a parlé en dernier sur
    chaque couple (source, portée), et ce qui est en suspens. Un couple est dans UN seul de ces
    états : admis, révoqué (ou écarté), en suspens."""
    admises: dict[Cle, SourceAdmise] = {}
    revoquees: dict[Cle, SourceRevoquee] = {}
    dernier: dict[Cle, str] = {}
    suspendues: dict[Cle, SourceEnSuspens] = {}
    for a in sorted(actes, key=lambda x: int(x["rang"])):
        cle = (a["source"], a["portee"])
        if a["acte"] == ADMETTRE:
            admises[cle] = SourceAdmise(
                source=a["source"], portee=a["portee"], natures=tuple(a["natures"]),
                niveau=a["niveau"], auteur=a["auteur"], critere=a["critere"], motif=a["motif"],
                le=a["le"], rang=int(a["rang"]))
            revoquees.pop(cle, None)
            suspendues.pop(cle, None)  # admise : plus en suspens
        elif a["acte"] == SUSPENDRE:
            ev = a.get("evaluation") or {}
            suspendues[cle] = SourceEnSuspens(
                source=a["source"], portee=a["portee"], natures=tuple(a["natures"]), niveau=a["niveau"],
                critere=a["critere"], note=float(ev.get("note", 0.0)), seuil=float(ev.get("seuil", 0.0)),
                motif=a["motif"], le=a["le"], rang=int(a["rang"]), evaluation=ev)
            admises.pop(cle, None)
            revoquees.pop(cle, None)
        elif a["acte"] == REVOQUER:
            suspendues.pop(cle, None)  # écartée : plus en suspens
            retiree = admises.pop(cle, None)
            revoquees[cle] = SourceRevoquee(
                source=a["source"], portee=a["portee"],
                natures=retiree.natures if retiree else (), auteur=a["auteur"], motif=a["motif"],
                le=a["le"], rang=int(a["rang"]))
        else:
            raise ValueError(f"journal des sources : acte inconnu au rang {a['rang']} ({a['acte']!r})")
        dernier[cle] = a["auteur"]
    return admises, revoquees, dernier, suspendues


def _source(source: str) -> str:
    hc = _hote_et_chemin(source)
    if hc is None or hc[1]:
        raise ActeRefuse(f"une source se nomme par son domaine, sans chemin ; reçu : {source!r}")
    return hc[0]


async def _portee(depot: Depot, portee: str) -> str:
    p = (portee or "").strip()
    if p == PORTEE_GENERALE:
        return p
    if p.startswith(PREFIXE_PORTEE_SPECIALITE) and _NOM.match(p[len(PREFIXE_PORTEE_SPECIALITE):]):
        return p
    if p.startswith(PREFIXE_PORTEE_EMETTEUR):
        emetteur = p[len(PREFIXE_PORTEE_EMETTEUR):]
        if not await depot.fiches(emetteur):
            raise ActeRefuse(f"portée « {p} » : aucune fiche n'existe pour cet émetteur")
        return p
    raise ActeRefuse(f"portée inconnue : {portee!r} (« {PORTEE_GENERALE} », "
                     f"« {PREFIXE_PORTEE_SPECIALITE}<nom> » ou « {PREFIXE_PORTEE_EMETTEUR}<identifiant> »)")


def _refuser_un_role_qui_utilise(auteur: str) -> None:
    """Celui qui utilise une source ne la qualifie jamais (ni pour l'admettre, ni pour la retirer)."""
    role = auteur[len(PREFIXE_SYSTEME):]
    if role in referentiel()["roles_qui_utilisent_les_sources"]:
        raise ActeRefuse(f"le rôle « {role} » utilise les sources : il ne peut pas les qualifier")


async def acter_source(depot: Depot, *, acte: str, source: str, portee: str, natures: Sequence[str],
                       niveau: str, auteur: str, motif: str, le: str, critere: str,
                       evaluation: Mapping[str, Any] | None = None) -> int:
    ref = referentiel()
    auteur = _auteur(auteur)
    motif = _texte(motif, "motif")
    le = _date(le)
    source = _source(source)
    portee = await _portee(depot, portee)
    critere = (critere or "").strip()

    actes = list(await depot.actes())
    admises, _, dernier, suspendues = etat_des_sources(actes)
    cle = (source, portee)

    if _est_systeme(auteur):
        _refuser_un_role_qui_utilise(auteur)
        if dernier.get(cle) == UTILISATEUR:
            raise ActeRefuse(f"« {source} » ({portee}) : l'utilisateur a statué en dernier ; "
                             "le système ne revient pas sur sa décision")

    if acte in (ADMETTRE, SUSPENDRE):
        connues = ref["natures"]
        demandees = {(n or "").strip() for n in natures}
        if not demandees:
            raise ActeRefuse("une admission nomme au moins une nature d'information")
        inconnues = sorted(demandees - set(connues))
        if inconnues:
            raise ActeRefuse(f"nature d'information inconnue : {', '.join(inconnues)}")
        natures_rangees = [n for n in connues if n in demandees]
        if niveau not in ref["niveaux"]:
            raise ActeRefuse(f"niveau inconnu : {niveau!r} (échelle : {', '.join(ref['niveaux'])})")
        if critere and critere not in ref["criteres"]:
            raise ActeRefuse(f"critère d'admission inconnu : {critere!r}")
        if acte == SUSPENDRE and (not _est_systeme(auteur) or not evaluation):
            raise ActeRefuse("seul le système met une source en suspens, et sur une évaluation")
        if _est_systeme(auteur) and (critere or acte == ADMETTRE):
            if not critere:
                raise ActeRefuse("une admission du système cite le critère écrit qu'elle applique")
            regle = ref["criteres"][critere]
            hors = [n for n in natures_rangees if n not in regle["natures"]]
            if hors:
                raise ActeRefuse(f"le critère « {critere} » ne vaut pas pour : {', '.join(hors)}")
            if _rang_niveau(niveau) < _rang_niveau(regle["niveau_max"]):
                raise ActeRefuse(f"le critère « {critere} » n'accorde pas plus que {regle['niveau_max']} ; "
                                 f"demandé : {niveau}")
        en_vigueur = admises.get(cle)
        if acte == SUSPENDRE and en_vigueur:
            raise ActeRefuse(f"« {source} » ({portee}) est admise : on ne la suspend pas, on la révoque")
        if en_vigueur and list(en_vigueur.natures) == natures_rangees and en_vigueur.niveau == niveau:
            raise ActeRefuse(f"« {source} » ({portee}) est déjà admise à l'identique")
        ligne = {"natures": natures_rangees, "niveau": niveau, "critere": critere,
                 "evaluation": dict(evaluation or {})}
    elif acte == REVOQUER:
        if cle not in admises and cle not in suspendues:
            raise ActeRefuse(f"« {source} » ({portee}) n'est ni admise ni en suspens : rien à révoquer")
        ligne = {"natures": [], "niveau": "", "critere": "", "evaluation": {}}
    else:
        raise ActeRefuse(f"acte inconnu : {acte!r}")

    rang = len(actes) + 1
    await depot.ajouter_acte(rang, {"rang": rang, "acte": acte, "source": source, "portee": portee,
                                    "auteur": auteur, "motif": motif, "le": le, **ligne})
    return rang


# ── L'évaluation d'une source inconnue ────────────────────────────────────────────────────────

def noter(evaluation: Evaluation) -> dict[str, Any]:
    """Valide la FORME d'une évaluation et calcule sa note : la part des « oui », sur toutes les
    questions du référentiel, pour toutes les publications lues. Rend l'évaluation telle qu'elle se
    range au journal. Le code ne juge pas le SENS d'une réponse (convention #68) ; il vérifie
    qu'elle porte sur une publication de la source, qu'elle répond à chaque question et qu'elle se
    motive — une forme qui manque ne se « complète » pas, elle se refuse."""
    regle = referentiel()["evaluation_des_sources"]
    questions = list(regle["questions"])
    source = _source(evaluation.source)
    lues: list[dict[str, Any]] = []
    for ex in evaluation.exemples:
        hc = _hote_et_chemin(ex.adresse)
        if hc is None or not _couvre(source, hc[0]):
            raise ActeRefuse(f"publication lue hors de la source évaluée ({source}) : {ex.adresse!r}")
        if any(l["adresse"] == ex.adresse for l in lues):
            raise ActeRefuse(f"la même publication est lue deux fois : {ex.adresse!r}")
        repondues = [r.question for r in ex.reponses]
        if sorted(repondues) != sorted(questions):
            manque = sorted(set(questions) - set(repondues))
            de_trop = sorted(set(repondues) - set(questions))
            raise ActeRefuse(f"{ex.adresse} : chaque question du référentiel reçoit UNE réponse"
                             + (f" ; sans réponse : {', '.join(manque)}" if manque else "")
                             + (f" ; inconnues ou en double : {', '.join(de_trop) or 'doublon'}"
                                if de_trop or len(repondues) != len(set(repondues)) else ""))
        for r in ex.reponses:
            if not (r.constat or "").strip():
                raise ActeRefuse(f"{ex.adresse} — « {r.question} » : une réponse se motive par ce qui a été constaté")
        lues.append({"adresse": ex.adresse,
                     "reponses": [{"question": r.question, "oui": bool(r.oui), "constat": r.constat.strip()}
                                  for r in sorted(ex.reponses, key=lambda r: questions.index(r.question))]})
    total = len(lues) * len(questions)
    oui = sum(1 for l in lues for r in l["reponses"] if r["oui"])
    note = round(oui / total, 4) if total else 0.0
    return {"note": note, "seuil": float(regle["seuil"]), "exemples_min": int(regle["exemples_min"]),
            "version_referentiel": referentiel()["version"], "evaluateur": evaluation.evaluateur,
            "exemples": lues}


async def evaluer_source(depot: Depot, evaluation: Evaluation, *, le: str) -> dict[str, Any]:
    """Arbitrage du 2026-11-14 : une source inconnue est jugée sur quelques publications ; au seuil
    ou au-dessus, le système l'admet ; en dessous, il la met en suspens pour votre arbitrage. Ce que
    ferait un vrai fonds : l'analyste propose une source nouvelle avec quelques articles à l'appui ;
    le responsable de la recherche l'agrée quand la grille est remplie, et tranche lui-même les cas
    limites — l'analyste ne s'en sert pas d'ici là."""
    ev = noter(evaluation)
    note, seuil, minimum = ev["note"], ev["seuil"], ev["exemples_min"]
    n = len(ev["exemples"])
    critere = (evaluation.critere or "").strip()
    if n < minimum:
        verdict = f"trop peu de publications lues pour juger ({n} sur {minimum} au moins)"
    elif not critere:
        verdict = "aucun critère écrit ne convient à cette source"
    elif note < seuil:
        verdict = f"note {note:.2f} sous le seuil {seuil:.2f}"
    else:
        verdict = ""
    acte = SUSPENDRE if verdict else ADMETTRE
    motif = (f"évaluée sur {n} publication(s) : note {note:.2f} (seuil {seuil:.2f})"
             + (f" — en suspens, {verdict} ; attend votre arbitrage" if verdict else f" — admise sous « {critere} »"))
    rang = await acter_source(
        depot, acte=acte, source=evaluation.source, portee=evaluation.portee, natures=evaluation.natures,
        niveau=evaluation.niveau, auteur=evaluation.evaluateur, motif=motif, le=le, critere=critere,
        evaluation=ev)
    return {"issue": "admise" if acte == ADMETTRE else "en_suspens", "rang": rang, "note": note,
            "seuil": seuil, "motif": motif}


# ── Les pages de relations investisseurs des autres sociétés ──────────────────────────────────

def page_investisseurs(adresse: str) -> str | None:
    """Le domaine d'une page de relations investisseurs reconnue à son adresse DÉDIÉE (premier
    élément du nom de domaine : ir., investor., …), ou `None`. Un simple chemin « /investors » sur
    un site quelconque ne suffit pas : n'importe quel blog peut en avoir un ; seul le lieu déclaré
    dans la fiche d'un émetteur fait foi pour un chemin."""
    hc = _hote_et_chemin(adresse)
    if hc is None:
        return None
    hote = hc[0]
    if hote.split(".", 1)[0] not in referentiel()["prefixes_relations_investisseurs"]:
        return None
    if hote.count(".") < 2:
        return None  # « investors.com » est un domaine entier, pas une section d'une société
    return hote


async def admettre_pages_investisseurs(depot: Depot, adresses: Sequence[str], *, le: str) -> list[dict[str, Any]]:
    """Le système admet lui-même, pour toutes les analyses, les pages de relations investisseurs
    des autres sociétés rencontrées dans ces adresses (arbitrage du 2026-11-14). Chaque admission
    est un acte du journal, signé du système, qui cite son critère ; l'utilisateur la révoque s'il
    le juge bon, et le système ne revient pas sur sa décision. Rend une ligne par domaine reconnu :
    admis (avec son rang), déjà admis, ou écarté (avec la raison)."""
    regle = referentiel()["criteres"][CRITERE_PAGES_INVESTISSEURS]
    vus: list[str] = []
    for a in adresses:
        d = page_investisseurs(a)
        if d and d not in vus:
            vus.append(d)
    rendu: list[dict[str, Any]] = []
    for d in vus:
        admises, _, dernier, _ = etat_des_sources(await depot.actes())
        cle = (d, PORTEE_GENERALE)
        if dernier.get(cle) == UTILISATEUR:  # l'utilisateur a statué : on n'y revient pas
            rendu.append({"source": d, "issue": "ecartee", "raison": "l'utilisateur a statué en dernier"})
            continue
        if cle in admises:
            rendu.append({"source": d, "issue": "deja_admise", "rang": admises[cle].rang})
            continue
        rang = await acter_source(
            depot, acte=ADMETTRE, source=d, portee=PORTEE_GENERALE, natures=regle["natures"],
            niveau=regle["niveau_max"], auteur=AUTEUR_PAGES_INVESTISSEURS, critere=CRITERE_PAGES_INVESTISSEURS,
            motif=f"page de relations investisseurs d'une société, reconnue à son adresse dédiée ({d})", le=le)
        rendu.append({"source": d, "issue": "admise", "rang": rang})
    return rendu


# ── La qualification ─────────────────────────────────────────────────────────────────────────

def qualifier(fiche: Fiche, adresse: str, nature: str) -> Qualification:
    ref = referentiel()
    if nature not in ref["natures"]:
        raise ValueError(f"nature d'information inconnue : {nature!r}")
    plancher = ref["niveau_sans_admission"]
    hc = _hote_et_chemin(adresse)
    if hc is None:
        # Une origine qu'on ne sait même pas lire vaut moins qu'une source inconnue mais nommée.
        return Qualification(False, ref["niveau_adresse_illisible"], f"adresse illisible : {adresse!r}")
    hote, chemin = hc

    candidats: list[tuple[int, str, str, str]] = []  # (rang du niveau, niveau, motif, source)

    # Les publications de la société : le lieu le plus précis qui couvre l'adresse.
    lieux = []
    for lieu in fiche.lieux:
        domaine, _, reste = lieu.adresse.partition("/")
        chemin_lieu = "/" + reste if reste else ""
        if _couvre(domaine, hote) and _sous_chemin(chemin_lieu, chemin):
            lieux.append((len(domaine), len(chemin_lieu), lieu))
    if lieux:
        lieu = max(lieux, key=lambda x: (x[0], x[1]))[2]
        niveau = ref["genres_de_lieu"][lieu.genre]["niveau"]
        candidats.append((_rang_niveau(niveau), niveau,
                          f"publication de la société ({lieu.genre}) : {lieu.adresse}", lieu.adresse))

    autres: list[SourceAdmise] = []
    for s in fiche.sources:
        if not _couvre(s.source, hote):
            continue
        if nature in s.natures:
            candidats.append((_rang_niveau(s.niveau), s.niveau,
                              f"{s.source} admise le {s.le} par {s.auteur} ({s.portee}) pour {nature}",
                              s.source))
        else:
            autres.append(s)

    if candidats:
        _, niveau, motif, source = min(candidats, key=lambda c: c[0])
        return Qualification(True, niveau, motif, source)

    if autres:
        s = autres[0]
        return Qualification(False, plancher,
                             f"{s.source} est admise pour {', '.join(s.natures)}, pas pour {nature}", s.source)
    for x in fiche.en_suspens:
        if _couvre(x.source, hote):
            return Qualification(False, plancher,
                                 f"{x.source} en suspens depuis le {x.le} (note {x.note:.2f} sous le seuil "
                                 f"{x.seuil:.2f} ou non jugeable) : attend votre arbitrage", x.source)
    for r in fiche.revocations:
        if _couvre(r.source, hote):
            return Qualification(False, plancher,
                                 f"{r.source} révoquée le {r.le} par {r.auteur} : {r.motif}", r.source)
    return Qualification(False, plancher, f"aucune admission ne couvre {hote}")


def pieces_a_signaler(fiche: Fiche, origines: Sequence[Origine]) -> tuple[Signalement, ...]:
    signalees: list[Signalement] = []
    for o in origines:
        hc = _hote_et_chemin(o.adresse)
        if hc is None:
            continue
        for r in fiche.revocations:
            touchee = _couvre(r.source, hc[0]) and o.nature in r.natures
            if touchee and not qualifier(fiche, o.adresse, o.nature).admise:
                signalees.append(Signalement(piece=o.piece, adresse=o.adresse, nature=o.nature,
                                             source=r.source, revoquee_le=r.le, motif=r.motif))
                break
    return tuple(signalees)


# ── L'écran ──────────────────────────────────────────────────────────────────────────────────

async def vue_ecran(depot: Depot, emetteur: str | None) -> dict[str, Any]:
    ref = referentiel()
    liste = []
    for e in await depot.emetteurs():
        f = _fiche_depuis(list(await depot.fiches(e))[-1])
        liste.append({"emetteur": f.emetteur, "raison_sociale": f.raison_sociale,
                      "specialite": f.specialite, "revision": f.revision, "le": f.le})
    actes = sorted((dict(a) for a in await depot.actes()), key=lambda a: int(a["rang"]))
    admises, _, _, suspendues = etat_des_sources(actes)
    en_vigueur = {s.rang for s in admises.values()} | {x.rang for x in suspendues.values()}
    for a in actes:
        a["en_vigueur"] = a["acte"] in (ADMETTRE, SUSPENDRE) and int(a["rang"]) in en_vigueur
    vue: dict[str, Any] = {
        "version_contrat": VERSION_CONTRAT,
        "emetteurs": liste,
        "journal_des_sources": actes,
        # Ce qui attend votre arbitrage, toutes portées confondues, le plus ancien d'abord.
        "en_suspens": [asdict(x) for x in sorted(suspendues.values(), key=lambda x: x.rang)],
        "referentiel": {k: ref[k] for k in ("version", "natures", "niveaux", "niveau_sans_admission",
                                             "niveau_adresse_illisible",
                                             "genres_de_lieu", "criteres", "evaluation_des_sources")},
    }
    if emetteur is not None:
        vue["fiche"] = asdict(await lire_fiche(depot, emetteur))
        vue["revisions"] = [dict(c) for c in await depot.fiches(emetteur)]
    return vue
