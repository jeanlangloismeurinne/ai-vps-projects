"""
Schéma Pydantic versionné du contrat de DÉCISION / VALIDATION (§9, §14 migration 026) — DÉRIVÉ des cartes.

`POST /theses/{id}/validate` fige la décision d'entrée. C'est le point où G2 s'exerce le plus fort :
**la décision est CONTRAINTE par l'analyse, indépendante de l'UX.** L'utilisateur ne « saisit » pas
une position — il acquitte une analyse et le contrat vérifie que l'acte est cohérent avec le verdict,
le sizing capé et les risques de la synthèse. Un `PROCEED` forcé sur des risques non acceptés, ou un
sizing au-dessus du plafond Kelly, est rejeté — le pendant décisionnel du `ready` forcé du readiness.

Réutilise `RiskMatrix` (la synthèse), `Hypothese`, `valider_pont_risques_hypotheses` d'analysis_v2
(source unique — G1). Le contrat ne recopie pas la synthèse : il la référence et se valide contre elle.

Garde-fous encodés :
  G2 verdict actionnable  on ne valide QUE PROCEED | PROCEED_AVEC_CONDITIONS. PASSER/SURVEILLER/
      TOO_HARD ne créent pas de position.
  §9 acquittements complets  bijection stricte risk_acks ↔ risques_acceptes (chaque risque accepté
      exactement une fois) ; pre_mortem_acked=True obligatoire. Bouton « Valider » = ces invariants.
  Q6 cap Kelly  position_sizing_pct ≤ pct_max ; et = pct_recommande, SAUF override tracé (A7) où
      il doit égaler override_utilisateur.valeur_pct. Aucun sizing « libre ».
  falsifiabilité  chaque risque accepté pointe une hypothèse existante (pont) ; chaque hypothèse
      porte son seuil_invalidation (hérité de Hypothese) — pilote le monitoring.
  PROCEED_AVEC_CONDITIONS ⇒ conditions_entree non vide (figées depuis la synthèse).
  valuation_range figée + cohérente (low ≤ base ≤ high).

Cible : pydantic v2 (container backend 2.13.4). Tester en container (host = v1).
"""
from __future__ import annotations

from typing import Literal

from pydantic import ConfigDict, Field, model_validator

from analysis_v2_schemas import (
    Strict, RiskMatrix, Hypothese, valider_pont_risques_hypotheses, SCHEMA_VERSION,
)

__all__ = ["ThesisValidation", "RiskAck", "ValuationRange", "SCHEMA_VERSION"]

_VERDICTS_ACTIONNABLES = {"PROCEED", "PROCEED_AVEC_CONDITIONS"}


class RiskAck(Strict):
    """Acquittement d'un risque accepté (§9 : « J'accepte ce risque », obligatoire).
    `accepted` est `Literal[True]` : un risque non acceptable ⇒ on ne valide pas la thèse, on ne
    l'acquitte pas à False."""
    risk_index: int = Field(ge=0)        # position dans synthesis.risques_acceptes
    accepted: Literal[True]


class ValuationRange(Strict):
    """Fourchette de valeur intrinsèque figée à l'entrée (theses.valuation_range, migration 026)."""
    low: float
    base: float
    high: float

    @model_validator(mode="after")
    def _ordonnee(self):
        if not (self.low <= self.base <= self.high):
            raise ValueError("valuation_range doit vérifier low ≤ base ≤ high")
        return self


class ThesisValidation(Strict):
    """Enregistrement de décision figé au validate. Se cross-valide contre la synthèse (RiskMatrix)
    dont il dérive — G2 : la décision n'est pas libre."""
    schema_version: Literal["v2.0.0"]
    thesis_id: int
    research_memo_id: int
    synthesis_analysis_id: int
    synthesis: RiskMatrix                 # fige le verdict, le sizing capé, les risques
    hypotheses: list[Hypothese] = Field(min_length=1)   # H1-Hn (chaque risque -> une hypothèse)
    risk_acks: list[RiskAck]              # un ack par risque accepté (§9)
    pre_mortem_acked: bool
    position_sizing_pct: float            # sizing FINAL retenu
    valuation_range: ValuationRange
    conditions_entree: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _decision_contrainte(self):
        s = self.synthesis
        # G2 : seul un verdict actionnable crée une position
        if s.verdict not in _VERDICTS_ACTIONNABLES:
            raise ValueError(f"verdict '{s.verdict}' non actionnable — pas de validation de thèse")
        # §9 : bijection acquittements ↔ risques acceptés (aucun risque silencieux)
        n = len(s.risques_acceptes)
        idx = sorted(a.risk_index for a in self.risk_acks)
        if idx != list(range(n)):
            raise ValueError(
                f"risk_acks doit couvrir exactement les {n} risques acceptés — reçu indices {idx}"
            )
        # pré-mortem acquitté
        if not self.pre_mortem_acked:
            raise ValueError("pre_mortem_acked doit être True pour valider (§9)")
        # falsifiabilité : pont risques -> hypothèses (chaque risque pointe une hypothèse existante)
        valider_pont_risques_hypotheses(s, self.hypotheses)
        # Q6 : sizing final borné et non libre
        ps = s.position_sizing
        attendu = ps.override_utilisateur.valeur_pct if ps.override_utilisateur else ps.pct_recommande
        if abs(self.position_sizing_pct - attendu) > 1e-9:
            raise ValueError(
                "position_sizing_pct doit refléter pct_recommande (ou l'override tracé A7), "
                f"attendu {attendu}, reçu {self.position_sizing_pct}"
            )
        if self.position_sizing_pct > ps.pct_max + 1e-9:
            raise ValueError(f"sizing {self.position_sizing_pct} > pct_max {ps.pct_max} (cap Kelly, Q6)")
        # PROCEED_AVEC_CONDITIONS : conditions figées non vides
        if s.verdict == "PROCEED_AVEC_CONDITIONS" and not self.conditions_entree:
            raise ValueError("conditions_entree requis si verdict=PROCEED_AVEC_CONDITIONS")
        return self
