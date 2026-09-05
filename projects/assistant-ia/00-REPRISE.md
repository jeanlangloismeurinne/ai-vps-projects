---
project: assistant-ia
updated: 2026-09-05
role: >
  Permet de reprendre le chantier « l'agent classe l'intention et capte la donnée ». Le doc système
  est réaligné (capacité 1 livrée) ; il reste à construire le chemin d'écriture vers le vault.
---

# Prompt de reprise — assistant-ia

> **Roadmap active : `roadmap/agent-intention-et-capture-kb.md`** — capacité en cours : §2.

## État

L'orchestrateur tourne en prod (`assistant.jlmvpscode.duckdns.org`) : import bancaire depuis Slack,
journal v2, kanban, système de feedback, miroir du vault. Rien de tout cela n'est en cause.

**Capacité 1 livrée et vérifiée le 2026-09-05.** `agent_system_doc` est en **v2 active** (2 175 car.,
`created_by=migration_016`), semée par `migrations/016_agent_system_doc_v2.sql`. Les dénis sont
supprimés, `create_reminder` et `web_search` sont nommés, la règle « agir sans demander » (D6) et la
règle de non-déni sont écrites. Le rejeu de C4 contre le modèle réel produit **2 lignes `web_search`
en `doc_version=2`** dans `agent_tool_calls` — là où la v1 n'en avait produit aucune en huit jours.
Zéro ligne de code applicatif : c'était bien le doc, et rien d'autre.

Le chantier ouvert est désormais le **chemin d'écriture vers le vault** (capacité 2). L'utilisateur
l'a désigné comme prioritaire : « la capture de note, c'est un rôle clef pour un assistant ».

## Reste à faire / dettes ouvertes

- **`journal_vault.py` ne sait pas ajouter une ligne à un fichier existant.** `write_entry` est
  append-only au sens *ne jamais écraser* : elle crée `{année}/{AAAA-MM-JJ}-{slug}.md` et suffixe en
  cas de collision. Le mode `append` des listes nommées (D5) exige une **fonction neuve**, avec les
  mêmes barrières (`slugify` + `_resolve_within_vault` + écriture atomique + commit git best-effort).
  La roadmap annonçait « zéro brique neuve » — c'était faux, elle est corrigée.
- **`write_entry` n'a jamais servi.** Le vault contient 6 `.md` : 3 de structure (`Accueil`,
  `Taxonomie`, `README`) et 3 du miroir kanban sous `tasks/`. Aucun répertoire d'année, aucun
  `notes/`, aucun `listes/`. Il n'existe donc **aucune convention établie** à respecter — la
  capacité 2 la pose.
- **Contrainte utilisateur du 09-05 : capter dans ce que kb-viewer indexe.** Vérifié :
  `projects/kb-viewer/build.sh` fait `npx quartz build -d /vault`, donc **tout** le vault est indexé
  et servi, quel que soit le répertoire. La contrainte exclut de capter ailleurs que dans le vault ;
  elle ne tranche pas le choix `{année}/…` vs `notes/…`, qui reste à arbitrer en ouvrant la
  capacité 2.
- **Le doc système v2 porte un paragraphe volontairement daté** : « enregistrer une note ou une
  liste durable dans la base de connaissance n'est pas encore branché ». Il devient **faux** dès que
  `capture_note` existe. C'est l'addendum de la capacité 4 qui le remplace — par une migration 017,
  jamais en modifiant la 016.
- **Fidélité de capture non traitée** (C7) : un titre de rappel de 130 caractères absorbe la charge
  utile et une phrase qui n'appartenait pas à la demande. Capacité 3. Noter que `create_reminder`
  appelle aujourd'hui `create_card(..., description=None)` : le corps de carte n'est pas alimenté.
- Les tickets de `feedback-tickets/` couvrant l'agent (`1787596637653`, `1787575860968`,
  `1787575776445`) sont **absorbés par cette roadmap** — ne pas les redécouper en unités de travail.

## Gotchas d'implémentation appris en chemin

- **`@admin`/`@update` n'est pas un canal de livraison** — c'est l'outil par lequel *l'utilisateur*
  coache l'agent depuis Slack. Le contenu livré du doc système passe par une migration, comme la v1.
- **Une migration qui sème du contenu doit se garder contre les décisions humaines postérieures** :
  garde « aucune version ≥ N n'existe », jamais « la version N n'existe pas ». Le runner rejoue tous
  les `.sql` à chaque démarrage.
- **`E'…' '\n' '…'` en SQL est un piège** : le préfixe `E` ne vaut que pour le littéral qui le porte,
  les fragments suivants insèrent un antislash-n littéral. Utiliser le dollar-quoting.
- **Rejouer un tour hors Slack** : copier le script dans `/app` puis `docker exec -w /app assistant-ia
  python <script>`. Depuis `/tmp`, `sys.path[0]` vaut `/tmp` et `import app` échoue.
- **`compose-deploy.sh` sans `-f`** quand le commit est déjà poussé : `--rebuild-only`. Sinon le
  script sort en code 2 (« index vide »).

## Où démarrer

Ouvrir la capacité 2 : trancher l'arborescence de capture (`{année}/{date}-{slug}.md` produit par
`write_entry`, contre `notes/{slug}.md` annoncé par la roadmap §A2), écrire `append_to_list` dans
`journal_vault.py`, puis `agent_tools/capture_note.py`. Le test négatif est déjà rouge et mesuré :
aucun `listes/`, aucune note captée dans le vault.
