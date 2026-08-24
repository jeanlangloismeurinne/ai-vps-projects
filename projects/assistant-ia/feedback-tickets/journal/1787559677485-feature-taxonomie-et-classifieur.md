---
id: 1787559677485
type: feature
status: closed
priority: high
date: 2026-08-24T08:21:17+00:00
closed_at: 2026-08-24T10:45:00+00:00
project: assistant-ia
url: 
milestone: journal-kb
---

## ✨ Feature

**Date** : 24/08/2026 08:21
**URL** : `N/A`

### Description

Le **schema file** du domaine + le **classifieur** (roadmap §3 et §4).

**1. Schema file** — `app/knowledge/categories.schema.yaml`, versionné dans le repo, sert de
prompt de cadrage au modèle :

```yaml
axes:
  contexte: [personnel, professionnel]        # obligatoire, exactement 1
  nature:   [idee, apprentissage, note_de_lecture, decision, question]  # obligatoire, 1..n
tags_libres: [management, politique, vacances, restaurant]  # 0..n, vocabulaire ouvert
```

Les deux axes sont à **vocabulaire fermé** ; `tags_libres` est ouvert (le modèle peut en proposer
de nouveaux). Le fichier est la source de vérité — le prompt est construit **depuis** le YAML,
jamais recopié en dur dans le code.

**2. Classifieur** — `app/services/journal_kb_classifier.py` :

- Appelle `deepinfra_client.chat_json` avec `DEEPINFRA_MODEL_CLASSIF` (Llama 3.1 8B),
  **température basse** (≤ 0.2).
- Sortie contrainte : `{contexte, nature[], tags[], title}`.
- Le `title` est produit **dans le même appel** que la classification (roadmap §5 : même contenu
  en entrée, donc un seul appel — pas deux).
- **Aucune reformulation du texte utilisateur** : le `body` stocké est le verbatim. Le modèle ne
  produit que des métadonnées.
- **Validation stricte** : `contexte` et `nature` doivent appartenir au vocabulaire du YAML ;
  toute valeur hors vocabulaire est rejetée (pas de correction silencieuse).
- **Comportement en cas d'échec** (JSON invalide, API indisponible, valeur hors vocabulaire après
  1 retry) : l'entrée est **quand même enregistrée** avec `contexte = NULL`, `nature = NULL`,
  `tags = {}` et un marqueur « à classer ». On ne perd jamais une note de l'utilisateur à cause
  du classifieur.

Le texte utilisateur est passé au modèle comme **donnée**, jamais comme instruction (même règle
que le modèle de sécurité de l'agent).

### Vérification attendue

Tests sur 4-5 phrases types (une pro, une perso, une note de lecture, une ambiguë) : sortie JSON
conforme au schéma, vocabulaire respecté. Un test avec réponse modèle volontairement invalide →
fallback « à classer », pas d'exception remontée.

### Notes d'implémentation

`app/knowledge/categories.schema.yaml` + `app/services/journal_kb_classifier.py`. Le prompt est
construit depuis le YAML au runtime (vérifié : aucune valeur du vocabulaire n'apparaît en dur dans
le `.py`). Un seul appel DeepInfra produit classification + `title`, température 0.15.

**Écart assumé vs le ticket** : l'axe `nature` est en `0..n` et non `1..n`. La roadmap
(`roadmap/journal-knowledge-base.md:72`) fait foi et dit `0..n`. Le `1..n` du ticket produisait un
défaut réel observé pendant les tests — une note « week-end à la montagne » était étiquetée
`note_de_lecture` parce que le modèle devait remplir le champ coûte que coûte. Le prompt demande
maintenant explicitement `[]` quand aucune valeur ne convient ; le vide est un signal honnête, repris
par le curator (#1787559677489).

Vérifications : 5 classifications réelles conformes au vocabulaire (rapport worker, avant le passage
en 0..n), puis 12 assertions locales après correction — `nature: []` accepté, valeurs hors
vocabulaire rejetées sans correction silencieuse, prompt porteur de la consigne `[]`. Fallback prouvé
sur API indisponible : `tags=["a_classer"]`, `contexte`/`nature` à NULL, aucune exception remontée.

⚠️ Non rejoué après le passage en `0..n` : les appels API réels (le classifieur auto-mode bloque
l'extraction de la clef DeepInfra). Ne porte que sur la qualité du choix du modèle, pas sur la
conformité — la validation stricte côté Python couvre ce risque. À reconfirmer après déploiement.
