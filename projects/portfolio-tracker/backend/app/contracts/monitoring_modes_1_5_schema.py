"""
Schéma Pydantic versionné du MONITORING MODES 1-5 (§10) — DÉRIVÉ de monitoring_modes_1_5_card.md.

Le mode 6 (revue annuelle, colonne vertébrale LT) a son contrat figé à part (monitoring_mode6_schema).
Ce fichier carde les 5 modes trimestriels/tactiques, dont l'invariant central est l'ANTI-CHURN
(audit §1.3) : les modes trimestriels (1, 2, 4) n'escaladent QUE sur franchissement d'un seuil
d'invalidation PRÉ-ENREGISTRÉ (figé au validate, carte C4). Seuls les modes 3 (décision review,
escalade) et 6 (revue annuelle) produisent un verdict de plein droit. Le thermomètre / valuation
status reste contextuel — jamais un déclencheur de vente.

Réutilise `HypothesisReview`/`HypStatut`/`ExitTrigger` de monitoring_mode6_schema (source unique — G1)
et `Strict` d'analysis_v2. Les 5 modes forment une UNION DISCRIMINÉE sur `mode` (parse robuste).

Garde-fous encodés :
  Mode 1  checklist de lecture ≤ 3 points, AUCUN verdict (pré-event).
  Mode 2  ANTI-CHURN : alert_level ∈ {REVIEW_REQUIRED, CRITICAL} ⇔ seuils_franchis non vide ; et
      seuils_franchis ⇔ l'ensemble des hypothèses au statut {alerte, invalidee} (le statut EST le
      franchissement). RAS ⇒ aucun franchissement. valuation_status contextuel (non contraignant).
  Mode 3  explicabilité : REDUIRE/SORTIR ⇒ exit_trigger renseigné ; MAINTENIR/RE_SYNTHESE ⇒ pas de
      trigger ; exit_trigger='hypothese_invalidee' ⇒ ≥1 hypothèse invalidee. Test d'inversion (Munger) requis.
  Mode 4  sector pulse contextuel : score -5..+5, hypothèses impactées listées, N'ESCALADE JAMAIS
      seul (pas d'alert_level — l'escalade passe par un mode 2/3 sur seuil franchi).
  Mode 5  routing PUR : route vers synthèse|debate + raison ; aucune donnée nouvelle produite.

PORTÉE EXACTE DE L'ANTI-CHURN — à ne pas surestimer. Ce que le contrat vérifie est la COHÉRENCE
INTERNE de l'escalade : statut ⇔ seuils_franchis ⇔ alert_level. Il ne peut PAS vérifier que le statut
lui-même est fondé, c'est-à-dire que le KPI observé a réellement franchi le `seuil_invalidation` figé
au validate — ces seuils vivent dans `theses_v2.hypotheses`, hors payload. Le contrat rend donc
impossible d'escalader SANS déclarer de franchissement ; il ne rend pas impossible de déclarer un
franchissement qui n'a pas eu lieu. Le rattrapage est en amont (les seuils chiffrés sont injectés dans
le contexte, chaque statut porte ses `source_entry_refs`) et dans le pont inter-objets d'
`agents/v2/monitoring.py`. Le dire ici plutôt que laisser croire que « 20/20 vérifiés » couvre le fond.

Cible : pydantic v2 (container backend 2.13.4). Le python hôte a v1 → tester en container.
"""
from __future__ import annotations

from typing import Annotated, Literal, Optional, Union

from pydantic import Field, model_validator

from .analysis_v2_schemas import Strict, SCHEMA_VERSION
from .monitoring_mode6_schema import HypothesisReview, ExitTrigger

__all__ = [
    "Mode1PreEvent", "Mode2QuarterlyReview", "Mode3DecisionReview",
    "Mode4SectorPulse", "Mode5Routing", "MonitoringSession", "SCHEMA_VERSION",
]

AlertLevel = Literal["RAS", "REVIEW_REQUIRED", "CRITICAL"]   # cf. monitoring_sessions.alert_level
Mode3Decision = Literal["MAINTENIR", "REDUIRE", "SORTIR", "RE_SYNTHESE"]

_STATUTS_FRANCHIS = {"alerte", "invalidee"}      # un statut ≠ active/confirmee = un seuil franchi
_ALERTES_ESCALADE = {"REVIEW_REQUIRED", "CRITICAL"}
_MODE3_SORTIE = {"REDUIRE", "SORTIR"}


class Mode1PreEvent(Strict):
    """J-2 avant publication : checklist de lecture, aucun verdict."""
    mode: Literal[1]
    thesis_id: int
    event: str = Field(min_length=1)                 # ce qui va être publié (résultats, investor day…)
    checklist: list[str] = Field(min_length=1, max_length=3)   # ≤ 3 points à surveiller


