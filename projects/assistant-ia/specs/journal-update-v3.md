# Spec — Journal Update v3

**Date :** 14 juin 2026  
**Projet :** assistant-ia / journal  
**Statut :** draft

---

## Périmètre

Cette mise à jour couvre quatre évolutions :

1. **Heure de relance configurable** (ticket #1780759170028)
2. **Réponses multiples par question** (ticket #1780759225530)
3. **Fréquence "jours de semaine"** (lundi–vendredi)
4. **Récapitulatif hebdomadaire** des réponses par Slack + page web

---

## 1. Heure de relance configurable

### Contexte

Actuellement la relance (follow-up) est envoyée exactement 3 heures après `heure_rappel`, en dur dans `app/jobs/journal_prompt.py`. L'utilisateur veut pouvoir définir cette heure lui-même dans les paramètres de chaque objectif.

### Changements base de données

```sql
-- Migration 007_heure_relance.sql
ALTER TABLE journal_objectifs
  ADD COLUMN IF NOT EXISTS heure_relance TIME DEFAULT NULL;
-- NULL = comportement actuel (rappel + 3h)
```

### Logique métier

- Si `heure_relance IS NULL` : comportement actuel inchangé (heure_rappel + 3h).
- Si `heure_relance IS NOT NULL` : la relance est déclenchée à cette heure fixe, à condition que l'objectif ne soit pas déjà complété et que `heure_relance > heure_rappel`.
- Validation à la saisie : `heure_relance` doit être postérieure à `heure_rappel` (erreur affichée sinon).

### Service — `journal_v2.py`

- Ajouter `heure_relance: time | None` dans `create_objectif()` et `update_objectif()`.

### Scheduler — `journal_prompt.py`

Remplacer le calcul actuel `sent_at + 3h` par :

```python
if objectif.heure_relance:
    relance_due = now.replace(
        hour=objectif.heure_relance.hour,
        minute=objectif.heure_relance.minute,
        second=0
    )
else:
    relance_due = notification.sent_at + timedelta(hours=3)
```

### UI Settings — `journal_settings.py` + template

Dans le formulaire d'édition d'un objectif, ajouter un champ **"Heure de la relance"** (input `type="time"`, optionnel) sous le champ "Heure du rappel". Afficher un hint : `"Laisser vide pour une relance automatique 3h après le rappel"`.

---

## 2. Réponses multiples par question

### Contexte

La contrainte `UNIQUE(question_id, objectif_id, session_date)` dans `journal_reponses` empêche d'enregistrer plusieurs réponses pour une même question le même jour. Certaines questions à texte libre (ex : "Qu'as-tu appris aujourd'hui ?") devraient accepter des entrées successives.

### Choix de conception

On introduit un **mode "multi-réponses"** au niveau de la question (opt-in), plutôt que de supprimer la contrainte globalement. Les questions classiques conservent leur comportement d'upsert.

### Changements base de données

```sql
-- Migration 007 (suite)
ALTER TABLE journal_questions
  ADD COLUMN IF NOT EXISTS multi_reponses BOOLEAN DEFAULT FALSE;

-- La contrainte UNIQUE existante reste inchangée pour les questions standard.
-- Pour les questions multi_reponses, on ne passe plus par l'upsert :
-- on insère toujours une nouvelle ligne (pas de ON CONFLICT).
-- On supprime la contrainte UNIQUE conditionnellement via un index partiel :

-- Supprimer l'ancienne contrainte UNIQUE globale
ALTER TABLE journal_reponses
  DROP CONSTRAINT IF EXISTS journal_reponses_question_id_objectif_id_session_date_key;

-- Recréer en index partiel uniquement pour les questions non-multi
CREATE UNIQUE INDEX IF NOT EXISTS journal_reponses_unique_single
  ON journal_reponses (question_id, objectif_id, session_date)
  WHERE question_id NOT IN (
    SELECT id FROM journal_questions WHERE multi_reponses = TRUE
  );
-- Note : cet index partiel est recalculé dynamiquement par Postgres.
-- Alternative plus robuste : ajouter une colonne `multi_reponses` dans journal_reponses
-- et utiliser un index partiel sur multi_reponses = FALSE.
```

> **Alternative recommandée** (plus robuste) : ajouter une colonne `entry_index SMALLINT DEFAULT 0` dans `journal_reponses` et modifier la contrainte unique en `UNIQUE(question_id, objectif_id, session_date, entry_index)`. Pour les questions standard, `entry_index` vaut toujours 0 (upsert). Pour les questions multi, on incrémente à chaque insertion.

```sql
ALTER TABLE journal_reponses
  DROP CONSTRAINT IF EXISTS journal_reponses_question_id_objectif_id_session_date_key;

ALTER TABLE journal_reponses
  ADD COLUMN IF NOT EXISTS entry_index SMALLINT DEFAULT 0;

CREATE UNIQUE INDEX IF NOT EXISTS journal_reponses_unique
  ON journal_reponses (question_id, objectif_id, session_date, entry_index);
```

**Retenu : l'approche `entry_index`**, plus simple à maintenir.

### Service — `journal_v2.py`

- `create_question()` et `update_question()` : ajouter paramètre `multi_reponses: bool = False`.
- `store_reponse()` :
  - Si `multi_reponses = False` : comportement inchangé, `entry_index = 0`, `ON CONFLICT DO UPDATE`.
  - Si `multi_reponses = True` : calculer `MAX(entry_index) + 1` pour ce `(question_id, objectif_id, session_date)`, insérer sans conflit.
- `get_session_reponses()` : pour les questions multi, retourner toutes les entrées (liste), pas seulement la dernière.
- Ajouter `delete_reponse(reponse_id)` pour permettre la suppression d'une entrée individuelle.

### Flux Slack

Le comportement après une réponse sur une question `multi_reponses = True` dépend de sa position dans la séquence :

**Cas A — question multi en milieu de séquence** (des questions obligatoires suivent) :
- Après chaque réponse, le bot propose deux boutons :
  - **"Ajouter une autre réponse"** → le bot renvoie la même question
  - **"Passer à la suite"** → le bot avance à la question suivante
- Boutons : `action_id = "jrn_multi_add_{q_index}"` et `"jrn_multi_next_{q_index}"`.

**Cas B — question multi en dernière position** (aucune question obligatoire ne suit) :
- La première réponse enregistrée **déclenche immédiatement la complétion de l'objectif**.
- Le bot envoie un message de complétion du type :
  > ✅ *Objectif atteint ! N'hésite pas à compléter avec d'autres réponses si tu le souhaites.*
- L'utilisateur peut continuer à envoyer des messages dans le thread : chaque message suivant est enregistré comme une entrée supplémentaire (`entry_index` incrémenté), sans bouton ni relance.
- La détection "dernière position" se fait via `is_last_required_or_all_optional_after(question_index, questions)` : vrai si toutes les questions d'index supérieur ont `is_required = False` ou `multi_reponses = True` déjà répondues.

> **Note :** `is_objectif_complete()` reste inchangé — il vérifie que toutes les questions `is_required=True` ont au moins une entrée (`entry_index = 0`). La question multi en dernière position est `is_required=True` et sera complète dès la première réponse.

### Formulaire web

- Pour une question `multi_reponses = True` :
  - Afficher les réponses existantes sous forme de liste avec un bouton "Supprimer" par entrée.
  - Afficher un champ vide supplémentaire pour ajouter une nouvelle réponse.
  - Le POST crée une nouvelle entrée sans toucher aux existantes.

### UI Settings

Dans le formulaire de création/édition d'une question, ajouter une **checkbox "Autoriser plusieurs réponses par jour"**, visible uniquement pour les types `text` et `short_text`.

---

## 3. Fréquence "jours de semaine" (lundi–vendredi)

### Contexte

`journal_objectifs.frequence` accepte `daily | weekly | monthly`. Ajouter `weekdays` pour les objectifs qui ne doivent pas s'activer le week-end.

### Changements base de données

Aucun changement de schéma : le champ `frequence VARCHAR(20)` et `jours JSONB` suffisent.  
`frequence = 'weekdays'` est une nouvelle valeur constante (pas de `jours` à configurer).

### Service — `journal_v2.py`

Dans `get_due_objectifs_today()`, ajouter le cas :

```python
elif objectif.frequence == 'weekdays':
    # weekday() : 0=lundi, 4=vendredi, 5=samedi, 6=dimanche
    due = today.weekday() < 5
```

### UI Settings

Dans le sélecteur de fréquence, ajouter l'option **"Jours de semaine (lun–ven)"** entre `daily` et `weekly`. Masquer le sélecteur de jours (inutile pour cette fréquence).

---

## 4. Récapitulatif hebdomadaire

### Description fonctionnelle

Chaque semaine, à un jour et une heure configurables, l'assistant envoie sur Slack un récapitulatif de toutes les réponses enregistrées pour l'objectif au cours des 7 derniers jours. Le message Slack contient un lien vers une page web paginée par semaine, accessible sans connexion via un token signé.

### Paramètres par objectif

| Paramètre | Type | Défaut | Description |
|-----------|------|--------|-------------|
| `recap_actif` | BOOLEAN | FALSE | Active/désactive le récap hebdo |
| `recap_jour` | SMALLINT (0–6) | 0 (lundi) | Jour d'envoi (0=lun, 6=dim) |
| `recap_heure` | TIME | `08:00` | Heure d'envoi |

### Changements base de données

```sql
-- Migration 008_recap_hebdo.sql
ALTER TABLE journal_objectifs
  ADD COLUMN IF NOT EXISTS recap_actif   BOOLEAN   DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS recap_jour    SMALLINT  DEFAULT 0,
  ADD COLUMN IF NOT EXISTS recap_heure   TIME      DEFAULT '08:00:00';

CREATE TABLE IF NOT EXISTS journal_recap_envois (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  objectif_id  UUID NOT NULL REFERENCES journal_objectifs(id),
  semaine_iso  VARCHAR(8) NOT NULL,   -- ex: '2026-W24'
  sent_at      TIMESTAMPTZ DEFAULT now(),
  UNIQUE (objectif_id, semaine_iso)   -- un seul envoi par objectif par semaine
);
```

### Token d'accès à la page web

La page récap est publique via un token signé (HMAC-SHA256, valide 60 jours) :

```
GET /journal/recap/{objectif_id}/{semaine_iso}?token={signed_token}
```

Token = `HMAC-SHA256(key=SESSION_SECRET, msg=f"{objectif_id}:{semaine_iso}")`  
Utiliser `itsdangerous.URLSafeSerializer` (déjà présent dans le projet).

### Scheduler — nouveau job `journal_recap.py`

Job APScheduler : **toutes les minutes** (même pattern que les rappels).

```python
async def send_recap_hebdo():
    now = datetime.now(tz_paris)
    today_weekday = now.weekday()   # 0=lun
    current_time  = now.strftime("%H:%M")

    objectifs = await get_objectifs_recap_dus(today_weekday, current_time)
    for obj in objectifs:
        semaine = now.strftime("%Y-W%W")
        if await recap_deja_envoye(obj.id, semaine):
            continue
        reponses = await get_reponses_semaine(obj.id, semaine)
        if not reponses:
            continue
        await envoyer_recap_slack(obj, reponses, semaine)
        await marquer_recap_envoye(obj.id, semaine)
```

### Service — `journal_v2.py` (nouvelles fonctions)

- `get_objectifs_recap_dus(weekday, heure_str)` → objectifs avec `recap_actif=TRUE`, `recap_jour=weekday`, `recap_heure` à l'heure courante (tolérance ±1 min).
- `get_reponses_semaine(objectif_id, semaine_iso)` → retourne un dict `{question: [réponses]}` pour les 7 jours de la semaine ISO.
- `marquer_recap_envoye(objectif_id, semaine_iso)` → upsert dans `journal_recap_envois`.
- `recap_deja_envoye(objectif_id, semaine_iso)` → vérifie `journal_recap_envois`.

### Message Slack

Structure du message envoyé dans `#journal` :

```
📋 *Récap semaine — [Nom de l'objectif]* (semaine du DD/MM au DD/MM)

*Question 1 : [texte de la question]*
• [réponse du lundi DD/MM]
• [réponse du mercredi DD/MM]
...

*Question 2 : [texte de la question]*
• [réponse du mardi DD/MM]
...

👉 <https://…/journal/recap/{id}/{semaine}?token={token}|Voir le récap complet>
```

- Si une question n'a aucune réponse sur la semaine : ne pas l'afficher.
- Limiter le message Slack à 3 000 caractères ; si dépassé, tronquer avec le lien "Voir le récap complet".

### Page web — `GET /journal/recap/{objectif_id}/{semaine_iso}`

Route publique (pas de cookie requis), accès conditionné au token signé.

**Affichage :**
- En-tête : nom de l'objectif + période (lun DD/MM → dim DD/MM).
- Navigation : `← Semaine précédente` / `Semaine suivante →` (liens avec tokens recalculés).
- Corps : une section par question (dans l'ordre `sort_order`), avec la liste des réponses par date.
- Footer : lien "Remplir le journal" → `/journal/fill/{objectif_id}` (nécessite auth).
- Rendu des valeurs cohérent avec `journal_fill.py` (notes en ●, choix en tags, texte brut, etc.).

**Erreurs :**
- Token invalide ou expiré → page 403 "Lien expiré".
- Semaine sans aucune réponse → page vide avec message "Aucune réponse enregistrée cette semaine."

### UI Settings

Dans le formulaire d'édition d'un objectif, ajouter une section **"Récapitulatif hebdomadaire"** :

```
[ ] Activer le récapitulatif hebdomadaire

  Jour d'envoi : [Lundi ▾]
  Heure d'envoi : [08:00]
```

La section jour/heure n'est visible que si la checkbox est cochée (JS simple, même pattern que les champs de fréquence existants).

---

## Plan de migration

| # | Migration | Description |
|---|-----------|-------------|
| 007 | `007_heure_relance_multi.sql` | Ajoute `heure_relance`, `multi_reponses`, `entry_index`, refait l'index unique |
| 008 | `008_recap_hebdo.sql` | Ajoute `recap_actif/jour/heure`, crée `journal_recap_envois` |

Les migrations sont idempotentes (`IF NOT EXISTS`, `IF EXISTS`) et s'appliquent au démarrage.

---

## Fichiers à modifier

| Fichier | Changements |
|---------|-------------|
| `migrations/007_*.sql` | Nouveau |
| `migrations/008_*.sql` | Nouveau |
| `app/services/journal_v2.py` | `create/update_objectif`, `store_reponse`, `get_due_objectifs_today`, + nouvelles fonctions récap |
| `app/jobs/journal_prompt.py` | Heure de relance configurable |
| `app/jobs/journal_recap.py` | Nouveau — job récap hebdo |
| `app/main.py` | Enregistrer le nouveau job scheduler |
| `app/handlers/journal_slack.py` | Flux multi-réponses (boutons add/next) |
| `app/routes/journal_settings.py` | Champs heure_relance, multi_reponses, recap_* |
| `app/routes/journal_fill.py` | Affichage/ajout/suppression entrées multi |
| `app/routes/journal_recap.py` | Nouveau — page récap publique tokenisée |
| `app/templates/journal_settings_*.html` | Nouveaux champs UI |
| `app/templates/journal_fill_*.html` | UI multi-réponses |
| `app/templates/journal_recap.html` | Nouveau |

---

## Points ouverts

- **Suppression d'entrées multi depuis Slack** : non couvert dans cette spec. Un utilisateur peut supprimer via le formulaire web uniquement.
- **Format des valeurs dans le récap** : à valider pour les types `ranking` et `scale` (affichage textuel ou graphique ?).
- **Langue de la navigation semaine** : français uniquement, pas de i18n prévue.
- **Timezone de `semaine_iso`** : toujours `Europe/Paris`.
