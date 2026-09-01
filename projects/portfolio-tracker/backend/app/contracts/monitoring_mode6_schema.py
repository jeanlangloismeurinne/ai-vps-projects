"""
Schéma Pydantic versionné du MONITORING MODE 6 (revue annuelle) + VALUATION THERMOMETER
(§10, §11) — DÉRIVÉ des cartes de provenance.

Mode 6 = colonne vertébrale de la revue long terme (audit §1.3) : déclenché à validated_at+365j
puis annuel, il relit thèse + research_memo + entries de l'année → verdict CONFIRMER/RENFORCER/
REDUIRE/SORTIR, réactualise la valuation_range et replanifie +365j. Contrairement aux modes
trimestriels (qui n'escaladent QUE sur franchissement de seuil d'invalidation pré-enregistré,
anti-churn), le mode 6 produit toujours un verdict de revue.

Deux invariants métier centraux (DÉCISION #5, §11) :
  ANTI-SEUIL-MÉCANIQUE  la sortie sur valorisation n'est JAMAIS `Prix > IV×1.15` (l'anti-pattern que
      l'audit rejette). Une sortie/réduction motivée par la valorisation exige un `rendement_prospectif`
      (IV réactualisée × croissance vs prix × alternatives) avec `suffisant=False` — un arbitrage
      prospectif, pas un ratio de prix.
  THERMOMÈTRE CONTEXTUEL  le ValuationThermometer signale une zone (attractif/juste/étiré/surévalué)
      et ALIMENTE la réévaluation, mais `contraignant=Literal[False]` : il ne déclenche jamais seul
      une vente. On peut être `surevalue` et CONFIRMER (thèse intacte).

Réutilise `ReverseDcf`/`NonEmptyRefs` d'analysis_v2 et `ValuationRange` de decision_validate (G1).

Garde-fous encodés :
  Explicabilité  SORTIR/REDUIRE ⇒ `exit_trigger` renseigné (pas de sortie muette, cf. NO-GO muet interdit).
  Déclencheur primaire §11  exit_trigger='hypothese_invalidee' ⇒ ≥1 hypothèse `invalidee`.
  Déclencheur secondaire §11  exit_trigger='rendement_insuffisant' ⇒ rendement_prospectif.suffisant=False.
  RENFORCER  ⇒ rendement_prospectif.suffisant=True (on renforce sur rendement attractif, justifié).
  Réactualisation  valuation_range_updated cohérente (low ≤ base ≤ high, héritée de ValuationRange).

CE QUE CE CONTRAT NE PEUT PAS VÉRIFIER — et où ça se rattrape :
  Le garde-fou 7 du prompt (« hypotheses_reviewed[] couvre les hypothèses figées de la thèse ») n'est
  PAS encodable ici : le contrat ne voit que le payload du modèle, jamais `theses_v2.hypotheses`.
  C'est un contrôle INTER-OBJETS, comme `valider_pont_risques_hypotheses` l'est intra-payload. Il vit
  donc dans `agents/v2/monitoring.py` (`_valider_pont_hypotheses`), qui a la thèse en main. Sans lui,
  un modèle peut passer le contrat en ne revoyant qu'une seule hypothèse — et les autres dériveraient
  un an de plus sans que rien ne le signale, ce qui est exactement ce que le mode 6 doit empêcher.

Cible : pydantic v2 (container backend 2.13.4). Tester en container (host = v1).
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import Field, model_validator

from .analysis_v2_schemas import Strict, ReverseDcf, NonEmptyRefs, SCHEMA_VERSION
from .decision_validate_schema import ValuationRange

__all__ = ["Mode6Review", "ValuationThermometer", "HypothesisReview",
           "RendementProspectif", "SCHEMA_VERSION"]

Mode6Verdict = Literal["CONFIRMER", "RENFORCER", "REDUIRE", "SORTIR"]
ThermometerZone = Literal["attractif", "juste", "etire", "surevalue"]
HypStatut = Literal["active", "alerte", "invalidee", "confirmee"]
ExitTrigger = Literal["hypothese_invalidee", "rendement_insuffisant"]  # les 2 déclencheurs §11

_VERDICTS_SORTIE = {"REDUIRE", "SORTIR"}


class HypothesisReview(Strict):
    """Statut d'une hypothèse figée (H1-Hn) à la revue. Le pont vers la thèse est l'id."""
    hypothese_id: str
    statut: HypStatut
    observation: str = Field(min_length=1)
    source_entry_refs: NonEmptyRefs        # A2 : le statut est étayé par les entries de l'année


class RendementProspectif(Strict):
    """Déclencheur secondaire §11 : arbitrage rendement/risque PROSPECTIF — jamais un seuil de prix
    mécanique. `suffisant` = le rendement attendu compense-t-il risque + coût d'opportunité ?"""
    iv_reactualisee: float
    rendement_attendu_pct: float           # rendement prospectif à terme
    cout_opportunite: str = Field(min_length=1)   # vs meilleures alternatives du portefeuille
    suffisant: bool


