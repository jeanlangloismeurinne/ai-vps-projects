---
project: assistant-ia
updated: 2026-09-05
role: >
  Permet de reprendre le chantier « l'agent classe l'intention et capte la donnée ». Le doc système
  est réaligné et le chemin d'écriture vers le vault existe (capacités 1 et 2 livrées) ; il reste à
  câbler la classification d'intention au tour de conversation.
---

# Prompt de reprise — assistant-ia

> **Roadmap active : `roadmap/agent-intention-et-capture-kb.md`** — capacité en cours : §3.

## État

L'orchestrateur tourne en prod (`assistant.jlmvpscode.duckdns.org`) : import bancaire depuis Slack,
journal v2, kanban, système de feedback, miroir du vault. Rien de tout cela n'est en cause.

**Capacité 1 livrée le 2026-09-05.** `agent_system_doc` était en v1 « je n'ai pas de mémoire » ; la
migration 016 a semé une v2 qui nomme les outils réellement exposés. Rejeu de C4 contre le modèle
réel : **2 lignes `web_search` en `doc_version=2`**, là où la v1 n'en avait produit aucune en huit
jours, pour **zéro ligne de code applicatif**. C'était bien le doc, et rien d'autre.

**Capacité 2 livrée le 2026-09-05** (commit `3493d55`, HTTP 200, un seul conteneur). L'agent écrit
désormais dans le vault :

- `capture_note` — deux modes, qui sont deux **adressages** et non deux formes de contenu :
  `note` (daté, `notes/{année}/{date}-{slug}.md`, classé et indexé dans `journal_kb_entries`) et
  `document` (par nom, `documents/{slug}.md`, ajout d'un **bloc Markdown libre** en fin de fichier).
- `list_documents` — outil de **lecture** rendant les noms des documents existants, sans leur
  contenu. Il n'était pas au périmètre : le rejeu a montré qu'il est indispensable (voir dettes).
- `journal_vault.append_to_document` — création par `O_CREAT|O_EXCL`, ajout par `O_APPEND`. Le
  fichier n'est **jamais réécrit** ; l'entête n'a aucun champ mutable.
- Doc système en **v4 active** (`migration_018`, 3 233 car.) : vocabulaire « document », Markdown
  libre, et consigne d'ordre « regarder les documents existants avant d'écrire, reprendre le nom
  exact ».

Acceptation : **16/16** au rejeu contre le modèle réel (`checks/replay_capture_corpus.py`), **59
assertions vertes** hors-ligne (`checks/check_agent_tools.py`), éprouvées par deux passes négatives.
`git diff` du vault sur un ajout : `1 file changed, 1 insertion(+)` — le critère `+n / -0` de D5.

## Reste à faire / dettes ouvertes

- **Capacité 3 — l'intention n'est pas encore classée au tour.** Le pré-classifieur (D2, sortie
  `{intents: [enum]}` en `json_schema` fermé) n'existe pas : c'est aujourd'hui le modèle qui décide
  seul, à partir du doc et des descriptions d'outils. C'est le prochain jalon.
- **Fidélité de capture non traitée (C7).** Un titre de rappel de 130 caractères absorbe la charge
  utile et une phrase qui n'appartenait pas à la demande. `create_reminder` appelle toujours
  `create_card(..., description=None)` : le corps de carte n'est pas alimenté.
- **`documents/sources-utiles.md` contient des doublons de rejeu.** Huit lignes dont plusieurs
  répétitions, produites par mes propres passes de test du 09-05 — l'utilisateur n'y a rien écrit.
  À vider ou supprimer d'un clic dans Obsidian ; `startups-spatial.md` et
  `startups-spatial-a-creuser.md` sont dans le même cas (c'est le doublon historique).
- **Le format d'accusé de réception reste minimal** (chemin écrit, pas d'URL kb-viewer cliquable) :
  c'est la capacité 4, et son test d'acceptation doit rester rouge jusque-là.
- Les tickets de `feedback-tickets/` couvrant l'agent (`1787596637653`, `1787575860968`,
  `1787575776445`) sont **absorbés par cette roadmap** — ne pas les redécouper en unités de travail.

## Gotchas d'implémentation appris en chemin

- **Un adressage par nom exige son outil de lecture, livré en même temps.** Deux rejeux de la même
  demande ont produit `startups-spatial.md` puis `startups-spatial-a-creuser.md` : deux fichiers
  pour une liste, aucune erreur levée, la moitié des entrées introuvable. Le modèle n'a pas l'état
  du coffre et repart de zéro à chaque tour. Aucune consigne de prose ne corrige ça — ce n'est pas
  un problème de comportement mais d'information manquante.
- **`journal_vault._one_line` contient deux caractères U+2028/U+2029 littéraux**, invisibles dans le
  source. L'outil `Edit` ne peut pas les matcher : ancrer toute édition de cette fonction sur du
  texte strictement ASCII, jamais sur la ligne `collapsed = re.sub(...)`.
- **Un doc système qui nie une capacité livrée est aussi grave qu'un doc qui en invente une.** La
  migration 017 a été avancée de la capacité 4 à la capacité 2 pour cette raison : la v2 ordonnait
  de dire que la capture « n'est pas encore branchée ». Le rejeu réussissait *malgré* elle (la
  description d'outil emportait la décision) — un succès par chance, pas par conception.
- **Un script de rejeu qui prédit un chemin teste le script, pas le code.** Ma correction de
  rejouabilité (suffixe de session dans le nom demandé) a viré au rouge parce que le modèle a fait
  exactement ce qu'on lui demande : réutiliser le nom du document existant. La bonne forme est de
  **relever l'état avant et après le tour et de déduire la cible du delta**.
- **`@admin`/`@update` n'est pas un canal de livraison** — c'est l'outil par lequel *l'utilisateur*
  coache l'agent depuis Slack. Le contenu livré du doc système passe par une migration.
- **Une migration qui sème du contenu se garde contre les décisions humaines postérieures** : garde
  « aucune version ≥ N n'existe », jamais « la version N n'existe pas ». Le runner rejoue tous les
  `.sql` à chaque démarrage.
- **`E'…' '\n' '…'` en SQL est un piège** : le préfixe `E` ne vaut que pour le littéral qui le porte.
  Utiliser le dollar-quoting.
- **Rejouer un tour hors Slack** : copier le script dans `/app` puis `docker exec -w /app assistant-ia
  python <script>`. Depuis `/tmp`, `sys.path[0]` vaut `/tmp` et `import app` échoue.
- **`compose-deploy.sh` sans `-f`** quand le commit est déjà poussé : `--rebuild-only`. Sinon le
  script sort en code 2 (« index vide »).

## Où démarrer

Ouvrir la capacité 3 : le pré-classifieur d'intention (D2) dans `handlers/agent_chat.py`, en amont
de `agent_tools/loop`, avec le texte utilisateur en **donnée délimitée** et un fallback
`["conversation"]` qui ne perd jamais un tour ; puis la fidélité C7 (titre court, charge utile en
corps de carte). Les deux tests négatifs sont mesurés et rouges : C6 a produit zéro effet, C7 un
titre de 130 caractères incluant la phrase à exclure.
