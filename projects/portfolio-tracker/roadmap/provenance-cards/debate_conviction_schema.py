"""
Schéma Pydantic versionné du CONVICTION CHALLENGE (debate-agent, option C « Maintenir », §9-§11) —
DÉRIVÉ de la carte de provenance debate_conviction_card.md.

Le debate-agent (renommage de l'opportunity-agent V1) intervient quand un monitoring (mode 2/3/6) a
soulevé un doute et que l'investisseur envisage de MAINTENIR une position. Son rôle n'est PAS de
re-décider : c'est de soumettre la conviction de maintien au test le plus dur (anti-biais de statu
quo : ancrage sur le prix d'entrée, coût irrécupérable, aversion à matérialiser une perte). Il
produit un challenge structuré + une RÉSOLUTION SUGGÉRÉE non contraignante — l'utilisateur tranche.

Ce contrat ferme le trou signalé au lot prompts : contrairement aux 8 agents amont + monitoring
mode 6 + exit/calibration, la sortie du debate-agent n'avait pas de Pydantic figé. Il alimente
`conviction_debates` (statuts open/closed_pass/closed_monitor/closed_proceed, déjà en DB).

Réutilise `Strict`/`NonEmptyRefs`/`BaseRate` d'analysis_v2 (source unique — G1).

Garde-fous encodés :
  G2 anti-complaisance  le maintien doit être MÉRITÉ. Une hypothèse dont le seuil d'INVALIDATION est
      franchi est une dégradation de thèse : on ne peut jamais conclure `closed_proceed` (maintenir
      avec conviction) dessus ; « monitorer » à travers une invalidation exige une escalade synthèse.
  Débat non décoratif  cas_contre_maintien ≥ 1 (un débat sans meilleur cas CONTRE est du théâtre) ;
      chaque contre-argument est sourcé (A2) + ancré (base_rate, règle 2).
  Explicabilité  resolution_rationale non vide (pendant du NO-GO muet interdit au readiness).
  Pont hypothèses  hypotheses_sous_tension référence les hypothèses figées (H1-Hn) ; statut du seuil
      déclaré (aucun/alerte/invalidation) — la direction du seuil n'est pas recomputable ici.
  Pas de verdict d'exécution  resolution_suggeree est une SUGGESTION (contrôle), pas un ordre : ni
      PROCEED/PASSER de synthèse, ni sizing.

Cible : pydantic v2 (container backend 2.13.4). Le python hôte a v1 → tester en container.
"""
from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from analysis_v2_schemas import Strict, NonEmptyRefs, BaseRate, SCHEMA_VERSION

__all__ = [
    "ConvictionChallenge", "HypotheseSousTension", "ContreArgument",
    "SeuilFranchi", "ResolutionDebat", "SCHEMA_VERSION",
]

# statut du seuil pré-enregistré confronté à l'observation courante (déclaré ; direction non recomputable)
SeuilFranchi = Literal["aucun", "alerte", "invalidation"]
# aligné sur les statuts de clôture de conviction_debates (DB) — SUGGÉRÉ, l'utilisateur tranche
ResolutionDebat = Literal["closed_pass", "closed_monitor", "closed_proceed"]


class HypotheseSousTension(Strict):
    """Une hypothèse figée (H1-Hn) remise en cause par le monitoring. Le pont vers la thèse est l'id ;
    le franchissement de seuil est DÉCLARÉ (les seuils peuvent être « au-dessus » ou « en dessous »,
    la direction n'est pas recomputable au niveau du contrat)."""
    hypothese_id: str
    seuil_alerte: float
    seuil_invalidation: float
    valeur_observee: float
    seuil_franchi: SeuilFranchi
    observation: str = Field(min_length=1)
    source_entry_refs: NonEmptyRefs        # A2 : le franchissement est étayé par les entries


class ContreArgument(Strict):
    """Le meilleur cas CONTRE le maintien (pas le plus commode). Sourcé + ancré."""
    titre: str = Field(min_length=1)
    explication: str = Field(min_length=1)
    probabilite: float = Field(ge=0, le=1)
    base_rate: BaseRate                    # règle 2 : probabilité ancrée
    source_entry_refs: NonEmptyRefs        # A2


class ConvictionChallenge(Strict):
    schema_version: Literal["v2.0.0"]
    thesis_id: int
    hypotheses_sous_tension: list[HypotheseSousTension] = Field(min_length=1)
    cas_contre_maintien: list[ContreArgument] = Field(min_length=1)   # débat non décoratif
    biais_a_surveiller: list[str] = Field(min_length=1)              # ancrage_prix_entree, cout_irrecuperable…
    cout_opportunite: str = Field(min_length=1)                       # « maintenir » se juge vs alternatives
    resolution_suggeree: ResolutionDebat                             # SUGGÉRÉE (non contraignante)
    resolution_rationale: str = Field(min_length=1)                  # explicabilité
    escalade_recommandee: bool = False                              # route mode 5 → synthèse si vrai

    @model_validator(mode="after")
    def _anti_complaisance(self):
        # G2 : une hypothèse au seuil d'INVALIDATION franchi = dégradation de thèse.
        invalidees = [h for h in self.hypotheses_sous_tension if h.seuil_franchi == "invalidation"]
        if invalidees:
            # on ne « maintient jamais avec conviction » sur une hypothèse invalidée
            if self.resolution_suggeree == "closed_proceed":
                raise ValueError(
                    "seuil d'invalidation franchi : resolution_suggeree='closed_proceed' interdite "
                    "(dégradation de thèse — maintenir avec conviction n'est pas défendable)"
                )
            # « monitorer » à travers une invalidation exige une escalade vers la synthèse complète
            if self.resolution_suggeree == "closed_monitor" and not self.escalade_recommandee:
                raise ValueError(
                    "seuil d'invalidation franchi + resolution='closed_monitor' exige "
                    "escalade_recommandee=True (re-synthèse, pas un monitoring silencieux)"
                )
        return self
