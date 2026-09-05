"""Registre NOMINATIF des sources admises — capacité 2 de `roadmap/02-spec-autorite-vs-actualite.md`.

**Le standing n'est pas une propriété de la source, c'est une propriété du couple
(source × nature)** (convention #50). Une rédaction spécialisée peut valoir B sur une
*interprétation* et rester C+ sur une *mesure chiffrée* : la même page, le même domaine, le même
jour. Une table à une entrée par domaine — ce qu'est `websearch._REPUTABLE_SUFFIXES` — ne peut pas
exprimer ça, et c'est pourquoi le correctif du défaut d'autorité n'est pas « monter les blogs ».

Ce module est le **détenteur unique** (#46) de la règle d'admission. Les deux sites qui qualifient
une source (`agents/v2/worker.py` au filtre de plancher, `knowledge/service.py` à l'écriture)
appellent la MÊME fonction `qualify()` — ils ne ré-implémentent rien. C'est délibéré : le worker
rejette sous plancher AVANT d'écrire (mesuré sur NVDA : 5 entrées produites, 5 rejetées), donc un
registre appliqué seulement à l'écriture n'admettrait jamais personne — il serait un no-op
silencieux, exactement le mode de panne de #32 (un plancher qu'aucune source ne peut atteindre).

⚠️ **L'ordre des deux règles est load-bearing.** La nature se dérive du `source_type` **GÉNÉRIQUE**
(celui du domaine seul), et le registre s'applique **ensuite**, conditionné à cette nature. L'ordre
inverse serait circulaire : le registre fixerait le source_type qui fixerait la nature qui
conditionne le registre. Concrètement, un `fact_financial` sur une source admise pour
`interpretation` reste `web_search_generic` — la promotion ne le suit pas sur le terrain de la
mesure.

Ce que ce module **refuse de faire**, et qui n'est pas une omission :

- **Aucune promotion automatique**, ni par corroboration. En biotech, *N* rédactions qui reprennent
  le même communiqué ne sont pas *N* sources indépendantes : la corroboration deviendrait un
  amplificateur de rumeur. L'admission est nominative, datée et motivée par écrit.
- **Aucune démotion.** Le registre ne promeut QUE `web_search_generic`. Un domaine déjà qualifié par
  une règle générique (presse financière, IR d'émetteur, régulateur) n'est jamais touché — piège
  #33 : une règle spécifique ne resserre jamais la règle générique au passage.
- **Aucun tier au-delà de B.** `_TIER_VERS_SOURCE_TYPE` n'a qu'une entrée : une admission qui
  demanderait B+ lève `TierNonSupporte` au chargement plutôt que d'accorder B en silence. Un
  desserrage tacite doit faire rougir un assert (`feedback_optional_schema_gate`), pas se ranger
  sous le plafond le plus proche.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional, Sequence
from urllib.parse import urlparse

from app.agents.v2.common import NATURES, derive_nature


class TierNonSupporte(ValueError):
    """Une admission demande un tier que le registre ne sait pas accorder."""


# Le registre ne connaît qu'une promotion, et elle est écrite en toutes lettres : `web_search_generic`
# (C+ 0.50) → `web_search_reputable` (B 0.65). B est exactement le plancher des trois champs desserrés
# par la capacité 0 (`positionnement.moat_preuves`, `positionnement.position_vs_pairs`,
# `marche.structure_5forces`) — c'est le bénéficiaire qui leur manquait, et rien de plus.
# Passer par un `source_type` DÉJÀ au vocabulaire évite un changement de contrat C1 (règle #19 :
# 3 points de synchro, dont les 12 prompts en base).
_TIER_VERS_SOURCE_TYPE: dict[str, str] = {"B": "web_search_reputable"}
_PROMOUVABLE = "web_search_generic"


@dataclass(frozen=True)
class SourceAdmise:
    """Une admission. `portee` est `secteur:<nom>` ou `ticker:<id>` — les deux sur le même pied.

    La portée se décide **à l'admission, source par source** : une rédaction qui suit toute la
    biotech clinique s'admet par secteur (le prochain émetteur du secteur en hérite sans recopie) ;
    une source qui ne vaut que pour un émetteur s'admet par ticker. Clefer le registre sur
    `tickers.sector` en base a été écarté sur une mesure : la colonne est **NULL sur les 17
    tickers**, donc un registre qui la lirait n'admettrait personne, sans rien dire.
    """
    domain: str
    portee: str
    natures: frozenset[str]
    tier: str
    admis_le: date
    motif: str

    def __post_init__(self) -> None:
        if self.tier not in _TIER_VERS_SOURCE_TYPE:
            raise TierNonSupporte(
                f"{self.domain} : tier {self.tier!r} demandé, seuls {sorted(_TIER_VERS_SOURCE_TYPE)} "
                "sont accordables. Élargir le plafond est une décision de doctrine (le « desserrage "
                "déguisé » nommé comme risque principal de la roadmap 02), pas un ajout de ligne."
            )
        inconnues = set(self.natures) - set(NATURES)
        if inconnues:
            raise ValueError(f"{self.domain} : natures hors vocabulaire {sorted(inconnues)}")
        if not self.natures:
            raise ValueError(f"{self.domain} : admise pour aucune nature — admission vide")
        if not self.motif.strip():
            raise ValueError(f"{self.domain} : admission sans motif écrit")

    @property
    def source_type_accorde(self) -> str:
        return _TIER_VERS_SOURCE_TYPE[self.tier]


# ── Secteur d'un émetteur, déclaré ICI et pas lu en base ─────────────────────
# `tickers.sector` est vide sur la totalité des 17 tickers (vérifié le 2026-09-05). Faire dépendre
# une règle de qualification d'une colonne éditable et non renseignée, c'est accepter qu'un émetteur
# perde ses sources admissibles parce qu'un champ d'IHM est resté vide — une panne muette. Défaut =
# aucun secteur, donc aucune source héritée (même politique que `issuer_domains_for` : on refuse un
# privilège de trop, on n'en accorde jamais par défaut).
_TICKER_SECTEURS: dict[str, str] = {
    "RVMD": "biotech_clinique",
}

# ── Les admissions ───────────────────────────────────────────────────────────
# Amorçage biotech clinique, validé par l'utilisateur le 2026-09-05. Les quatre sont admises pour
# `interpretation` SEULEMENT : aucune ne peut fonder une mesure chiffrée, et c'est ce qui rend
# l'ouverture acceptable. Sur un champ d'interprétation, la section « facteurs de risque » d'un 10-K
# est du boilerplate juridique malgré son tier A, tandis qu'une rédaction qui suit les essais
# cliniques et le calendrier réglementaire est strictement meilleure — le système la classait 0.50.
_ADMISES: tuple[SourceAdmise, ...] = (
    SourceAdmise(
        domain="endpts.com", portee="secteur:biotech_clinique",
        natures=frozenset({"interpretation"}), tier="B", admis_le=date(2026, 9, 5),
        motif="Rédaction spécialisée biotech à couverture clinique et réglementaire de fond. "
              "Standing sur l'interprétation (lecture concurrentielle d'un résultat d'essai, "
              "portée d'une décision d'agence) ; aucun standing sur le chiffre, qui reste au dépôt.",
    ),
    SourceAdmise(
        domain="statnews.com", portee="secteur:biotech_clinique",
        natures=frozenset({"interpretation"}), tier="B", admis_le=date(2026, 9, 5),
        motif="Rédaction santé/biotech analysant les données d'essais et leur contexte "
              "réglementaire. Admise pour l'interprétation ; les chiffres qu'elle cite sont des "
              "reprises, et une reprise n'ajoute rien à la source primaire (elle ajoute un risque "
              "de transcription).",
    ),
    SourceAdmise(
        domain="fiercebiotech.com", portee="secteur:biotech_clinique",
        natures=frozenset({"interpretation"}), tier="B", admis_le=date(2026, 9, 5),
        motif="Couverture sectorielle large, plus proche du fil d'actualité que de l'analyse de "
              "fond. Utile pour situer un émetteur dans son paysage concurrentiel ; B est le "
              "plafond juste, et l'analyste doit le lire dans le tier.",
    ),
    SourceAdmise(
        domain="biopharmadive.com", portee="secteur:biotech_clinique",
        natures=frozenset({"interpretation"}), tier="B", admis_le=date(2026, 9, 5),
        motif="Analyse sectorielle et concurrentielle — angle « position face aux pairs », qui est "
              "l'un des trois champs desserrés B+ → B sans bénéficiaire jusqu'ici.",
    ),
)


def secteur_de(ticker_id: Optional[str]) -> Optional[str]:
    """Secteur déclaré de l'émetteur. Ticker inconnu → `None`, donc aucune source héritée."""
    return _TICKER_SECTEURS.get((ticker_id or "").strip().upper())


