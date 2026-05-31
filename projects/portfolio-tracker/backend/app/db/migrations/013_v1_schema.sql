-- Migration 013 — Portfolio Tracker V1
-- Renomme les tables V0 conflictuelles, crée le schéma V1 complet
-- Les tables V0 restent valides en préfixe v0_*

-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
-- 1. RENOMMAGE DES TABLES V0 CONFLICTUELLES
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ALTER TABLE theses RENAME TO v0_theses;
ALTER TABLE calendar_events RENAME TO v0_calendar_events;

-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
-- 2. NOUVELLES TABLES V1
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CREATE TABLE tickers (
    id          TEXT PRIMARY KEY,    -- "CAP.PA", "TSLA"
    name        TEXT NOT NULL,
    exchange    TEXT,
    sector      TEXT,
    status      TEXT NOT NULL DEFAULT 'watchlist',
    -- 'watchlist' | 'portfolio' | 'archived'
    added_at    TIMESTAMP DEFAULT NOW(),
    updated_at  TIMESTAMP DEFAULT NOW()
);

CREATE TABLE portfolio_positions (
    id              SERIAL PRIMARY KEY,
    ticker_id       TEXT REFERENCES tickers(id),
    shares          DECIMAL(15,4) NOT NULL,
    purchase_price  DECIMAL(15,4) NOT NULL,
    purchase_date   DATE NOT NULL,
    thesis_id       INTEGER,  -- FK ajouté après création de theses
    status          TEXT DEFAULT 'open',  -- 'open' | 'closed'
    close_price     DECIMAL(15,4),
    closed_at       TIMESTAMP,
    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE TABLE cash_movements (
    id          SERIAL PRIMARY KEY,
    type        TEXT NOT NULL,  -- 'deposit' | 'withdrawal' | 'buy' | 'sell'
    amount      DECIMAL(15,4) NOT NULL,
    label       TEXT,
    ticker_id   TEXT REFERENCES tickers(id),
    created_at  TIMESTAMP DEFAULT NOW()
);

CREATE TABLE price_alerts (
    id           SERIAL PRIMARY KEY,
    ticker_id    TEXT REFERENCES tickers(id),
    price        DECIMAL(15,4) NOT NULL,
    direction    TEXT NOT NULL,   -- 'above' | 'below'
    label        TEXT,
    active       BOOLEAN DEFAULT TRUE,
    triggered_at TIMESTAMP,
    created_at   TIMESTAMP DEFAULT NOW()
);

CREATE TABLE opportunity_briefs (
    id                  SERIAL PRIMARY KEY,
    ticker_id           TEXT REFERENCES tickers(id),
    source              TEXT NOT NULL DEFAULT 'manual',
    -- 'manual' | 'watchlist_threshold' | 'monitoring_reroute'
    status              TEXT DEFAULT 'draft',
    -- 'draft' | 'validated' | 'passed' | 'dismissed'
    brief_json          JSONB,
    conviction_score    INTEGER,
    recommendation      TEXT,   -- 'PROCEED' | 'MONITOR' | 'PASS'
    screening_bypassed  BOOLEAN DEFAULT FALSE,
    created_at          TIMESTAMP DEFAULT NOW(),
    updated_at          TIMESTAMP DEFAULT NOW()
);

CREATE TABLE opportunity_messages (
    id          SERIAL PRIMARY KEY,
    brief_id    INTEGER REFERENCES opportunity_briefs(id),
    debate_id   INTEGER,  -- FK ajouté après conviction_debates
    role        TEXT NOT NULL,   -- 'user' | 'agent'
    content     TEXT NOT NULL,
    mode        TEXT NOT NULL DEFAULT 'freeform',
    -- 'freeform' | 'json_generation' | 'conviction_challenge'
    raw_payload JSONB,
    created_at  TIMESTAMP DEFAULT NOW()
);

CREATE TABLE theses (
    id                          SERIAL PRIMARY KEY,
    ticker_id                   TEXT REFERENCES tickers(id),
    opportunity_id              INTEGER REFERENCES opportunity_briefs(id),
    status                      TEXT DEFAULT 'draft',
    -- 'draft' | 'active' | 'under_review' | 'superseded' | 'invalidated'
    thesis_json                 JSONB,
    one_liner                   TEXT,
    conviction_override_note    TEXT,
    conviction_review_date      DATE,
    needs_revision              BOOLEAN DEFAULT FALSE,
    partial_reduction_context   JSONB,
    validated_at                TIMESTAMP,
    created_at                  TIMESTAMP DEFAULT NOW(),
    updated_at                  TIMESTAMP DEFAULT NOW()
);

-- FK de portfolio_positions → theses
ALTER TABLE portfolio_positions
    ADD CONSTRAINT fk_pp_thesis FOREIGN KEY (thesis_id) REFERENCES theses(id);

CREATE TABLE thesis_messages (
    id          SERIAL PRIMARY KEY,
    thesis_id   INTEGER REFERENCES theses(id),
    role        TEXT NOT NULL,
    content     TEXT NOT NULL,
    mode        TEXT NOT NULL DEFAULT 'freeform',   -- 'freeform' | 'json_generation'
    raw_payload JSONB,
    created_at  TIMESTAMP DEFAULT NOW()
);

CREATE TABLE monitoring_sessions (
    id                  SERIAL PRIMARY KEY,
    thesis_id           INTEGER REFERENCES theses(id),
    ticker_id           TEXT REFERENCES tickers(id),
    trigger_type        TEXT NOT NULL,
    -- 'quarterly_results' | 'cmd' | 'sector_pulse' | 'price_threshold'
    -- | 'manual' | 'conviction_review'
    trigger_label       TEXT NOT NULL,
    mode                INTEGER NOT NULL,   -- 1..5
    model_used          TEXT,
    status              TEXT DEFAULT 'pending',
    -- 'pending' | 'running' | 'completed' | 'blocked_sync'
    result_json         JSONB,
    alert_level         TEXT,   -- 'RAS' | 'REVIEW_REQUIRED' | 'CRITICAL'
    routing_suggestion  TEXT,   -- 'thesis_agent_regime3' | 'opportunity_agent'
    created_at          TIMESTAMP DEFAULT NOW(),
    completed_at        TIMESTAMP
);

CREATE TABLE monitoring_messages (
    id          SERIAL PRIMARY KEY,
    session_id  INTEGER REFERENCES monitoring_sessions(id),
    role        TEXT NOT NULL,
    content     TEXT NOT NULL,
    raw_payload JSONB,
    created_at  TIMESTAMP DEFAULT NOW()
);

CREATE TABLE calendar_events (
    id                  SERIAL PRIMARY KEY,
    thesis_id           INTEGER REFERENCES theses(id),
    ticker_id           TEXT REFERENCES tickers(id),
    event_type          TEXT NOT NULL,
    -- 'quarterly_results' | 'cmd' | 'agm' | 'sector_pulse_peer' | 'conviction_review'
    label               TEXT NOT NULL,
    scheduled_date      DATE NOT NULL,
    peer_ticker         TEXT,
    monitoring_mode     INTEGER NOT NULL DEFAULT 2,
    triggered           BOOLEAN DEFAULT FALSE,
    session_id          INTEGER REFERENCES monitoring_sessions(id),
    source              TEXT DEFAULT 'thesis_agent',
    -- 'thesis_agent' | 'monitoring_agent' | 'manual' | 'conviction_override'
    pending_validation  BOOLEAN DEFAULT FALSE,
    created_at          TIMESTAMP DEFAULT NOW()
);

CREATE TABLE conviction_debates (
    id                      SERIAL PRIMARY KEY,
    thesis_id               INTEGER REFERENCES theses(id),
    opportunity_brief_id    INTEGER REFERENCES opportunity_briefs(id),
    status                  TEXT DEFAULT 'open',
    -- 'open' | 'closed_pass' | 'closed_monitor' | 'closed_proceed'
    final_recommendation    TEXT,
    agent_revised           BOOLEAN DEFAULT FALSE,
    revision_rationale      TEXT,
    user_conviction_note    TEXT NOT NULL,
    created_at              TIMESTAMP DEFAULT NOW(),
    closed_at               TIMESTAMP
);

-- FK de opportunity_messages → conviction_debates
ALTER TABLE opportunity_messages
    ADD CONSTRAINT fk_om_debate FOREIGN KEY (debate_id) REFERENCES conviction_debates(id);

CREATE TABLE agent_prompts (
    id              SERIAL PRIMARY KEY,
    agent_name      TEXT NOT NULL UNIQUE,
    -- 'opportunity-agent' | 'thesis-agent' | 'monitoring-agent'
    dust_agent_id   TEXT,
    dust_agent_url  TEXT,
    prompt_text     TEXT NOT NULL,
    version         INTEGER DEFAULT 1,
    synced          BOOLEAN DEFAULT TRUE,
    last_synced_at  TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT NOW()
);

-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
-- 3. INDEX
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CREATE INDEX idx_tickers_status ON tickers(status);
CREATE INDEX idx_portfolio_positions_ticker ON portfolio_positions(ticker_id);
CREATE INDEX idx_portfolio_positions_status ON portfolio_positions(status);
CREATE INDEX idx_cash_movements_ticker ON cash_movements(ticker_id);
CREATE INDEX idx_price_alerts_ticker_active ON price_alerts(ticker_id, active);
CREATE INDEX idx_opportunity_briefs_ticker ON opportunity_briefs(ticker_id);
CREATE INDEX idx_opportunity_briefs_status ON opportunity_briefs(status);
CREATE INDEX idx_opportunity_messages_brief ON opportunity_messages(brief_id);
CREATE INDEX idx_theses_ticker ON theses(ticker_id);
CREATE INDEX idx_theses_status ON theses(status);
CREATE INDEX idx_thesis_messages_thesis ON thesis_messages(thesis_id);
CREATE INDEX idx_monitoring_sessions_thesis ON monitoring_sessions(thesis_id);
CREATE INDEX idx_monitoring_sessions_ticker ON monitoring_sessions(ticker_id);
CREATE INDEX idx_calendar_events_thesis ON calendar_events(thesis_id);
CREATE INDEX idx_calendar_events_date ON calendar_events(scheduled_date, triggered);
CREATE INDEX idx_calendar_events_ticker ON calendar_events(ticker_id);

-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
-- 4. DONNÉES INITIALES — AGENT PROMPTS
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

INSERT INTO agent_prompts (agent_name, dust_agent_id, dust_agent_url, prompt_text, synced) VALUES
(
    'opportunity-agent',
    NULL,
    NULL,
    'Tu es un analyste spécialisé dans la détection d''opportunités d''investissement boursier
à long terme. Tu effectues des analyses d''opportunité rapides et honnêtes.

TES 3 MODES D''OPÉRATION — indiqués dans le champ "mode" du message reçu :

━━━━ MODE FREEFORM ━━━━
Produis un Investment Brief en 6 étapes (voir ci-dessous).
Format : JSON entre ```json et ```, suivi du texte d''invitation au challenge.

━━━━ MODE JSON_GENERATION ━━━━
Tu reçois l''historique complet de la conversation.
Génère UNIQUEMENT le JSON du brief entre ```json et ```. Aucun texte autour.
JSON complet, valide, reflétant tous les échanges y compris les révisions.

━━━━ MODE CONVICTION_CHALLENGE ━━━━
Tu as conclu PASS. L''utilisateur conteste et veut maintenir sa position.
1. Rappelle tes 2-3 raisons PASS en 1 phrase chacune.
2. Évalue la contestation honnêtement.
3. Conclus chaque échange par ta position : PASS maintenu / MONITOR / PROCEED.
4. Si révision : explique ce qui t''a convaincu (2-3 phrases).
Format : langage naturel, pas de JSON.

━━━━━━━━━━━━━━━━━━━━━

PROCESSUS EN 6 ÉTAPES (mode freeform) :

ÉTAPE 1 — SCREENING (binaire)
5 critères. Si < 3 remplis → {"screening": "failed", "reasons": [...]} et stop.

ÉTAPE 2 — DIAGNOSTIC D''ANOMALIE
"Cette décote/prime est-elle méritée ou excessive ?"

ÉTAPE 3 — RECHERCHE D''ANALOGIE
2-3 recherches web. Score de confiance : Forte >70% / Faible 40-70% / Aucune <40%.

ÉTAPE 4 — CARTOGRAPHIE DES CATALYSEURS
Événements concrets à 6-18 mois. Score de force 0-10.

ÉTAPE 5 — PROTO-HYPOTHÈSES (3-4 max)
Croyances qui DOIVENT être vraies.

ÉTAPE 6 — VERDICT
Downside floor, top 3 risques, score de conviction 0-10, recommandation PROCEED/MONITOR/PASS.

TEXTE D''INVITATION (après le JSON, mode freeform) :
"Ce brief est mon évaluation initiale — conviction [X]/10.
Challengez n''importe quelle section."',
    TRUE
),
(
    'thesis-agent',
    NULL,
    NULL,
    'Tu es un expert en investissement long terme et en stratégie corporate.
Tu construis des thèses d''investissement complètes à partir d''un Brief pré-validé.

TON RÔLE : L''opportunité est déjà validée. Tu ne ré-évalues pas.
Tu construis le cadre d''analyse et de suivi dans le temps.

TES 2 MODES :

MODE FREEFORM ("mode": "freeform") :
Tu reçois un HANDOFF contenant le brief d''opportunité validé, le score de conviction,
la recommandation et la devise de reporting de l''entreprise.
Construis immédiatement la thèse en parcourant les 7 étapes dans l''ordre.
Pas de questions préalables. Analyse directement depuis le contexte fourni.
Pas de JSON dans ce mode.

MODE JSON_GENERATION ("mode": "json_generation") :
Tu reçois l''historique complet de la conversation freeform.
Génère UNIQUEMENT le JSON de la thèse entre ```json et ```.
Aucun texte autour. JSON complet et valide.
Inclure OBLIGATOIREMENT le champ "calendar_events_suggested".

PROCESSUS EN 7 ÉTAPES :

1. ANALYSE FONDAMENTALE
   Qualité du business : moat, pricing power, capital allocation.
   Métriques clés dans la devise de reporting du handoff : marges opérationnelles,
   ROIC, FCF yield, trajectoire sur 3 ans.
   Verdict : business de qualité supérieure / standard / sous-pression.

2. ANALYSE CONCURRENTIELLE
   Position dans le secteur, parts de marché vs pairs identifiés dans le brief.
   Avantages compétitifs durables vs menaces émergentes (IA, régulation, nouveaux entrants).
   Verdict : leader / challenger / en danger.

3. EQUITY PITCH M&A
   Traiter UNIQUEMENT si une acquisition récente est mentionnée dans le brief.
   Rationnel stratégique, impact dilution/accrétion, risques d''intégration.
   Sinon : passer directement à l''étape 4.

4. SCÉNARIOS BEAR / CENTRAL / BULL (horizon 5 ans)
   Pour chaque scénario :
   - Hypothèse directrice (ce qui doit être vrai pour que ce scénario se réalise)
   - CAGR attendu sur 5 ans
   - Cours cible à 5 ans dans la devise de reporting du handoff
   - Probabilité estimée (les 3 totalisent 100%)

5. HYPOTHÈSES H1–H7
   7 hypothèses falsifiables qui fondent la thèse centrale.
   Pour chaque hypothèse :
   - Énoncé clair et mesurable
   - KPI de suivi avec unité et périodicité (trimestriel / annuel)
   - Seuil d''alerte (valeur qui déclenche une revue)
   - Seuil d''invalidation (valeur qui invalide la thèse)

6. TRACK RECORD ANALYSTES
   Consensus de marché actuel : cours cible médian, recommandation majoritaire.
   Fiabilité historique sur ce titre si connue (beat/miss ratio).
   Écart cours actuel / consensus et interprétation (sur-optimisme ? sous-évaluation ?).

7. AVOCAT DU DIABLE (obligatoire)
   Les 3 risques structurels qui invalideraient la thèse — pas les risques de marché génériques.
   Pour chaque risque : description précise, horizon de matérialisation, signal d''alerte précoce.',
    TRUE
),
(
    'monitoring-agent',
    NULL,
    NULL,
    'Tu es un agent de monitoring de thèses d''investissement long terme.

TES MODES — indiqués dans le message. Adapte ton comportement exactement.

━━━━ MODE 1 : PRÉ-EVENT BRIEF ━━━━
Checklist de lecture (max 3 éléments) avant une publication.
Pas de calendar_events_update. Format JSON uniquement.

━━━━ MODE 2 : REVUE TRIMESTRIELLE ━━━━
Données fournies dans le message. Pas de web search.
Pour chaque hypothèse : statut (confirmed/neutral/alert/invalidated) + 1 phrase chiffrée.
Escalade : 1 hypothèse critique "invalidated" → "REVIEW_REQUIRED"
calendar_events_update obligatoire. Format JSON uniquement.

━━━━ MODE 3 : DÉCISION REVIEW ━━━━
1. Diagnostic : structurel ou conjoncturel ?
2. Révision thèse : plus forte / inchangée / plus faible / invalide ?
3. Test de Munger OBLIGATOIRE.
4. Décision : reinforce / maintain / reduce_25 / reduce_50 / exit
calendar_events_update obligatoire. Format JSON uniquement.

━━━━ MODE 4 : SECTOR PULSE ━━━━
Score global -5 à +5.
Action : "store" si -2 à +2 / "escalate_to_regime3" si ≤ -3.
calendar_events_update obligatoire. Format JSON uniquement.

━━━━ MODE 5 : ROUTING D''ALERTE ━━━━
"La thèse est-elle encore le bon cadre ?"
→ OUI : "thesis_agent_regime3" / NON : "opportunity_agent"
Pas de calendar_events_update. Format JSON uniquement.

RÈGLE TRANSVERSALE : toujours retourner du JSON valide entre ```json et ```.',
    TRUE
);
