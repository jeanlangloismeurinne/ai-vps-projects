---
status: figée
role: >
  Décide comment l'agent conversationnel classe l'intention d'un tour, capte la donnée dans le
  vault et rend compte de ce qu'il a fait — pour que « enregistre », « crée une liste » et
  « rappelle-moi » produisent un effet, et non un déni.
---

# Chantier — L'agent classe l'intention et capte la donnée avant de répondre

> Origine : ticket bug `1787596637653` (2026-08-24), puis **deux revues** des conversations réelles
> du channel `#assistant` (table `agent_conversations`) : 08-24 → 08-27, puis 08-27 → 09-01.
> Dépend de : `agent-consignes-systeme.md` (v1 livrée) et `agent-outillage.md` (v1 livrée).

---

## Principe directeur

**Le doc système est la seule surface de comportement de l'agent.** `agent_chat.py:191` construit
le prompt à partir de `agent_system_doc WHERE active`, et de rien d'autre. Tout ce qui n'y est pas
écrit n'existe pas pour le modèle — quelles que soient les capacités réellement câblées dans le code.

Corollaire, et c'est le fait central de ce chantier : **corriger la configuration ne corrige pas le
comportement.** On refuse donc l'ordre inverse — construire des outils avant que le doc les nomme
produit du code jamais appelé.

Ce qu'on refuse aussi : que le doc système fasse *exister* un outil (invariant A3), et qu'une
capture s'écrive ailleurs que dans le vault de l'utilisateur.

---

## Constat — mesuré le 2026-09-05

### La ligne de base, requêtée avant d'écrire cette roadmap

| Mesure | Valeur | Conséquence |
|---|---|---|
| `agent_system_doc` | **1 seule version, active, 435 car., inchangée depuis le 2026-08-24 09:25** | La capacité 1 n'a jamais été exécutée. Le doc dit encore « Tu n'exécutes aucune action et ne disposes d'aucun outil. » |
| `agent_tool_calls` | **2 lignes, toutes deux `create_reminder`, verdict `ok`** | `web_search` n'a **jamais** été appelé. |
| `/storage/journal-vault` | **6 fichiers `.md`** : 3 structurels + 3 du miroir kanban | **Zéro** note captée depuis une conversation. Aucun répertoire de notes ni de listes. |
| `agent_instruction_queue` | vide | Aucune consigne `@admin` en attente : rien n'est bloqué par une revue. |
| `cards` / colonne `Rappels` | 2 cartes (IKEA 08-24, courses 08-28) | Le rappel du 1er décembre demandé le 08-28 **n'existe pas**. |

### Le fait qui invalide une décision de la version précédente de ce document

La version du 2026-08-27 écrivait : *« `SEARCH_PROVIDER=none` aujourd'hui → l'agent n'a réellement
pas d'outil web »*. **C'était déjà faux à l'écriture.** Le commit `90f0531` « activer la recherche
web Exa (`SEARCH_PROVIDER=exa`) » date du **2026-08-24 19:25** — trois jours plus tôt. La valeur
`exa` est présente aussi bien dans le `.env` courant que dans la copie de référence pré-migration.

Et pourtant, le **2026-09-01**, huit jours après l'activation, l'agent répondait encore : *« Je ne
peux pas non plus rechercher des startups spatiales. »*

> **C'est la preuve du principe directeur, et elle a coûté huit jours.** La config a été corrigée,
> le comportement n'a pas bougé d'un mot. Toute capacité de ce chantier qui ne passe pas par le doc
> système est, par défaut, suspecte de ne rien changer.

### Corpus de non-régression — les 9 tours verbatim

Ce tableau **est** le test d'acceptation du chantier : chaque ligne se rejoue, et l'attendu est
observable en base ou dans le vault. Les 5 premières lignes viennent de la revue du 08-27, les
4 dernières de la revue du 09-05.

