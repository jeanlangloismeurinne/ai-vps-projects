"""
Schéma Pydantic versionné de la SORTIE / POST-MORTEM / CALIBRATION (§11, §12, migration 032) —
DÉRIVÉ des cartes de provenance. Dernier maillon : la boucle d'apprentissage long terme (A5).

Copie runtime FIDÈLE de `roadmap/provenance-cards/exit_calibration_schema.py` (seuls les imports
croisés passent en relatifs — règle #19, 3 points de synchro).

Trois contrats liés :
  • ExitPlan       — sortie thèse-driven en tranches (§11, DÉCISION #5). L'origine est un déclencheur
                     de thèse, jamais un pur seuil de prix ; les tranches ne sont que l'exécution.
  • PostMortem     — au dernier lot vendu : durée, perf, statut FINAL de CHAQUE hypothèse, leçons →
                     pattern_library (`lesson_learned`, réutilisables par les bull-agents comparables).
  • CalibrationEntry — registre A5 : prédit (à l'entrée) vs réalisé (à la sortie). Après 15-20 positions,
                     révèle le biais systématique (« vos IV hautes sont 20 % trop basses »).

Réutilise `Strict` d'analysis_v2 (G1). `valider_postmortem_couvre` est le contrôle inter-JSON (comme
`valider_pont_risques_hypotheses` en §8.5) : un post-mortem ne peut pas oublier une hypothèse figée.

⚠️ PORTÉE EXACTE DE CE CONTRAT — à ne pas surestimer (leçon du lot 8, convention #37). Un contrat
valide UN objet, jamais la cohérence entre deux. Ce fichier vérifie la cohérence INTERNE du payload
(Σ des tranches, ordres consécutifs, ≥1 leçon taguée, ≥1 paire de calibration). Il ne peut PAS
vérifier que l'`origine` déclarée correspond à l'état réel de la thèse — `origine='hypothese_invalidee'`
passe parfaitement sur une thèse dont les quatre hypothèses sont `confirmee`, parce que les statuts
vivent dans `theses_v2.hypotheses`, hors payload. Ni que la somme des tranches correspond aux titres
réellement détenus. Ces invariants-là portent sur une RELATION entre deux objets : ils se vérifient
en code, dans `agents/v2/exit.py` (`_valider_pont_sortie`, `_valider_pont_postmortem`).

Garde-fous encodés :
  Sortie thèse-driven (§11)  `origine` typée obligatoire — la sortie a une CAUSE de thèse, pas un
      ratio de prix. `accelerated_exit` ⇒ conditions_accelerees non vides.
  Tranches cohérentes  Σ pct_a_vendre ≤ 100 ; ordres = 1..n consécutifs (exécution déterministe).
  Post-mortem complet  hypotheses_finales couvre EXACTEMENT les hypothèses figées de la thèse
      (bijection — chaque H reçoit un verdict, comme les risk_acks au validate) ; ≥1 leçon, chaque
      leçon taguée (réutilisable par pattern_library, sinon irrécupérable pour un comparable).
  Calibration A5  ≥1 paire prédit/réalisé ; c'est le grain de l'apprentissage LT.

Cible : pydantic v2 (container backend 2.13.4). Tester en container (host = v1).
"""
from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from .analysis_v2_schemas import SCHEMA_VERSION, Strict

__all__ = ["ExitPlan", "ExitTranche", "ConditionAcceleree", "PostMortem", "HypothesisOutcome",
           "Lecon", "CalibrationEntry", "CalibrationPair", "valider_postmortem_couvre",
           "SCHEMA_VERSION"]

ExitStatus = Literal["plan_created", "partially_exited", "closed", "accelerated_exit"]
# §11 : la sortie est thèse-driven — l'origine est une cause de thèse, jamais un seuil de prix seul
ExitOrigin = Literal["thesis_degradation", "rendement_insuffisant", "hypothese_invalidee", "reallocation"]
AccelType = Literal["hypothese_invalidee", "iv_revisee_baisse"]
HypFinalStatut = Literal["confirmee", "invalidee", "partiellement_confirmee", "non_concluante"]


