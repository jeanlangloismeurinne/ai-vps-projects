"""L'ancien code lit la fiche de l'émetteur (module M1) — acceptation A15 de `M1-fiche-emetteur.md`.

Avant M1, l'ancien code tenait lui-même ses sources : le site de trois sociétés, quatre listes de
domaines (`websearch`), un registre de quatre publications et la spécialité d'un titre
(`source_registry`). Tout cela vit désormais dans la fiche et son journal des sources, datés, motivés
et signés ; ce fichier est le SEUL endroit de l'ancien code qui les lit, et il ne lit que le contrat du
module (`app/modules/emetteurs/contrat.py`).

Le module rend un NIVEAU (A, A-, B+…) ; l'ancien code parle en `source_type`, qui porte aussi le score
de `service.RELIABILITY_TABLE` (A vaut 0,95 pour un dépôt officiel, 0,90 pour une page investisseurs).
La traduction se fait par ce que la fiche dit de la source — le GENRE du lieu de publication, ou le
CRITÈRE écrit de l'admission —, jamais par une liste de domaines : un critère inconnu de cette table
est une erreur nommée, pas un repli silencieux.

Trois qualifications, parce que l'ancien code en a trois usages (l'ordre est load-bearing, voir
l'en-tête de l'ancien `source_registry`, dont la règle est reprise ici) :
  · `source_type_generique` : ce que la source vaut QUELLE QUE SOIT la nature de l'information — le
    plus bas des niveaux sur les natures. La nature d'une entrée se dérive de celui-ci : le dériver
    d'un niveau accordé pour une seule nature serait circulaire.
  · `source_type_max` : le plafond montré au modèle avant qu'il ne rédige — le plus haut des niveaux.
  · `qualifier` : la qualification d'une entrée, pour SA nature ; une source admise pour
    l'interprétation n'a aucun standing sur une mesure chiffrée.

Sans fiche (émetteur inconnu ou non désigné), aucune source n'est admise (A10, A11) : ce qui n'a pas
de fiche n'a pas de sources tenues pour fiables. Les producteurs qui déclarent eux-mêmes leur
`source_type` (un dépôt lu à la SEC par `edgar_feed`, par exemple) ne sont pas touchés : seule une
source qualifiée par défaut, `web_search_generic`, passe par la fiche.
"""
from __future__ import annotations

import logging
from typing import Optional
from urllib.parse import urlsplit

from app.agents.v2.common import NATURES, derive_nature
from app.modules.emetteurs import contrat as E

logger = logging.getLogger(__name__)

NON_ADMISE = "web_search_generic"
SANS_URL = "llm_memory"

# Le genre du lieu → `source_type` (une société qui publie elle-même).
_PAR_GENRE: dict[str, str] = {
    "relations_investisseurs": "company_ir_official",
    "site": "web_search_reputable",
}
# Le critère écrit de l'admission → `source_type`. Une autorité publique se distingue par son niveau :
# A pour celle qui reçoit les dépôts (la SEC), A- pour les régulateurs européens — mêmes scores que
# l'ancien code.
_PAR_CRITERE: dict[str, str | dict[str, str]] = {
    "autorite_publique": {"A": "edgar_official", "A-": "regulator_filing_eu"},
    E.CRITERE_PAGES_INVESTISSEURS: "company_ir_official",
    "presse_financiere": "financial_press",
    "organisme_publiant_ses_estimations": "web_search_reputable",
    "redaction_specialisee": "web_search_reputable",
}
_NATURES: tuple[str, ...] = tuple(sorted(NATURES))


class CritereNonTraduit(LookupError):
    """La fiche admet une source sous un critère (ou un niveau) que l'ancien code ne sait pas
    traduire : on le dit, au lieu de lui prêter un score au hasard."""


def fiche_vide(emetteur: Optional[str]) -> E.Fiche:
    """Ce que voit l'ancien code d'un émetteur sans fiche : aucun lieu, aucune source admise."""
    return E.Fiche(emetteur=(emetteur or "").strip().upper(), raison_sociale="")


