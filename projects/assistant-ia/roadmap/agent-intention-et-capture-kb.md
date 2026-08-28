---
status: draft
milestone: agent-intention-capture-kb
---

# Chantier — L'agent classe l'intention et capte la donnée avant de répondre

> Origine : ticket bug `1787596637653` (2026-08-24) + revue des conversations réelles du
> channel `#assistant` (`agent_conversations`, 08-24 → 08-27).
> Statut : **direction à valider** — la vanne direction s'ouvre (comportement structurant +
> écriture dans le vault + interaction avec le doc système versionné, §5 des chantiers voisins).
> Dépend de : `agent-consignes-systeme.md` (v1 livrée) et `agent-outillage.md` (v1 livrée).

---

## Constat — ce que fait l'agent aujourd'hui vs la cible

Extraits **verbatim** des tours réels (channel `#assistant`) :

| Message utilisateur | Réponse actuelle de l'agent | Cible (roadmaps) |
|---|---|---|
| « Note de lecture Safran : le EU Space Act… » (×5) | répond en conversation, ne capte **rien** | classer *note de lecture* → **écrire dans le vault Obsidian** (KB) puis réagir |
| « Stocke ce lien dans une liste de sources utiles : payloadspace.com » | « Je ne peux pas stocker d'informations… je n'ai pas de mémoire persistante » | classer *stockage* → capter la source dans la KB, confirmer |
| « Rappelle-moi samedi 9h… IKEA » | « C'est noté, je vous rappellerai » | OK sur le principe — mais l'outil `create_reminder` doit réellement être invoqué |
| « Revue de l'actualité politique publiée hier/aujourd'hui » | « Je ne peux pas consulter l'actualité en temps réel » | selon décision D4 : chercher (web_search) ou orienter proprement, sans nier tout apport |
| « <lien PDF> » | « Je ne peux pas accéder à des liens externes ni ouvrir des PDF » | correct (pas de `fetch_url`, SSRF §4 outillage) — reste à formuler comme une orientation |

**Cause racine identifiée** (vérifiée en base) : le document système **actif est la version 1**
(`agent_system_doc`, 435 caractères, activé le 2026-08-24 **avant** la livraison de l'outillage).
Il dit littéralement :

> « Tu n'exécutes aucune action et ne disposes d'aucun outil. »

Le comportement de l'agent tient **entièrement** dans ce doc (`agent_chat.py:191`, prompt système
= `agent_system_doc WHERE active`, rien d'autre concaténé). Le doc raconte donc au modèle qu'il est
un chatbot sans mémoire ni outil — et le modèle joue ce rôle : il **nie** avoir une mémoire, il ne
**classe rien**, il ne **capte rien**. Les outils (`create_reminder`, `web_search`) existent dans
le registre (`agent_tools/registry.py`) mais le doc n'en parle pas → le modèle ne les mobilise pas.

Le ticket bug demande deux choses distinctes :
1. **Classer l'intention en amont** — « sa première tâche est de classifier l'intention de
   l'utilisateur et de savoir comment traiter la donnée avant de répondre ».
2. **Capter en base compatible Obsidian** — « est-ce que l'agent a stocké les entrées en base
   compatible Obsidian ? » → **non** : les tours ne vivent que dans `agent_conversations`, jamais
   dans `/storage/journal-vault`.

---

## Décisions

### Tranché (proposition — à amender par l'utilisateur)

- **D0 — Cause racine = doc système périmé.** Le premier levier, le moins cher, est de réaligner
  `agent_system_doc` via le cycle `@admin`/`@update` (revue de diff humaine, §4 consignes). Aucune
  ligne de code n'est requise pour supprimer les dénis « je n'ai ni mémoire ni outil ».
- **D1 — Taxonomie d'intention (5 classes)** dérivée des tours réels :
  `note_lecture` · `stockage_source` · `rappel` · `question` · `conversation`. Vocabulaire **fermé**,
  extensible plus tard, aligné sur la logique `journal_kb_classifier` (enum `json_schema`).
- **D2 — La classification est du CODE, pas une consigne au modèle.** Conforme au §5 (donnée ≠
  instruction) : un pré-classifieur déterministe (DeepSeek-V4-Flash, `response_format: json_schema`,
  fallback « à classer ») annote le tour et **oriente** la sélection d'outil. Le doc système peut
  dire *quand* capter ; il ne décide pas *si* on écrit — c'est le code + le régime de confirmation.
- **D3 — La capture réutilise l'existant, pas une nouvelle brique.** Nouvel outil `capture_note`
  dans `agent_tools/` qui appelle `journal_kb_classifier` (métadonnées) + le writer du vault
  (`journal_vault`, enveloppe federation-ready). `effect=write`, `reversible=true`, périmètre =
  données de l'utilisateur → le régime de confirmation en **découle** du manifeste (jamais codé à la
  main), cf. `agent-outillage` §3.

