# Système de contrôle — Tickets · Roadmap · Session Brief

> Instructions pour Claude Code. Lire ce fichier intégralement avant toute session de travail
> sur un projet qui utilise ce système.

---

## Architecture

Trois couches hiérarchiques. Ne pas les confondre.

```
ROADMAP        → tu définis l'implémentation (l'utilisateur délègue la réflexion)
TICKETS        → tu implémentes (actionnable, portée limitée)
SESSION BRIEF  → ce que tu fais maintenant (opérationnel, une session)
```

Un item roadmap génère des tickets. Les tickets alimentent le brief.
Un ticket ne remonte jamais directement en roadmap sauf escalade explicite (> 2 questions nécessaires).

---

## Localisation des fichiers

```
projects/{projet}/
  feedback-tickets/
    {id}-{type}-{slug}.md        ← tickets
    {id}-spec-{slug}.md          ← specs attachées à un ticket
  roadmap/
    roadmap-{id}-{slug}.md       ← items de roadmap
  SESSION_BRIEF.md               ← brief de session courante
  TICKETS.md                     ← index auto-généré, ne jamais éditer manuellement
```

---

## Format des tickets

Frontmatter :
```yaml
---
id: {timestamp_ms}
type: bug | feature | suggestion | error
status: open | blocked | closed
priority: low | medium | high | critical
date: {ISO 8601}
project: {nom_projet}
url: {url optionnelle}
milestone: {nom_milestone}           # optionnel — ex: V2-budget
needs_clarification: true            # optionnel — signal explicite de l'utilisateur
closed_at: {ISO 8601}                # ajouté à la fermeture uniquement
---
```

Corps du fichier :
```markdown
## {emoji} {label}

**Date** : {date lisible}
**URL** : `{url}`

### Description

{texte}

### Questions avant implémentation     ← présente uniquement si status: blocked

**Q1** : {question concise}
**R1** : *(en attente)*

**Q2** : {question concise}
**R2** : {réponse de l'utilisateur}

### Notes d'implémentation             ← tu ajoutes tes hypothèses ici si tu implémentes avec ambiguïté
```

---

## Format des items de roadmap

```markdown
---
id: roadmap-{timestamp}
status: draft | spec-ready | tickets-created | done
created: {ISO 8601}
project: {nom_projet}
---

## {titre de la direction ou feature complexe}

### Direction / Feature (utilisateur)
{ce que l'utilisateur a écrit — ne pas modifier}

### Contraintes connues
{optionnel — rempli par l'utilisateur}

---
### Spec générée
*(Claude Code remplit cette section)*

### Tickets créés
*(Claude Code liste ici les IDs des tickets créés)*
```

---

## Format du SESSION_BRIEF.md

```markdown
# Session Brief — {projet} — {YYYY-MM-DD}

## Scope
Milestone actif : {nom}
Ne pas toucher : {modules hors-scope}

## Roadmap — définition (avant implémentation)
- [ ] roadmap-{id} : {instruction précise pour Claude}
- [ ] Créer item roadmap pour : "{direction courte}"

## Pré-actions (specs à générer)
- [ ] Générer spec pour : "{description rapide}" → attacher au ticket #{id}

## Tickets à traiter
- [ ] #{id} — {type} — {résumé court} (priority: critical)
- [ ] #{id} — {type} — {résumé court} (priority: high)
- [ ] #{id} — {type} — {résumé court} (priority: low)

## Contexte additionnel
{optionnel : hypothèses, préférences techniques, décisions déjà prises}

## Résumé de session
*(Claude Code remplit cette section à la fin)*
```

---

## Commande de déclenchement

Phrase exacte : **"execute le brief session pour {projet}"**

À cette commande, exécuter les étapes suivantes dans l'ordre strict.

---

## Étape 1 — Lire le contexte

1. Lire `SESSION_BRIEF.md` dans le répertoire du projet
2. Lire `TICKETS.md` pour la vue globale des tickets ouverts
3. Pour chaque item roadmap référencé : lire `roadmap/{fichier}.md`
4. Pour chaque ticket listé dans le brief : lire le fichier `.md` complet dans `feedback-tickets/`
5. Pour chaque spec attachée pertinente : lire `feedback-tickets/{id}-spec-*.md`

---

## Étape 2 — Traiter les items roadmap

Pour chaque item en section "Roadmap — définition" :

1. Analyser le code existant du projet (fichiers pertinents à la direction)
2. Analyser les tickets existants pour détecter ce qui existe déjà
3. Rédiger la spec dans la section `### Spec générée` du fichier roadmap
4. Créer les tickets dérivés dans `feedback-tickets/` au format standard
   — Assigner `milestone` = nom du roadmap item sur chaque ticket créé
   — Assigner `priority` selon l'urgence estimée
5. Lister les IDs créés dans `### Tickets créés`
6. Passer `status` du roadmap item à `tickets-created`
7. Cocher l'item dans SESSION_BRIEF.md : `- [x]`

---

## Étape 3 — Traiter les pré-actions (specs)

Pour chaque "Générer spec pour" :

1. Générer le fichier `feedback-tickets/{ticket_id}-spec-{slug}.md`
2. La spec doit contenir : objectif, comportement attendu (cas nominal + edge cases),
   contraintes techniques, fichiers à modifier, hors-scope explicite
3. Cocher dans SESSION_BRIEF.md : `- [x]`

---