| # | Message utilisateur (verbatim) | Réponse actuelle | Cible |
|---|---|---|---|
| C1 | « Note de lecture Safran : le EU Space Act… » (×5) | répond en conversation, ne capte **rien** | `capture_note` → fichier dans le vault, puis réaction |
| C2 | « Stocke ce lien dans une liste de sources utiles : payloadspace.com » | « Je ne peux pas stocker d'informations… je n'ai pas de mémoire persistante » | append dans `listes/sources-utiles.md` + accusé |
| C3 | « Rappelle-moi samedi 9h… IKEA » | « C'est noté, je vous rappellerai » | ✅ carte créée — reste la restitution vérifiable (C4) |
| C4 | « Revue de l'actualité politique publiée hier/aujourd'hui » | « Je ne peux pas consulter l'actualité en temps réel » | `web_search` (Exa, **déjà actif**) → réponse sourcée |
| C5 | « `<lien PDF>` » | « Je ne peux pas accéder à des liens externes ni ouvrir des PDF » | refus correct (pas de `fetch_url`, SSRF) — mais **orienter**, pas nier |
| **C6** | « **Enregistre ce climatiseur** dans une liste de potentiels options de climatisation à acheter cet hiver. **Crée un rappel** pour regarder cela le 1er décembre. `<lien Amazon>` » | nie la mémoire ; **demande** « souhaitez-vous que je programme ce rappel ? » → **jamais créé** | **deux** actions dans le tour : append liste + `create_reminder` au 2026-12-01, exécutées sans demander |
| **C7** | « Rappelle-moi demain matin à 9h d'acheter la liste de courses suivante : pain, chips de légumes et Pringles, tomates cerises, abricot, tranche de rôti. ⏎ **Je prendrai madame Loïc, hummus et concombre chez moi.** » | rappel créé, mais **toute la liste écrasée dans le titre** (130 car.) et la 2ᵉ phrase fusionnée en « Prendre aussi madame Loïc, hummus et concombre chez toi » | titre court + items dans le corps de la carte ; la 2ᵉ phrase n'entre **pas** dans le rappel (elle dit ce que l'utilisateur a déjà) |
| **C8** | « Crée une liste de startups du secteur du spatial dont les innovations sont à creuser. Voilà de premiers noms : Isembard, Tachyon Industrie » | nie la mémoire **et** nie la recherche web | création de `listes/startups-spatial.md` avec 2 items ; `web_search` disponible pour « creuser » |
| **C9** | (transverse à C3/C6/C7) accusé de réception | « C'est noté, rappel programmé pour demain à 9h » | accusé **vérifiable** : ce qui a été écrit, où, et un lien — plus boutons *Annuler* / *Modifier* |

### Ce que les 4 nouveaux tours ajoutent au diagnostic

Trois défauts que la version du 08-27 ne voyait pas, parce qu'ils n'étaient pas encore observables :

1. **Un tour porte plusieurs intentions.** C6 en porte deux (`stockage_source` + `rappel`). La
   taxonomie D1 n'en prévoyait qu'une par tour : elle aurait forcé l'agent à en perdre une.
2. **La liste nommée est une demande récurrente, pas un cas isolé.** C2 (08-24), C6 (08-28),
   C8 (09-01) — **trois demandes en huit jours**, chacune nommant explicitement « une liste ».
3. **Demander au lieu de faire perd l'action.** C6 est la mesure : l'agent a demandé confirmation,
   l'utilisateur n'a pas répondu, et le rappel du 1er décembre n'existe pas. Ce n'est pas une
   préférence d'ergonomie, c'est une perte de donnée constatée.

---

## Décisions

### Tranché

- **D0 — Cause racine = doc système périmé.** Confirmée deux fois, à onze jours d'intervalle. Le
  premier levier, le moins cher, est de réaligner `agent_system_doc` via le cycle `@admin`/`@update`
  (revue de diff humaine). Aucune ligne de code n'est requise pour supprimer les dénis.
- **D1 — Taxonomie d'intention à 5 classes, mais *multi-étiquette*** (amendé par C6) :
  `note_lecture` · `stockage_source` · `rappel` · `question` · `conversation`. Le pré-classifieur
  renvoie une **liste** d'intentions, pas une valeur unique. Vocabulaire fermé, aligné sur
  `journal_kb_classifier`.
- **D2 — ~~La classification est du CODE~~ → périmé par la mesure du 2026-09-05 (soir).** La
  décision présumait que l'agent ne classait pas l'intention. Le rejeu de C6 et C7 contre le
  modèle réel montre l'inverse : **4 appels d'outil sur 4, deux intentions correctement séparées
  dans chacun des deux tours**, sans une ligne de code de classification. La taxonomie D1 est déjà
  appliquée — en prose, par le paragraphe « Avant de répondre, classe l'intention du message » du
  doc v4. Construire le pré-classifieur aurait été le miroir exact de l'erreur D0 : du code qui ne
  change pas le comportement, parce que le comportement se joue ailleurs.
  *Ce qui échouait vraiment était ailleurs — voir D8 et D9.*
- **D8 — Un contrat d'outil qui exige une information que le modèle n'a pas est un piège**
  *(2026-09-05, mesuré)*. `date_mode=absolute` n'acceptait que `AAAA-MM-JJ` : « le 1er décembre »
  n'a pas d'année, le modèle en a donc inventé une — **2025, son année de coupure** — et le code
  a refusé la date passée. Le refus était juste, la question posée au modèle était impossible.
  `date` accepte désormais `MM-JJ` et le **code** choisit la prochaine occurrence : c'est la même
  frontière que partout ailleurs dans ce module. *Règle générale : avant de durcir une consigne,
  vérifier que le schéma permet de la respecter.*
- **D9 — Le modèle range mal ce qu'on ne lui a pas donné où ranger** *(2026-09-05, mesuré)*.
  `create_reminder` n'avait qu'un champ de texte : toute la liste de courses s'est déversée dans
  le titre (165 caractères), seconde phrase de l'utilisateur comprise. Un champ `details` alimente
  le corps de carte, et le titre est **borné par le code à 60 caractères** — erreur explicite, pas
  troncature : tronquer amputerait la charge utile en silence.
- **D10 — Le classifieur, s'il revient, choisira une *posture*, pas un outil** *(tranché avec
  l'utilisateur, 2026-09-05)*. Le besoin réel n'est pas de router vers un outil (ça marche) mais
  d'adapter la **manière de répondre** à la situation : explorer/brainstormer sur une question,
  exécuter avec le strict minimum de mots sur une action, identifier le thème et les documents
  existants sur une capture. Les postures vivent **dans le doc système**, en blocs nommés ; le code
  sélectionne le bloc en vigueur. L'invariant A3 est préservé : la surface de comportement reste
  versionnée, relue et éditable depuis Slack. → **capacité 5**.
- **D11 — La conversation est le fil Slack** *(tranché avec l'utilisateur, 2026-09-06)*.
  L'amendement du 09-06 exige une frontière : « même
  conversation » doit être une valeur, pas une intuition. Le fil (`thread_ts`) est la seule
  frontière que l'utilisateur **voit et choisit** — il a d'ailleurs répondu dans le fil, c'est
  l'origine de la demande. Un message parent ouvre donc une conversation neuve, ce qui donne
  gratuitement la seconde moitié de l'amendement : aucun état à effacer, `list_documents` redevient
  obligatoire parce qu'il n'y a rien d'autre. *Conséquence à assumer : l'historique se lit alors par
  fil, et non plus sur les 20 derniers tours du channel (B2). Un message parent ne verrait plus les
  tours d'une autre conversation — c'est le but, mais c'est un changement de ce dont l'agent se
  souvient, pas un détail d'implémentation.*
- **D12 — Deux types de liens, et c'est la distinction qui porte tout** *(tranché avec
  l'utilisateur, 2026-09-06)*. Une note neuve ne réécrit pas la note du même thème : elle s'y
  **relie**. Mais un lien indifférencié ne sert à rien — il faut séparer :
  - **`enfant`** — *appartenance* : cette entrée fait partie du thème X. C'est ce lien, et lui
    seul, qui permet d'assembler une **note globale** du thème.
  - **`voisin`** — *proximité sémantique ou conceptuelle*, sans appartenance. Deux notes qui
    s'éclairent, rangées sous des thèmes différents.

  Sans ce typage, assembler « tout ce qui parle des Mémoires de De Gaulle » ramènerait aussi tout
  ce qui parle vaguement d'histoire militaire, et la note globale deviendrait illisible — donc
  inutile, donc non relue.
- **D13 — La note globale est *dérivée*, jamais détentrice** *(2026-09-06)*. Elle assemble des
  entrées qui vivent ailleurs : elle ne contient **aucun contenu unique**, et peut donc être
  **régénérée** sans rien risquer. C'est ce qui rend un agent d'organisation acceptable dans un
  coffre dont tout le reste est append-only : il réécrit uniquement du dérivé. La règle inchangée
  et non négociable reste que `notes/` et `documents/` sont la source, et qu'on n'y **réécrit
  jamais** — le critère `git diff` = `+n / -0` de la capacité 2 vaut toujours, et devient `-0` tout
  court sur les fichiers sources touchés par une passe d'organisation.
  *Même architecture que partout ici : Markdown = pivot, le reste = index dérivé (`KNOWLEDGE_ARCHITECTURE.md`).*
- **D14 — Les liens s'écrivent dans un seul sens : du parent vers l'enfant** *(2026-09-06,
  vérifié)*. Écrire le lien retour dans chaque note source obligerait à **rééditer** des fichiers
  sources à chaque nouvelle entrée — exactement ce que D13 interdit. Inutile de toute façon : le
  viewer rend déjà les liens entrants (`projects/kb-viewer/quartz/quartz.layout.ts:46` →
  `Component.Backlinks()`, plus `Component.Graph()`), et Obsidian fait de même nativement.
  *La réciprocité est un problème d'affichage, pas de stockage.*
- **D3 — La capture réutilise l'existant.** Outil `capture_note` appelant `journal_kb_classifier`
  (métadonnées) puis le writer `journal_vault` (enveloppe federation-ready). Les deux modules
  existent — vérifié : `app/services/journal_kb_classifier.py`, `app/services/journal_vault.py`.
- **D4 — ~~À trancher~~ → tranché par les faits, et déjà appliqué.** Exa est actif depuis le
  2026-08-24 19:25. Il n'y a **rien à activer** : il reste à faire en sorte que le doc système le
  nomme, pour que le modèle le mobilise. *Cette décision ne coûte plus rien et n'a jamais rien coûté
  — elle a seulement attendu la capacité 1.*
- **D5 — Un document nommé = une note KB append-only dans le vault** *(tranché avec l'utilisateur,
  09-05 ; **généralisé le même jour**, cf. l'amendement de la capacité 2)*.
  Un fichier par document sous `documents/{slug}.md`, l'agent y **ajoute un bloc Markdown libre**
  sans réécrire le fichier. Relisible dans Obsidian et sur kb-viewer.
  ⚠️ *Corollaire découvert au rejeu : un adressage par nom ne vaut rien sans son outil de lecture.*
  Le modèle repart de zéro à chaque tour et n'a pas l'état du coffre ; sans `list_documents` il
  réinvente un nom voisin et fabrique un doublon silencieux. **Toute future primitive adressée par
  un libellé humain doit livrer son outil de lecture avec elle.**
  ⚠️ *Corrigé le 09-05 : « zéro brique neuve » était faux.* `journal_vault.write_entry` ne sait
  **pas** ajouter une ligne à un fichier existant — elle crée `{année}/{AAAA-MM-JJ}-{slug}.md` et
  suffixe en cas de collision. L'append demande une fonction neuve dans `journal_vault.py`, avec
  les mêmes barrières (`slugify` + `_resolve_within_vault` + écriture atomique + commit git).
  *Ceci renverse la reco de la version 08-27* (« on ne crée une liste dédiée que si un besoin de
  relecture agrégée apparaît ») : trois demandes en huit jours **sont** ce besoin.
- **D6 — Écrire d'abord, confirmer a posteriori** *(tranché avec l'utilisateur, 09-05)*. C'est le
  défaut dérivé du manifeste (`effect=write`, `reversible=true`, données propres) → `visibility=true`.
  Justifié par C6 : demander avant a fait perdre le rappel. L'annulation reste à un clic.
- **D7 — Le doc de la capacité 1 ne mentionne pas `capture_note`** (qui n'existe qu'en capacité 2).
  La capacité 1 ne référence que les outils **réellement exposés** (`create_reminder`, `web_search`).
  Un addendum suit en capacité 4. Un doc qui nomme un outil absent recrée le défaut en miroir.

*(Plus aucune décision ouverte. `status: figée` s'entend au sens « aucune décision ne bloque
l'exécution » — pas « aucune décision ne sera révisée » : D2 a été périmée par sa propre mesure de
ligne de base, ce qui est le fonctionnement attendu et non un accident.)*

---

## Capacités (ordre imposé)

**Justification de l'ordre.** 1 d'abord parce que c'est la seule surface de comportement : tant que
le doc nie les outils, mesurer quoi que ce soit revient à mesurer le doc, pas le code (D4 en est la
démonstration, à huit jours de coût). 2 avant 3 parce que router une intention vers un outil qui
n'existe pas est un no-op. 4 en dernier parce qu'elle consomme les sorties de 2 et 3.

*Ajout du 2026-09-06.* Les capacités 5, 6 et 7 traitent trois **portées de temps** distinctes du
même problème — retrouver où une information doit aller :

| Capacité | Portée | Ce qui retrouve la cible |
|---|---|---|
| **5** | le tour d'après, dans le fil | rien à chercher : la conversation **porte** la cible |
| **6** | une conversation neuve, utilisateur présent | un outil de lecture, à l'écriture |
| **7** | à froid, tout le corpus, chaque semaine | une passe d'organisation, sur du dérivé |

Elles se cumulent et ne se remplacent pas. **6 avant 7** : 6 relie pendant que l'utilisateur peut
corriger d'un mot, 7 rattrape ce qui a échappé — et 7 sans 6 aurait chaque semaine plus à recoller.
L'ordre est aussi celui du risque : 7 est le premier composant qui écrit dans le coffre sans témoin.

⚠️ **Chaque test d'acceptation se vérifie AVANT le correctif : il doit échouer.** La ligne de base
ci-dessus fournit les valeurs de départ — elles ont été requêtées, pas remémorées.

### 1. Doc système réaligné · contexte partagé : `agent_system_doc` + migration de contenu
> Le plus rentable, sans une ligne de code applicatif. **Non délégable** (jugement + sécurité de
> prose).
>
> ⚠️ **Amendement du 2026-09-05 (utilisateur).** La version figée disait « soumettre le diff via
> `@update` ». C'est le mauvais canal : `@admin`/`@update` appartient à l'**utilisateur**, pour
> coacher l'agent depuis Slack sans ouvrir autre chose. Le contenu livré passe par une **migration**,
> comme la v1 semée par `011_agent_consignes.sql`. L'invariant A3 (aucune auto-modification sans
> revue humaine) est préservé : le texte est relu dans le terminal, versionné en git, et le garde
> d'idempotence interdit à la migration d'écraser une décision prise ensuite dans Slack.

- [x] Rédiger la version 2 du doc : rôle réel (assistant personnel **avec mémoire et outils**),
  posture « classer l'intention avant de répondre », suppression des formules « je n'ai pas de
  mémoire » / « je ne peux rien stocker » / « je ne peux pas rechercher ».
- [x] Y nommer les outils **réellement exposés** — `create_reminder`, `web_search` — en disant
  *quand* les mobiliser, jamais *comment* (le doc ne crée pas d'outil).
- [x] Y écrire la règle de non-déni : face à une limite réelle (PDF, lien externe), **orienter**
  vers ce qui est possible ; ne jamais nier un apport qui existe.
- [x] Livrer par `migrations/016_agent_system_doc_v2.sql`, avec garde d'idempotence « aucune
  version ≥ 2 n'existe » — une migration ne rejoue jamais par-dessus une décision humaine
  postérieure (rollback, ou v3 approuvée dans Slack).

- **Acceptation** : `SELECT version, active FROM agent_system_doc` renvoie une **v2 active**, et le
  rejeu de **C4** produit au moins une ligne `web_search` dans `agent_tool_calls`.
  *Test négatif (mesuré le 09-05) : v1 seule, `web_search` à 0 appel → rouge.*

  ✅ **Vert le 2026-09-05.** v2 active (`created_by=migration_016`, `parent_version=1`, 2 175 car.)
  après rebuild vérifié (HTTP 200, un seul conteneur). Rejeu de C4 contre le modèle réel :
  2 itérations, 2 appels d'outil, **2 lignes `web_search` en `verdict=ok` avec `doc_version=2`**,
  8 sources taintées (bfmtv, lesechos, lcp, lefigaro, rfi, france24, rtl, franceinfo), et une
  réponse sourcée au lieu de « Je ne peux pas consulter l'actualité en temps réel ».
  La colonne `doc_version` sépare l'avant/après sans ambiguïté : tout ce qui porte `v1` est du
  `create_reminder`, les `web_search` portent tous `v2`. **Zéro ligne de code applicatif.**

### 2. `capture_note` et documents nommés · contexte partagé : `agent_tools/` (manifest·policy·registry) + `journal_kb_classifier` + `journal_vault`
> Construit le chemin d'écriture manquant. Fortement couplé (contrat de manifeste + classifieur +
> writer) → **inline**, ou **un** worker Sonnet sur la capacité entière, jamais par item.
>
> ⚠️ **Amendement du 2026-09-05 (utilisateur), en cours de livraison.** La version figée parlait de
> « listes nommées » et d'un mode `append` qui ajoute *une ligne*. L'objection : un Markdown porte
> déjà les puces, les tableaux, les cases à cocher et les titres — coder une primitive par forme de
> contenu, c'est coder une primitive par idée que l'utilisateur pourrait avoir. Ce qui distingue
> réellement les deux modes n'est pas la forme mais l'**adressage** : daté (`note`) contre nommé
> (`document`). `listes/` est donc devenu `documents/`, le contenu est du Markdown libre, et les
> deux invariants de sécurité sont inchangés : **chemin dérivé par le code**, **ajout qui ne
> réécrit jamais**.

- [x] `agent_tools/capture_note.py` : `MANIFEST` (`effect=write`, `taints_context=false`,
  `reversible=true`, `visibility=true` (D6), `egress=none`) + `_execute` appelant le classifieur
  puis le writer ; exporter `SPEC`, l'ajouter à `_ALL` dans `registry.py`.
- [x] Deux modes : `note` (fichier daté neuf) et `document` (ajoute un **bloc Markdown libre** à
  `documents/{slug}.md` **sans réécrire le fichier**) ; création implicite si le slug est inconnu.
- [x] `agent_tools/list_documents.py` (**hors périmètre initial, ajouté le 09-05**) : outil de
  **lecture** rendant les noms des documents existants, sans leur contenu. L'adressage par nom est
  inutilisable sans lui — mesuré : deux rejeux de C8 ont produit `startups-spatial.md` puis
  `startups-spatial-a-creuser.md`, deux fichiers pour une liste, sans qu'aucune erreur ne soit levée.
- [x] Écriture au format **enveloppe document commune** (federation-ready), métadonnées issues de
  `journal_kb_classifier`, vocabulaire construit au runtime depuis `categories.schema.yaml` — jamais
  recopié en dur.
- [x] Échec d'outil = erreur explicite en `role=tool`, jamais résultat vide (leçon SearXNG) ; le
  fallback « à classer » du classifieur ne perd jamais la note.
- [x] Étendre `checks/check_agent_tools.py` (§G) : doc empoisonné → `capture_note` n'écrit toujours
  que dans le vault, régime de confirmation **dérivé** du manifeste et non codé à la main, et
  chaque forme Markdown (puce, case à cocher, ligne de tableau, paragraphe, titre, séparateur)
  écrite **verbatim** avec le front-matter intact.
- [x] `migrations/017` (v3, la capture existe) puis `migrations/018` (v4, vocabulaire « document »
  + consigne d'ordre « lire les documents existants avant d'écrire »). La 017 a été avancée depuis
  la capacité 4 : laisser en ligne un doc qui *ordonne* de nier une capacité livrée reproduit D0.

- **Acceptation** : rejeu de **C1** → un `.md` neuf dans `/storage/journal-vault`. Rejeu de **C2**
  puis **C8** → un document touché sous `documents/` et un document neuf. Un **second** ajout
  laisse le contenu antérieur intact (`git diff` du vault = `+n` lignes, `-0`). **C8bis** (même
  demande, autre formulation) → *aucun* document supplémentaire.
  *Test négatif (mesuré le 09-05) : 6 `.md` au total, aucun répertoire de documents → rouge.*

  ✅ **Vert le 2026-09-05**, doc v4 active, 16/16 assertions du rejeu contre le modèle réel.
  Les 5 cas ont appelé `capture_note`, et 4 sur 5 ont appelé `list_documents` **avant** d'écrire.
  `git diff` du vault : `document sources utiles complété (+1)` → `1 file changed, 1 insertion(+)`,
  soit exactement le critère `+n / -0`. C8bis a bien complété `startups-spatial-r29251.md` au lieu
  d'en forger un second — le doublon mesuré le matin ne se reproduit plus.
  Checks hors-ligne : 59 assertions vertes, **éprouvées par deux passes négatives** — repli du bloc
  sur une ligne → 4 asserts rouges (dont « paragraphe multi-ligne : écrit verbatim ») ; réécriture
  du fichier avec `updated_at` + fuite du contenu par `list_documents` → 24 asserts rouges (dont
  « le front-matter du fichier est intact » et « list_documents ne rend pas le contenu »).

### 3. ~~Intention multi-étiquette câblée au tour~~ → Le contrat d'outil rend l'action possible · contexte partagé : `agent_tools/create_reminder.py`
> ⚠️ **Capacité réécrite le 2026-09-05 (soir) par sa propre mesure de ligne de base.** Le titre
> d'origine désignait un pré-classifieur ; la mesure a montré que la classification fonctionnait
> déjà et que l'échec était dans le contrat de `create_reminder` (D2, D8, D9).
>
> **La ligne de base a été requêtée avant le lot, et c'est ce qui a sauvé la capacité.** Les valeurs
> rouges inscrites plus haut dataient d'*avant* la capacité 2 : les rejouer telles quelles aurait
> fait construire un routeur pour un routage qui marche.

- [x] ~~Pré-classifieur~~ — retiré du périmètre (D2). Le doc v4 classe déjà, mesuré 4/4.
- [x] ~~Router~~ — retiré du périmètre. Mesuré : C6 et C7 enchaînent **3 outils chacun**
  (`list_documents` → `capture_note` → `create_reminder`) dans un seul tour.
- [x] **L'année manquante** (D8) : `date` accepte `MM-JJ`, le code résout la prochaine occurrence
  (y compris le 29 février, par balayage d'années plutôt que `+1`). L'année explicite de
  l'utilisateur reste souveraine ; une année passée reste refusée.
- [x] **Fidélité de capture** (D9, C7) : champ `details` → `description` de la carte, titre borné
  à 60 par le code avec une erreur qui **nomme le champ où mettre le reste**.
- [x] Ce dont l'utilisateur dit s'occuper lui-même ne figure **nulle part** dans le rappel — ni en
  liste, ni en aparté, ni entre parenthèses. *La mention « ni entre parenthèses » n'est pas du
  zèle : sans elle, le modèle rangeait la phrase exclue dans un aparté étiqueté et l'assertion
  restait rouge.*
- [x] `checks/replay_intent_corpus.py` (rejeu réel) + `check_agent_tools.py` §D et §H (hors-ligne).

- **Acceptation** : rejeu de **C6** → **deux** effets pour un seul message : un document touché
  sous `documents/` **et** une carte `Rappels` datée du **2026-12-01**. Rejeu de **C7** → titre de
  carte < 60 caractères, items en corps, et « madame Loïc, hummus et concombre » **absent** du
  rappel.
  *Test négatif (mesuré le 09-05 au soir, contre la capacité 2 déjà en ligne — pas remémoré) :
  5 assertions rouges sur 9. C6 : `create_reminder` refusé sur `{"date": "2025-12-01"}`, aucune
  carte créée. C7 : titre de 165 caractères, `description` vide, les trois termes à exclure
  fusionnés dedans.*

  ✅ **Vert le 2026-09-05** (commits `3004ef1` puis `802b180`, HTTP 200, un seul conteneur).
  **9/9 au rejeu réel, deux fois de suite contre l'image construite.** C6 : le modèle écrit
  `12-01`, le code résout `2026-12-01`, trois outils enchaînés dans le tour. C7 : titre
  `'Acheter les courses'` (19 car.), corps à 83 car. contenant les cinq articles, zéro terme exclu.
  Hors-ligne : **145 assertions vertes** (23 neuves), **éprouvées par deux passes négatives** —
  retrait du support `MM-JJ` → 5 asserts rouges ; retour au champ unique tronqué à 200 → 5 asserts
  rouges, dont « la borne du titre tient le critère d'acceptation (≤ 60) » et « le corps part en
  base dans `description` ».

### 4. Restitution vérifiable et fin des dénis résiduels · contexte partagé : `handlers/agent_tool_actions.py` + rendu Slack + addendum au doc système
> Consomme les sorties de 2 et 3. Les boutons *Annuler* / *Modifier* existent déjà — il manque le
> contenu de l'accusé.

- [ ] L'accusé de réception nomme **ce qui a été écrit et où**, avec un lien (carte kanban, ou page
  kb-viewer de la note) — plus « C'est noté » sans référent (C9).
- [ ] Reformuler les refus légitimes en orientations (C5 : PDF et lien externe restent hors
  périmètre — le dire en proposant l'extrait ou la recherche, sans nier tout apport).
- [ ] Addendum au doc système : *quand* proposer une capture, *comment* rendre compte (suite de la
  capacité 1, même cycle de revue de diff).

- **Acceptation** : rejeu de **C3** et **C6** → la réponse Slack contient une URL cliquable vers
  l'objet créé, et le rejeu de **C5** ne contient plus la formule « je ne peux pas accéder ».
  *Test négatif (mesuré le 09-05) : « C'est noté, rappel programmé pour demain à 9h » — aucun lien,
  aucun référent → rouge.*

### 5. Postures situées · contexte partagé : `agent_system_doc` (v5 en blocs) + `handlers/agent_chat.py` + nouveau `services/agent_posture.py`
> **Ajoutée le 2026-09-05 (soir), à la demande de l'utilisateur.** Ce qui remplace D2 : le
> classifieur ne choisit pas un outil — ça marche déjà — il choisit **comment répondre**.
>
> Le doc v4 est un compromis unique pour toutes les situations : il ordonne à la fois « agis, ne
> demande pas la permission » et « rends compte de façon vérifiable », ce qui sert mal une question
> ouverte comme une exécution. Une posture n'est pas un ton, c'est un **budget de mots et un ordre
> d'opérations différents**.

| Mode | Ce que l'utilisateur attend |
|---|---|
| `exploration` | une question ouverte : développer, proposer des pistes, chercher sur le web, ne rien écrire |
| `action` | exécuter, puis le strict minimum de mots ; ne demander une précision que si elle bloque réellement |
| `capture` | identifier le thème, regarder les documents existants, ranger l'information au bon endroit sans reformuler |

> ⚠️ **Amendement du 2026-09-06 (utilisateur) — la posture tient sur la conversation, pas sur le
> message.** Quand l'utilisateur répond à l'agent dans une **même conversation**, l'agent garde la
> posture en cours : une chaîne de notes de lecture reste en `capture`, et les réponses suivantes
> vont dans **la note du même thème**, pas dans un fichier neuf ni dans une autre posture.
>
> **Et la moitié qui compte autant : cette continuité s'arrête à la conversation.** Une **nouvelle**
> conversation sur le même thème ne rejoue aucun état mémorisé — elle repasse par `list_documents`
> pour retrouver le bon document. Un agent qui « se souvient » du fichier d'hier reconstruit le
> doublon silencieux de la capacité 2 par l'autre bout : au lieu d'inventer un nom voisin, il écrit
> avec confiance dans un nom périmé. **La continuité est une portée, pas une mémoire.**

#### Ligne de base de l'amendement — mesurée le 2026-09-06, avant toute écriture

Trois faits, requêtés dans les logs, la base et le vault. Ils ne se rejouent pas : ils sont datés.

| # | Fait mesuré | Conséquence |
|---|---|---|
| **B1** | Le **2026-09-06 à 07:05**, l'utilisateur répond dans le fil de la note de 06:51 → `slack_app.py:52` route tout message porteur d'un `thread_ts` vers `_handle_thread_message`, qui ne connaît que les fils du journal → `WARNING message non traité`. **Aucune réponse, aucune ligne en base, rien dans le vault.** | La continuité n'est pas *mal* faite : le tour de suite **n'atteint jamais l'agent**. Rien de §5 n'est testable avant ça. |
| **B2** | `agent_conversations.load_recent_turns` filtre sur `channel_id` **seul** et rend les 20 derniers tours du channel, `thread_ts` ignoré à la lecture (il n'est écrit que pour l'audit, et vaut toujours `slack_ts`). | **La « conversation » n'existe pas dans le code.** L'historique est une fenêtre glissante qui colle un tour du 09-06 à côté d'un tour du 08-24 : impossible d'y accrocher une posture ou un document courant. |
| **B3** | Le vault porte `2026-09-06-memoires-de-charles-de-gaulle.md` (réel) et **trois** fichiers `eu-space-act-*` datés du 09-05 pour un même thème. Le tour de 06:51 a appelé `capture_note` **seul** — pas de `list_documents` avant. | Une note de lecture part en mode `note` (fichier daté neuf) à chaque tour. Le thème se fragmente **par construction** : c'est le symptôme que l'amendement nomme. |

- [x] **B1 d'abord — router la réponse en fil vers l'agent.** `_handle_thread_message` retombe sur
  `handle_conversation_turn` quand le fil n'est ni une session journal v2 ni un fil de l'ancien
  journal, et que le channel est `ASSISTANT_CHANNEL_ID`. L'ordre des branches reste normatif : le
  journal garde la priorité. *C'est un correctif de routage, pas une posture — il se livre et se
  vérifie séparément, sinon son échec sera lu comme un échec de la v5.*
  ✅ **Livré le 2026-09-06** (commit `1970700`, HTTP 200, un seul conteneur). La branche reprend les
  deux gardes des branches parentes — dédup d'événement (elle écrit dans le vault) et auteur humain
  — et `agent_chat` rattache désormais réponse, historique et audit à la **racine** du fil
  (`thread_ts` était écrit mais jamais lu). Checks §I et §J : **12 assertions neuves, 157 au total**,
  écrites au point de lecture réel (`_handle_thread_message`, `handle_conversation_turn`) et
  **éprouvées par deux passes négatives** — branche retirée → *« une réponse en fil d'#assistant
  atteint l'agent — appels=0 »* ; racine remise à `slack_ts` → *« la réponse est postée sous la
  racine du fil, pas sous elle-même — ['222.2'] »*.
  ⚠️ *Ce que B1 ne fait pas* : le tour de suite part avec l'historique **du channel** (B2 intact).
  Ça répond, ça ne tient pas encore la posture ni le document courant.
- [ ] **B2 — donner une portée à la conversation.** `load_recent_turns` prend le fil comme borne
  (cf. **D11**), et c'est cette même borne qui porte l'état de posture et le document courant.
- [ ] La posture **et** le document courant sont portés par la conversation, jamais par le
  processus ni par une mémoire globale : deux conversations simultanées ne se contaminent pas, et
  un redémarrage ne perd rien d'autre que ce que la base porte déjà.
- [ ] **Le tour de suite n'est pas reclassé à zéro** : la posture de la conversation est l'état par
  défaut du tour suivant. Elle **change** quand le tour porte une demande d'une autre nature
  (« et rappelle-moi d'en reparler lundi » dans une chaîne `capture` ⇒ `capture` + `action`), jamais
  parce que le message est court ou elliptique. *Un « oui, et aussi ceci » ne retombe pas en
  `conversation`.*
- [ ] **Une nouvelle conversation ne réutilise aucun document mémorisé** : `list_documents` est
  rappelé. Le doc v5 dit *pourquoi* (le nom exact est ce qui retrouve le fichier), pas seulement
  *quoi faire*.

- [ ] `agent_system_doc` **v5 découpé en blocs nommés** (`socle`, `exploration`, `action`,
  `capture`) — un seul document versionné, relu, éditable depuis Slack. Le socle porte ce qui vaut
  toujours (identité, non-déni, mémoire, outils) ; chaque bloc ne porte que ce qui lui est propre.
- [ ] `services/agent_posture.py` : `json_schema` fermé, sortie `{modes: [enum]}` **multi-étiquette**
  (C6 = `capture` + `action`), T ≤ 0.2, texte utilisateur en **donnée délimitée**, fallback
  `["exploration"]` sur JSON invalide ou API indisponible — on ne perd jamais un tour.
- [ ] `agent_chat` compose le prompt = socle + blocs des modes retenus. **Tous les fragments
  viennent du doc actif** : le code sélectionne, il ne rédige pas (invariant A3 préservé).
- [ ] La posture retenue est journalisée (nouvelle colonne sur `agent_conversations`) : sans ça, on
  ne saura pas *a posteriori* si une réponse décevante vient du bloc ou du choix du bloc. La
  journalisation dit aussi **si la posture a été classée ou héritée** du tour précédent — sinon on
  ne pourra pas distinguer « le classifieur a bien retrouvé `capture` » de « la continuité a
  fonctionné », et les deux se réparent à des endroits différents.

- **Acceptation** : **cinq** tours rejoués contre le modèle réel, avec la posture mesurée en base.
  Une question ouverte (« que penses-tu de X ? ») → mode `exploration`, réponse développée, **zéro
  écriture**. Une demande d'action (« rappelle-moi… ») → mode `action`, outil appelé, **réponse
  d'acquittement sous 300 caractères**. Une capture (« note que… ») → mode `capture`,
  `list_documents` appelé **avant** `capture_note`.
  Puis les deux tours de l'amendement du 09-06, qui ne se mesurent qu'**enchaînés** :
  - **P4 — la suite dans le même fil.** Une réponse en fil sous la capture précédente
    (« et il ajoute que … ») → le tour **atteint l'agent** (B1), la posture reste `capture`, et
    l'écriture atterrit **dans le même fichier** que P3. Critère : `git diff` du vault = `+n / -0`
    sur ce fichier, et **aucun `.md` supplémentaire** créé par le tour.
  - **P5 — le même document, une conversation neuve.** Un message parent (hors fil) reprenant un
    **document nommé** (« mes sources utiles ») → `list_documents` **est appelé** avant l'écriture,
    et l'écriture retombe sur le même fichier **par son nom**, pas par un état gardé. Critère : la
    ligne `list_documents` existe dans `agent_tool_calls` pour ce tour, et le compte de `.md` du
    vault est inchangé.
    *P5 ne couvre que les documents nommés.* Le même scénario sur une **note de lecture** est hors
    de portée du modèle tant que la capacité 6 n'est pas livrée : `list_documents` ne voit pas
    `notes/`. Ne pas l'écrire comme une exigence de §5 — ce serait un test qu'aucun comportement ne
    peut satisfaire.

  ⚠️ *Le test négatif se mesure d'abord : longueur de réponse et ordre d'appel actuels, sous doc
  v4, avant d'écrire la v5. Sans quoi on ne saura pas si la v5 a changé quoi que ce soit.*
  ⚠️ **P4 et P5 se rougissent l'un l'autre — c'est le seul couple qui prouve quelque chose.** Une
  implémentation qui mémorise le document globalement passe P4 et **doit** rater P5 (elle écrira
  sans appeler `list_documents`). Une implémentation qui ne porte aucun état passe P5 et rate P4
  (fichier neuf, ou tour perdu). Les mesurer séparément laisserait passer les deux erreurs.
  *Test négatif déjà acquis pour P4, mesuré le 2026-09-06 : le tour de 07:05 n'a produit ni réponse,
  ni ligne en base, ni octet dans le vault (B1).*

### 6. Retrouver le thème à l'écriture · contexte partagé : nouvel outil de lecture sur `journal_kb_entries` + `capture_note` + doc système
> **Ajoutée le 2026-09-06 (utilisateur).** La capacité 5 fait tenir la conversation ; celle-ci
> traite le tour d'après : **une conversation neuve sur un thème déjà noté**. C'est l'option 1 des
> deux que l'utilisateur a posées — les deux se cumulent, celle-ci agit *au moment de l'écriture*,
> pendant que l'utilisateur est là pour corriger.

**Le fait qui commande cette capacité — mesuré le 2026-09-06.** `list_documents` fait
`documents_dir.glob("*.md")` (`journal_vault.py:479-484`) : il est **structurellement aveugle** à
`notes/`. Une note de lecture n'est donc pas retrouvable, quel que soit le comportement du modèle
— ce n'est pas une consigne à durcir, c'est une information hors de portée. *Même nature d'erreur
que D0 et D8 : le modèle ne peut pas respecter une consigne que son outillage rend impossible.*

Ce qui manque n'est pas à construire : `journal_kb_entries` (migration `009`) porte déjà
`title`, `tags[]`, `nature[]`, `uri`, `created_at`, avec index GIN sur les tags. Il lui manque un
outil de lecture. **Preuve que l'index suffit et que le défaut est réel**, les 4 entrées présentes :

| titre | nature | tags | fichier |
|---|---|---|---|
| Mémoires de Charles de Gaulle | `note_de_lecture` | histoire, militaire, Charles de Gaulle | `notes/2026/2026-09-06-…` |
| EU Space Act et équipementiers | `note_de_lecture` | Safran, EU Space Act, constellations, Airbus | `…-equipementiers.md` |
| EU Space Act et autorisation unique | `note_de_lecture` | espace, réglementation, EU Space Act, … | `…-autorisation-unique.md` |
| **EU Space Act et équipementiers** | `note_de_lecture` | espace, réglementation, EU Space Act, … | `…-equipementiers-2.md` |

**Deux entrées de titre strictement identique, deux fichiers.** C'est le doublon de la capacité 2,
reproduit à l'identique du côté `notes/` — et il a la même cause : un adressage sans son outil de
lecture (D5).

- [ ] Outil de **lecture** `search_notes` sur `journal_kb_entries` : rend `titre`, `tags`,
  `nature`, `uri`, `date` — **jamais le corps**, même règle et même raison que `list_documents`
  (la question est « ce thème existe-t-il déjà ? », pas « que disait-il ? »). `effect=READ`,
  `taints_context=false` (contenu de l'utilisateur, cf. la docstring de `list_documents`).
- [ ] Le doc système dit **quand** l'appeler — avant d'écrire une note, quand l'utilisateur reprend
  un sujet — jamais *comment*. L'outil vient de `registry.py`, comme les autres (invariant A3).
- [ ] La capture reste une **note neuve** (D12, choix utilisateur) : rien n'est réécrit. Elle porte
  un lien `enfant` vers le thème. La note pré-existante n'est **pas touchée**.
- [ ] Amender la docstring de `capture_note` : elle justifie aujourd'hui le mode `note` par
  « cinq notes sur le même sujet coexistent lisiblement ». C'était vrai comme *contrat d'écriture*,
  c'est faux comme *contrat de relecture* — et un correctif qui n'enlève pas la justification
  périmée laisse la prochaine session la rétablir de bonne foi.

- **Acceptation** : rejeu de **C10** — une conversation neuve reprenant les *Mémoires de Charles de
  Gaulle*. Attendu : une ligne `search_notes` dans `agent_tool_calls` **avant** la ligne
  `capture_note` ; un `.md` neuf portant un lien `enfant` vers le thème ; et
  `2026-09-06-memoires-de-charles-de-gaulle.md` **inchangé au bit près** (`git diff` = vide sur ce
  fichier, pas `+n / -0` : zéro).
  ⚠️ *Le test négatif se mesure d'abord, et il est déjà à moitié acquis* : `search_notes` n'existe
  pas → 0 appel, et la paire `EU Space Act et équipementiers` / `…-2` est la trace de ce que
  produit son absence. **À requêter avant le lot**, pas à recopier d'ici : la capacité 5 aura pu
  déplacer la ligne de base, comme elle l'a fait pour la capacité 3.

### 7. Agent d'organisation de la base de connaissance · contexte partagé : `journal_kb_entries` + table de liens + notes globales dérivées + planificateur
> **Ajoutée le 2026-09-06 (utilisateur).** L'option 2 : une passe **hebdomadaire** qui regroupe les
> entrées voisines, pose les tags et tisse les liens — dans l'esprit du *LLM wiki* de Karpathy qui
> inspire déjà `KNOWLEDGE_ARCHITECTURE.md`. Elle ne remplace pas la capacité 6 : celle-ci relie au
> moment où l'utilisateur est présent, celle-là rattrape le reste, à froid, sur tout le corpus.

⚠️ **C'est le premier composant autorisé à écrire dans le vault sans que l'utilisateur soit là.**
Tout le reste du chantier tient sur « on ajoute, on ne réécrit jamais ». D13 et D14 sont ce qui
rend cette capacité acceptable, et elles ne se négocient pas en cours de route :
**la passe n'écrit que du dérivé** (notes globales, table de liens) et **ne touche aucun octet** de
`notes/` ni de `documents/`.

- [ ] Table `journal_kb_links` : `(from_doc_id, to_doc_id, type, created_by, created_at)`, `type ∈
  {enfant, voisin}` (D12), contrainte d'unicité sur le triplet. Le graphe vit en base — dérivé,
  reconstructible, jamais l'unique domicile d'un fait.
- [ ] **Notes globales dérivées**, une par thème : elles assemblent les entrées liées en `enfant`,
  portent en tête un avertissement « note assemblée, ne pas éditer à la main », et un lien vers
  chaque enfant (D14 — le retour est rendu par `Backlinks()`, rien à écrire). Régénérées à chaque
  passe.
- [ ] La passe **ne propose pas, elle applique** — mais uniquement sur du dérivé, et le vault est
  versionné en git : chaque passe est un commit, donc annulable d'un `git revert`. *C'est cette
  réversibilité qui remplace la confirmation, exactement comme D6 pour `capture_note`.*
- [ ] Cadence hebdomadaire. Le planificateur existe déjà (`check_objectif_reminders` tourne chaque
  minute) — **ne pas introduire un second mécanisme de planification** pour une passe par semaine.
- [ ] Le résultat est **rendu compte** : un message Slack listant ce que la passe a regroupé, sans
  quoi elle travaille dans le dos de l'utilisateur — ce qui est précisément le reproche fait aux
  systèmes de rangement automatique.

- **Acceptation**, sur le corpus réel (les 4 entrées ci-dessus, dont la paire *EU Space Act et
  équipementiers*) :
  1. Après une passe, les entrées `EU Space Act` sont **enfants d'un même thème**, et il existe une
     note globale qui les assemble toutes.
  2. `git diff` de la passe : **aucune ligne retirée ni modifiée** sous `notes/` et `documents/`.
     Une seule ligne `-` sur un fichier source fait échouer la capacité.
  3. **Une seconde passe immédiate produit un diff vide.** C'est le critère qui distingue un
     assembleur d'un générateur qui bavarde ; sans lui, chaque semaine réécrit tout et l'historique
     git du vault devient illisible.
  4. Une entrée que rien n'apparente reste **sans parent** — elle n'est pas rattachée de force au
     thème le moins éloigné. *Le test négatif s'écrit là : injecter une note hors-sujet et vérifier
     qu'elle reste orpheline. Un agent de regroupement qui ne laisse jamais d'orphelin ne mesure
     rien, il range tout.*

---

## Annexe — contrats détaillés

### A1 — Taxonomie d'intention (D1, multi-étiquette)

| Classe | Déclencheur verbatim observé | Traitement cible |
|---|---|---|
| `note_lecture` | « Note de lecture Safran : … » (C1) | `capture_note` mode `note` → vault |
| `stockage_source` | « Stocke ce lien dans une liste… » (C2, C6, C8) | `capture_note` mode `document` → `documents/{slug}.md` |
| `rappel` | « Rappelle-moi samedi 9h… » (C3, C6, C7) | `create_reminder` → carte colonne `Rappels` |
| `question` | « Revue de l'actualité… » (C4) | réponse + `web_search` (Exa, actif) |
| `conversation` | « Bonjour » | tour normal |

Sortie : `{ intents: [enum], confidence?: number }` — `intents` **contraint par enum**, non vide,
fallback `["conversation"]`. C6 est le cas qui impose la liste : `["stockage_source", "rappel"]`.

### A2 — `capture_note` : contrat de manifeste (D3/D5/D6)

```
effect         = write     # écrit dans le vault de l'utilisateur
taints_context = false     # n'injecte pas de contenu tiers non relu
reversible     = true      # fichier Markdown supprimable / éditable
visibility     = true      # D6 : exécution puis confirmation a posteriori
egress         = none      # pas de sortie réseau
```

Le régime de confirmation **découle** de ce manifeste (`agent_tools/policy.py`, fonction pure) — il
n'est jamais écrit à la main.

Arborescence du vault — **état réel au 2026-09-06**, corrigée : la version figée décrivait
`listes/` et un mode `append`, tous deux abandonnés par l'amendement de la capacité 2 (l'adressage,
pas la forme). *Une annexe périmée est le défaut D0 en miniature — elle finit par être lue comme
une spécification.*

```
/storage/journal-vault/
  notes/{année}/{AAAA-MM-JJ}-{slug}.md   ← capture_note mode "note"      (C1)  — adressage daté
  documents/{slug}.md                    ← capture_note mode "document"  (C2, C6, C8) — par nom
  tasks/…                                ← miroir kanban, déjà livré
```

À venir, capacité 7 : une note globale **dérivée** par thème (D13), assemblant les entrées liées en
`enfant` — hors des deux répertoires sources, qui restent en écriture par ajout seul.

### A3 — Invariants de sécurité (non négociables)

- Prompt système = `agent_system_doc WHERE active` **uniquement** ; message et historique en rôles
  `user`/`assistant` (données), jamais `system` — vérifié le 09-05 à `agent_chat.py:191`.
- Liste d'outils = `agent_tools/registry.py` **exclusivement** ; le doc système ne fait **jamais**
  exister un outil (`checks/check_agent_tools.py` §A).
- Le pré-classifieur voit le texte utilisateur en **donnée délimitée**, jamais en instruction.
- Aucune auto-modification du doc système sans revue de diff humaine.

### A4 — Preuves horodatées

**Session du 2026-08-27** : `agent_system_doc` = 1 version active, 435 car. · `agent_conversations`
= 18 tours, aucun routage vers le vault · `agent_instruction_queue` vide · `registry._ALL` =
(`create_reminder`, `web_search`).

**Session du 2026-09-05** : `agent_system_doc` = **toujours** 1 version active, 435 car., inchangée
depuis le 08-24 09:25 · `agent_conversations` = 24 tours (08-24 → 09-01) · `agent_tool_calls` = 2
lignes, deux `create_reminder`, **zéro `web_search`** · vault = 6 `.md`, zéro note captée · colonne
`Rappels` = 2 cartes, **aucune au 1er décembre** · `SEARCH_PROVIDER=exa` dans le `.env` et dans la
copie pré-migration, activé par le commit `90f0531` du **2026-08-24 19:25**.
