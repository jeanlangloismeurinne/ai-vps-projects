"""Outillage de l'agent conversationnel — cadre d'autorisation (`roadmap/agent-outillage.md`).

Découpage volontaire, dans l'ordre de lecture :

| Module | Rôle |
|---|---|
| `manifest.py` | ce qu'un outil **déclare** de lui-même + l'état d'un tour (`TurnState`) |
| `policy.py` | la **seule** fonction qui décide d'un régime, à partir du manifeste |
| `registry.py` | ce qui **existe** — liste codée en dur, jamais dérivée du doc système |
| `audit.py` | la trace (`agent_tool_calls`), y compris des refus |
| `loop.py` | la boucle bornée : appel modèle → policy → exécution → réinjection |
| `create_reminder.py`, `web_search.py` | les outils eux-mêmes |

La contrainte de conception dominante : **ajouter le dixième outil doit coûter moins cher que le
premier**. Un nouvel outil remplit un manifeste et écrit son exécuteur ; il ne touche ni à
`policy`, ni à `loop`.
"""