### À trancher (surface de validation)

- **D4 — Actualité / web.** `SEARCH_PROVIDER=none` aujourd'hui → l'agent n'a réellement pas d'outil
  web, mais il le **surformule** en niant tout apport. Deux options :
  (a) **activer Exa** (`SEARCH_PROVIDER=exa`, clé déjà disponible pour ce projet) → l'agent cherche ;
  (b) garder `none` et **corriger seulement le libellé** (orienter, ne pas nier). — *Reco : (a),
  l'outil est déjà câblé et taintant/confirmé par construction.*
- **D5 — « Liste de sources » = quoi, concrètement ?** Une note KB taguée `source` dans le vault
  (réutilise `capture_note`, D3), ou un artefact dédié (page/liste) ? — *Reco : note KB taguée, zéro
  brique neuve ; on ne crée une liste dédiée que si un besoin de relecture agrégée apparaît.*
- **D6 — Capture : automatique ou confirmée ?** Une `note_lecture` détectée → on écrit directement puis
  confirmation *a posteriori* (Annuler/Modifier), ou on demande **avant** ? Le manifeste tranche par
  défaut (écriture réversible sur données propres → exécution + confirmation a posteriori) — valider
  que ce défaut convient, ou forcer `visibility=false` pour confirmer avant.
- **D7 — Périmètre du réalignement du doc (Sprint 1).** Le doc doit-il déjà mentionner `capture_note`
  (qui n'existe qu'après Sprint 2) ? — *Reco : non ; Sprint 1 ne référence que les outils existants
  (reminder + web selon D4), un court addendum au doc suit après Sprint 2.*

---

## Sprints

### Sprint 1 — Réalignement du doc système · contexte partagé : `agent_system_doc` + cycle `@admin`/`@update` (prose versionnée)
> Le plus rentable, sans code. Supprime les dénis de rôle/mémoire immédiatement. Passe par la
> **revue de diff humaine** (§4 consignes) — jamais d'auto-activation. **Non délégable** (jugement +
> sécurité de prose) → Opus inline, l'utilisateur approuve le diff.
- [ ] Rédiger la nouvelle version du doc système : rôle réel (assistant personnel **avec mémoire**
  et outils), posture « classer l'intention avant de répondre » (D1/D2), fin des formules « je n'ai
  pas de mémoire / je ne peux rien stocker ». → #TBD
