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

from pydantic import BaseModel, ConfigDict, Field, model_validator

SCHEMA_VERSION = "v2.0.0"


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


class GroundedSynthesis(_Strict):
    """Sortie du tour LLM. Le backend (`synthesis_feed`) vérifie le grounding, dérive le tier et
    persiste. Le modèle NE fournit ni source_type, ni reliability_* (dérivés), ni le field cible
    (imposé par le mandat) — il compose la prose et l'adosse aux entries."""
    title: str = Field(min_length=1)
    synthesis_markdown: str = Field(min_length=1)
    claims: list[SynthesisClaim] = Field(min_length=1)
    lang: str = "fr"

    def cited_entry_ids(self) -> list[int]:
        """Union dé-dupliquée, triée, des ids cités par toutes les assertions."""
        seen: set[int] = set()
        for c in self.claims:
            seen.update(c.cited_entry_ids)
        return sorted(seen)
