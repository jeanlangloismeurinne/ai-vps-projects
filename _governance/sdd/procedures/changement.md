# Procédure — changement en cours de route

**Règle** : aucune modification silencieuse. Un changement est un **événement qui déclenche
un recentrage**, pas un document à remplir.

| Ce qui change | Qui tranche | Ce qui se passe |
|---|---|---|
| **Local** — choix interne, invisible hors du lot | l'exécutant | une ligne dans le rapport de lot / le journal |
| **Jalon ou spec** — cas ajouté, capacité redécoupée, ordre changé | l'orchestrateur, utilisateur informé | roadmap modifiée (avec la raison) → recentrage |
| **Mission, principe, modèle de référence** | **l'utilisateur seul** | voir ci-dessous |

## Changement de mission ou de principe
1. L'agent rédige l'amendement (avant / après, raison) ; l'utilisateur tranche.
2. `MISSION.md` mis à jour + ligne dans « Historique des principes ».
3. `grep -n 'P<n>' JURISPRUDENCE.md` → chaque décision citant le principe changé est
   relue : confirmée, ou soumise à l'utilisateur. Renuméroter les principes est interdit
   (ajouter, ou marquer « retiré ») : la jurisprudence pointe sur les numéros.
4. Test d'arbitrage relancé si un principe a changé de sens ou d'ordre.
5. Recentrage (le jalon actif sert-il encore la mission ?).

## Ce qui protège des cascades
- Un lot en cours est mené à un point stable (commit vert) avant d'appliquer le changement.
- Changements additifs de préférence : ajouter, migrer, puis retirer l'ancien.
