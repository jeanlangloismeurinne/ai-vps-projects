---
id: roadmap-1786304902922
status: spec-ready
created: 2026-08-09T00:00:00.000000
project: portfolio-tracker
---

## Refonte du flux d'investissement — processus de fonds professionnel

### Direction / Feature (utilisateur)

Révision profonde du flux d'investissement de bout en bout. Carte blanche pour restructurer les agents, leur nombre, leurs fonctions, les données intégrées, et le processus complet. Objectif : un flux aussi professionnel que possible, inspiré d'un vrai fonds d'investissement. L'ambition sera dégradée selon les données accessibles et leur coût.

### Contraintes connues

- FMP free tier cassé (Legacy Endpoint error) — seuls yfinance + FRED sont disponibles
- yfinance fournit 184 champs via `.info` + balance sheet / financials / cashflow (3 ans)
- Pas d'accès gratuit aux transactions insiders individuelles ni à l'historique 10 ans de financials
- Contrainte budget Dust : 5 USD/mois — les agents coûteux ne peuvent pas être appelés à la légère
- Le système monitoring (5 modes) et la page décision sont bien construits → à conserver

---

## Spec générée

### 1. Audit du flux actuel — faiblesses structurelles

Le flux V1 actuel se décompose en :
```
Watchlist → (Opportunité optionnelle) → Thèse → Position → Monitoring → Décision
```

**Problèmes fondamentaux :**

| # | Problème | Impact |
|---|---|---|
| P1 | L'étape opportunité est bypassable (`opportunity_id` optional) | On entre en thèse sans screening |
| P2 | `recommendation = PASS` sans enforcement — ne bloque rien | Le vote de l'agent est ignoré |
| P3 | Aucune phase de **recherche approfondie** entre screening et thèse | Le thesis-agent travaille sans une base documentaire solide |
| P4 | Le brief_json ne contient pas de valeur intrinsèque, moat, ni cercle de compétence | Aucune logique de valorisation dans le processus |
| P5 | L'agent ne voit pas le portefeuille — impossible d'évaluer le coût d'opportunité | Chaque décision est prise en silo |
| P6 | Aucun pré-mortem obligatoire avant validation de position | Les biais de confirmation ne sont pas challengés |
| P7 | Pas de logique de sizing de position | L'allocation est décidée hors-système |
| P8 | Pas de revue annuelle structurée de thèse | Les thèses vieillissent sans réévaluation |

---

### 2. Référentiel cible — processus d'un fonds valeur long terme

Un fonds de type Sequoia, Fundsmith, ou Nomad Investment Partnership suit ce processus :

**Phase A — Sourcing** : génération d'idées (screeners quantitatifs, thèmes sectoriels, pairs, alertes news)

**Phase B — Triage** : filtrage rapide (≤ 30 min) → GO / NO-GO
- Cercle de compétence : comprend-on ce business ?
- Santé financière rapide : rentabilité, bilan, cash-flow
- Valorisation grossière : est-ce dans la zone de prix intéressante ?

**Phase C — Recherche approfondie** (2-4h dans un fonds réel, ici guidée par agent)
- Analyse du modèle économique : comment l'entreprise gagne-t-elle de l'argent ?
- Fossé concurrentiel (moat) : pourquoi cette position est-elle défendable dans 10 ans ?
- Analyse financière structurée : ROIC, FCF, levier, qualité des résultats
- Management : track record d'allocation du capital, incentives, honnêteté
- Analyse sectorielle : dynamiques du secteur, position vs. pairs
- Valeur intrinsèque : fourchette DCF / multiples normalisés + marge de sécurité

**Phase D — Construction de thèse** (hypothèses falsifiables, sizing, catalyseurs)

**Phase E — Comité d'investissement / conviction challenge** (pré-mortem obligatoire)

