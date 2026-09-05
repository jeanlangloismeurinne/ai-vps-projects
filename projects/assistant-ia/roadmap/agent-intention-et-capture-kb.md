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
- **D2 — La classification est du CODE, pas une consigne au modèle.** Pré-classifieur déterministe
  (DeepSeek `response_format: json_schema`, T ≤ 0.2, texte utilisateur en **donnée délimitée**,
  fallback `["conversation"]`) qui **oriente** la sélection d'outil. Le doc dit *quand* capter ; il
  ne décide pas *si* on écrit — c'est le code + le régime de confirmation.
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

*(Plus aucune décision ouverte : c'est ce qui autorise `status: figée`.)*

---

## Capacités (ordre imposé)

**Justification de l'ordre.** 1 d'abord parce que c'est la seule surface de comportement : tant que
le doc nie les outils, mesurer quoi que ce soit revient à mesurer le doc, pas le code (D4 en est la
démonstration, à huit jours de coût). 2 avant 3 parce que router une intention vers un outil qui
n'existe pas est un no-op. 4 en dernier parce qu'elle consomme les sorties de 2 et 3.

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

### 3. Intention multi-étiquette câblée au tour · contexte partagé : `handlers/agent_chat.py` (`handle_conversation_turn`) + `agent_tools/loop` + contrat du classifieur
> Branche le pré-classifieur en amont du tour et oriente la boucle. Couplé au chat handler et à
> fort jugement → **non délégable**.

- [ ] Pré-classifieur (D2) : `json_schema` fermé, sortie `{intents: [enum], confidence?}` —
  **liste**, pas valeur unique ; fallback `["conversation"]` sur JSON invalide ou API indisponible
  (aucune exception remontée : on ne perd jamais un tour).
- [ ] Router : `note_lecture`/`stockage_source` → `capture_note` ; `rappel` → `create_reminder` ;
  `question` → réponse + `web_search` ; `conversation` → tour normal. **Plusieurs intentions dans un
  tour déclenchent plusieurs outils.** La classification *oriente*, la policy *décide*.
- [ ] Fidélité de capture (C7) : le titre d'un rappel reste court, la charge utile va dans le corps
  de la carte ; une phrase qui n'appartient pas à la demande n'y est pas fusionnée.

- **Acceptation** : rejeu de **C6** → **deux** effets pour un seul message : une ligne dans
  `listes/*.md` **et** une carte `Rappels` datée du **2026-12-01**. Rejeu de **C7** → titre de carte
  < 60 caractères, items en corps, et « madame Loïc, hummus et concombre » **absent** du rappel.
  *Test négatif (mesuré le 09-05) : C6 a produit zéro effet, C7 un titre de 130 caractères
  incluant la phrase à exclure → rouge sur les deux.*

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

---

## Annexe — contrats détaillés

### A1 — Taxonomie d'intention (D1, multi-étiquette)

| Classe | Déclencheur verbatim observé | Traitement cible |
|---|---|---|
| `note_lecture` | « Note de lecture Safran : … » (C1) | `capture_note` mode `note` → vault |
| `stockage_source` | « Stocke ce lien dans une liste… » (C2, C6, C8) | `capture_note` mode `append` → `listes/{slug}.md` |
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

Arborescence cible du vault (les deux premiers répertoires n'existent pas encore) :

```
/storage/journal-vault/
  notes/{slug}.md      ← capture_note mode "note"    (C1)
  listes/{slug}.md     ← capture_note mode "append"  (C2, C6, C8)
  tasks/…              ← miroir kanban, déjà livré
```

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
