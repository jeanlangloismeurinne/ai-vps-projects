# SPEC — Scheduler V1 & Page Monitoring
_Rédigée le 2026-06-14_

## Contexte

Le scheduler V0 (`event_router.py`) sera mis à l'arrêt. La V1 reprend toute sa logique métier et l'étend. La V0 continue de tourner pendant la transition ; aucune modification n'est faite dessus.

L'architecture V1 repose sur la table `calendar_events` (V1) — distincte de `v0_calendar_events` utilisée par le V0. Les `monitoring_sessions` sont créées automatiquement par le scheduler pour les modes 1, 2, 3, 4. Le Mode 5 (routing) reste manuel avec alerte Slack.

---

## 1. Migration 019

Fichier : `backend/app/db/migrations/019_scheduler_v1.sql`

```sql
-- Tracking du brief J-2 séparé du triggered J+1
ALTER TABLE calendar_events
  ADD COLUMN brief_triggered BOOLEAN NOT NULL DEFAULT FALSE;

-- Lien explicite session → événement calendrier déclencheur
-- NULL pour sessions manuelles, renseigné pour sessions auto-scheduler
ALTER TABLE monitoring_sessions
  ADD COLUMN calendar_event_id INTEGER REFERENCES calendar_events(id) ON DELETE SET NULL;
```

Application manuelle (non auto) :
```bash
docker exec shared-postgres psql -U admin -d db_portfolio -f /chemin/019_scheduler_v1.sql
```

---

## 2. `backend/app/calendar/event_router_v1.py` — nouveau fichier

### Architecture

```python
class EventRouterV1:
    async def process_daily_events(self):
        today = date.today()
        await self._trigger_pre_event_briefs(today)    # J-2, Mode 1
        await self._trigger_quarterly_reviews(today)   # J+1, Mode 2
        await self._trigger_sector_pulses(today)       # J+1, Mode 4
        await self._trigger_conviction_reviews(today)  # Jour J, Mode 3
```

### Règles communes

- Filtre `pending_validation = FALSE` — un event non validé ne déclenche rien
- Si `monitoring-agent.synced = FALSE` : pas d'exécution, log warning, continue vers ticker suivant
- Chaque session créée reçoit `calendar_event_id = ce.id`
- Erreurs catchées individuellement par ticker — une erreur n'arrête pas les autres
- Appel direct à `MonitoringAgentV1` (pas de boucle HTTP interne)

---

### `_trigger_pre_event_briefs(today)` — Mode 1, J-2

**Condition SQL :**
```sql
SELECT ce.*, t.name AS ticker_name, t.company_type,
       th.thesis_json, th.id AS thesis_id
FROM calendar_events ce
JOIN tickers t ON t.id = ce.ticker_id
LEFT JOIN theses th ON th.id = ce.thesis_id AND th.status = 'active'
WHERE ce.scheduled_date = $1 + INTERVAL '2 days'
  AND ce.brief_triggered = FALSE
  AND ce.triggered = FALSE
  AND ce.pending_validation = FALSE
  AND ce.event_type IN ('quarterly_results', 'cmd', 'agm')
```

**Contexte injecté à l'agent :**
```
Ticker : {ticker_id}
Trigger : {label}
Mode demandé : 1
company_type : {public|private}
Événement : {event_type} prévu le {scheduled_date}

[Si thèse active]
Thèse — one_liner : ...
Hypothèses à surveiller :
  H1 — {text} | KPI : {kpi_metric} | Seuil alerte : {alert_threshold}
  H2 — ...
```

**Actions après succès :**
- `INSERT monitoring_sessions` (mode=1, status=completed, calendar_event_id=ce.id)
- `INSERT monitoring_messages` (role=user + role=agent)
- `UPDATE calendar_events SET brief_triggered = TRUE`
- Slack : `📋 Pré-event brief — {ticker} | {label} dans 2 jours`

---

### `_trigger_quarterly_reviews(today)` — Mode 2, J+1

