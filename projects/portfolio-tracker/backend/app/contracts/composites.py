"""
Composites runtime — assemblages backend de contrats figés, PAS des JSON d'agent originaux.

`SynthesisOutput` = la sortie combinée du thesis-agent (synthèse) telle que persistée dans
investment_analyses.result_json pour analysis_type='synthesis' : le SEUL verdict du flux (risk_matrix,
Q2) + les hypothèses falsifiables (§8.4-8.5). Les deux sous-contrats (RiskMatrix, Hypothese) restent
la source figée d'analysis_v2_schemas ; ce module ne fait que les composer sous extra='forbid'.
"""
from __future__ import annotations

from pydantic import ConfigDict, Field

from .analysis_v2_schemas import Hypothese, RiskMatrix, Strict, valider_pont_risques_hypotheses

__all__ = ["SynthesisOutput"]


class SynthesisOutput(Strict):
    model_config = ConfigDict(extra="forbid")
    schema_version: str = "v2.0.0"
    risk_matrix: RiskMatrix
    hypotheses: list[Hypothese] = Field(min_length=1)

    def valider_pont(self) -> None:
        """Contrôle inter-JSON (§8.5) : chaque risque accepté pointe une hypothèse existante."""
        valider_pont_risques_hypotheses(self.risk_matrix, self.hypotheses)
