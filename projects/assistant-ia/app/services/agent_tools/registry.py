"""Ce qui existe — liste codée en dur (#1787579840503, roadmap §3.1).

**Point non négociable du chantier.** La liste des outils exposés au modèle est construite
*exclusivement* depuis ce module Python. Aucun chemin de code ne dérive un outil du contenu de
`agent_system_doc`.

```
agent_system_doc (versionné, relu) ──"décrit QUAND utiliser"──> prompt système
registry.py      (code)            ──"définit CE QUI EXISTE"──> tools_json
                                        ✗ jamais depuis le doc
```

Le doc système peut dire « quand on te demande un rappel, utilise l'outil prévu » — c'est une
*façon de répondre*, autorisée par le §5.2 de `agent-consignes-systeme.md`. Il ne peut pas faire
exister un outil. Vérifié par un test : construire `tools_json()` avec un doc système contenant
des définitions d'outils inventées, et constater que la liste produite est inchangée — ce qui est
trivialement vrai ici puisque `tools_json()` ne prend aucun argument, et c'est *exactement* la
propriété qu'on veut préserver dans le temps.

Première entrée concrète du registre annoncé par `#1787559677498`, qui reste ouvert pour son autre
volet (déclencheurs `@bidule` définis par consigne).
"""
from __future__ import annotations

from typing import Any

from app.services.agent_tools import create_reminder, web_search
from app.services.agent_tools.base import ToolSpec

# Ordre = ordre d'exposition au modèle. Tous les outils du catalogue, configurés ou non.
_ALL: tuple[ToolSpec, ...] = (
    create_reminder.SPEC,
    web_search.SPEC,
)


def _is_available(spec: ToolSpec) -> bool:
    """Un outil dont le backend n'est pas configuré n'est pas exposé.

    Sinon le modèle l'appellerait, recevrait une erreur, et l'utilisateur aurait attendu deux
    tours de boucle pour un « je ne peux pas ». Ce filtre dépend de la **configuration**, jamais
    du doc système : la propriété d'isolation du §3.1 est préservée.
    """
    if spec.manifest.name == "web_search":
        return web_search.search_is_configured()
    return True


def available_specs() -> list[ToolSpec]:
    return [s for s in _ALL if _is_available(s)]


def get(name: str) -> ToolSpec | None:
    """Spec d'un outil **exposé**. `None` si l'outil n'existe pas ou n'est pas disponible.

    Passe par `available_specs()` et non par `_ALL` : un modèle qui invente un nom d'outil, ou qui
    en appelle un retiré de la configuration, doit recevoir une erreur — jamais une exécution.
    """
    return next((s for s in available_specs() if s.manifest.name == name), None)


def tools_json() -> list[dict[str, Any]]:
    """Le paramètre `tools` envoyé à DeepInfra. Ne prend aucune entrée, par construction."""
    return [s.manifest.to_tools_json() for s in available_specs()]


def catalogue() -> str:
    """Résumé lisible du catalogue, pour les logs et le diagnostic."""
    return ", ".join(
        f"{s.manifest.name}({s.manifest.effect.value}"
        f"{', taint' if s.manifest.taints_context else ''})"
        for s in available_specs()
    ) or "(aucun)"