**Condition SQL :**
```sql
SELECT ce.*, t.name, t.company_type,
       th.thesis_json, th.id AS thesis_id
FROM calendar_events ce
JOIN tickers t ON t.id = ce.ticker_id
LEFT JOIN theses th ON th.id = ce.thesis_id AND th.status = 'active'
WHERE ce.scheduled_date = $1 - INTERVAL '1 day'
  AND ce.triggered = FALSE
  AND ce.pending_validation = FALSE
  AND ce.event_type IN ('quarterly_results', 'cmd')
```

**Contexte injecté :**
```
Ticker : {ticker_id}
Trigger : {label}
Mode demandé : 2
company_type : {public|private}

[Si thèse active]
Thèse JSON : {thesis_json complet}

[Si société cotée]
Données de marché : prix={price}, PER NTM={forward_pe}, market_cap={market_cap}
Via DataService.get_m1() — cache accepté (pas de refresh forcé)

[Si société non cotée]
Profil private : {private_company_profiles complet}
```

**Normalisation du JSON retourné** (voir §3) : `hypothesis_reviews[]` fusionné avec hypothèses thèse → `hypotheses_reviewed[]`.

**Actions après succès :**
```
INSERT monitoring_sessions (mode=2, result_json normalisé, alert_level, calendar_event_id)
INSERT monitoring_messages (user context + agent response)
UPDATE calendar_events SET triggered = TRUE

Si alert_level = RAS :
  Slack : "✅ Monitoring RAS — {ticker} | {label}"

Si alert_level = REVIEW_REQUIRED :
  Slack : "⚠️ Révision requise — {ticker} | {label}\n→ {URL_BASE}/ticker/{ticker_id}/monitoring/{session_id}"
  [Mode 5 reste manuel]

Si alert_level = CRITICAL :
  Slack : "🔴 CRITIQUE — {ticker} | {label}\n→ {URL_BASE}/ticker/{ticker_id}/monitoring/{session_id}"
  [Mode 3 reste manuel]
```

---

### `_trigger_sector_pulses(today)` — Mode 4, J+1

**Condition SQL :**
```sql
SELECT ce.*, ce.peer_ticker,
       t.company_type, th.thesis_json, th.id AS thesis_id
FROM calendar_events ce
JOIN tickers t ON t.id = ce.ticker_id
LEFT JOIN theses th ON th.id = ce.thesis_id AND th.status = 'active'
WHERE ce.scheduled_date = $1 - INTERVAL '1 day'
  AND ce.triggered = FALSE
  AND ce.pending_validation = FALSE
  AND ce.event_type = 'sector_pulse_peer'
```

**Contexte injecté :**
```
Ticker suivi : {ticker_id}
Pair qui publie : {peer_ticker}
Trigger : {label}
Mode demandé : 4

Hypothèses à scorer (-5 à +5) :
  H1 — {text}
  ...
```

**Actions après succès :**
```
INSERT monitoring_sessions (mode=4, result_json, calendar_event_id)
UPDATE calendar_events SET triggered = TRUE

Si action = store (score -2 à +2) :
  Pas de notification Slack

Si action = escalate_to_regime3 (score ≤ -3) :
  Slack : "⚠️ Sector Pulse négatif — {peer_ticker} → {ticker}\nScore : {sector_health_score}/5\n→ {URL session}"
  [Mode 3 reste manuel]
```

---

### `_trigger_conviction_reviews(today)` — Mode 3, Jour J

**Condition SQL :**
```sql
WHERE ce.scheduled_date = $1
  AND ce.triggered = FALSE
  AND ce.pending_validation = FALSE
  AND ce.event_type = 'conviction_review'
```

**Actions après succès :**
```
INSERT monitoring_sessions (mode=3, result_json, calendar_event_id)
UPDATE calendar_events SET triggered = TRUE

Slack : "🔍 Révision conviction — {ticker}\nDécision : {decision} | Conviction : {revised_conviction}/10\n→ {URL session}"
```