async def charger(conn, emetteur: Optional[str]) -> E.Fiche:
    """La fiche en vigueur, relue à chaque appel (une révocation vaut dès qu'elle est actée).
    Sans fiche : la fiche vide, et l'absence est journalisée — c'est un acte qui reste à faire."""
    code = (emetteur or "").strip().upper()
    if not code:
        return fiche_vide(None)
    try:
        return await E.lire_fiche(E.depot_base(conn), code)
    except E.FicheAbsente:
        logger.warning("fiche de l'émetteur absente pour %s : aucune source n'est admise", code)
        return fiche_vide(code)


def _source_type(fiche: E.Fiche, q: E.Qualification, nature: str) -> str:
    if not q.admise:
        return NON_ADMISE
    for lieu in fiche.lieux:
        if lieu.adresse == q.source:
            return _PAR_GENRE[lieu.genre]
    for s in fiche.sources:
        if s.source == q.source and nature in s.natures and s.niveau == q.niveau:
            regle = _PAR_CRITERE.get(s.critere)
            if isinstance(regle, dict):
                regle = regle.get(s.niveau)
            if regle is None:
                raise CritereNonTraduit(f"{s.source} : critère {s.critere!r} au niveau {s.niveau!r}")
            return regle
    raise CritereNonTraduit(f"qualification sans admission correspondante : {q}")


def _par_nature(fiche: E.Fiche, url: str) -> dict[str, str]:
    return {n: _source_type(fiche, E.qualifier(fiche, url, n), n) for n in _NATURES}


def _rang(source_type: str) -> float:
    from .service import RELIABILITY_TABLE  # import tardif : service importe ce fichier
    return RELIABILITY_TABLE[source_type][1]


def source_type_generique(url: Optional[str], fiche: E.Fiche) -> str:
    """Ce que la source vaut quelle que soit la nature de l'information. Sans URL → `llm_memory`."""
    if not url or not urlsplit(url).netloc:
        return SANS_URL
    return min(_par_nature(fiche, url).values(), key=_rang)


def source_type_max(url: Optional[str], fiche: E.Fiche) -> str:
    """Le plafond affiché au modèle : le meilleur cas, car l'entrée n'a pas encore de nature."""
    if not url or not urlsplit(url).netloc:
        return SANS_URL
    return max(_par_nature(fiche, url).values(), key=_rang)


def est_lieu_de_la_societe(url: Optional[str], fiche: E.Fiche) -> bool:
    """Vrai si l'adresse relève d'un lieu où la société publie elle-même."""
    if not url:
        return False
    q = E.qualifier(fiche, url, _NATURES[0])
    return any(lieu.adresse == q.source for lieu in fiche.lieux)


def domaines_de_la_societe(fiche: E.Fiche) -> tuple[str, ...]:
    """Les domaines où la société publie (sans chemin), pour interroger d'abord la source d'origine."""
    domaines = {lieu.adresse.split("/", 1)[0] for lieu in fiche.lieux}
    # Un sous-domaine d'un domaine déjà interrogé n'apporte rien (`ir.revmed.com` sous `revmed.com`).
    return tuple(sorted(d for d in domaines if not any(d.endswith("." + autre) for autre in domaines)))


def qualifier(
    *,
    source_type: str,
    url: Optional[str],
    fiche: E.Fiche,
    entry_type: str,
    content: Optional[str] = None,
    nature_declaree: Optional[str] = None,
) -> tuple[str, str, str]:
    """`(source_type, nature, motif)` — le passage unique des deux sites qui qualifient une entrée
    (le search-worker avant son plancher, `service.store_knowledge` à l'écriture).

    La nature se dérive du `source_type` reçu, le générique. Seule une source qualifiée par défaut
    (`web_search_generic`) passe ensuite par la fiche, pour CETTE nature : une qualification déjà
    établie par un producteur déterministe n'est jamais touchée (#33). `content` est transmis à
    `derive_nature`, son seul lecteur (#46, #78).
    """
    nature, motif = derive_nature(
        entry_type=entry_type, source_type=source_type, content=content, declared=nature_declaree,
    )
    if source_type != NON_ADMISE or not url:
        return source_type, nature, motif
    q = E.qualifier(fiche, url, nature)
    accorde = _source_type(fiche, q, nature)
    motif += f" ; fiche de {fiche.emetteur or '—'} : {q.motif}"
    return accorde, nature, motif