class ValuationThermometer(Strict):
    """Contextuel (§11) : signale la zone et alimente la réévaluation, ne contraint jamais."""
    zone: ThermometerZone
    reverse_dcf: ReverseDcf                 # ce que le prix price déjà (A4)
    action_suggeree: str = Field(min_length=1)     # NON contraignante
    contraignant: Literal[False] = False    # §11 : ne déclenche jamais SEUL une vente


class Mode6Review(Strict):
    schema_version: Literal["v2.0.0"]
    thesis_id: int
    verdict: Mode6Verdict
    rationale: str = Field(min_length=1)
    hypotheses_reviewed: list[HypothesisReview] = Field(min_length=1)
    valuation_range_updated: ValuationRange           # réactualisée
    thermometer: ValuationThermometer
    rendement_prospectif: Optional[RendementProspectif] = None
    exit_trigger: Optional[ExitTrigger] = None
    next_review_date: str                   # +365j (replanification annuelle)

    @model_validator(mode="after")
    def _revue_coherente(self):
        invalidees = [h for h in self.hypotheses_reviewed if h.statut == "invalidee"]

        # Explicabilité : une sortie/réduction n'est jamais muette
        if self.verdict in _VERDICTS_SORTIE and self.exit_trigger is None:
            raise ValueError(f"verdict '{self.verdict}' exige un exit_trigger (pas de sortie muette)")
        # CONFIRMER/RENFORCER n'emportent pas d'exit_trigger
        if self.verdict in {"CONFIRMER", "RENFORCER"} and self.exit_trigger is not None:
            raise ValueError(f"verdict '{self.verdict}' incompatible avec un exit_trigger")

        # Déclencheur primaire §11 : sortie sur hypothèse invalidée ⇒ il en faut une
        if self.exit_trigger == "hypothese_invalidee" and not invalidees:
            raise ValueError("exit_trigger='hypothese_invalidee' sans hypothèse au statut 'invalidee'")

        # Déclencheur secondaire §11 (ANTI-SEUIL-MÉCANIQUE) : sortie sur valorisation ⇒ arbitrage
        # prospectif explicite, jamais un ratio de prix
        if self.exit_trigger == "rendement_insuffisant":
            if self.rendement_prospectif is None or self.rendement_prospectif.suffisant:
                raise ValueError(
                    "exit_trigger='rendement_insuffisant' exige rendement_prospectif.suffisant=False "
                    "(arbitrage prospectif, pas un seuil de prix mécanique — §11)"
                )

        # RENFORCER se justifie par un rendement prospectif suffisant
        if self.verdict == "RENFORCER":
            if self.rendement_prospectif is None or not self.rendement_prospectif.suffisant:
                raise ValueError("RENFORCER exige rendement_prospectif.suffisant=True")

        return self