---

## 3. `backend/app/api/monitoring_v2.py` — modifications

### A. Fix normalisation hypothèses (critique)

Ajouter la fonction `_normalize_monitoring_result` et l'appeler après `agent.extract_json()` dans `create_and_run_session` :

```python
def _normalize_monitoring_result(parsed: dict, thesis_json: dict | None) -> dict:
    """
    Fusionne hypothesis_reviews[] (agent) avec les hypothèses de la thèse.
    Produit hypotheses_reviewed[] utilisable directement par la Page 5.
    """
    if not parsed:
        return parsed
    reviews_raw = parsed.get("hypothesis_reviews", [])
    if not reviews_raw or not thesis_json:
        return parsed

    reviews_by_id = {}
    for r in reviews_raw:
        if not isinstance(r, dict):
            continue
        hid = str(r.get("hypothesis_id") or r.get("id") or "")
        reviews_by_id[hid] = r
        reviews_by_id[hid.replace("H", "")] = r  # tolère "H1" et "1"

    thesis_hyps = thesis_json.get("hypotheses", [])
    hypotheses_reviewed = []
    for h in thesis_hyps:
        hid_full = str(h.get("id", ""))         # "H1"
        hid_num  = hid_full.replace("H", "")    # "1"
        review = reviews_by_id.get(hid_full) or reviews_by_id.get(hid_num) or {}
        hypotheses_reviewed.append({
            "id":                    hid_full,
            "text":                  h.get("text", ""),
            "weight":                h.get("weight", ""),
            "kpi_metric":            h.get("kpi_metric", ""),
            "kpi_unit":              h.get("kpi_unit", ""),
            "alert_threshold":       h.get("alert_threshold", {}),
            "invalidation_threshold":h.get("invalidation_threshold", {}),
            "status":                review.get("status", "unverified"),
            "observation":           review.get("observation", ""),
        })

    out = dict(parsed)
    out["hypotheses_reviewed"] = hypotheses_reviewed
    return out
```

Appel dans `create_and_run_session`, après `parsed = agent.extract_json(result["content"])` :
```python
# Charger thesis_json si thesis_id renseigné
thesis_json_for_norm = None
if data.thesis_id:
    async with get_db_session() as db:
        th = await db.fetchrow("SELECT thesis_json FROM theses WHERE id=$1", data.thesis_id)
        if th:
            thesis_json_for_norm = th["thesis_json"]

if parsed:
    parsed = _normalize_monitoring_result(parsed, thesis_json_for_norm)
```

### B. Ajout `calendar_event_id` dans `SessionCreate`

```python
class SessionCreate(BaseModel):
    ...
    calendar_event_id: Optional[int] = None
```

Dans l'INSERT `monitoring_sessions`, ajouter la colonne.

### C. Nouvel endpoint — sessions liées à un événement calendrier

Dans `calendar_v2.py` :

```python
@router.get("/{event_id}/sessions")
async def list_event_sessions(event_id: int):
    """Sessions monitoring liées à cet événement calendrier."""
    async with get_db_session() as db:
        rows = await db.fetch(
            """SELECT ms.*, t.name AS ticker_name
               FROM monitoring_sessions ms
               LEFT JOIN tickers t ON t.id = ms.ticker_id
               WHERE ms.calendar_event_id = $1
               ORDER BY ms.created_at ASC""",
            event_id,
        )
    return [_serialize(r) for r in rows]
```

---

## 4. `backend/app/main.py` — ajout job V1

```python
scheduler.add_job(
    _daily_check_v1,
    CronTrigger(hour=7, minute=5, timezone="Europe/Paris"),
    id="daily_check_v1", replace_existing=True,
)

async def _daily_check_v1():
    from app.calendar.event_router_v1 import EventRouterV1
    await EventRouterV1().process_daily_events()
```

Décalé à 7h05 pour ne pas entrer en collision avec le V0 à 7h00.

