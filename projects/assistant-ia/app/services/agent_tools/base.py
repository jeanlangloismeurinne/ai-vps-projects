"""Contrat commun à tous les outils (#1787579840503).

Le cycle d'un appel est le même pour tout le catalogue, et c'est ce qui rend le catalogue
extensible :

```
arguments du modèle → resolve()  → policy() → execute()
   (2 chaînes)        (code pur)   (régime)   (effet)
```

`resolve()` est la matérialisation de la frontière modèle / code (roadmap §2.3) : le modèle
propose une expression, le code produit le payload réel — dates résolues, destinations choisies,
bornes validées. Il tourne **avant** `policy()`, pour deux raisons :

1. La confirmation doit afficher ce qui sera *réellement* écrit, pas ce que le modèle a dit.
2. Un payload résolu au moment de l'affichage puis figé ne peut pas dériver entre l'affichage et
   le clic (« demain 9h » résolu deux fois à cheval sur minuit ne donne pas la même date).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

from app.services.agent_tools.manifest import ToolManifest, TurnState


class ToolError(Exception):
    """Échec métier d'un outil (argument invalide, date passée, backend indisponible…).

    Toujours réinjecté au modèle comme `{"error": …}` en `role=tool`, **jamais** un résultat
    vide : c'est la leçon SearXNG (roadmap §6) et elle vaut pour tous les outils. Un résultat
    vide fait conclure au modèle qu'il n'y a rien à trouver ; une erreur lui dit qu'il n'a pas
    cherché.
    """


@dataclass
class ToolContext:
    """Ce qu'un exécuteur sait du tour en cours, sans rien pouvoir en décider."""
    turn: TurnState


@dataclass
class PreparedCall:
    """Sortie de `resolve()` : le payload réel + ce que l'utilisateur en verra."""
    resolved: dict[str, Any]
    # Résumé en une ligne, affiché dans la confirmation. Pour un rappel : titre + date résolue
    # dans le fuseau de l'utilisateur — la partie qui rend une mauvaise interprétation visible.
    summary: str = ""


@dataclass
class ToolResult:
    """Sortie de `execute()`."""
    # Ce qui repart au modèle en `role=tool` (sérialisé en JSON s'il ne s'agit pas d'une chaîne).
    payload: Any
    # Sources de taint à ajouter au tour, ex. `["web:exemple.com"]`. Vide pour un outil interne.
    taint_sources: list[str] = field(default_factory=list)
    # Blocs Slack à poster après l'exécution (confirmation a posteriori : annuler / éditer).
    slack_blocks: list[dict[str, Any]] | None = None
    slack_text: str = ""


Executor = Callable[[dict[str, Any], ToolContext], Awaitable[ToolResult]]
Resolver = Callable[[dict[str, Any], ToolContext], Awaitable[PreparedCall]]


@dataclass(frozen=True)
class ToolSpec:
    """Un outil = un manifeste + un exécuteur (+ un résolveur si le code a du travail à faire)."""
    manifest: ToolManifest
    execute: Executor
    resolve: Resolver | None = None