**Phase F — Entry & Position** (sizing documenté, règle d'entrée)

**Phase G — Monitoring continu** (existant, bien construit)

**Phase H — Décision de sortie** (existant) + post-mortem d'apprentissage

---

### 3. Nouveau flux proposé — 4 phases IA

```
[PHASE 1 — SCREENING]          ~3 min | screening-agent (nouveau)
        ↓ GO
[PHASE 2 — RECHERCHE]          ~15-30 min | research-agent (nouveau)
        ↓ research_memo validé
[PHASE 3 — THÈSE]              ~15 min | thesis-agent (existant, renforcé)
        ↓ pré-mortem intégré
[PHASE 4 — VALIDATION]         → portfolio_position
        ↓
[MONITORING]                   modes 1-6 (existant + mode 6 nouveau)
        ↓
[DÉCISION / SORTIE]            existant + post-mortem
```

---

### 4. Architecture des agents — nouveau schéma

#### 4.1 screening-agent (NOUVEAU — remplace l'opportunity-agent en mode freeform initial)

**Rôle** : Triage rapide structuré — décision GO / NO-GO avec justification claire.
**Modèle recommandé** : `gemini-2.5-flash` (rapide, économique)
**Input** : données M1 quantitatives (yfinance) + note de l'utilisateur (pourquoi ce ticker)

**Output JSON — `screening_json`** :
```json
{
  "cercle_competence": {
    "score": 3,
    "note": "Business model compréhensible (cloud infra), mais pricing power du segment IA opaque"
  },
  "sante_financiere": {
    "score": 4,
    "fcf_positif": true,
    "levier_acceptable": true,
    "marge_operationnelle_pct": 28,
    "note": "FCF yield 4.2%, dette nette négative — bilan sain"
  },
  "valorisation_grossiere": {
    "score": 2,
    "zone": "chère",
    "pe_ntm": 32,
    "note": "P/E NTM de 32 pour une croissance de 12% — prime élevée vs. secteur"
  },
  "verdict": {
    "go": true,
    "score_global": 9,
    "motif_pass": null,
    "points_attention": ["valorisation tendue", "segment IA peu lisible"]
  }
}
```

**Règle verdict GO/NO-GO** :
- NO-GO automatique si : `cercle_competence.score < 2` OU `sante_financiere.fcf_positif = false` ET `levier_acceptable = false`
- GO avec réserves si : `valorisation_grossiere.zone = "chère"` → passer en recherche avec flag
- Dans tous les cas, le GO/NO-GO est une recommandation — l'utilisateur valide

**Ce qui change vs. l'opportunity-agent actuel** :
- Le screening est court (≤ 3 min pour l'IA) et structuré — pas un dialogue libre
- Le GO est enforced : on ne peut pas créer une research_memo sans screening GO
- Le mode freeform de l'opportunity-agent actuel migre vers la Phase 2 (research-agent)

---

#### 4.2 research-agent (NOUVEAU — le plus important du redesign)

**Rôle** : Produire un research memo structuré de qualité institutionnelle — le document de référence pour toute la durée de vie de l'investissement.
**Modèle recommandé** : `claude-opus-4-8` ou `claude-sonnet-4-6` (profondeur analytique requise)
**Mode de fonctionnement** : hybride — freeform en premier (dialogue avec l'utilisateur pour collecter le contexte qualitatif), puis json_generation pour la crystallisation

**Particularité** : c'est le seul agent avec lequel l'utilisateur a un **vrai dialogue** pour construire la compréhension. L'agent pose des questions, l'utilisateur répond, et ensemble ils construisent la recherche.

**Input injecté automatiquement** :
- M1 quantitatif complet (yfinance: prix, valorisation, marges, 3 ans financials)
- Short interest + insider ownership (yfinance.info : `heldPercentInsiders`, `shortPercentOfFloat`, `shortRatio`)
- Balance sheet : net debt, working capital, invested capital (yfinance.balance_sheet)
- Contexte portefeuille actif (positions + leur performance)
- Température de marché (FRED)

**Output JSON — `research_memo_json`** :
```json
{
  "business_model": {
    "description": "Éditeur de logiciels SaaS B2B pour la gestion RH...",
    "drivers_revenus": ["licences annuelles", "services professionnels", "marketplace"],
    "modele_pricing": "per-seat + modules add-on",
    "qualite_revenus": "high",
    "note_qualite": "90% de revenus récurrents, NRR > 110% — revenus très prévisibles"
  },
  "moat": {
    "score": 4,
    "type": ["switching_costs", "network_effects"],
    "description": "Intégration profonde dans les SIRH clients — coût de migration estimé à 18 mois de projet. Effet réseau modéré via marketplace de partenaires.",
    "durabilite": "forte sur 5 ans, incertaine sur 10 ans (cloud natif concurrent)"
  },
  "analyse_financiere": {
    "roic_estime_pct": 18,
    "methode_roic": "NOPAT / Invested Capital — approximé depuis données yfinance",
    "fcf_yield_pct": 4.2,
    "croissance_revenue_3y_cagr_pct": 14,
    "dette_nette_ebitda": -0.3,
    "qualite_earnings": "high",
    "points_vigilance": ["capex en hausse 2025", "dilution options ~2% par an"]
  },
  "management": {
    "score": 3,
    "insiders_pct": 1.6,
    "note_insiders": "Faible — fondateur a cédé la majorité de ses parts en 2023",
    "track_record_capital": "Bonne croissance organique, acquisitions disciplinées",
    "risques_comportement": ["rémunération CEO élevée vs. benchmarks sectoriels"]
  },
  "analyse_sectorielle": {
    "dynamique": "favorable",
    "croissance_marche_pct": 12,
    "position_concurrentielle": "leader sur le segment mid-market européen",
    "menaces": ["SAP modernisation", "Workday expansion géographique"]
  },
  "valeur_intrinseque": {
    "methode": "FCF yield normalisé + croissance conservatrice 10%/an + exit multiple 18x",
    "fourchette_basse": 95,
    "fourchette_centrale": 115,
    "fourchette_haute": 140,
    "prix_actuel": 108,
    "marge_securite_centrale_pct": -6,
    "zone": "juste_prix",
    "note": "Au prix actuel, valorisation tendue mais justifiée par la qualité. Attendre une correction de 10-15% pour une marge de sécurité confortable."
  },
  "opportunity_cost": {
    "note": "Comparé à NVDA (thèse active, +23%, moat tech fort), cette opportunité offre moins de croissance mais plus de prévisibilité. Adapté si l'objectif est de diversifier hors tech hardware.",
    "verdict": "complémentaire au portefeuille actuel"
  },
  "verdict_recherche": {
    "recommandation": "PROCEED_AVEC_CONDITIONS",
    "conditions": ["Attendre prix < 98 pour marge de sécurité positive", "Confirmer tendance capex Q3 2026"],
    "conviction": 7
  }
}
```

**Champs `recommandation` possibles** :
- `PROCEED` — thesis à lancer maintenant
- `PROCEED_AVEC_CONDITIONS` — proceed mais avec conditions explicites (ex: attendre prix cible)
- `PASSER` — ne pas investir, motif documenté
- `SURVEILLER` — intéressant mais pas maintenant, remettre en watchlist avec alerte

---

#### 4.3 thesis-agent (EXISTANT — renforcé)

**Rôle** : Construction de la thèse d'investissement depuis le research_memo.
**Modèle** : `claude-sonnet-4-6` (inchangé)

**Changements par rapport à V1** :
1. L'input inclut le `research_memo_json` complet (handoff enrichi)
2. Nouveaux champs dans `thesis_json` :
   - `position_sizing` : `pct_portefeuille_cible`, `pct_max`, `justification`
   - `pre_mortem` : liste des scénarios d'échec les plus probables (l'agent joue le diable)
   - `conditions_entree` : prix limite, déclencheurs d'achat
   - `valeur_intrinseque` : reprise depuis research_memo avec mise à jour si nécessaire
3. **Pré-mortem obligatoire** : le thesis-agent génère automatiquement un bloc `pre_mortem` avec les 3 scénarios d'échec les plus crédibles AVANT que l'utilisateur puisse valider. L'utilisateur doit acquitter explicitement ce bloc.

**`position_sizing` — logique de sizing** :
```
Base : [conviction_score / 10] × [marge_securite / 20%] × [max_concentration]
Ajusté par : température de marché (×0.7 si "hot"), liquidité du titre, corrélation portefeuille
```
L'agent calcule une fourchette recommandée et l'utilisateur peut la modifier avec justification.

---

#### 4.4 monitoring-agent (EXISTANT — ajout mode 6)

**Mode 6 — Revue Annuelle de Thèse** (nouveau) :
- Déclencheur : calendrier — 1 an après validation de position (et chaque année suivante)
- Comportement : relecture complète de la thèse originale + research_memo + toutes les sessions de monitoring de l'année → verdict global (CONFIRMER / RÉDUIRE / SORTIR / RENFORCER)
- Output : mise à jour de `thesis_json.hypotheses` + recommandation de sizing
- Modèle : `claude-sonnet-4-6` (profondeur requise)

---

#### 4.5 debate-agent (renommage de l'opportunity-agent en mode conviction_challenge)

L'agent de débat (option C de la page décision) reste inchangé dans son fonctionnement. Renommage conceptuel uniquement pour clarifier les rôles.

---

### 5. Données — inventaire et réalisme

#### 5.1 Disponibles aujourd'hui (sans coût additionnel)

| Donnée | Source | Utilisation dans le nouveau flux |
|---|---|---|
| Prix, valorisation (P/E, EV/EBITDA, P/B) | yfinance.info | Screening + Recherche |
| Marges (gross, operating, EBITDA, net) | yfinance.info | Screening (santé financière) |
| ROE, ROA | yfinance.info | Screening + ROIC approximation |
| Debt/Equity, Total Debt, Net Debt | yfinance.info + balance_sheet | Screening + Recherche |
| Insider ownership % | yfinance.info (`heldPercentInsiders`) | Recherche (management) |
| Short interest, short ratio | yfinance.info | Recherche (positionnement marché) |
| 3 ans financials (Revenue, OpInc, Net Inc, FCF) | yfinance.financials + cashflow | Recherche (analyse financière) |
| Balance sheet (Invested Capital, Working Capital) | yfinance.balance_sheet | ROIC calculation |
| Prix historique 1y/5y/max | yfinance.history | Screening + Recherche |
| Earnings dates | yfinance.calendar | Monitoring |
| Buffett indicator, CAPE | FRED | Contexte macro (température) |

#### 5.2 Manquants mais récupérables (effort de développement, sans coût API)

| Donnée | Comment | Priorité |
|---|---|---|
| ROIC calculé sur 5 ans | Calculer depuis yfinance (NOPAT / Invested Capital) sur les 5 ans de historique | Haute |
| Capital allocation trend (capex/FCF, dividendes, buybacks) | Calculer depuis yfinance.cashflow 5 ans | Haute |
| Insider ownership trend | yfinance.insider_transactions (si disponible dans la version installée) | Moyenne |
| Newsflow récent | RSS Google News déjà dans m2_events.py | Déjà disponible |
| Ratios sectoriels pairs | Calculer depuis tickers en watchlist/portefeuille | Moyenne |

#### 5.3 Nécessitent une décision de coût

| Donnée | Source | Coût estimé | Valeur ajoutée |
|---|---|---|---|
| Historique financials 10 ans | FMP Starter ($29/mois) ou Simplywall.st API | ~30€/mois | Élevée — ROIC long terme fiable |
| Insider transactions individuelles | FMP Starter ou Insider Monkey API | ~30€/mois | Moyenne — proxy via ownership% suffisant |
| Transcriptions earnings calls | Motley Fool Transcripts API, Seeking Alpha | ~20€/mois | Élevée — qualité management |
| Données alternat. (web traffic, app downloads) | SimilarWeb, Sensor Tower | >100€/mois | Trop cher pour phase 1 |
| Rating analystes consensus détaillé | FMP Starter / Refinitiv | ~30€/mois | Moyenne — déjà dans M1 partiellement |

**Recommandation** : démarrer avec yfinance étendu (5 ans historique + ROIC calculé + capital allocation). Si la démarche prend de l'ampleur → FMP Starter à $29/mois. Éviter les sources > $50/mois pour l'instant.

---

### 6. Modifications base de données

#### 6.1 Nouvelle table `screenings`

```sql
CREATE TABLE screenings (
    id              SERIAL PRIMARY KEY,
    ticker_id       TEXT REFERENCES tickers(id),
    screening_json  JSONB NOT NULL DEFAULT '{}',
    verdict         TEXT NOT NULL,  -- 'GO' | 'NO-GO'
    score_global    INT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);
```

#### 6.2 Nouvelle table `research_memos`

```sql
CREATE TABLE research_memos (
    id              SERIAL PRIMARY KEY,
    ticker_id       TEXT REFERENCES tickers(id),
    screening_id    INT REFERENCES screenings(id),
    memo_json       JSONB NOT NULL DEFAULT '{}',
    recommandation  TEXT,  -- 'PROCEED' | 'PROCEED_AVEC_CONDITIONS' | 'PASSER' | 'SURVEILLER'
    conviction      INT,
    status          TEXT NOT NULL DEFAULT 'draft',  -- 'draft' | 'validated'
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE TABLE research_messages (
    id              SERIAL PRIMARY KEY,
    memo_id         INT REFERENCES research_memos(id),
    role            TEXT NOT NULL,  -- 'user' | 'agent'
    content         TEXT NOT NULL,
    tokens_in       INT,
    tokens_out      INT,
    cost_usd        FLOAT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
```

#### 6.3 Modifications `theses`

```sql
ALTER TABLE theses
    ADD COLUMN research_memo_id INT REFERENCES research_memos(id),
    ADD COLUMN pre_mortem_acked BOOL DEFAULT FALSE,
    ADD COLUMN position_sizing_pct FLOAT,
    ADD COLUMN conditions_entree JSONB DEFAULT '{}';
```

#### 6.4 Migration des données existantes

- Les `opportunity_briefs` existants sont conservés (table inchangée)
- Les thèses existantes ont `research_memo_id = NULL` — comportement identique à V1
- La gate obligatoire (Phase 1+2 avant thèse) ne s'applique qu'aux nouveaux flux

#### 6.5 Prochaine migration : `023_v2_research_flow.sql`

---

### 7. Modifications frontend — nouvelles pages et composants

#### 7.1 Nouvelles pages

| Page | URL | Description |
|---|---|---|
| Screening | `/ticker/[id]/screening/new` | Formulaire court (note utilisateur) + lancement screening-agent + résultat GO/NO-GO |
| Research | `/ticker/[id]/research/[memo_id]` | Interface de recherche collaborative (chat + memo structuré côte à côte) |

#### 7.2 Modifications pages existantes

- **watchlist-v2.js** : bouton "Analyser" → redirige vers `/screening/new` (plus vers `/opportunity/new`)
- **thesis/[thesis_id].js** : nouveau panneau "Pré-mortem" à acquitter avant "Valider la thèse"
- **portfolio.js** : afficher le sizing cible vs. sizing actuel par position

#### 7.3 Nouveaux composants

| Composant | Description |
|---|---|
| `ScreeningResultCard.js` | Affiche les 3 scores (cercle compétence, santé, valorisation) + verdict GO/NO-GO |
| `ResearchMemoEditor.js` | Analogue à `ThesisEditorV2.js` mais pour le research_memo — sections : business model, moat, financials, management, valeur intrinsèque |
| `PreMortemPanel.js` | Panneau affichant les 3 scénarios d'échec générés — bouton "J'ai pris connaissance" obligatoire |
| `PositionSizingWidget.js` | Slider sizing avec justification — min/recommended/max + input libre |

---

### 8. Nouvelles API REST

```
# Screening
POST   /tickers/{id}/screenings          Créer + exécuter screening → screening_json
GET    /tickers/{id}/screenings          Liste
GET    /tickers/{id}/screenings/{id}     Détail

# Research
POST   /tickers/{id}/research            Créer memo (requiert screening_id GO)
GET    /tickers/{id}/research            Liste
GET    /tickers/{id}/research/{memo_id}  Détail + messages
POST   /research/{memo_id}/chat          Message → research-agent (freeform)
POST   /research/{memo_id}/refresh-json  json_generation → update memo_json
POST   /research/{memo_id}/validate      Marquer validated — débloque création thèse

# Thèse (modifications)
POST   /tickers/{id}/theses              research_memo_id devient requis (sauf legacy import)
POST   /theses/{id}/ack-pre-mortem       Acquitter le pré-mortem → permet validate
```

---

### 9. Parcours utilisateur V2 de bout en bout

```
[WATCHLIST]
Ajout ticker → tickers.status = 'watchlist'
         ↓ clic "Analyser" 
[SCREENING /ticker/:id/screening/new]
Note rapide utilisateur + M1 auto-injectées
→ screening-agent → screening_json (GO/NO-GO)
         ↓ si GO
[RESEARCH /ticker/:id/research/:memo_id]
Chat libre avec research-agent (3-5 échanges max) 
→ json_generation → research_memo_json
→ Validation utilisateur
         ↓ research validé + recommandation PROCEED
[THÈSE /ticker/:id/thesis/:id]
Handoff research_memo → thesis-agent
→ thesis_json + pre_mortem auto-généré
→ Pré-mortem affiché → utilisateur acquitte
→ Valider la thèse (maintenant possible)
         ↓
[PORTFOLIO /portfolio]
Position enregistrée avec sizing documenté
         ↓
[MONITORING /ticker/:id/monitoring/:id]
Modes 1-5 existants + Mode 6 (revue annuelle)
         ↓
[DÉCISION /ticker/:id/decision/:thesis_id]
4 options existantes (Maintenir / Réduire / Sortir / Renforcer)
         ↓ Sortir
[POST-MORTEM]
Déclenchement automatique (stub existant dans portfolio/post_mortem.py)
```

---

### 10. Plan de migration — V1 → V2

**Stratégie : activation progressive**

Le nouveau flux est activé uniquement pour les nouveaux tickers. Les thèses existantes (NVDA, CAP, TSLA, etc.) restent dans le flux V1 — leur monitoring continue normalement.

**Étapes** :
1. Migration DB `023_v2_research_flow.sql` — nouvelles tables, colonnes theses
2. Backend : screening-agent + research-agent + nouvelles API
3. Frontend : pages Screening + Research + modifications watchlist + pré-mortem
4. Config Dust : créer les 2 nouveaux agents (screening-agent, research-agent) + sync admin
5. Test sur 1 ticker fictif
6. Mise en production

**Compatibilité** :
- `POST /tickers/{id}/theses` : `research_memo_id` requis si ticker créé après la migration. Pour les anciens tickers, comportement V1 maintenu (`opportunity_id` optionnel).
- Discriminant : `tickers.created_at > migration_date` (ou flag `v2_flow: bool` sur tickers)

---

### 11. Dégradations acceptables (V1 → V2 réaliste)

| Fonctionnalité | Version idéale | Dégradation acceptable |
|---|---|---|
| Analyse management | Transcriptions earnings + proxy filings | Estimation par l'agent depuis insider ownership % + track record qualitatif (chat) |
| ROIC historique 10 ans | FMP Starter | ROIC approximé sur 3 ans depuis yfinance |
| Valeur intrinsèque | Modèle DCF complet | Fourchette estimée par l'agent avec méthodologie explicite |
| Capital allocation 10 ans | FMP Starter | 3 ans yfinance + qualitatif agent |
| Newsflow structuré | NewsAPI / Refinitiv | RSS Google News existant (m2_events.py) |
| Short selling analysis | Données S3 Partners ($500/mois) | Short ratio + short % float yfinance (déjà disponible) |

---

### Tickets créés

*(à créer lors de la session d'implémentation — ce roadmap est au stade spec-ready)*
