"""
Contrat runtime de la SYNTHÈSE GROUNDED (ingestion-agent, mode synthèse) — SCHEMA_VERSION v2.0.0.

Ce contrat est DISTINCT de `ingestion_extraction_schema.py` (C2 « document → entries »), qui décrit
l'extraction de masse d'un document brut et interdit structurellement `agent_synthesis`. Ici on couvre
l'AUTRE chemin de l'ingestion-agent décrit dans 00-REPRISE (MàJ 2026-08-26) : composer une entry de
**synthèse** pour un champ qualitatif que le fetch ne peut PAS fonder (ex. `produits.unit_economics`,
`marche.structure_5forces`), STRICTEMENT à partir d'entries tier A/A-/B+ déjà en base.

Invariant central (anti-hallucination, G3/#24/#25/#28) : le modèle n'apporte AUCUN fait hors-KB. Chaque
assertion (`SynthesisClaim`) doit citer ≥1 `entry_id`. La vérification que ces ids appartiennent bien au
corpus citable, et la DÉRIVATION du tier, sont faites en Python par `synthesis_feed` (jamais déclarées
par le modèle — cf. #24). Le tier n'est donc PAS dans ce contrat : le modèle ne le choisit pas.

Cible : pydantic v2 (container backend 2.13.4). Tester en container (host = v1).
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

SCHEMA_VERSION = "v2.1.0"


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SynthesisClaim(_Strict):
    """Une assertion atomique de la synthèse, adossée à ≥1 entry citée. Sans citation, l'assertion
    serait un fait hors-KB (interdit) — d'où `min_length=1` sur `cited_entry_ids`."""
    text: str = Field(min_length=1)
    cited_entry_ids: list[int] = Field(min_length=1)

    @model_validator(mode="after")
    def _ids_positifs(self):
        if any(i <= 0 for i in self.cited_entry_ids):
            raise ValueError("cited_entry_ids doit contenir des entry_id positifs")
        return self


class Approximation(_Strict):
    """Le 4ᵉ barreau de l'échelle d'escalade : la donnée n'est pas obtenable, on l'APPROCHE à partir
    des pièces déjà au dossier, et on dit comment.

    Chaque champ existe pour une raison de fond :
      • `methode` — le calcul en toutes lettres. Une estimation dont personne ne peut refaire le
        chemin n'est pas une estimation, c'est un chiffre.
      • `sens_erreur` — TROIS états, jamais deux (#44). « 80,5 % » et « 80,5 % au plancher » ne se
        lisent pas pareil : le second dit que le vrai chiffre est au-dessus.
      • `hypotheses` — `min_length=1`. Une approximation SANS hypothèse énoncée est une mesure
        déguisée, et c'est précisément le mode de panne que la capacité 5 corrige.
      • `cited_entry_ids` — `min_length=1`. Les ingrédients viennent du corpus ou n'existent pas :
        approcher un chiffre n'est PAS une autorisation d'apporter un fait hors-KB.

    Ce que ce contrat NE porte PAS, délibérément : le tier de l'estimation. Il est DÉRIVÉ en Python
    (« un cran sous la pièce citée la plus faible », second emploi de la règle des synthèses) — le
    modèle ne s'auto-note pas, même sur une estimation (#24).
    """
    valeur: str = Field(min_length=1)          # le chiffre approché, AVEC son unité, en toutes lettres
    methode: str = Field(min_length=1)         # le calcul refaisable : « 267 143 / 331 839 = 80,5 % »
    sens_erreur: Literal["plancher", "plafond", "indetermine"]
    hypotheses: list[str] = Field(min_length=1)
    cited_entry_ids: list[int] = Field(min_length=1)

    @model_validator(mode="after")
    def _ids_positifs(self):
        if any(i <= 0 for i in self.cited_entry_ids):
            raise ValueError("Approximation.cited_entry_ids doit contenir des entry_id positifs")
        return self