- [ ] Référencer les outils **existants** (`create_reminder`, `web_search` selon D4) : *quand* les
  mobiliser, jamais *comment* (le doc ne crée pas d'outil, `agent-outillage` §3.1). → #TBD
- [ ] Soumettre le diff via `@update` (ou page d'édition) et faire **approuver** la nouvelle version
  active ; vérifier au tour suivant que l'agent ne nie plus mémoire/outils. → #TBD
- [ ] Trancher D4 (activer Exa ou non) et, si activation, poser `SEARCH_PROVIDER`/`EXA_API_KEY` en
  env Coolify. → #TBD

### Sprint 2 — Outil `capture_note` (écriture KB Obsidian) · contexte partagé : `agent_tools/` (manifest·policy·registry·base) + `journal_kb_classifier` + `journal_vault`
> Construit le chemin d'écriture manquant. Couplé (contrat manifeste + classifieur + writer vault)
> → Opus inline, ou **un** worker Sonnet sur le sprint entier (jamais par item). Vérif = un tour
> `note_lecture` produit bien un fichier Markdown dans `/storage/journal-vault`.
- [ ] `agent_tools/capture_note.py` : `MANIFEST` (`effect=write`, `reversible=true`,
  `visibility` selon D6, périmètre vault utilisateur) + `_execute` appelant le classifieur puis le
  writer ; exporter `SPEC`, l'ajouter à `_ALL` dans `registry.py`. → #TBD
- [ ] Écriture au format **enveloppe document commune** (federation-ready, `KNOWLEDGE_ARCHITECTURE.md`)
  dans le vault ; métadonnées = sortie `journal_kb_classifier` (`contexte/nature/tags/title`). → #TBD
- [ ] Échec d'outil = erreur explicite `role=tool`, jamais résultat vide (leçon SearXNG, CLAUDE.md
  outillage) ; fallback « à classer » du classifieur ne perd jamais la note. → #TBD
- [ ] Étendre `checks/check_agent_tools.py` : doc empoisonné → `capture_note` reste hors périmètre
  (n'écrit que dans le vault), régime de confirmation dérivé et non codé. → #TBD
- [ ] Addendum au doc système : *quand* proposer une capture (suite de Sprint 1, revue de diff). → #TBD

### Sprint 3 — Classification d'intention câblée au tour · contexte partagé : `agent_chat.py` (`handle_conversation_turn`) + `agent_tools/loop` + contrat du classifieur
> Branche le pré-classifieur en amont du tour et oriente la boucle. Couplé au chat handler +
> jugement → **non délégable**, Opus inline.
- [ ] Pré-classifieur d'intention (D2) : DeepSeek-V4-Flash `json_schema`, enum = taxonomie D1,
  température ≤ 0.2, texte utilisateur en **donnée délimitée**, fallback `conversation`. → #TBD
- [ ] Router dans `handle_conversation_turn` : `note_lecture`/`stockage_source` → biaiser vers
  `capture_note` ; `rappel` → `create_reminder` ; `question` → réponse (+ `web_search` selon D4) ;
  `conversation` → tour normal. La classification **oriente**, la policy/le manifeste **décident**. → #TBD
- [ ] Corriger la formulation « je ne peux pas… » : orienter (`/feature`, extraits, recherche) sans
  nier un apport possible (cas actualité + PDF). → #TBD
- [ ] Vérif de bout en bout sur les 5 messages verbatim du constat : chacun est classé et traité
  conformément à la cible. → #TBD

---

## Annexe — contrats / specs détaillés

### A1 — Taxonomie d'intention (D1)

| Classe | Déclencheur typique (verbatim observé) | Traitement cible |
|---|---|---|
| `note_lecture` | « Note de lecture Safran : … » | `capture_note` → vault (KB Obsidian) + réaction |
| `stockage_source` | « Stocke ce lien dans une liste de sources… » | `capture_note` taguée `source` (D5) + accusé |
| `rappel` | « Rappelle-moi samedi 9h… » | `create_reminder` (carte Kanban `Rappels`) |
| `question` | « Quelles différences de perf optique/radar ? » | réponse ; `web_search` si activé (D4) |
| `conversation` | « Bonjour » | tour de conversation normal |

Sortie du pré-classifieur (schema fermé, comme `journal_kb_classifier`) :
`{ intent: enum, confidence?: number }` — `intent` **contraint par enum**, fallback `conversation`
sur JSON invalide / API down (aucune exception remontée : on ne perd jamais un tour).

### A2 — `capture_note` : contrat de manifeste (D3/D6)

```
effect        = write            # écrit dans le vault de l'utilisateur
taints_context= false            # n'injecte pas de contenu tiers non relu
reversible    = true             # fichier Markdown supprimable / éditable
visibility    = <D6>             # true → confirmation a posteriori ; false → confirmation avant
egress        = none             # pas de sortie réseau
```

Le régime de confirmation **découle** de ce manifeste (`agent_tools/policy.py`, fonction pure) —
il n'est jamais écrit à la main, cf. `agent-outillage.md` §3 et CLAUDE.md § outillage.

`_execute` : `journal_kb_classifier.classify(text)` → métadonnées → writer `journal_vault`
(enveloppe federation-ready). Réutilise le vocabulaire de `app/knowledge/categories.schema.yaml`
(jamais recopié en dur : construit au runtime depuis le schema file).

### A3 — Invariants de sécurité repris des chantiers voisins (non négociables)

- Prompt système = `agent_system_doc WHERE active` **uniquement** ; message + historique en rôles
  `user`/`assistant` (données), jamais `system` (`agent_chat.py:191`).
- Liste d'outils = `agent_tools/registry.py` **exclusivement** ; le doc système ne fait **jamais**
  exister un outil (vérifié par `checks/check_agent_tools.py` §A).
- Le pré-classifieur voit le texte utilisateur en **donnée délimitée**, jamais en instruction (§5.1).
- Aucune auto-modification du doc système sans revue de diff humaine (§4 consignes).

### A4 — Preuves (session du 2026-08-27)

- `agent_system_doc` : 1 seule version, `active=true`, 435 car., contenu = « …aucun outil ».
- `agent_conversations` : 18 tours (08-24 → 08-27), aucun routage vers le vault.
- `agent_instruction_queue` : vide (aucune consigne `@admin` en attente).
- `agent_tools/registry.py` `_ALL` = (`create_reminder.SPEC`, `web_search.SPEC`).