---

## 5. Page 5 — `/frontend/pages/ticker/[ticker_id]/monitoring/[session_id].js`

### Chargements au montage

```js
const [session, setSession] = useState(null)
const [messages, setMessages] = useState([])
const [linkedSessions, setLinkedSessions] = useState([])  // sessions du même calendar_event

// Chargement
const [sRes, mRes] = await Promise.all([
  fetch(`${API}/tickers/${ticker_id}/monitoring/${session_id}`),
  fetch(`${API}/monitoring/${session_id}/messages`),
])
const s = await sRes.json()
setSession(s)

if (s.calendar_event_id) {
  const lRes = await fetch(`${API}/calendar-v2/${s.calendar_event_id}/sessions`)
  if (lRes.ok) setLinkedSessions(await lRes.json())
}
```

La session mode 1 liée est : `linkedSessions.find(s => s.mode === 1)`.

### Layout par mode

#### Mode 1 — Checklist pré-event

Champs : `result_json.checklist_items[]` → `[{text, signal, detail}]`

```
┌─ Checklist de lecture — {trigger_label} ──────────────────┐
│  1. {text}                                                 │
│     ✓ Signal confirmation — {detail}   [vert]              │
│  2. {text}                                                 │
│     ✗ Signal alerte — {detail}         [rouge]             │
└───────────────────────────────────────────────────────────┘
[Bouton Archiver]
```

#### Mode 2 — Revue trimestrielle

Layout **deux colonnes** :

**Col gauche — Checklist J-2 (session mode 1 liée)**
- Si `linkedSessions` contient une session mode=1 → afficher ses `checklist_items`
- Sinon → "Aucun pré-event brief lié à cet événement"

**Col droite — Hypothèses post-monitoring**

Champ : `result_json.hypotheses_reviewed[]`

Pour chaque hypothèse :
```
[H1]  HIGH    ✅ CONFIRMED
Énoncé : "La croissance du backlog IT Services dépasse 8%..."
KPI : Backlog growth rate | Seuil alerte : 6% | Invalidation : 3%
Observation : "Backlog +9.2% en Q2 — au-dessus du seuil cible"
```

Codes couleur statut :
- `confirmed`  → emerald
- `neutral`    → gray
- `alert`      → amber
- `invalidated`→ red
- `unverified` → gray clair

**Bandeau récapitulatif sous les hypothèses :**
```
X confirmées | Y neutres | Z en alerte | W invalidées  [badge alert_level]
```

**Boutons d'action** (selon alert_level) :
- `REVIEW_REQUIRED` → bouton orange "Lancer Mode 5 — Routing"
- `CRITICAL` → bouton rouge "Lancer Mode 3 — Décision Review"

Ces boutons appellent `POST /tickers/{ticker_id}/monitoring` avec le mode correspondant et `calendar_event_id` de la session courante.

#### Mode 3 — Décision Review

Champs :
- `result_json.diagnostic` : "structural" | "conjunctural"
- `result_json.diagnostic_detail`
- `result_json.revised_conviction` : 0-10
- `result_json.decision` : reinforce | maintain | reduce_25 | reduce_50 | exit
- `result_json.munger_test_conclusion`
- `result_json.hypotheses_reviewed[]` (même layout que mode 2)

```
┌─ Diagnostic ──────────────────────────────────────────────┐
│  STRUCTUREL / CONJONCTUREL                                 │
│  {diagnostic_detail}                                       │
├─ Conviction révisée ───────────────────────────────────────┤
│  {revised_conviction}/10                                   │
├─ Test de Munger ───────────────────────────────────────────┤
│  {munger_test_conclusion}                                  │
├─ Décision ─────────────────────────────────────────────────┤
│  [REINFORCE] [MAINTAIN] [REDUCE 25%] [REDUCE 50%] [EXIT]  │
│  (badge coloré selon gravité)                              │
└───────────────────────────────────────────────────────────┘
[Hypothèses — même layout que mode 2]
```