def _domaine(url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    host = (urlparse(url).netloc or "").lower()
    return host.removeprefix("www.") or None


def _portees_actives(ticker_id: Optional[str]) -> set[str]:
    portees = {f"ticker:{(ticker_id or '').strip().upper()}"}
    secteur = secteur_de(ticker_id)
    if secteur:
        portees.add(f"secteur:{secteur}")
    return portees


def admissions_pour(url: Optional[str], ticker_id: Optional[str]) -> tuple[SourceAdmise, ...]:
    """Admissions applicables à cette URL pour CET émetteur, toutes natures confondues.

    Le sous-domaine hérite du domaine admis (`www.endpts.com`, `news.endpts.com`) : l'admission
    porte sur une rédaction, pas sur un préfixe d'hôte.
    """
    bare = _domaine(url)
    if not bare:
        return ()
    portees = _portees_actives(ticker_id)
    return tuple(
        s for s in _ADMISES
        if s.portee in portees and (bare == s.domain or bare.endswith("." + s.domain))
    )


def plafond_registre(url: Optional[str], ticker_id: Optional[str]) -> Optional[str]:
    """`source_type` le plus favorable que le registre puisse accorder, TOUTES natures confondues.

    Sert au moment de la RECHERCHE, où la nature de la future entry n'existe pas encore : le
    `source_type_max` affiché au modèle est un **plafond** (« on borne, on ne promeut pas »), et un
    plafond se calcule sur le meilleur cas. La qualification exacte, elle, est rendue par
    `qualify()` à l'écriture et peut être strictement plus basse. Sous-qualifier ici ferait écarter
    une source admise avant même qu'elle soit lue.
    """
    admissions = admissions_pour(url, ticker_id)
    return admissions[0].source_type_accorde if admissions else None


def qualify(
    *,
    source_type: str,
    url: Optional[str],
    ticker_id: Optional[str],
    entry_type: str,
    covers: Optional[Sequence[str]] = None,
    nature_declaree: Optional[str] = None,
) -> tuple[str, str, str]:
    """`(source_type, nature, motif)` — le passage unique des deux sites de qualification.

    Appelée par `worker._resolve_source_type` (avant le filtre de plancher) ET par
    `service.store_knowledge` (à l'écriture), sur les MÊMES entrées : les deux ne peuvent donc pas
    diverger, même schéma que le recalcul de `compute_reliability` déjà fait deux fois.

    La nature est dérivée du `source_type` reçu, c'est-à-dire du GÉNÉRIQUE — voir l'avertissement en
    tête de module. Le registre ne s'applique qu'ensuite, et seulement à `web_search_generic`.
    """
    nature, motif = derive_nature(
        entry_type=entry_type, source_type=source_type, covers=covers, declared=nature_declaree,
    )
    if source_type != _PROMOUVABLE:
        return source_type, nature, motif

    admissions = admissions_pour(url, ticker_id)
    if not admissions:
        return source_type, nature, motif

    retenue = next((s for s in admissions if nature in s.natures), None)
    if retenue is None:
        # Le domaine EST au registre, mais pas pour cette nature-là. On le dit : un refus muet se
        # lirait comme un domaine inconnu, alors que c'est une admission délibérément bornée.
        natures_admises = sorted({n for s in admissions for n in s.natures})
        motif += (
            f" ; registre : `{_domaine(url)}` admis pour {natures_admises} seulement, "
            f"aucun standing sur `{nature}` — reste `{_PROMOUVABLE}`"
        )
        return source_type, nature, motif

    motif += (
        f" ; registre : `{retenue.domain}` admis {retenue.admis_le.isoformat()} "
        f"({retenue.portee}) pour `{nature}` → tier {retenue.tier}"
    )
    return retenue.source_type_accorde, nature, motif
