"""Manifeste d'outil et état d'un tour (#1787579840503, roadmap §3.4).

Le défaut de la version précédente de la roadmap était de coder **une** règle en dur : chaque
nouvel outil aurait rouvert le débat sécurité. Ici la politique est une fonction pure d'un
manifeste — ajouter un outil est de la **donnée**, pas du raisonnement neuf.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Effect(str, Enum):
    """Ce que l'outil fait au monde.

    `outbound` = l'effet sort du système (mail, message à un tiers, appel d'API externe qui
    modifie quelque chose) : irrattrapable, donc toujours en confirmation préalable.
    """
    READ = "read"
    WRITE = "write"
    OUTBOUND = "outbound"


@dataclass(frozen=True)
class RateLimit:
    """Quotas de l'outil. Ils vivent ici et nulle part ailleurs : des constantes dispersées dans
    les exécuteurs seraient introuvables lors d'une relecture de sécurité (roadmap §3.5)."""
    per_turn: int
    per_day: int


@dataclass(frozen=True)
class ToolManifest:
    """Tout ce qu'un outil déclare de lui-même.

    Attributes:
        name, description, schema: le contrat envoyé au modèle (JSON schema strict).
        effect: `read` | `write` | `outbound`.
        taints_context: l'outil fait-il entrer dans le contexte du contenu que l'utilisateur
            demandeur n'a pas tapé lui-même ? **Ce n'est pas un synonyme de « sort du VPS »** :
            un futur `read_file` sur `/storage/Documents` ou un `read_thread` Slack taintent
            sans rien appeler à l'extérieur (roadmap §2.2). Classer les outils en
            `read_external` / `side_effect` était une fausse complétude.
        reversible: l'effet s'annule-t-il en un clic ?
        scope: sur les données de qui l'outil agit-il (libellé libre, pour l'audit humain).
        visibility: l'utilisateur voit-il l'effet immédiatement dans le fil ?
        rate_limit: quotas par tour et par jour.
        egress: politique réseau applicable (roadmap §4), `None` pour un outil interne.
    """
    name: str
    description: str
    schema: dict[str, Any]
    effect: Effect
    taints_context: bool
    reversible: bool
    scope: str
    visibility: bool
    rate_limit: RateLimit
    egress: str | None = None

    def to_tools_json(self) -> dict[str, Any]:
        """Entrée `tools[]` au format OpenAI-compat attendu par DeepInfra."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.schema,
            },
        }


@dataclass
class TurnState:
    """L'état d'un tour de conversation — ce que `policy` observe en plus du manifeste.

    `taint_sources` n'est **jamais rabaissé** pendant le tour, mais il n'interdit rien : il fait
    basculer le régime de confirmation. C'est tout l'objet de la révision du 2026-08-24 —
    l'ancien latch refusait, celui-ci demande (roadmap §2.4).
    """
    channel_id: str
    user_id: str | None = None
    slack_ts: str | None = None
    thread_ts: str | None = None
    doc_version: int | None = None

    # Sources non fiables entrées dans le contexte : `["web:exemple.com", "file:rapport.pdf"]`.
    # Un tableau et non un booléen : en incident, la seule question qui compte est *laquelle*
    # était présente au moment de l'écriture (roadmap §5).
    taint_sources: list[str] = field(default_factory=list)

    # Appels déjà passés dans ce tour, par outil.
    turn_counts: dict[str, int] = field(default_factory=dict)
    # Appels `ok` des dernières 24 h, par outil — chargé une fois depuis `agent_tool_calls`.
    daily_counts: dict[str, int] = field(default_factory=dict)

    def add_taint(self, source: str) -> None:
        """Ajoute une source de taint (dédupliquée, ordre d'apparition conservé)."""
        if source and source not in self.taint_sources:
            self.taint_sources.append(source)

    def record_call(self, name: str) -> None:
        self.turn_counts[name] = self.turn_counts.get(name, 0) + 1
        self.daily_counts[name] = self.daily_counts.get(name, 0) + 1

    @property
    def is_tainted(self) -> bool:
        return bool(self.taint_sources)
