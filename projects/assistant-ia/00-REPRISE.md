---
project: assistant-ia
updated: 2026-09-05
role: >
  Permet de reprendre le chantier « l'agent classe l'intention et capte la donnée » — l'agent
  conversationnel Slack nie avoir mémoire et outils alors que les deux sont câblés.
---

# Prompt de reprise — assistant-ia

> **Roadmap active : `roadmap/agent-intention-et-capture-kb.md`** — capacité en cours : §1.

## État

L'orchestrateur tourne en prod (`assistant.jlmvpscode.duckdns.org`) : import bancaire depuis Slack,
journal v2, kanban, système de feedback, miroir du vault. Rien de tout cela n'est en cause.

Le chantier ouvert porte sur **l'agent conversationnel du channel `#assistant`**. L'outillage v1 est
livré (`agent_tools/` : manifeste, policy dérivée, registre, boucle bornée, audit, `create_reminder`,
`web_search`) et Exa est actif depuis le 2026-08-24. **Mais le doc système est resté en v1** — il
dit « Tu n'exécutes aucune action et ne disposes d'aucun outil » — et comme `agent_chat.py:191`
construit le prompt à partir de ce seul document, le modèle joue ce rôle : il nie sa mémoire, nie
savoir chercher, et ne capte rien.

Mesuré le 2026-09-05, sur 24 tours réels : **2 appels d'outils au total**, tous deux
`create_reminder` ; **zéro** `web_search` malgré Exa actif ; **zéro** note dans le vault. Un rappel
demandé le 28/08 pour le 1er décembre n'a jamais été créé — l'agent a demandé confirmation au lieu
d'agir, et la demande s'est perdue.

La roadmap est **figée** : quatre capacités ordonnées, chacune avec un test d'acceptation rejouable
sur un corpus de 9 messages utilisateur verbatim (C1 → C9), et chacune avec sa valeur de départ déjà
requêtée — les tests négatifs sont donc déjà rouges, mesure à l'appui.

## Reste à faire / dettes ouvertes

- **Le doc système n'a jamais été réaligné** (capacité 1). C'est la cause racine, elle coûte zéro
  ligne de code, et elle attend depuis le 2026-08-24. Elle exige une **revue de diff humaine** via
  `@update` — non délégable, non auto-activable.
- **Preuve à ne pas réapprendre** : Exa a été activé le 24/08 et l'agent niait encore savoir
  chercher le 01/09. Corriger la configuration ne corrige pas le comportement — seul le doc le fait.
  Toute capacité qui ne passe pas par lui est suspecte de ne rien changer. *(Consigné dans
  `DECISIONS.md`.)*
- **Répertoires `notes/` et `listes/` absents du vault** — à créer par la capacité 2, pas à la main.
- **Fidélité de capture non traitée** (C7) : un titre de rappel de 130 caractères absorbe la charge
  utile et une phrase qui n'appartenait pas à la demande. Capacité 3.
- Les tickets de `feedback-tickets/` couvrant l'agent (`1787596637653`, `1787575860968`,
  `1787575776445`) sont **absorbés par cette roadmap** — ne pas les redécouper en unités de travail.

## Où démarrer

Rédiger la v2 du `agent_system_doc` (capacité 1), la soumettre via `@update`, la faire approuver —
puis rejouer C4 et vérifier qu'une ligne `web_search` apparaît dans `agent_tool_calls`.