class Mode2QuarterlyReview(Strict):
    """J+1 après publication : statut des hypothèses + niveau d'alerte anti-churn + valuation status."""
    mode: Literal[2]
    thesis_id: int
    hypotheses_reviewed: list[HypothesisReview] = Field(min_length=1)
    seuils_franchis: list[str] = Field(default_factory=list)   # ids des hypothèses dont un seuil est franchi
    alert_level: AlertLevel
    valuation_status: str = Field(min_length=1)      # contextuel (attractif/juste/étiré/surévalué) — non contraignant

    @model_validator(mode="after")
    def _anti_churn(self):
        ids = {h.hypothese_id for h in self.hypotheses_reviewed}
        # référentiel : les seuils franchis pointent des hypothèses revues
        inconnus = set(self.seuils_franchis) - ids
        if inconnus:
            raise ValueError(f"seuils_franchis hors hypotheses_reviewed: {sorted(inconnus)}")
        # le statut EST le franchissement : {alerte, invalidee} ⇔ présent dans seuils_franchis
        franchis_par_statut = {h.hypothese_id for h in self.hypotheses_reviewed
                               if h.statut in _STATUTS_FRANCHIS}
        if set(self.seuils_franchis) != franchis_par_statut:
            raise ValueError(
                "seuils_franchis incohérent avec les statuts d'hypothèses "
                f"(statut alerte/invalidee = {sorted(franchis_par_statut)}, "
                f"déclaré {sorted(set(self.seuils_franchis))})"
            )
        # ANTI-CHURN : on n'escalade QUE sur franchissement pré-enregistré
        if self.alert_level in _ALERTES_ESCALADE and not self.seuils_franchis:
            raise ValueError(
                f"alert_level='{self.alert_level}' sans seuil franchi — anti-churn : "
                "les modes trimestriels n'escaladent que sur franchissement pré-enregistré (§10)"
            )
        if self.alert_level == "RAS" and self.seuils_franchis:
            raise ValueError("alert_level='RAS' incohérent avec des seuils franchis")
        return self


class Mode3DecisionReview(Strict):
    """Escalade : diagnostic + test d'inversion (Munger) + décision motivée. Produit un verdict."""
    mode: Literal[3]
    thesis_id: int
    diagnostic: str = Field(min_length=1)
    munger_inversion: str = Field(min_length=1)      # « qu'est-ce qui tuerait la thèse ? » (inversion)
    hypotheses_reviewed: list[HypothesisReview] = Field(min_length=1)
    decision: Mode3Decision
    rationale: str = Field(min_length=1)
    exit_trigger: Optional[ExitTrigger] = None       # §11 : hypothese_invalidee | rendement_insuffisant

    @model_validator(mode="after")
    def _decision_explicable(self):
        invalidees = [h for h in self.hypotheses_reviewed if h.statut == "invalidee"]
        # explicabilité : une réduction/sortie n'est jamais muette
        if self.decision in _MODE3_SORTIE and self.exit_trigger is None:
            raise ValueError(f"decision '{self.decision}' exige un exit_trigger (pas de sortie muette)")
        if self.decision in {"MAINTENIR", "RE_SYNTHESE"} and self.exit_trigger is not None:
            raise ValueError(f"decision '{self.decision}' incompatible avec un exit_trigger")
        # déclencheur primaire §11
        if self.exit_trigger == "hypothese_invalidee" and not invalidees:
            raise ValueError("exit_trigger='hypothese_invalidee' sans hypothèse au statut 'invalidee'")
        return self


class Mode4SectorPulse(Strict):
    """J+1 résultats d'un pair : score d'impact -5..+5 sur les hypothèses surveillées. Contextuel :
    n'escalade jamais seul — l'escalade passe par un mode 2/3 sur franchissement de seuil."""
    mode: Literal[4]
    thesis_id: int
    pair_ticker: str = Field(min_length=1)
    sector_score: int = Field(ge=-5, le=5)
    hypotheses_impactees: list[str] = Field(default_factory=list)   # ids des hypothèses concernées
    note: str = Field(min_length=1)


class Mode5Routing(Strict):
    """Après un mode 2/4 REVIEW_REQUIRED : routing PUR vers la synthèse (dégradation matérielle) ou
    le debate-agent (option C). Aucune donnée nouvelle."""
    mode: Literal[5]
    thesis_id: int
    source_mode: Literal[2, 4]
    route: Literal["synthese", "debate"]
    raison: str = Field(min_length=1)


# union discriminée : parse robuste par `mode` (pydantic v2)
MonitoringSession = Annotated[
    Union[Mode1PreEvent, Mode2QuarterlyReview, Mode3DecisionReview, Mode4SectorPulse, Mode5Routing],
    Field(discriminator="mode"),
]
