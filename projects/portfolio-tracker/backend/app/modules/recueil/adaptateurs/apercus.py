"""Un aperçu n'est pas une pièce, c'est un signal (M2 §7, accord de l'utilisateur du 2026-11-19).

Ce que fait un analyste devant un fil d'agence dont il ne lit que le chapeau : il va chercher la
pièce d'origine (le communiqué de la société), ou le texte complet de la dépêche chez un diffuseur
qui la reprend sous licence. Ici : UNE recherche par le titre de l'aperçu, hors du domaine de
l'agence, avec le texte des résultats ; puis du code, sans modèle :
- un résultat sur un lieu de la fiche de l'émetteur est une pièce d'origine candidate ;
- un texte qui nomme l'agence, contient mot pour mot une phrase entière de l'aperçu et est plus
  long que lui est une reprise reconnue. Aucune liste de diffuseurs : la règle se vérifie sur le texte.

Le diffuseur n'est pas une source : c'est un lieu de lecture. La reprise garde l'adresse de la
publication de l'agence (c'est l'agence que M1 qualifie) et nomme le diffuseur (`lu_chez`).
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from app.modules.chef_de_dossier.contrat import Depense
from app.modules.emetteurs import contrat as E

from . import MoteurInjoignable, Resultat, Texte, referentiel_de


def ref() -> Mapping[str, Any]:
    return referentiel_de("apercus.json")


@dataclass
class Suite:
    """Ce que le suivi d'un aperçu a trouvé : les pièces d'origine candidates (sur les lieux donnés,
    dans l'ordre du moteur), la reprise reconnue, ce qu'il a coûté, et ce qui a été constaté."""
    origine: list[Resultat] = field(default_factory=list)
    reprise: Texte | None = None
    depense: Depense = field(default_factory=Depense)
    detail: str = ""


_INVISIBLES = re.compile(r"[​-‏⁠﻿]")
_GUILLEMETS = str.maketrans({"’": "'", "‘": "'", "“": '"', "”": '"', "«": '"', "»": '"'})


def _norme(texte: str) -> str:
    t = _INVISIBLES.sub("", unicodedata.normalize("NFKC", texte)).translate(_GUILLEMETS)
    return re.sub(r"\s+", " ", t).strip().lower()


def phrases(texte: str) -> list[str]:
    """Les phrases de l'aperçu qui l'identifient : entières (coupées aux fins de phrase, aux
    paragraphes et aux élisions « ... » du moteur), d'au moins `mots_min_par_phrase` mots, sans titre."""
    n = int(ref()["mots_min_par_phrase"])
    out: list[str] = []
    for bloc in re.split(r"\n\s*\n|\.\.\.|…", texte):
        for p in re.split(r"(?<=[.!?\"\u201d])\s+", bloc.strip()):
            p = _norme(p)
            if len(p.split()) >= n and not p.startswith("#") and p not in out:
                out.append(p)
    return out


def interrompu(texte: str, *, plafond: int = 0) -> bool:
    """Le texte s'arrête-t-il en cours de phrase (en plein mot ou entre deux mots) ? C'est la marque
    d'un texte que le site a coupé (M2 §8) ; un texte qui atteint `plafond` (ce que l'équipe demande
    au moteur) a été coupé par nous, il n'est pas suspect."""
    t = texte.strip().rstrip(ref()["fermants"]).rstrip()
    if not t or (plafond and len(texte.strip()) >= plafond):
        return False
    return t[-1] not in ref()["fins_de_phrase"]


def nom_de_l_agence(source: str) -> str:
    """« reuters.com » → reuters ; « nikkei.co.jp » → nikkei ; « markets.ft.com » → ft."""
    etiquettes = [e for e in source.lower().split(".") if e]
    if len(etiquettes) >= 2:
        etiquettes = etiquettes[:-1]
        if len(etiquettes) >= 2 and etiquettes[-1] in ref()["suffixes_de_second_niveau"]:
            etiquettes = etiquettes[:-1]
    return etiquettes[-1] if etiquettes else ""


def nomme(source: str, texte: str) -> bool:
    """Le texte nomme-t-il l'agence ? Un mot, ou deux mots accolés (« Les Echos » → lesechos)."""
    nom = nom_de_l_agence(source)
    mots = re.findall(r"[a-z0-9]+", _norme(texte))
    return bool(nom) and (nom in mots or any(a + b == nom for a, b in zip(mots, mots[1:])))


def phrase_commune(apercu: str, candidat: str) -> str:
    """La première phrase de l'aperçu que le candidat contient mot pour mot, ou ""."""
    c = _norme(candidat)
    return next((p for p in phrases(apercu) if p in c), "")


def reprise_reconnue(apercu: Texte, source: str, candidat: Resultat) -> str:
    """Le motif de la reconnaissance si le candidat est une reprise de l'aperçu, sinon ""."""
    if len(candidat.texte) <= len(apercu.texte) or not nomme(source, candidat.texte):
        return ""
    p = phrase_commune(apercu.texte, candidat.texte)
    return f"nomme {nom_de_l_agence(source)}, contient « {p[:120]} »" if p else ""


def _sur(adresse: str, domaines: Sequence[str]) -> bool:
    d = E.domaine(adresse) or ""
    return any(d == s or d.endswith("." + s) for s in domaines if s)


async def suivre(moteur: Any, apercu: Texte, *, source: str, lieux: Sequence[str] = ()) -> Suite:
    """UNE recherche par le titre de l'aperçu, hors du domaine de `source` ; `lieux` : les domaines où
    une pièce d'origine peut se trouver (ceux de la fiche de l'émetteur), vide pour n'en chercher aucune."""
    if not apercu.titre.strip():
        return Suite(detail="aperçu sans titre : rien à chercher")
    try:
        resultats, depense = await moteur.rechercher(apercu.titre.strip(), exclus=[source],
                                                     nombre=int(ref()["nombre"]), avec_texte=True)
    except MoteurInjoignable as exc:
        return Suite(detail=f"moteur de recherche : {exc}")
    suite = Suite(depense=depense)
    suite.origine = [r for r in resultats if lieux and _sur(r.adresse, lieux)]
    for r in resultats:
        if _sur(r.adresse, [source]) or r in suite.origine:
            continue
        motif = reprise_reconnue(apercu, source, r)
        if motif:
            suite.reprise = Texte(apercu.adresse, r.texte, apercu.titre or r.titre, apercu.publie_le or r.publie_le,
                                  lu_chez=r.adresse)
            suite.detail = f"reprise lue chez {r.adresse} ({motif})"
            break
    if not suite.reprise:
        suite.detail = (f"{len(resultats)} résultat(s) pour « {apercu.titre.strip()} », "
                        f"{len(suite.origine)} sur les lieux de l'émetteur, aucune reprise reconnue")
    return suite
