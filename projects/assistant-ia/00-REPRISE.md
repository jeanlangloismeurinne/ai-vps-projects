---
project: assistant-ia
updated: 2026-09-06
role: >
  Permet de reprendre le chantier « l'agent classe l'intention et capte la donnée ». Le doc système
  est réaligné, le chemin d'écriture vers le vault existe et les contrats d'outil laissent enfin
  l'action aboutir (capacités 1, 2 et 3 livrées) ; répondre dans le fil atteint enfin l'agent.
  Restent la restitution vérifiable et les postures, qui doivent tenir sur la conversation entière.
---

# Prompt de reprise — assistant-ia

> **Roadmap active : `roadmap/agent-intention-et-capture-kb.md`** — prochaines capacités : §4 et §5.

## État

L'orchestrateur tourne en prod (`assistant.jlmvpscode.duckdns.org`) : import bancaire depuis Slack,
journal v2, kanban, système de feedback, miroir du vault. Rien de tout cela n'est en cause.

**Capacités 1, 2 et 3 livrées le 2026-09-05.** L'agent nomme ses outils (doc système v4), écrit
dans le vault (`capture_note` + `list_documents`, documents Markdown adressés par nom), et ses
actions aboutissent : `create_reminder` accepte une date sans année et range la charge utile dans
le corps de la carte.

Le résultat qui compte, mesuré au rejeu réel : **un seul message produit trois outils enchaînés**
(`list_documents` → `capture_note` → `create_reminder`) et **deux effets durables** — un document
dans le vault et une carte datée. Acceptation **9/9, deux fois de suite** contre l'image construite
(`checks/replay_intent_corpus.py`), **157 assertions vertes** hors-ligne
(`checks/check_agent_tools.py`), éprouvées par deux passes négatives par capacité.

**B1 livré le 2026-09-06** (commit `1970700`) : **répondre dans le fil atteint enfin l'agent.**
Jusque-là, tout message porteur d'un `thread_ts` partait vers les seules branches du journal et se
perdait en silence — mesuré le matin même à 07:05, sur la suite d'une note de lecture : aucune
réponse, aucune ligne en base, rien dans le vault. `agent_chat` rattache maintenant réponse,
historique et audit à la **racine** du fil. C'est le préalable de la capacité 5 : on ne peut pas
faire tenir une posture sur une conversation dont la moitié des tours n'arrive pas.

## Reste à faire / dettes ouvertes

- **Capacité 4 — la restitution n'est pas vérifiable.** L'accusé de réception nomme le fichier
  écrit mais ne donne **aucune URL cliquable** (carte kanban ou page kb-viewer). Son test
  d'acceptation doit rester rouge jusque-là.
- **Capacité 5 — les postures situées** (le vrai remplaçant de D2, cf. roadmap §5). Le doc v4 est
  un compromis unique : il ordonne à la fois « agis sans demander » et « rends compte », ce qui
  sert mal une question ouverte comme une exécution. Cible : doc v5 en **blocs nommés**
  (`socle`/`exploration`/`action`/`capture`), un classifieur de **posture** (pas d'outil), et une
  composition du prompt qui ne fait que **sélectionner** des fragments du doc actif.
  ⚠️ *Mesurer d'abord la ligne de base : longueur de réponse et ordre d'appel sous doc v4.*
- **La posture doit tenir sur la conversation** *(amendement utilisateur du 2026-09-06, inscrit
  dans §5)*. Une réponse dans le même fil garde la posture en cours et va **dans la note du même
  thème** ; une **nouvelle** conversation sur ce thème repasse par `list_documents`. La continuité
  est une **portée**, pas une mémoire — un agent qui retient le fichier d'hier écrira avec confiance
  dans un nom périmé, ce qui est le doublon de la capacité 2 par l'autre bout. **D11 tranché : la
  conversation est le fil Slack.**
- **B2 — la « conversation » n'existe pas encore dans le code.** `load_recent_turns` filtre sur
  `channel_id` seul et rend les 20 derniers tours du channel : la fenêtre colle un tour du 09-06 à
  côté d'un tour du 08-24. C'est ce qui reste à faire pour que la posture et le document courant
  aient où se poser. *(B1, le correctif de routage, est livré — voir ci-dessous.)*
- **Le vault porte des doublons de rejeu.** `documents/sources-utiles.md`, `startups-spatial*.md`,
  `courses.md`, `climatisation-r*.md` — produits par mes passes de test des 09-05, l'utilisateur
  n'y a rien écrit. À vider ou supprimer d'un clic dans Obsidian.
- Les tickets de `feedback-tickets/` couvrant l'agent (`1787596637653`, `1787575860968`,
  `1787575776445`) sont **absorbés par cette roadmap** — ne pas les redécouper en unités de travail.

## Gotchas d'implémentation appris en chemin