class LacuneDeclaree(_Strict):
    """Une QUESTION que la synthèse a posée et n'a pas pu refermer.

    ⚠️ Le cœur de la capacité 5, et la raison d'être de ce contrat. Le prompt de synthèse PRESCRIT
    déjà de déclarer le trou (« écris "non documenté en base" plutôt que de le reconstruire »), et le
    modèle obéit : ~20 trous déclarés sur le corpus NVDA+MSFT au 2026-09-09. Mais ils atterrissent en
    PROSE, dans `synthesis_markdown` — invisibles à tout lecteur, à la porte de couverture, à l'écran.
    C'est la forme exacte de la convention #55 : *une règle juste chez le PRODUCTEUR reste aveugle au
    LECTEUR tant que son discriminant n'est pas DANS la ligne.* Ce modèle met le trou dans la ligne.

    L'unité est la QUESTION, pas le critère (arbitrage utilisateur 2026-09-09). Une synthèse peut être
    parfaitement fondante pour son champ ET porter trois questions ouvertes : le critère reste `fondé`,
    les questions sont nommées à l'écran, et approchées quand les pièces le permettent. Traiter la
    PIÈCE comme non fondante dès qu'elle mentionne une absence fabriquerait 3 fausses lacunes pour en
    corriger 1 vraie — mesuré sur corpus réel avant d'écrire ce contrat.
    """
    question: str = Field(min_length=1)        # l'information cherchée, en toutes lettres
    # DEUX causes nommées, jamais une seule : elles n'appellent pas le même remède, et c'est la
    # distinction que la capacité 4 a déjà payée entre `collecte` et `rafraichissement`.
    #   non_publie_source  → l'émetteur ne publie pas ce chiffre : information SUR l'émetteur, une
    #                        collecte de plus ne le trouvera jamais.
    #   non_documente_base → le corpus ne le porte pas encore : vrai trou de collecte.
    statut: Literal["non_publie_source", "non_documente_base"]
    approximation: Optional[Approximation] = None   # None = aucune méthode tenable (5ᵉ barreau)


class GroundedSynthesis(_Strict):
    """Sortie du tour LLM. Le backend (`synthesis_feed`) vérifie le grounding, dérive le tier et
    persiste. Le modèle NE fournit ni source_type, ni reliability_* (dérivés), ni le field cible
    (imposé par le mandat) — il compose la prose et l'adosse aux entries."""
    title: str = Field(min_length=1)
    synthesis_markdown: str = Field(min_length=1)
    claims: list[SynthesisClaim] = Field(min_length=1)
    # ⚠️ REQUIS, mais peut être VIDE — et la nuance est le point. Avec un défaut `= []`, un modèle qui
    # omet le champ produirait la même valeur qu'un modèle qui affirme « je n'ai rien laissé ouvert » :
    # « pas demandé » et « rien à signaler » se liraient identiquement, ce qui est le trou silencieux
    # qu'on est en train de fermer. Requis, l'omission devient une erreur de contrat — bruyante.
    lacunes: list[LacuneDeclaree]
    lang: str = "fr"

    def approximation_entry_ids(self) -> list[int]:
        """Union triée des ids cités par les APPROXIMATIONS. Distincte de `cited_entry_ids()` : une
        pièce peut fonder une estimation sans fonder aucune assertion de la synthèse (cas MSFT — #64
        porte le CA total, il ne dit rien du taux de récurrence)."""
        seen: set[int] = set()
        for lac in self.lacunes:
            if lac.approximation is not None:
                seen.update(lac.approximation.cited_entry_ids)
        return sorted(seen)

    def cited_entry_ids(self) -> list[int]:
        """Union dé-dupliquée, triée, des ids cités par toutes les assertions."""
        seen: set[int] = set()
        for c in self.claims:
            seen.update(c.cited_entry_ids)
        return sorted(seen)
