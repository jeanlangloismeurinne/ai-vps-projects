# Session Brief — assistant-ia — 2026-08-24

## Roadmap — définition (avant implémentation)
- [x] roadmap-agent-consignes-systeme : Roadmap — Agent conversationnel & consignes système auto-accumulées
- [x] roadmap-journal-knowledge-base : Roadmap — Base de connaissance du journal (Obsidian + index Postgres)

## Résumé de session — 2026-08-24 08:21

Étape 4a du CONTROL_SYSTEM : les deux roadmaps (`status: spec-ready`) ont été converties en
tickets. **Aucun code écrit** — conforme au brief (« avant implémentation »).

🗂 **Tickets créés depuis roadmap (15)**

- Prérequis partagé : `1787559677482`
- `journal-kb` : `1787559677483` · `1787559677484` · `1787559677485` · `1787559677486` ·
  `1787559677487` · `1787559677488` — hors v1 : `1787559677489`
- `agent-consignes` : `1787559677492` · `1787559677493` · `1787559677494` · `1787559677495` ·
  `1787559677496` · `1787559677497` — hors v1 : `1787559677498`
- `knowledge-federation` : `1787559677490` · `1787559677491`

🔓 **Débloqué** : `1787252691603` (`blocked` → `open`) — modèle de sécurité §5 validé et réparti
en contraintes vérifiables dans les tickets, décisions §7 tranchées.

🔎 **Trois écarts entre les roadmaps et le réel, corrigés dans les tickets**

1. `app/slack_app.py:42` fait `if not thread_ts: return` → tout message **parent** est ignoré.
   Les deux chantiers supposaient de capter ces messages (note libre, `@admin`). Prérequis
   commun extrait en `1787559677482`.
2. **Aucun Nextcloud sur le VPS** alors que la décision §6 reposait dessus → vault en **dépôt git**
   (option B). Roadmap journal §6 révisée, §6.1 conservée pour un retour éventuel.
3. Migration annoncée `003_journal_kb.sql` alors que le dossier va **jusqu'à 008** → renumérotée
   `009` (et `010` / `011` pour la suite).

💡 **Gain repéré** : le client DeepInfra existe déjà en production dans
`portfolio-tracker/backend/app/agents/providers/deepinfra_provider.py` → portage, pas écriture.

⚠️ **À trancher avant de démarrer `1787559677490`** : la roadmap journal §5 dit « la fédération
est construite dès maintenant », `KNOWLEDGE_ARCHITECTURE.md` §4 dit « ne rien construire tant que
le besoin n'est pas là ». Ticket marqué `needs_clarification`.

📋 **Actions manuelles côté utilisateur, avant `1787559677493`**

- Inviter `@ai_vps_jlm` dans `#assistant` (`C0ATLALRZL3`) et `#feedback-assistant` (`C0BSB9S9HHS`)
  — channels **privés**, aucun événement reçu sans ça.
- Provisionner `DEEPINFRA_API_KEY` dans les variables d'env Coolify d'assistant-ia.

## Résumé de session — 2026-08-24 12:05