- **La ligne de base d'un test d'acceptation se requête AVANT le lot, jamais après.** C'est ce qui
  a sauvé la capacité 3 : la roadmap la donnait pour rouge (« C6 a produit zéro effet »), mais ces
  valeurs dataient d'*avant* la capacité 2. Le rejeu du soir a montré que le modèle classait déjà
  les intentions et enchaînait déjà les outils. Le pré-classifieur D2, pourtant « tranché » dans
  une roadmap « figée », **n'a jamais été écrit** — il aurait été du code jamais appelé.
- **Un schéma qui exige une information que le modèle n'a pas est un piège** : « le 1er décembre »
  sans année → le modèle écrit son année de coupure → le code refuse à juste titre → l'action est
  perdue. Avant de durcir une consigne, vérifier que le schéma permet de la respecter.
- **Interdire un rangement ne suffit pas sans interdire ses contournements.** « n'entre pas dans le
  rappel » a laissé le modèle produire un aparté `(À prendre chez toi : …)`. C'est « ni en aparté,
  ni entre parenthèses » qui a fait passer l'assertion au vert.
- **Un champ écrit mais jamais lu est un faux ami.** `agent_conversations.thread_ts` était rempli
  depuis le premier jour — il valait toujours `slack_ts`, et aucune requête ne le lisait. Vu de la
  base, la conversation *semblait* modélisée ; en réalité elle ne l'était pas. Avant de bâtir sur
  une colonne, chercher qui la **lit**, pas qui l'écrit.
- **Le dernier `else` d'un dispatcher est l'endroit où les messages meurent.** La branche « fil »
  interrogeait deux propriétaires possibles (journal v2, ancien journal) et **journalisait un
  WARNING** quand aucun ne revendiquait — un `logger.warning` n'est pas un traitement. Le message
  était perdu sans erreur, sans réponse et sans trace côté utilisateur. Pour toute branche
  terminale : ou bien c'est hors périmètre *et le périmètre est borné explicitement*, ou bien il
  manque un propriétaire.
- **Une passe négative qui produit une trace de pile ne prouve rien** : mon check mourait sur la
  première `ToolError` au lieu de rougir ses assertions, emportant les sections suivantes. Rattraper
  le refus et le traiter comme un **résultat mesuré** — sinon on ignore ce que le check gardait.
- **Une borne écrite en fonction d'elle-même ne borne rien** : les tests de frontière `TITLE_MAX` /
  `TITLE_MAX + 1` restaient verts avec `TITLE_MAX = 200`. Le critère d'acceptation s'énonce en
  **valeur absolue** (`TITLE_MAX <= 60`), sans quoi la passe négative ne le voit pas.
- **Un adressage par nom exige son outil de lecture, livré en même temps** (leçon de la capacité 2 :
  deux rejeux ont produit `startups-spatial.md` puis `startups-spatial-a-creuser.md`).
- **`journal_vault._one_line` contient deux caractères U+2028/U+2029 littéraux**, invisibles dans le
  source : ancrer toute édition de cette fonction sur du texte strictement ASCII.
- **Un doc système qui nie une capacité livrée est aussi grave qu'un doc qui en invente une.**
- **`@admin`/`@update` n'est pas un canal de livraison** — le contenu livré du doc passe par une
  migration, avec une garde « aucune version ≥ N n'existe » (jamais « la version N n'existe pas »).
- **`E'…' '\n' '…'` en SQL est un piège** : le préfixe `E` ne vaut que pour son propre littéral.
  Utiliser le dollar-quoting.
- **Rejouer un tour hors Slack** : `docker cp` le script dans `/app/checks/`, puis
  `docker exec -w /app -e PYTHONPATH=/app assistant-ia python checks/<script>`. Depuis `/tmp`,
  `sys.path[0]` vaut `/tmp` et `import app` échoue.
- **`compose-deploy.sh` sans `-f`** quand le commit est déjà poussé : `--rebuild-only`.

## Où démarrer

Deux capacités indépendantes, dans l'ordre de valeur :

**§5 (postures situées)** — c'est la demande explicite de l'utilisateur : que l'agent adapte sa
manière de répondre à la situation (exploration ≠ action ≠ capture), **et qu'il garde cette posture
quand l'utilisateur répond dans le même fil**. Commencer par **mesurer** la ligne de base sous doc
v4 (longueur de réponse et ordre d'appel sur trois tours types), puis écrire la v5 en blocs nommés.
Les tours P4/P5 de l'acceptation **se rougissent l'un l'autre** : une implémentation qui mémorise
le document globalement passe P4 et rate P5, une qui ne porte aucun état passe P5 et rate P4.

**§4 (restitution vérifiable)** — plus petite : ajouter l'URL de la carte kanban et de la page
kb-viewer dans l'accusé de réception. Les boutons *Annuler* / *Modifier* existent déjà.