# ─────────────────────────────── ExitPlan (§11) ───────────────────────────────
class ExitTranche(Strict):
    ordre: int = Field(ge=1)
    pct_a_vendre: float = Field(gt=0, le=100)
    declencheur: str = Field(min_length=1)   # seuil/condition d'EXÉCUTION de la tranche


class ConditionAcceleree(Strict):
    """Sortie accélérée → Mode 3 auto (§11) : hypothèse critique invalidée, ou IV révisée −20 %+."""
    type: AccelType
    seuil: str = Field(min_length=1)


class ExitPlan(Strict):
    schema_version: Literal["v2.0.0"]
    thesis_id: int
    origine: ExitOrigin                      # thèse-driven, obligatoire
    tranches: list[ExitTranche] = Field(min_length=1)
    conditions_accelerees: list[ConditionAcceleree] = Field(default_factory=list)
    exit_status: ExitStatus

    @model_validator(mode="after")
    def _tranches_coherentes(self):
        total = sum(t.pct_a_vendre for t in self.tranches)
        if total > 100 + 1e-9:
            raise ValueError(f"Σ pct_a_vendre = {total} > 100")
        ordres = sorted(t.ordre for t in self.tranches)
        if ordres != list(range(1, len(self.tranches) + 1)):
            raise ValueError(f"ordres de tranches doivent être 1..n consécutifs — reçu {ordres}")
        if self.exit_status == "accelerated_exit" and not self.conditions_accelerees:
            raise ValueError("exit_status='accelerated_exit' exige des conditions_accelerees")
        return self


# ─────────────────────────────── PostMortem (§12) ─────────────────────────────
class HypothesisOutcome(Strict):
    hypothese_id: str
    statut_final: HypFinalStatut
    predite_vs_realisee: str = Field(min_length=1)   # observation prédit/réalisé (nourrit A5)


class Lecon(Strict):
    lecon: str = Field(min_length=1)
    tags: list[str] = Field(min_length=1)    # réutilisable par pattern_library (sinon irrécupérable)


class PostMortem(Strict):
    schema_version: Literal["v2.0.0"]
    thesis_id: int
    duree_jours: int = Field(ge=0)
    performance_pct: float
    hypotheses_finales: list[HypothesisOutcome] = Field(min_length=1)
    decision_sortie: str = Field(min_length=1)
    lecons: list[Lecon] = Field(min_length=1)  # un post-mortem sans leçon est inutile


def valider_postmortem_couvre(pm: PostMortem, hypothese_ids: list[str]) -> None:
    """Contrôle inter-JSON (niveau thèse) : le post-mortem juge EXACTEMENT les hypothèses figées —
    aucune oubliée, aucune inventée. Pendant de la bijection risk_acks au validate (C4)."""
    got = {h.hypothese_id for h in pm.hypotheses_finales}
    attendu = set(hypothese_ids)
    if got != attendu:
        raise ValueError(
            f"hypotheses_finales {sorted(got)} != hypothèses figées {sorted(attendu)} "
            f"(manquantes={sorted(attendu - got)}, surplus={sorted(got - attendu)})"
        )


# ───────────────────────── CalibrationEntry (A5) ──────────────────────────────
class CalibrationPair(Strict):
    """Un couple prédit/réalisé. `metric` ex: 'iv_base', 'risque:H3', 'rendement_5ans'."""
    metric: str = Field(min_length=1)
    predite: float
    realisee: float


class CalibrationEntry(Strict):
    schema_version: Literal["v2.0.0"]
    thesis_id: int
    paires: list[CalibrationPair] = Field(min_length=1)  # ≥1 couple prédit/réalisé (grain A5)
