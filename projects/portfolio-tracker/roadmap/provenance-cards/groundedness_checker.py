"""
Groundedness-checker (A2) — 3ᵉ dérivé des cartes de provenance.

Structure de sortie + partie DÉTERMINISTE de la vérification (recompute des `derived` à formule
connue, comptes, existence des refs, planchers de tier). La partie LLM-judge (« l'entry soutient-elle
le fait ? », cohérence jugement↔preuves) est injectée via une callable `judge`, pour que le cœur
reste testable sans modèle. Voir groundedness_rules.md.

Cible : pydantic v2 (container backend 2.13.4). Le python hôte a v1 → tester en container.
"""
from typing import Callable, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

Status = Literal[
    "grounded", "unsupported", "inconsistent", "ungrounded", "base_rate_fabrique", "skipped"
]
Tier = Literal["A", "A-", "B+", "B", "B-", "C+", "C"]
Nature = Literal["factual", "judgment", "derived", "ref", "controle", "user", "checker"]

_TIER_ORDER = ["C", "C+", "B-", "B", "B+", "A-", "A"]


def tier_ge(t: str, floor: str) -> bool:
    """t >= floor dans l'ordre de fiabilité."""
    return _TIER_ORDER.index(t) >= _TIER_ORDER.index(floor)


# ─────────────────────────── sortie du checker ──────────────────────────────
class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class GroundingVerdict(Strict):
    field_path: str
    nature: Nature
    status: Status
    grounding_score: float = Field(ge=0.0, le=1.0)
    refs_checked: list[int] = Field(default_factory=list)
    note: Optional[str] = None


class GroundingReport(Strict):
    affirmations_total: int
    etayees: int
    non_etayees: int
    blocking: bool = False
    verdicts: list[GroundingVerdict] = Field(default_factory=list)

    @classmethod
    def from_verdicts(cls, verdicts: list[GroundingVerdict], blocking_paths: set[str] = frozenset()):
        checked = [v for v in verdicts if v.status != "skipped"]
        etayees = sum(1 for v in checked if v.status == "grounded")
        blocking = any(v.field_path in blocking_paths and v.status != "grounded" for v in verdicts)
        return cls(
            affirmations_total=len(checked),
            etayees=etayees,
            non_etayees=len(checked) - etayees,
            blocking=blocking,
            verdicts=verdicts,
        )


# ─────────────── vérifications DÉTERMINISTES (aucun token LLM) ───────────────
_TOL = 0.5  # tolérance en points de %


def check_marge_securite(value: float, prix_actuel: float, iv_base: float) -> bool:
    return abs((iv_base - prix_actuel) / prix_actuel * 100 - value) <= _TOL


def check_perte_pct(value: float, prix_actuel: float, prix_bear: float) -> bool:
    return abs((prix_actuel - prix_bear) / prix_actuel * 100 - value) <= _TOL


def check_sources_summary(declared: dict, ref_tiers: list[str]) -> bool:
    """Recompte les tiers depuis le snapshot et compare aux comptes déclarés."""
    a = sum(1 for t in ref_tiers if t in ("A", "A-"))
    b = sum(1 for t in ref_tiers if t in ("B+", "B", "B-"))
    c = sum(1 for t in ref_tiers if t in ("C+", "C"))
    return (
        declared.get("tier_A") == a
        and declared.get("tier_B") == b
        and declared.get("tier_C_llm_memory") == c
        and declared.get("total_entries") == len(ref_tiers)
    )


def check_ref_exists(entry_id: int, snapshot_ids: set[int]) -> bool:
    return entry_id in snapshot_ids


# ─────────────────────────── dispatch par nature ────────────────────────────
Judge = Callable[[str, str], float]  # (affirmation, contenu_source) -> score 0..1


def check_field(
    field_path: str,
    nature: Nature,
    grounding: str,
    *,
    tier_floor: Optional[str] = None,
    ref_tiers: Optional[list[str]] = None,
    ref_ids: Optional[list[int]] = None,
    snapshot_ids: Optional[set[int]] = None,
    deterministic_ok: Optional[bool] = None,   # résultat d'un recompute si formule connue
    judge_score: Optional[float] = None,       # score LLM-judge si fourni
) -> GroundingVerdict:
    """Applique la règle nature×grounding. deterministic_ok / judge_score sont calculés en amont
    (recompute local ou appel Haiku batché) — ici on tranche le statut."""
    ref_ids = ref_ids or []

    if nature in ("checker",):
        return GroundingVerdict(field_path=field_path, nature=nature, status="skipped", grounding_score=1.0)

    if nature == "ref":
        ok = all(check_ref_exists(i, snapshot_ids or set()) for i in ref_ids)
        return GroundingVerdict(field_path=field_path, nature=nature,
                                status="grounded" if ok else "ungrounded",
                                grounding_score=1.0 if ok else 0.0, refs_checked=ref_ids)

    if nature in ("controle", "user"):
        ok = deterministic_ok is not False
        return GroundingVerdict(field_path=field_path, nature=nature,
                                status="grounded" if ok else "ungrounded",
                                grounding_score=1.0 if ok else 0.0)

    if nature == "factual":
        # (a) plancher de tier  (b) LLM-judge : l'entry soutient le fait
        if tier_floor and ref_tiers and not all(tier_ge(t, tier_floor) for t in ref_tiers):
            return GroundingVerdict(field_path=field_path, nature=nature, status="unsupported",
                                    grounding_score=0.3, refs_checked=ref_ids, note="tier sous plancher")
        s = 1.0 if judge_score is None else judge_score
        return GroundingVerdict(field_path=field_path, nature=nature,
                                status="grounded" if s >= 0.6 else "unsupported",
                                grounding_score=s, refs_checked=ref_ids)

    if nature == "judgment":
        # cohérence avec le frère factuel (délégué)
        s = 1.0 if judge_score is None else judge_score
        return GroundingVerdict(field_path=field_path, nature=nature,
                                status="grounded" if s >= 0.6 else "inconsistent",
                                grounding_score=s, refs_checked=ref_ids)

    if nature == "derived":
        if deterministic_ok is not None:               # formule connue -> recompute
            return GroundingVerdict(field_path=field_path, nature=nature,
                                    status="grounded" if deterministic_ok else "inconsistent",
                                    grounding_score=1.0 if deterministic_ok else 0.0,
                                    note="recompute déterministe")
        s = 1.0 if judge_score is None else judge_score  # narratif -> LLM-judge cohérence
        return GroundingVerdict(field_path=field_path, nature=nature,
                                status="grounded" if s >= 0.6 else "inconsistent", grounding_score=s)

    return GroundingVerdict(field_path=field_path, nature=nature, status="skipped", grounding_score=1.0)
