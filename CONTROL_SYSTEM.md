# Système de contrôle — Tickets · Roadmap · Session Brief

> Instructions pour Claude Code. Lire ce fichier au démarrage de toute session de travail
> sur un projet qui utilise ce système.

---

## Principe

Trois couches. Ne pas les confondre.

```
ROADMAP        → espace de réflexion / direction (docs libres). Génère des tickets.
TICKETS        → unité de travail actionnable, portée limitée.
SESSION BRIEF  → ce qu'on traite maintenant (une session).
```

L'exécution tourne sous l'abonnement Claude Code : les consignes sont tapées **manuellement**
dans le terminal. Toute la logique multi-modèle passe par des **sous-agents** (couverts par
l'abonnement), jamais par des appels API externes.

---

## Modèle d'exécution — Opus orchestrateur + workers Sonnet

La session tourne sur **Opus** (modèle par défaut). Opus n'implémente pas tout lui-même :

```
Opus (orchestrateur)
  ├─ lit brief + tickets (descriptions seules — pas de lecture de code pour classer)
  ├─ ticket COMPLEXE → Opus l'implémente lui-même
  └─ ticket SIMPLE   → délègue à un sous-agent worker (Sonnet 4.6)
                         └─ implémente + renvoie un COMPTE-RENDU structuré
       Opus vérifie le compte-rendu contre la spec du ticket :
         · conforme      → ferme le ticket
         · écart détecté → lit le code de CE ticket uniquement, corrige, ferme
```

**But de la délégation** (on est en abonnement, pas facturé au token) : préserver le contexte
et le quota d'Opus pour le travail qui le mérite, paralléliser les tickets simples, rester sous
les limites d'usage. Ce n'est pas une optimisation de coût monétaire.

**Classification simple vs complexe** — décidée par Opus depuis la *description* du ticket, sans
lire le code :

| Simple → délègue au worker | Complexe → Opus fait lui-même |
|---|---|
| Portée locale, 1-2 fichiers | Multi-fichiers couplés, refacto |
| Description non-ambiguë | Ambiguïté nécessitant du jugement |
| Aucun choix d'architecture | Choix structurant en jeu |
| Ex : libellé, champ, petit endpoint clair, bug ciblé | Sécurité / données sensibles, ou `needs_clarification: true` |

Opus peut lancer **plusieurs workers en parallèle** pour des tickets simples indépendants.
Si deux tickets touchent le même fichier, ne pas les paralléliser (les sérialiser, ou Opus les fait).

---

## Contrat du sous-agent worker

Lancé via l'outil `Agent` avec `model: sonnet`. Accès outils complet (édition, tests, run).
Entrée : le chemin du fichier ticket + « implémente ce ticket et renvoie le compte-rendu ci-dessous ».

Le worker **doit vérifier son travail** (compiler / lancer les tests / vérifier le comportement)
avant de rendre la main, puis renvoyer **exactement** ce format :

```
1. Interprétation : ce que j'ai compris du ticket (1-2 phrases)
2. Fichiers modifiés : chemin + une ligne de "pourquoi" chacun
3. Décisions / hypothèses prises
4. Vérification : ce que j'ai lancé (test / compile / run) et le résultat
5. Ambiguïtés que j'ai tranchées seul
```

**Ce que la vérification par compte-rendu attrape** — et ce qu'elle n'attrape pas :

- ✅ **Contre-sens / dérive de spec** : Opus compare les points 1 et 5 à la spec. C'est le risque
  principal des tickets délégués, et c'est couvert sans relire le code.
- ❌ **Bugs de correctness** (code juste-de-compréhension mais faux) : aucun compte-rendu en prose
  ne les révèle. Le filet reste le point 4 (tests / run). Si le point 4 est absent ou faible,
  Opus lit le code du ticket.

---

## Localisation des fichiers

```
projects/{projet}/
  feedback-tickets/
    {id}-{type}-{slug}.md        ← tickets
    {id}-spec-{slug}.md          ← specs attachées à un ticket
  roadmap/
    *.md                         ← docs libres (directions, specs, audits, notes)
  SESSION_BRIEF.md               ← brief de session courante
  TICKETS.md                     ← index auto-généré, ne jamais éditer à la main
```

> Le dossier `feedback-tickets/` est la convention partout (y compris bank-review et assistant-ia).

---

## Format des tickets

Frontmatter :
```yaml
---
id: {timestamp_ms}
type: bug | feature | suggestion | error
status: open | blocked | closed
priority: high | medium | low           # ordre de traitement décroissant
date: {ISO 8601}
project: {nom_projet}
url: {url optionnelle}
milestone: {nom}                        # optionnel
needs_clarification: true               # optionnel — l'utilisateur veut être questionné avant impl.
closed_at: {ISO 8601 UTC}               # ajouté à la fermeture uniquement
---
```

Corps :
```markdown
## {emoji} {label}

**Date** : {date lisible}
**URL** : `{url}`

### Description
{texte}

### Notes d'implémentation        ← hypothèses / compte-rendu vérifié ajoutés à la fermeture
```

Plus de section `### Questions` dans le fichier : les clarifications se font **en direct dans le
terminal** (voir Étape 2).

---

## Format des items de roadmap

Le dossier `roadmap/` est un **espace de docs libre** — pas de gabarit imposé. Un fichier peut être
une direction, une spec, un audit, une note. Nommer librement (`00-principe-directeur.md`,
`spec-v2.md`, etc.). Quand une direction est mûre, elle génère des tickets (Étape 4b).

---

## Format du SESSION_BRIEF.md

```markdown
# Session Brief — {projet} — {YYYY-MM-DD}

## Scope
Milestone actif : {nom}   ·   Ne pas toucher : {modules hors-scope}

## Roadmap à définir (optionnel)
- [ ] {fichier roadmap ou direction courte} → générer les tickets

## Tickets à traiter
- [ ] #{id} — {type} — {résumé} (priority: {niveau})

## Contexte additionnel (optionnel)
{préférences techniques, décisions déjà prises}

## Résumé de session
*(rempli par Claude à la fin)*
```

---

## Commande de déclenchement

**« execute le brief session pour {projet} »**

Exécuter alors les étapes suivantes dans l'ordre.

---

## Étape 1 — Lire le contexte

1. `SESSION_BRIEF.md` du projet
2. `TICKETS.md` (vue globale)
3. Chaque ticket listé dans le brief : lire le `.md` complet + sa spec `{id}-spec-*.md` si présente
4. Chaque direction roadmap référencée : lire le(s) fichier(s)

Puis classer chaque ticket **simple / complexe** depuis sa description (sans lire de code).

---

## Étape 2 — Clarifications (tickets `needs_clarification: true`)

Pour ces tickets, **Opus** (pas un worker) pose ses questions **directement dans le terminal**,
attend les réponses de l'utilisateur, puis implémente dans la même passe. Ne rien écrire dans le
fichier avant d'avoir la réponse — on évite ainsi le double aller-retour et les relectures de code.

Si l'utilisateur n'est pas disponible : passer `status: blocked`, noter la question en une ligne
dans `### Notes d'implémentation`, et passer au ticket suivant.

---

## Étape 3 — Traiter les tickets (par priorité décroissante)

Pour chaque ticket :

**Complexe** → Opus l'implémente lui-même, vérifie (tests / run), ferme.

**Simple** → déléguer à un worker Sonnet (contrat ci-dessus). Puis :
1. Lire le compte-rendu.
2. Comparer points 1 et 5 à la spec du ticket.
3. Conforme et point 4 crédible → fermer. Écart, ou vérification faible → lire le code de ce
   ticket, corriger si besoin, fermer.

Lancer les workers de tickets simples **indépendants** en parallèle (fichiers disjoints).

**Escalade** — si un ticket « simple » se révèle demander un choix d'architecture ou > 2 questions :
ne pas forcer. Créer une note dans `roadmap/`, passer le ticket `blocked` avec un pointeur dans
`### Notes d'implémentation`, continuer.

---

## Étape 4 — Roadmap (si le brief le demande)

**a. Direction déjà mûre → tickets.** Analyser le code pertinent + les tickets existants (éviter
les doublons), puis créer les tickets dérivés dans `feedback-tickets/` au format standard
(assigner `milestone` et `priority`). Lister les IDs créés dans le fichier roadmap concerné.

**b. Direction à défricher.** Rédiger / compléter le doc dans `roadmap/`. Ne pas implémenter :
une direction génère d'abord des tickets.

---

## Fermeture d'un ticket

Frontmatter :
```yaml
status: closed
closed_at: {datetime ISO 8601 UTC}
```

Ajouter dans `### Notes d'implémentation` un **compte-rendu vérifié de 2-3 lignes** (ce qui a été
fait + comment ça a été vérifié) — pour que l'utilisateur suive sans lire le code.

Régénérer `TICKETS.md` : automatique si le projet a un endpoint qui le régénère (le prochain appel
API le fera) ; sinon le régénérer à la main au format existant (tableaux par type, open/closed).

---

## Étape 5 — Résumé de session

Cocher les items traités dans `SESSION_BRIEF.md` et remplir :

```markdown
## Résumé de session — {YYYY-MM-DD HH:MM}

✅ Implémentés (Opus) : #{id}, #{id}
🤖 Implémentés (worker Sonnet, vérifiés) : #{id}, #{id}
🔎 Écarts corrigés après vérification : #{id}
⏸ Bloqués (attente utilisateur) : #{id}
🗂 Tickets créés depuis roadmap : #{id}, #{id}
```

Ne pas supprimer `SESSION_BRIEF.md` — l'utilisateur crée le suivant depuis le hub.

---

## Règles de décision (résumé)

- **Déléguer à un worker** : portée locale, description claire, pas de choix d'architecture.
- **Faire soi-même (Opus)** : couplage multi-fichiers, ambiguïté de jugement, `needs_clarification`,
  sécurité / données sensibles.
- **Questionner en direct** : `needs_clarification: true`, ou détail bloquant absent de la description.
- **Escalader en roadmap** : choix d'architecture structurant, ou > 2 questions nécessaires.
- **Vérifier avant de fermer** : tests / run pour la correctness ; compte-rendu pour le contre-sens.

---

## Effort / modèles

- Session : **Opus** par défaut.
- Worker tickets simples : **Sonnet 4.6** (`model: sonnet`). `Haiku` réservé au trivial (libellé, config).
- Sur un ticket complexe traité par Opus, laisser l'effort par défaut (élevé) ; réserver l'effort
  maximal aux tickets architecturaux.
