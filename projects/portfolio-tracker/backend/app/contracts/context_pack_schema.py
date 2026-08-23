"""
Schéma Pydantic versionné du `context_pack` (curator, §7 + §5.3) — DÉRIVÉ des cartes de provenance.

Artefact distillé produit par le curator quand `readiness = ready` : l'état des connaissances par
dimension MVDD + les `source_entry_refs`. Persisté comme `knowledge_entry` source_type='agent_synthesis'
(versionné) — c'est le mécanisme de réutilisation DURABLE (§5.3) : research/bull/bear/synthèse le
rechargent en tête de prompt, donc l'assessment du curator n'est jamais jeté, et le prompt caching
l'amortit. Le `readiness_report_json` répond « peut-on décider ? » ; le `context_pack` répond
« avec quoi décide-t-on ? ».

Réutilise `SourceEntryRef` / `NonEmptyRefs` / `BaseRatePct` / `Tier` d'analysis_v2_schemas (source
unique — G1). Le snapshot figé A1/A2 (entry_version, content_snapshot, reliability_at_use) se
matérialise dans `analysis_knowledge_refs` au store, comme pour toute analyse — le JSON ne porte
que la référence (entry_id, version).

Garde-fous encodés :
  A2 (grounding)  agent_synthesis est « dérivé de sources, non originale » : CHAQUE dimension porte
      des source_entry_refs NON VIDES. Une synthèse sans citation est rejetée.
  READY-ONLY  le front-load n'existe que si `readiness_verdict='ready'` (cf. readiness_report_card :
      `ready ⇒ context_pack_entry_id`). Le gate Opus est en amont ; le pack en est le fruit.
  COMPLÉTUDE  couvre EXACTEMENT les 8 dimensions MVDD (ready exige les 2 blocs au plancher → toutes
      couvertes). Mêmes dimensions que readiness Coverage (aucun trou, aucune dimension fantôme).
  DISCIPLINE CACHE (§5.3)  aucun champ volatil (pas de generated_at/session_id — extra='forbid') ;
      dimensions en ordre CANONIQUE ; refs triées par (entry_id, version) → sérialisation déterministe
      → cacheable en tête de prompt. Interdits en tête réglés structurellement.

Cible : pydantic v2 (container backend 2.13.4). Tester en container (host = v1).
"""
from __future__ import annotations

from typing import Literal

from pydantic import ConfigDict, Field, model_validator

from .analysis_v2_schemas import (
    Strict, SourceEntryRef, NonEmptyRefs, BaseRatePct, Tier, SCHEMA_VERSION,
)

__all__ = ["ContextPack", "DimensionDigest", "SCHEMA_VERSION"]

Bloc = Literal["structuree", "qualitative_marche"]

# ordre CANONIQUE des dimensions MVDD (§7) — figé pour la discipline de cache (§5.3).
# Aligné sur _DIMS_STRUCTUREE / _DIMS_QUALITATIVE de readiness_report_schema.py.
CANONICAL_DIMS: list[tuple[str, str]] = [
    ("structuree", "business_model"),
    ("structuree", "financials"),
    ("structuree", "valorisation"),
    ("qualitative_marche", "produits"),
    ("qualitative_marche", "positionnement"),
    ("qualitative_marche", "marche"),
    ("qualitative_marche", "management_allocation"),
    ("qualitative_marche", "risques"),
]


class DimensionDigest(Strict):
    """État distillé d'une dimension MVDD. `synthese` = le condensé lisible (Markdown) ; le grounding
    est DÉLÉGUÉ aux refs (jamais de synthèse hors-sol — A2)."""
    bloc: Bloc
    dimension: str
    synthese: str = Field(min_length=1)      # distillé — état des connaissances de la dimension
    tier_atteint: Tier                       # meilleur tier des sources distillées
    source_entry_refs: NonEmptyRefs          # A2 : agent_synthesis DOIT citer ses sources
    incertitudes: list[str] = Field(default_factory=list)  # résiduelles (investissables) sur la dim

    @model_validator(mode="after")
    def _refs_triees(self):
        # discipline cache : refs déterministes (triées par entry_id puis version)
        cle = [(r.entry_id, r.version) for r in self.source_entry_refs]
        if cle != sorted(cle):
            raise ValueError(f"{self.dimension}: source_entry_refs non triées (déterminisme cache §5.3)")
        return self


class ContextPack(Strict):
    schema_version: Literal["v2.0.0"]
    ticker_id: str
    readiness_report_id: int                 # de quel readiness ce pack est le fruit
    readiness_verdict: Literal["ready"]       # front-load ⇒ ready uniquement
    dimensions: list[DimensionDigest]         # exactement les 8 dims MVDD, ordre canonique
    base_rates_reutilisables: list[BaseRatePct] = Field(default_factory=list)  # corpus sectoriel §6.6

    @model_validator(mode="after")
    def _completude_et_ordre(self):
        got = [(d.bloc, d.dimension) for d in self.dimensions]
        # complétude : exactement les 8 dimensions MVDD (aucun trou, aucune fantôme)
        if set(got) != set(CANONICAL_DIMS):
            manquantes = set(CANONICAL_DIMS) - set(got)
            surplus = set(got) - set(CANONICAL_DIMS)
            raise ValueError(
                f"dimensions incomplètes/hors MVDD — manquantes={sorted(manquantes)} "
                f"surplus={sorted(surplus)}"
            )
        # ordre canonique (discipline cache §5.3 : JSON trié en tête de prompt)
        if got != CANONICAL_DIMS:
            raise ValueError("dimensions pas dans l'ordre canonique (déterminisme cache §5.3)")
        return self