#### Mode 4 — Sector Pulse

Champs :
- `result_json.sector_health_score` : -5 à +5
- `result_json.action` : "store" | "escalate_to_regime3"
- `result_json.sector_observations`
- `result_json.hypothesis_impacts[]` : `[{hypothesis_id, impact_direction, observation}]`

```
┌─ Score sectoriel ──────────────────────────────────────────┐
│  Pair : {peer_ticker}                                       │
│  Score : [jauge -5 ████░░ +5]  {sector_health_score}       │
│  {sector_observations}                                      │
├─ Impact par hypothèse ─────────────────────────────────────┤
│  H1  ↑ positif  "Résultats pair confirment reprise..."     │
│  H3  ↓ négatif  "Guidance cloud conservatrice..."          │
├─ Action ───────────────────────────────────────────────────┤
│  STORE / ESCALADE → RÉGIME 3                               │
│  [Si escalade : bouton "Lancer Mode 3"]                    │
└───────────────────────────────────────────────────────────┘
```

#### Mode 5 — Routing d'alerte

Champs :
- `result_json.routing_suggestion` : "thesis_agent_regime3" | "opportunity_agent"
- `result_json.rationale`
- `result_json.alert_summary`

```
┌─ Suggestion de routage ────────────────────────────────────┐
│  Résumé alerte : {alert_summary}                           │
│  Raisonnement : {rationale}                                │
│                                                            │
│  [Décision Review — Mode 3]  [Relancer analyse fresh]      │
└───────────────────────────────────────────────────────────┘
```

### Section commune — Mises à jour calendrier (Modes 2/3/4)

Champ : `result_json.calendar_events_update[]`

Format attendu de l'agent :
```json
[
  {
    "event_type": "quarterly_results",
    "label": "Résultats Q3 2026",
    "scheduled_date": "2026-10-22",
    "monitoring_mode": 2,
    "action": "create",
    "id": null
  }
]
```

Affichage : boutons Valider / Ignorer par item. Valider → `POST /calendar-v2` ou `PATCH /calendar-v2/{id}`. Aucun auto-insert backend.

### Chat agent (tous modes, en bas de page)

Composant `AgentChat` existant — inchangé.

---

## 6. Récapitulatif des fichiers à créer/modifier

| Fichier | Nature | Priorité |
|---|---|---|
| `backend/app/db/migrations/019_scheduler_v1.sql` | Nouveau | P0 |
| `backend/app/calendar/event_router_v1.py` | Nouveau | P0 |
| `backend/app/main.py` | Modification (ajout job 7h05) | P0 |
| `backend/app/api/monitoring_v2.py` | Modification (normalisation + calendar_event_id) | P1 |
| `backend/app/api/calendar_v2.py` | Modification (endpoint GET /{event_id}/sessions) | P1 |
| `frontend/pages/ticker/[ticker_id]/monitoring/[session_id].js` | Refonte | P2 |

---

## 7. Ce qui reste manuel (intentionnel)

| Action | Déclencheur | Raison |
|---|---|---|
| Mode 5 (routing) | Bouton Page 5 après REVIEW_REQUIRED | Qualification, pas d'exécution mécanique |
| Mode 3 (décision) après Mode 2 | Bouton Page 5 | Décision d'allocation, engagement utilisateur |
| Mode 3 (décision) après Mode 4 escalade | Bouton Page 5 | Idem |
| Validation `calendar_events_update` | Boutons Page 5 | Dates suggérées à vérifier par l'utilisateur |
| Sessions ad hoc | Depuis Page 5 ou Page 2 | Monitoring à la demande |

---

## 8. URL de base Slack

Les notifications Slack incluent des liens directs :
```
https://portfolio.jlmvpscode.duckdns.org/ticker/{ticker_id}/monitoring/{session_id}
```

La constante `PORTFOLIO_BASE_URL` doit être ajoutée dans `config.py` ou en dur dans `slack_webhook.py`.
