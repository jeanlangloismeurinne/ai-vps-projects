---
project: assistant-ia
updated: 2026-09-06
role: >
  Permet de reprendre le chantier « l'agent classe l'intention et capte la donnée ». Le doc système
  est réaligné, le chemin d'écriture vers le vault existe, les contrats d'outil laissent l'action
  aboutir (capacités 1, 2 et 3 livrées), répondre dans le fil atteint l'agent (B1, vérifié par un
  vrai message) et la KB est enfin navigable. Reste la restitution vérifiable — devenue urgente
  depuis qu'un accusé de réception mensonger a été mesuré — et surtout : faire tenir la posture ET
  la cible d'écriture sur trois portées de temps (la conversation, la suivante, puis le corpus).
---

# Prompt de reprise — assistant-ia

> **Roadmap active : `roadmap/agent-intention-et-capture-kb.md`** — prochaines capacités : §4, §5,
> puis §6 et §7 (ajoutées le 2026-09-06).

**Le fil conducteur des capacités 5 à 7 : trois portées de temps du même problème** — retrouver où
une information doit aller. §5 = le tour d'après, dans le fil (la conversation *porte* la cible,
rien à chercher) · §6 = une conversation neuve, utilisateur présent (un outil de lecture, à
l'écriture) · §7 = à froid, tout le corpus, chaque semaine. Elles se cumulent, ne se remplacent
pas, et **6 vient avant 7** : 6 relie pendant que l'utilisateur peut corriger d'un mot.

## État

L'orchestrateur tourne en prod (`assistant.jlmvpscode.duckdns.org`) : import bancaire depuis Slack,
journal v2, kanban, système de feedback, miroir du vault. Rien de tout cela n'est en cause.

**Capacités 1, 2 et 3 livrées le 2026-09-05.** L'agent nomme ses outils (doc système v4), écrit
dans le vault (`capture_note` + `list_documents`, documents Markdown adressés par nom), et ses
actions aboutissent : `create_reminder` accepte une date sans année et range la charge utile dans
le corps de la carte. Acceptation **9/9, deux fois de suite** contre l'image construite
(`checks/replay_intent_corpus.py`), **157 assertions vertes** hors-ligne
(`checks/check_agent_tools.py`), éprouvées par deux passes négatives par capacité.

**B1 livré ET vérifié le 2026-09-06** (commit `1970700`). Jusque-là, tout message porteur d'un
`thread_ts` partait vers les seules branches du journal et se perdait en silence. La vérification
qui manquait est faite : le message perdu à 07:05 a été renvoyé dans son fil à 11:03, il a atteint
l'agent, et les deux tours sont en base rattachés à la racine `1788677480.225329`.

**Navigation de la KB livrée le 2026-09-06** (commit `4c596d5`). Le défaut signalé par
l'utilisateur avait une cause unique et mesurable : `Accueil.md` proposait `[[Journal]]` et
`[[Tâches]]`, deux fichiers `.base` (plugin Obsidian Bases) **que Quartz ne rend pas** — 404 sur le
site depuis 12 jours, et pas seulement sur l'accueil : la barre latérale de chaque note pointait
dessus aussi, **55 liens morts** au total. `kb_schema_notes` génère désormais trois vraies pages
`.md` — `Accueil` (synthèse par thème, page d'entrée), `Journal` (toutes les notes, antéchronologique),
`Tâches` (le kanban par tableau et colonne) — **balayées depuis le disque et non depuis l'index** :
un lien ne peut alors désigner qu'un fichier qui existe, l'invariant est structurel et non surveillé.
Les `.base` restent générés (utiles dans Obsidian desktop) mais **plus aucune page n'y renvoie**.

## Reste à faire / dettes ouvertes

- **Capacité 4 — la restitution n'est pas vérifiable, et ce n'est plus une gêne cosmétique.**
  Mesuré le 2026-09-06 à 11:03 : l'agent a répondu *« Noté. Cette analyse est ajoutée à votre note
  de lecture »* avec **zéro appel d'outil**, dernier commit du vault à 06:51, `git status` vide.
  Perte silencieuse **plus** accusé de réception mensonger. C'est pire que le défaut P4 : là où le
  modèle refusait d'agir, il affirme maintenant avoir agi. Un accusé qui ne cite pas d'URL
  vérifiable ne coûte rien à fabriquer — c'est exactement ce qui rend §4 nécessaire. *Le tour a été
  rattrapé à la main (`checks/recover_lost_captures.py`) ; la cause, elle, est ouverte.*
- **Capacité 5 — les postures situées** (le vrai remplaçant de D2, cf. roadmap §5). Le doc v4 est
  un compromis unique : il ordonne à la fois « agis sans demander » et « rends compte », ce qui
  sert mal une question ouverte comme une exécution. Cible : doc v5 en **blocs nommés**
  (`socle`/`exploration`/`action`/`capture`), un classifieur de **posture** (pas d'outil), et une
  composition du prompt qui ne fait que **sélectionner** des fragments du doc actif.
  ⚠️ *Mesurer d'abord la ligne de base : longueur de réponse et ordre d'appel sous doc v4.*
- **La posture doit tenir sur la conversation** *(amendement utilisateur du 2026-09-06, inscrit
  dans §5)*. Une réponse dans le même fil garde la posture en cours et va **dans la note du même
  thème**. La continuité est une **portée**, pas une mémoire : un agent qui retient le fichier
  d'hier écrira avec confiance dans un nom périmé — le doublon de la capacité 2 par l'autre bout.
  **D11 tranché : la conversation est le fil Slack.** Ce qui se passe à la conversation *suivante*
  n'est pas de son ressort : c'est la capacité 6.
- **B2 — la « conversation » n'existe pas encore dans le code.** `load_recent_turns` filtre sur
  `channel_id` seul et rend les 20 derniers tours du channel : la fenêtre colle un tour du 09-06 à
  côté d'un tour du 08-24. C'est le premier morceau de la capacité 5 — la posture et la cible
  d'écriture n'ont aujourd'hui **où se poser**. *(B1, le correctif de routage, est livré et vérifié.)*
- **Capacité 6 — retrouver le thème à l'écriture** *(ajoutée le 2026-09-06)*. `list_documents` fait
  `glob("documents/*.md")` : il est **structurellement aveugle à `notes/`**. Une note de lecture
  n'est donc pas retrouvable — quel que soit le comportement du modèle. L'index `journal_kb_entries`
  porte déjà `title`/`tags[]`/`nature[]`/`uri` ; il lui manque son **outil de lecture**
  (`search_notes`).
  *Ligne de base remesurée le 09-06 : les deux notes De Gaulle viennent du **même fil**
  (`1788677480.225329`, 06:51 et 11:03) et sont rangées sous deux tags disjoints — `Charles de
  Gaulle` et `De Gaulle` — sans aucun lien entre elles. Symptôme plus dur que l'ancien titre
  dupliqué : `search_notes` devra rapprocher deux libellés qui ne s'égalent pas. Il est visible en
  permanence sous « Notes isolées » sur la page d'accueil du coffre.*
- **Capacité 7 — agent d'organisation hebdomadaire** *(ajoutée le 2026-09-06)*. Regroupe les
  entrées voisines, tisse les liens, assemble une **note globale par thème**. Liens **typés** :
  `enfant` (appartenance) vs `voisin` (proximité sémantique), D12. ⚠️ **Premier composant qui écrira
  dans le vault sans témoin** : il n'écrit que du **dérivé** (D13), ne touche aucun octet de
  `notes/` ni `documents/`, et une seconde passe immédiate doit produire un **diff vide**. Une
  entrée que rien n'apparente reste **orpheline** — un regroupeur qui ne laisse jamais d'orphelin ne
  mesure rien, il range tout. *Son test de regroupement porte sur les 4 notes Safran, dont
  « propulsion électrique » qui ne partage aucun mot-clef avec les autres hors `Safran`/`satellite` :
  c'est elle qui distingue un assembleur d'un `grep`.*
- Les tickets de `feedback-tickets/` couvrant l'agent (`1787596637653`, `1787575860968`,
  `1787575776445`) sont **absorbés par cette roadmap** — ne pas les redécouper en unités de travail.

## Gotchas d'implémentation appris en chemin

- **Un `__pycache__` périmé fabrique un vert (ou un rouge) qui ne correspond à aucun source.** Après
  une passe négative, j'ai remis `_SEUIL_THEME` de 1 à 2 par `sed` dans le conteneur : le fichier
  lisait 2, le runtime appliquait 1, et `m.__file__` pointait pourtant le bon chemin. Cause :
  patch et restauration dans **la même seconde**, pour une taille d'octets identique — l'invalidation
  `(mtime, size)` du bytecode ne voit rien. La première génération réelle a produit 21 thèmes bidon.
  **Ne pas patcher un `.py` à la main dans le conteneur pour une passe négative** ; si c'est
  inévitable, `find /app/app -name __pycache__ -type d -exec rm -rf {} +` avant de conclure.
- **Un contrôle se teste à l'endroit où le lecteur l'éprouve.** `[[Journal]]` désignait un fichier
  qui *existait* dans le coffre : tout check écrit au point d'écriture serait resté vert pendant que
  le site rendait 404. D'où deux checks et non un : `check_kb_navigation.py` (le wikilink désigne un
  fichier) **et** `check_kb_site_links.py` (le href résout sur le HTML servi). C'est le second qui
  aurait vu le défaut.
- **La ligne de base d'un test d'acceptation se requête AVANT le lot, jamais après.** C'est ce qui
  a sauvé la capacité 3 : la roadmap la donnait pour rouge, mais ces valeurs dataient d'*avant* la
  capacité 2. Le pré-classifieur D2, pourtant « tranché » dans une roadmap « figée », **n'a jamais
  été écrit** — il aurait été du code jamais appelé.
- **Une fixture de rejeu qui écrit dans le vrai coffre y laisse des faits inventés.** Trois notes
  `eu-space-act-*` ont servi douze jours de « corpus réel » à deux tests d'acceptation. Elles
  portaient une thèse *réglementaire* que l'utilisateur n'a jamais écrite (la sienne était
  *commerciale*) — c'est lui qui l'a repéré, pas un check. Avant de bâtir une acceptation sur des
  données du vault, **remonter à leur tour d'origine dans `agent_conversations`**.
- **Un schéma qui exige une information que le modèle n'a pas est un piège** : « le 1er décembre »
  sans année → le modèle écrit son année de coupure → le code refuse à juste titre → l'action est
  perdue. Avant de durcir une consigne, vérifier que le schéma permet de la respecter.
- **Interdire un rangement ne suffit pas sans interdire ses contournements** (« ni en aparté, ni
  entre parenthèses »).
- **Un champ écrit mais jamais lu est un faux ami.** `agent_conversations.thread_ts` était rempli
  depuis le premier jour, valait toujours `slack_ts`, et aucune requête ne le lisait. Avant de bâtir
  sur une colonne, chercher qui la **lit**, pas qui l'écrit.
- **Le dernier `else` d'un dispatcher est l'endroit où les messages meurent** : un `logger.warning`
  n'est pas un traitement. Pour toute branche terminale : ou bien c'est hors périmètre *et le
  périmètre est borné explicitement*, ou bien il manque un propriétaire.
- **Une passe négative qui produit une trace de pile ne prouve rien.** Corollaire appliqué dans les
  checks : accéder aux pages par `pages.get(nom, "")` et non `pages[nom]`, pour qu'une page absente
  **rougisse une assertion nommée** au lieu de tuer le bilan sur un `KeyError`.
- **Une borne écrite en fonction d'elle-même ne borne rien** : le critère s'énonce en **valeur
  absolue** (`TITLE_MAX <= 60`), sans quoi la passe négative ne le voit pas.
- **Un adressage par nom exige son outil de lecture, livré en même temps.** Et le piège suivant :
  un outil de lecture qui ne couvre qu'une partie du corpus. `list_documents` rend `verdict=ok` et
  ne voit que `documents/`, jamais `notes/` — le doublon revient *avec* l'outil, donc invisible à
  l'audit. Vérifier que la **couverture** de `list_*` égale l'espace adressable de `write_*`.
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
- **kb-viewer n'est pas déployé par `compose-deploy.sh`.** Le site se reconstruit tout seul : une
  path unit systemd surveille `.git/logs/HEAD` du vault. Après un commit du coffre, attendre
  `systemctl status kb-viewer-build.service` plutôt que de lancer `build.sh` à la main.

## Où démarrer

Quatre capacités ouvertes. **§5 → §6 → §7 forment une chaîne** (trois portées de temps, cf. l'entête)
et se font dans cet ordre ; **§4 est indépendante** et peut s'intercaler.

**§4 (restitution vérifiable)** — la plus petite, et elle a gagné en urgence : ajouter l'URL de la
carte kanban et de la page kb-viewer dans l'accusé de réception. Le mensonge du 11:03 montre qu'un
accusé sans URL ne prouve rien ; une URL, si. Les boutons *Annuler* / *Modifier* existent déjà.

**§5 (postures situées)** — la demande explicite de l'utilisateur : que l'agent adapte sa manière
de répondre à la situation (exploration ≠ action ≠ capture), **et qu'il garde cette posture quand
l'utilisateur répond dans le même fil**. Attaquer par **B2** (donner une portée à la conversation,
D11 = le fil), puis **mesurer** la ligne de base sous doc v4, puis écrire la v5 en blocs nommés.
Les tours P4/P5 de l'acceptation **se rougissent l'un l'autre** : une implémentation qui mémorise le
document globalement passe P4 et rate P5, une qui ne porte aucun état passe P5 et rate P4.

**§6 (retrouver le thème à l'écriture)** — la plus mécanique des trois, et celle dont le défaut est
déjà prouvé dans l'index : livrer `search_notes` sur `journal_kb_entries`, faire porter à la note
neuve un lien `enfant` vers son thème, sans toucher la note pré-existante. *Requêter la ligne de
base avant le lot* — §5 aura pu la déplacer, comme la capacité 2 l'avait fait pour la 3.

**§7 (agent d'organisation)** — la plus lourde et la plus risquée : premier écrivain sans témoin.
Ne l'ouvrir qu'une fois §6 en ligne, sinon elle a chaque semaine plus à recoller.
