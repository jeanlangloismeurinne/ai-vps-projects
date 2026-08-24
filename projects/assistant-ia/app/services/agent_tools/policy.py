"""La politique d'autorisation — une seule fonction, testée en table (#1787579840503, roadmap §3).

Un seul endroit à relire pour auditer le comportement de tout le catalogue. Un nouvel outil
remplit son manifeste et **ne touche pas à ce fichier**.

Ce que cette fonction n'est *pas* : la seule ligne de défense. Le garde-fou principal est la
frontière modèle / code (roadmap §2.3) — le modèle propose deux chaînes validées, le code décide
de la destination, de l'auteur, du canal. C'est pourquoi ces règles peuvent être souples.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from app.services.agent_tools.manifest import Effect, ToolManifest, TurnState


class Verdict(str, Enum):
    EXECUTE = "execute"              # exécution immédiate (+ confirmation a posteriori si écriture)
    CONFIRM_FIRST = "confirm_first"  # rien n'est écrit avant un clic
    REFUSE = "refuse"


@dataclass(frozen=True)
class Decision:
    verdict: Verdict
    reason: str = ""

    @property
    def audit_verdict(self) -> str:
        """Valeur écrite dans `agent_tool_calls.verdict`."""
        return {
            Verdict.EXECUTE: "ok",
            Verdict.CONFIRM_FIRST: "confirmation_requise",
            Verdict.REFUSE: "refused",
        }[self.verdict]


def policy(manifest: ToolManifest, turn: TurnState) -> Decision:
    """Décide du régime d'un appel, à partir du manifeste et de l'état du tour.

    Ordre des tests — les quotas d'abord (un refus de quota prime sur tout régime), puis les
    lectures (jamais soumises à confirmation), puis la règle de dérivation.
    """
    # ── Quotas ───────────────────────────────────────────────────────────────
    rl = manifest.rate_limit
    used_turn = turn.turn_counts.get(manifest.name, 0)
    if used_turn >= rl.per_turn:
        return Decision(
            Verdict.REFUSE,
            f"quota par tour atteint pour `{manifest.name}` ({rl.per_turn} appel(s) max). "
            f"Demande à l'utilisateur de relancer au tour suivant.",
        )
    used_day = turn.daily_counts.get(manifest.name, 0)
    if used_day >= rl.per_day:
        return Decision(
            Verdict.REFUSE,
            f"quota journalier atteint pour `{manifest.name}` ({rl.per_day} appels / 24 h).",
        )

    # ── Les lectures ne passent jamais devant l'utilisateur ──────────────────
    # L'arbre du §3.2 s'ouvre sur « le modèle demande un outil **à effet de bord** ». Une lecture
    # ne fait qu'ajouter du taint : son pire cas est une mauvaise réponse, pas une écriture. Sans
    # ce court-circuit, une deuxième recherche web dans le même tour demanderait une confirmation
    # — du bruit pur, qui use la vigilance sur laquelle repose tout le dispositif.
    if manifest.effect == Effect.READ:
        return Decision(Verdict.EXECUTE)

    # ── Règle de dérivation (roadmap §3.4) ───────────────────────────────────
    if manifest.effect == Effect.OUTBOUND:
        return Decision(Verdict.CONFIRM_FIRST, "l'effet sort du système : irrattrapable")
    if not manifest.reversible:
        return Decision(Verdict.CONFIRM_FIRST, "effet non réversible en un clic")
    if not manifest.visibility:
        return Decision(Verdict.CONFIRM_FIRST, "effet non visible immédiatement dans le fil")
    if turn.is_tainted:
        # Le cas central du chantier : du contenu que personne n'a relu est dans le contexte au
        # moment où une écriture est décidée. On n'interdit pas — on montre le payload résolu et
        # sa provenance, et rien ne s'écrit sans clic.
        return Decision(
            Verdict.CONFIRM_FIRST,
            "contenu non vérifié dans le contexte : " + ", ".join(turn.taint_sources),
        )

    # Écriture réversible et visible, contexte propre → immédiat + confirmation a posteriori.
    return Decision(Verdict.EXECUTE)