## Étape 4 — Traiter les tickets

Traiter dans l'ordre de priorité : `critical` → `high` → `medium` → `low`

Pour chaque ticket, appliquer le **premier cas qui correspond** :

**CAS A — status: blocked, au moins une question avec `*(en attente)*`**
→ SKIP. L'utilisateur n'a pas encore répondu.
→ Résumé : `⏸ #{id} — en attente de réponses utilisateur`

**CAS B — status: blocked, toutes les réponses sont remplies (plus de `*(en attente)*`)**
→ Lire les réponses dans `### Questions avant implémentation`
→ Passer `status: open` dans le frontmatter
→ Implémenter en tenant compte des réponses
→ Fermer le ticket (voir règles de fermeture)

**CAS C — `needs_clarification: true` dans le frontmatter, pas encore de section `### Questions`**
→ Écrire les questions (max 2) dans le corps du ticket
→ Passer `status: blocked`
→ SKIP
→ Résumé : `⏸ #{id} — questions écrites, en attente utilisateur`

**CAS D — status: open, ambiguïté mineure (≤ 2 questions nécessaires)**
Deux sous-cas :
- Interprétation évidente → implémenter, documenter l'hypothèse dans `### Notes d'implémentation` :
  "J'ai supposé X. Si incorrect : modifier Y dans fichier Z."
- Choix laissé à l'utilisateur → écrire questions, passer à `blocked`, SKIP

**CAS E — status: open, ambiguïté structurelle (> 2 questions nécessaires)**
→ Ne pas implémenter
→ Créer un item `roadmap/roadmap-{timestamp}-{slug}.md` avec la description du ticket
→ Passer `status: blocked` sur le ticket, ajouter note : "Escaladé en roadmap-{id}"
→ Résumé : `⚠ #{id} — escaladé → roadmap-{id}`

**CAS F — status: open, tout clair**
→ Implémenter
→ Fermer le ticket (voir règles de fermeture ci-dessous)

---

## Règles de fermeture d'un ticket

Modifier le frontmatter :
```yaml
status: closed
closed_at: {datetime ISO 8601 avec timezone UTC}
```

Si le projet a un endpoint API qui régénère `TICKETS.md` automatiquement (ex: bank-review),
ne pas régénérer manuellement — le prochain appel API le fera.

Si le projet n'a pas d'endpoint dédié, régénérer `TICKETS.md` manuellement en suivant
le format existant (tableau par type, séparation open/closed).

---

## Étape 5 — Mettre à jour le SESSION_BRIEF.md

Cocher tous les items traités.
Remplir la section `## Résumé de session` :

```markdown
## Résumé de session — {YYYY-MM-DD HH:MM}

✅ Implémentés : #{id}, #{id}
⏸ En attente de réponses : #{id} (Q1), #{id} (Q1, Q2)
⚠ Escaladés en roadmap : #{id} → roadmap-{id}
📋 Specs générées : {nom_fichier}.md
🗂 Tickets créés depuis roadmap : #{id}, #{id}
```

Ne pas supprimer le SESSION_BRIEF.md. L'utilisateur crée le suivant manuellement
depuis le hub quand il est prêt pour la prochaine session.

---

## Règles de décision : quand poser des questions

**Implémenter directement :**
- Comportement attendu non-ambigu
- Edge cases avec traitement logique évident
- Aucun choix UX/design laissé ouvert

**Écrire des questions (max 2), passer à `blocked` :**
- Plusieurs comportements raisonnables existent, l'utilisateur doit choisir
- Le scope est ambigu (affecte A uniquement ou aussi B ?)
- Un détail UX est critique et absent de la description

**Implémenter avec hypothèse documentée :**
- Ambiguïté mineure, interprétation évidente
- Toujours documenter dans `### Notes d'implémentation`
- Maximum 1 hypothèse par ticket sans vérification utilisateur

**Escalader en roadmap :**
- Plus de 2 questions nécessaires pour clarifier
- Choix d'architecture structurant en jeu
- L'implémentation nécessite une analyse du code existant pour définir quoi faire

---

## Format des questions dans un ticket

Ajouter EXACTEMENT cette section après `### Description`, avant toute autre section existante :

```markdown
### Questions avant implémentation

**Q1** : {question concise — une seule chose à la fois}
**R1** : *(en attente)*

**Q2** : {question concise}
**R2** : *(en attente)*
```

Ne pas modifier le reste du fichier. Passer `status: blocked` dans le frontmatter.

---

## Génération d'une spec

Une spec est un fichier Markdown autonome contenant :
- Objectif et contexte
- Comportement attendu : cas nominal + edge cases
- Contraintes techniques
- Liste non-exhaustive des fichiers à modifier
- Hors-scope explicite

Nommage :
- Spec attachée à un ticket : `feedback-tickets/{ticket_id}-spec-{slug}.md`
- Spec d'un item roadmap : dans le fichier roadmap, section `### Spec générée`

---

## Règles générales

1. Toujours traiter dans l'ordre : roadmap → pré-actions → tickets par priorité
2. Maximum 2 questions par ticket, sans exception
3. Ne jamais sortir du scope défini dans `## Scope` du brief
4. Un item roadmap n'est jamais implémenté directement — il génère des tickets d'abord
5. Les specs (`-spec-*.md`) sont permanentes — ne jamais les supprimer
6. Documenter toute hypothèse dans `### Notes d'implémentation` du ticket concerné