Deuxième passe : **exécution de la V1 complète** (choix utilisateur : « tous les tickets de la V1
dans l'ordre optimal »). 13 tickets livrés, l'ombrelle `1787252691603` fermée.

✅ **Implémentés (Opus)** : `1787559677482` · `1787559677485` · `1787559677487` ·
`1787559677494` · `1787559677495` · `1787559677496` · `1787559677497`
🤖 **Implémentés (worker Sonnet, vérifiés)** : `1787559677483` · `1787559677484` ·
`1787559677486` · `1787559677488` · `1787559677492` · `1787559677493`
🏁 **Ombrelle fermée** : `1787252691603`
⏭ **Hors V1, restés ouverts** : `1787559677489` · `1787559677498` ·
`1787559677490` / `1787559677491` (knowledge-federation, `490` toujours `needs_clarification`)

🔎 **Écarts corrigés après vérification**

1. `1787559677485` — le ticket imposait `nature` en `1..n`, la roadmap
   (`journal-knowledge-base.md:72`) dit `0..n`. Le minimum forcé produisait un vrai défaut observé :
   une note de week-end en montagne classée `note_de_lecture`. **La roadmap fait foi** → schema,
   validateur et prompt corrigés ; une liste vide est désormais un signal honnête.
2. `1787559677486` — `ensure_vault()` levait une exception si `git init` échouait, ce qui tuait
   toute l'ingestion et **perdait la note de l'utilisateur** pour un problème d'outillage — l'inverse
   de ce que le vault protège. Aligné sur `_commit` : best-effort, avertissement en log.
   Découvert parce que l'image de production n'embarquait pas `git` (corrigé dans le `Dockerfile`).
3. `1787559677495` — un garde-fou refusait **le cas nominal** : le motif attrapait tout backtick
   Markdown inline, or le doc système cite `` `/feature` ``. Toute proposition préservant le texte
   d'origine était auto-rejetée. Réduit à `$(`. Assertion de non-régression ajoutée : le doc actif
   doit passer ses propres bornes.
4. `1787559677497` — retour d'erreur figé sur `edit/1` (faux dès que la version active change) et
   messages non encodés dans l'en-tête `Location`.

🔐 **Configuration DeepInfra** — la clé de portfolio-tracker a été **copiée chiffrée** d'app à app
directement dans la base Coolify (ciphertext Laravel, jamais déchiffré ni affiché), puis
déchiffrement vérifié côté Coolify. ⚠️ **Clé empruntée : en générer une propre à assistant-ia.**
`DEEPINFRA_MODEL_CLASSIF` basculé sur la variante `-Turbo` : `Meta-Llama-3.1-8B-Instruct` est
**déprécié chez DeepInfra depuis le 2026-07-16**.

📋 **Actions manuelles restantes côté utilisateur**

- Inviter `@ai_vps_jlm` dans `#assistant` (`C0ATLALRZL3`) et `#feedback-assistant` (`C0BSB9S9HHS`)
  — channels privés, **aucun événement reçu sans ça**.
- Renseigner `AGENT_APPROVERS` (Slack user ID) : sans elle **personne ne peut approuver un diff**.
  Aucun ID utilisateur n'existe en base, la valeur ne pouvait pas être devinée ; au premier clic le
  bot affiche l'ID à copier.
- Générer une clé DeepInfra propre à assistant-ia.

🧪 **Vérification** — 37 assertions pour `497`, 43 pour `495`+`496`, 20 pour `494`, 22 pour `487`,
12 pour `485`, exécutées dans le container avec restauration de l'état de la base après chaque run.
Toutes les vérifications passant par un **appel réel à DeepInfra** restent à faire après
déploiement : le classifieur `0..n`, un tour de conversation dans `#assistant` et un aller-retour
complet consigne → `@update` → approbation.

## Résumé de session — 2026-08-24 13:12

Troisième passe : **déblocage de la configuration + étape 1 de la prochaine session**
(vérifications réelles contre DeepInfra). Deux commits : `8d3d3db`, `a574a75`.

🔓 **Bloquants levés**

- `AGENT_APPROVERS=UJ724E07L` (Jean Langlois-Meurinne) provisionnée dans Coolify et vérifiée
  dans le container. `is_approver` : `True` pour cet ID, `False` pour un ID inconnu et pour `None`.
- `@ai_vps_jlm` est **déjà membre** de `#assistant` et `#feedback-assistant` (vérifié via
  `conversations.info`, `is_member=true`) — action utilisateur faite, plus un bloquant.

✅ **Vérifications réelles passées** (les chemins jamais exercés contre l'API)

- Doc système actif en base (version 1), tour de conversation complet contre
  `DeepSeek-V4-Flash` → réponse cohérente avec le doc (refus d'exécuter, oriente vers `/feature`).
- Classifieur : 3 cas, aucun fallback, vocabulaire respecté, `0..n` honoré.

🐛 **Défaut réel trouvé — le correctif `0..n` de la passe précédente ne tenait pas**

La vérification a montré que le week-end en montagne était **toujours** classé `note_de_lecture` :
le schema et le prompt avaient bien été corrigés, mais la contrainte ne s'appliquait jamais.
Cause : **DeepInfra refuse `response_format: json_schema` pour Llama 3.1 8B-Turbo (HTTP 405)**.
Trois conséquences, toutes observées :

1. Chaque classification coûtait **2 requêtes** (405 puis fallback `json_object`).
2. Le vocabulaire fermé n'était plus qu'une consigne en prose → `nature: ["vacances"]`
   (un **tag libre**) 1 tirage sur 2, rejeté par le validateur → note en « à classer ».
3. La cardinalité `0..n` n'était jamais honorée (0/4 tirages avec liste vide).

**Correctif** (`a574a75`) : bascule sur `DeepSeek-V4-Flash`, qui supporte `json_schema`, et
passage du vocabulaire en **`enum`** — toujours dérivé de `categories.schema.yaml`, jamais en dur.
Mesuré après correctif : 4/4 tirages conformes, 0 hors-vocabulaire, 1 seul appel API.
La validation Python est **conservée** : elle reste le seul garde-fou si `chat_json` retombe
sur `json_object`.

🧪 `checks/check_classifier_live.py` fige ces 3 cas contre l'API réelle (à lancer dans le
container, la clé n'est pas sur l'hôte). ⚠️ `checks/check_kb_export.py` échoue dans le container
(`parents[3]` suppose l'arborescence du repo) — pré-existant, sans lien avec cette session.

⚖️ **Arbitrages rendus en séance**

- **Fédération KB : on ne construit pas.** `1787559677490` et `1787559677491` fermés
  `wont-do-for-now`. La charte `KNOWLEDGE_ARCHITECTURE.md` §4 (transverse) l'emporte sur la
  roadmap journal §5 (un seul projet) ; aucune requête multi-source n'a été formulée, le besoin
  était supposé. L'export « enveloppe commune » étant livré, la décision est réversible.
  Roadmap journal §5 marquée caduque avec la condition de réouverture, pour ne pas rejouer
  ce débat dans six mois.
- **Accès web (`1787575860968`)** : la contrainte « éviter Exa pour préserver les crédits »
  n'a pas à être arbitrée — `websearch.py` de portfolio-tracker est agnostique du fournisseur
  (`SEARCH_PROVIDER=exa|serper|none`), assistant-ia aura sa propre clé quoi qu'il arrive.
  SearXNG reste écarté (résultats vides silencieux depuis une IP captchaée, déjà constaté).
  ⚠️ Le vrai sujet est le **tool-calling** : l'agent n'a aucun outil en v1 *par conception*
  (modèle de sécurité §5). Ce ticket demande une **roadmap**, pas une implémentation directe.

✨ **Livré aussi** : `1787575776445` — indicateur « je réfléchis… » posté avant l'appel modèle
puis remplacé par la réponse (`chat.update`), un seul message dans le fil. Vérifié de bout en
bout contre Slack et DeepInfra, état Slack et base restaurés après le test.

📋 **Reste côté utilisateur** : générer une clé DeepInfra propre à assistant-ia (celle de
portfolio-tracker est toujours empruntée).

## Prochaine session — ordre d'exécution proposé

1. ~~Vérifications réelles post-déploiement~~ — **faites** (session 13:12), un défaut trouvé
   et corrigé. Reste **un** aller-retour non exercé : consigne → `@update` → approbation d'un
   diff, qui passe par un vrai clic dans Slack et ne peut pas être simulé hors interface.
   `AGENT_APPROVERS` étant désormais renseignée, c'est faisable dès le prochain message.
2. ~~Trancher `1787559677490`~~ — **tranché** : fermé `wont-do-for-now` avec `491` (voir ci-dessus).
3. **Roadmap pour `1787575860968`** (accès web) : c'est le chantier suivant le plus lourd, il
   touche le modèle de sécurité §5 (donner un premier outil à l'agent). Analyse préalable déjà
   écrite dans le ticket — partir de là, pas de zéro.
4. Puis `1787559677489` (curator/lint KB) et `1787559677498` (registre `@bidule`, v2).
