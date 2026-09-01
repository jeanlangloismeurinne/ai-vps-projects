-- ============================================================================
-- 032_v2_exit_calibration_debate.sql — LOT 9 : sortie, calibration, débat
--
-- POURQUOI CETTE MIGRATION EXISTE (chaque point est une VÉRIFICATION en base,
-- pas une supposition — le lot 8 a montré ce que coûte l'inverse) :
--
--   1. conviction_debates_thesis_id_fkey FOREIGN KEY (thesis_id) REFERENCES theses(id)
--      + user_conviction_note NOT NULL
--      Le débat V1 pointe la table V1 et exige une note d'UX V1. Un débat sur la
--      thèse V2 #4 n'a littéralement aucune ligne où s'accrocher. Or un débat est
--      un JUGEMENT : convention #34, les jugements sont disjoints. D'où
--      `conviction_debates_v2`. C'est le défaut du lot 8 (monitoring_sessions),
--      à l'identique, sur une table qu'on aurait pu croire neutre.
--
--   2. post_mortems.position_id  uuid  REFERENCES positions(id)
--      pattern_library.evidence_position_ids  uuid[]
--      Ces deux tables (0 ligne) appartiennent à la strate v0 : clés uuid, FK vers
--      `positions` (2 lignes, voisine de `v0_theses` / `v0_calendar_events`).
--      Le portefeuille vivant est `portfolio_positions`, en INT. Il n'existe aucun
--      cast qui rende `post_mortems` écrivable depuis le flux V2 : on ne « répare »
--      pas une table v0, on lui donne une sœur V2. D'où `post_mortems_v2`.
--
--   3. theses_v2_status_check CHECK (status IN ('draft','active','under_review',
--                                               'superseded','invalidated'))
--      Aucun statut TERMINAL. Le post-mortem se déclenche au dernier lot vendu —
--      et à cet instant la thèse n'a nulle part où aller. `invalidated` ne convient
--      que pour l'origine `hypothese_invalidee` : sortir pour `reallocation` ou
--      `rendement_insuffisant` en marquant la thèse « invalidée » écrirait un
--      jugement FAUX dans l'historique, précisément celui que la calibration A5 va
--      relire dans deux ans. D'où l'ouverture à 'closed'.
--
--   4. portfolio_positions n'a pas d'`exit_status` (§11 en exige un).
--   5. price_alerts n'a ni `exit_plan_id` ni `alert_type` : les alertes de tranche
--      seraient indiscernables des alertes de prix posées à la main.
--   6. analysis_refs_kind_domain ferme le domaine sur ('analysis','research_memo',
--      'readiness','grounding','monitoring') : 'debate' et 'post_mortem' rejettent.
--   7. exit_plans / exit_executions / calibration_registry n'existent pas.
--
-- CE QUE CETTE MIGRATION N'A PAS FAIT, ET POURQUOI :
--   * pas de CHECK ajouté sur `cash_movements.type`. Il n'en a AUCUN aujourd'hui
--     (données présentes : 'buy', 'deposit') : 'sell' passe sans rien changer. En
--     poser un maintenant reviendrait à figer un domaine V1 qu'on n'a pas
--     inventorié — un CHECK écrit de mémoire casse le flux V1 en silence.
--   * pas de CHECK ajouté sur `knowledge_entries.entry_type` (vérifié : aucun).
--     Les leçons s'écrivent en `lesson_learned` sans migration.
--   * pattern_library reste DORMANTE, et ce n'est pas un oubli. Les leçons vont
--     dans `knowledge_entries` parce que cette table-là est vectorisée (embedding
--     1024d, index hnsw) : un bull-agent travaillant sur un comparable RETROUVERA
--     la leçon par similarité. Rangée dans pattern_library (uuid, sans embedding,
--     clé texte à deviner), la même leçon serait écrite et jamais relue.
--   * pas de contrainte sur la CLÔTURE d'un débat. Le garde-fou anti-complaisance
--     porte sur `resolution_suggeree` — la sortie de l'AGENT, ce que le routeur
--     lit. Le statut de clôture est la décision de l'humain, qui reste souverain
--     y compris pour maintenir contre l'avis du débat. Contraindre l'agent,
--     jamais l'utilisateur.
--
-- Idempotente : rejouable sans effet de bord.
-- ============================================================================

BEGIN;

-- ─────────────────────────────────────────────────────────────────────────────
-- 1. theses_v2 : un statut terminal (défaut 3)
-- ─────────────────────────────────────────────────────────────────────────────
ALTER TABLE theses_v2 DROP CONSTRAINT IF EXISTS theses_v2_status_check;
ALTER TABLE theses_v2 ADD CONSTRAINT theses_v2_status_check
    CHECK (status IN ('draft', 'active', 'under_review', 'superseded', 'invalidated', 'closed'));

-- ─────────────────────────────────────────────────────────────────────────────
-- 2. exit_plans — le plan de sortie THÈSE-DRIVEN (§11)
-- ─────────────────────────────────────────────────────────────────────────────
-- `origine` est NOT NULL et typée : §11 dit que la sortie a une CAUSE DE THÈSE,
-- jamais un pur ratio de prix. Les tranches ne sont que l'exécution de cette cause.
CREATE TABLE IF NOT EXISTS exit_plans (
    id                     SERIAL PRIMARY KEY,
    thesis_v2_id           INT  NOT NULL REFERENCES theses_v2(id),
    ticker_id              TEXT NOT NULL REFERENCES tickers(id),
    position_id            INT  REFERENCES portfolio_positions(id),

    -- La cause amont : quelle session de monitoring a routé vers 'exit_plan'.
    -- Nullable car un plan peut être demandé à la main, mais tracée quand elle existe.
    monitoring_session_v2_id INT REFERENCES monitoring_sessions_v2(id),

    origine                TEXT NOT NULL,
    exit_status            TEXT,
    plan_json              JSONB,
    context_sent           TEXT,
    raw_content            TEXT,

    status                 TEXT NOT NULL DEFAULT 'completed',
    provider_used          TEXT,
    model_used             TEXT,
    prompt_snapshot        TEXT,
    tokens_in              INT     DEFAULT 0,
    tokens_out             INT     DEFAULT 0,
    cost_usd               NUMERIC(12,6) DEFAULT 0,

    created_at             TIMESTAMPTZ DEFAULT NOW(),
    updated_at             TIMESTAMPTZ DEFAULT NOW(),
    closed_at              TIMESTAMPTZ
);

ALTER TABLE exit_plans DROP CONSTRAINT IF EXISTS ep_origine_domaine;
ALTER TABLE exit_plans ADD CONSTRAINT ep_origine_domaine
    CHECK (origine IN ('thesis_degradation', 'rendement_insuffisant',
                       'hypothese_invalidee', 'reallocation'));

ALTER TABLE exit_plans DROP CONSTRAINT IF EXISTS ep_status_domaine;
ALTER TABLE exit_plans ADD CONSTRAINT ep_status_domaine
    CHECK (status IN ('completed', 'failed'));

ALTER TABLE exit_plans DROP CONSTRAINT IF EXISTS ep_exit_status_domaine;
ALTER TABLE exit_plans ADD CONSTRAINT ep_exit_status_domaine
    CHECK (exit_status IS NULL
           OR exit_status IN ('plan_created', 'partially_exited', 'closed', 'accelerated_exit'));

-- Un plan abouti a forcément un état de sortie ; un plan `failed` n'en a pas.
ALTER TABLE exit_plans DROP CONSTRAINT IF EXISTS ep_exit_status_si_complet;
ALTER TABLE exit_plans ADD CONSTRAINT ep_exit_status_si_complet
    CHECK (status <> 'completed' OR exit_status IS NOT NULL);

-- ⚠ GARDE-FOU ARGENT RÉEL n°1. Deux plans ouverts sur la même thèse, c'est deux
-- séries de tranches sur les MÊMES titres : la seconde vend ce que la première a
-- déjà vendu. Aucun contrat Pydantic ne peut le voir (il ne valide qu'un objet,
-- convention #37) et aucun code ne le verra non plus le jour où deux requêtes
-- arrivent en parallèle. Ça se refuse donc en base.
DROP INDEX IF EXISTS uq_exit_plan_actif;
CREATE UNIQUE INDEX uq_exit_plan_actif ON exit_plans(thesis_v2_id)
    WHERE status = 'completed' AND exit_status <> 'closed';

CREATE INDEX IF NOT EXISTS idx_exit_plans_thesis   ON exit_plans(thesis_v2_id);
CREATE INDEX IF NOT EXISTS idx_exit_plans_ticker   ON exit_plans(ticker_id);
CREATE INDEX IF NOT EXISTS idx_exit_plans_position ON exit_plans(position_id)
    WHERE position_id IS NOT NULL;

-- ─────────────────────────────────────────────────────────────────────────────
-- 3. exit_executions — une ligne par tranche RÉELLEMENT exécutée
-- ─────────────────────────────────────────────────────────────────────────────
-- Le plan est un jugement ; l'exécution est un fait du monde (des titres ont
-- quitté le portefeuille, du cash est entré). D'où deux tables : rejouer le plan
-- ne doit jamais rejouer les ventes.
CREATE TABLE IF NOT EXISTS exit_executions (
    id                SERIAL PRIMARY KEY,
    exit_plan_id      INT  NOT NULL REFERENCES exit_plans(id) ON DELETE CASCADE,
    ordre             INT  NOT NULL,
    pct_a_vendre      NUMERIC(7,4) NOT NULL,
    declencheur       TEXT NOT NULL DEFAULT '',

    -- DEUX prix, et les deux noms le disent. `portfolio_positions` porte déjà cette dualité
    -- (`purchase_price` natif / `purchase_price_eur`) mais nomme `sell_price` la valeur EUR : une
    -- colonne `sell_price` nue ici, de sens inverse, serait un piège pour le prochain lecteur.
    -- Le natif sert la comparaison entrée/sortie (464 USD vs 500 EUR ne se comparent pas) ;
    -- l'EUR est la vérité de trésorerie.
    shares_sold       NUMERIC(15,4) NOT NULL,
    sell_price_native NUMERIC(15,4) NOT NULL,
    sell_currency     TEXT NOT NULL DEFAULT 'EUR',
    fx_rate           NUMERIC(18,8),
    sell_price_eur    NUMERIC(15,4) NOT NULL,
    proceeds_eur      NUMERIC(15,4)
        GENERATED ALWAYS AS (shares_sold * sell_price_eur) STORED,

    executed_at       DATE NOT NULL DEFAULT CURRENT_DATE,
    cash_movement_id  INT  REFERENCES cash_movements(id),
    note              TEXT,
    created_at        TIMESTAMPTZ DEFAULT NOW()
);

-- ⚠ GARDE-FOU ARGENT RÉEL n°2. Une tranche s'exécute UNE FOIS. Sans cette unicité,
-- un double POST (un doigt qui glisse, un retry réseau) revend la tranche 2 et
-- crédite deux fois le cash : la position et la trésorerie divergent du réel, en
-- silence, et plus rien ne les rapproche.
ALTER TABLE exit_executions DROP CONSTRAINT IF EXISTS uq_exit_execution_tranche;
ALTER TABLE exit_executions ADD CONSTRAINT uq_exit_execution_tranche
    UNIQUE (exit_plan_id, ordre);

ALTER TABLE exit_executions DROP CONSTRAINT IF EXISTS ee_quantites_positives;
ALTER TABLE exit_executions ADD CONSTRAINT ee_quantites_positives
    CHECK (ordre >= 1 AND shares_sold > 0 AND sell_price_native > 0 AND sell_price_eur > 0
           AND pct_a_vendre > 0 AND pct_a_vendre <= 100);

CREATE INDEX IF NOT EXISTS idx_exit_exec_plan ON exit_executions(exit_plan_id);

-- ─────────────────────────────────────────────────────────────────────────────
-- 4. post_mortems_v2 — le bilan au dernier lot vendu (§12)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS post_mortems_v2 (
    id                SERIAL PRIMARY KEY,
    thesis_v2_id      INT  NOT NULL REFERENCES theses_v2(id),
    ticker_id         TEXT NOT NULL REFERENCES tickers(id),
    exit_plan_id      INT  REFERENCES exit_plans(id),
    position_id       INT  REFERENCES portfolio_positions(id),

    duree_jours       INT,
    performance_pct   NUMERIC(12,4),
    result_json       JSONB,
    context_sent      TEXT,
    raw_content       TEXT,

    -- Traçabilité des leçons écrites en knowledge_entries (type 'lesson_learned') :
    -- sans ça, on ne sait plus quelle entry vient de quel post-mortem.
    lesson_entry_ids  INT[] NOT NULL DEFAULT '{}',

    status            TEXT NOT NULL DEFAULT 'completed',
    provider_used     TEXT,
    model_used        TEXT,
    prompt_snapshot   TEXT,
    tokens_in         INT     DEFAULT 0,
    tokens_out        INT     DEFAULT 0,
    cost_usd          NUMERIC(12,6) DEFAULT 0,

    -- La calibration est un SECOND appel modèle, mais elle n'a pas de vie propre : elle
    -- exige un post-mortem abouti (c'est un pont vérifié en code) et son produit, ce
    -- sont les lignes de `calibration_registry`. Lui donner sa table d'exécution
    -- reviendrait à créer une table à une ligne par post-mortem, jointe à vie. On garde
    -- donc sa dépense et son texte brut ICI — audités comme tout appel modèle.
    calibration_json      JSONB,
    calibration_raw       TEXT,
    calibration_tokens_in  INT DEFAULT 0,
    calibration_tokens_out INT DEFAULT 0,
    calibration_cost_usd   NUMERIC(12,6) DEFAULT 0,
    calibration_at         TIMESTAMPTZ,

    created_at        TIMESTAMPTZ DEFAULT NOW()
);

-- Colonnes de calibration ajoutées séparément : la table peut préexister (idempotence).
ALTER TABLE post_mortems_v2 ADD COLUMN IF NOT EXISTS calibration_json       JSONB;
ALTER TABLE post_mortems_v2 ADD COLUMN IF NOT EXISTS calibration_raw        TEXT;
ALTER TABLE post_mortems_v2 ADD COLUMN IF NOT EXISTS calibration_tokens_in  INT DEFAULT 0;
ALTER TABLE post_mortems_v2 ADD COLUMN IF NOT EXISTS calibration_tokens_out INT DEFAULT 0;
ALTER TABLE post_mortems_v2 ADD COLUMN IF NOT EXISTS calibration_cost_usd   NUMERIC(12,6) DEFAULT 0;
ALTER TABLE post_mortems_v2 ADD COLUMN IF NOT EXISTS calibration_at         TIMESTAMPTZ;

ALTER TABLE post_mortems_v2 DROP CONSTRAINT IF EXISTS pm_v2_status_domaine;
ALTER TABLE post_mortems_v2 ADD CONSTRAINT pm_v2_status_domaine
    CHECK (status IN ('completed', 'failed'));

-- ⚠ GARDE-FOU CALIBRATION. Un second post-mortem sur la même thèse produirait une
-- seconde série de paires prédit/réalisé : le registre A5 compterait deux fois la
-- même position et le « biais systématique » qu'il révèle serait un artefact de
-- doublon. Une thèse, un bilan.
DROP INDEX IF EXISTS uq_post_mortem_v2_thesis;
CREATE UNIQUE INDEX uq_post_mortem_v2_thesis ON post_mortems_v2(thesis_v2_id)
    WHERE status = 'completed';

CREATE INDEX IF NOT EXISTS idx_pm_v2_ticker ON post_mortems_v2(ticker_id);

-- ─────────────────────────────────────────────────────────────────────────────
-- 5. calibration_registry — le registre A5 (prédit à l'entrée vs réalisé)
-- ─────────────────────────────────────────────────────────────────────────────
-- Grain volontairement fin (une LIGNE par métrique, pas un JSON par thèse) : la
-- question à laquelle ce registre doit répondre est « sur mes 20 positions, mes IV
-- hautes sont-elles systématiquement trop basses ? ». Elle s'écrit en SQL sur des
-- lignes ; elle ne s'écrit pas sur des blobs.
CREATE TABLE IF NOT EXISTS calibration_registry (
    id              SERIAL PRIMARY KEY,
    thesis_v2_id    INT  NOT NULL REFERENCES theses_v2(id),
    ticker_id       TEXT NOT NULL REFERENCES tickers(id),
    post_mortem_id  INT  REFERENCES post_mortems_v2(id),

    metric          TEXT NOT NULL,
    predite         DOUBLE PRECISION NOT NULL,
    realisee        DOUBLE PRECISION NOT NULL,
    -- Calculé par Postgres : un écart stocké par le code finit par diverger de ses
    -- deux termes le jour où l'un est corrigé.
    ecart           DOUBLE PRECISION GENERATED ALWAYS AS (realisee - predite) STORED,

    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Même raison que l'unicité du post-mortem : une métrique enregistrée deux fois
-- pour la même thèse fausse la moyenne des écarts, qui EST le produit du registre.
ALTER TABLE calibration_registry DROP CONSTRAINT IF EXISTS uq_calibration_metric;
ALTER TABLE calibration_registry ADD CONSTRAINT uq_calibration_metric
    UNIQUE (thesis_v2_id, metric);

CREATE INDEX IF NOT EXISTS idx_calibration_metric ON calibration_registry(metric);
CREATE INDEX IF NOT EXISTS idx_calibration_ticker ON calibration_registry(ticker_id);

-- ─────────────────────────────────────────────────────────────────────────────
-- 6. conviction_debates_v2 — le débat, jugement disjoint (défaut 1, #34)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS conviction_debates_v2 (
    id                       SERIAL PRIMARY KEY,
    thesis_v2_id             INT  NOT NULL REFERENCES theses_v2(id),
    ticker_id                TEXT NOT NULL REFERENCES tickers(id),
    monitoring_session_v2_id INT  REFERENCES monitoring_sessions_v2(id),

    challenge_json           JSONB,
    context_sent             TEXT,
    raw_content              TEXT,

    -- Dénormalisations lues par le routeur / l'UX (elles ne parsent pas le JSON).
    resolution_suggeree      TEXT,
    escalade_recommandee     BOOLEAN NOT NULL DEFAULT FALSE,
    -- DÉRIVÉE EN CODE des seuils FIGÉS de theses_v2.hypotheses, jamais des seuils
    -- que le modèle a déclarés (voir contracts/debate_conviction_schema.py, §PORTÉE).
    invalidation_franchie    BOOLEAN NOT NULL DEFAULT FALSE,

    status                   TEXT NOT NULL DEFAULT 'open',
    closure_note             TEXT,
    closed_at                TIMESTAMPTZ,

    provider_used            TEXT,
    model_used               TEXT,
    prompt_snapshot          TEXT,
    tokens_in                INT     DEFAULT 0,
    tokens_out               INT     DEFAULT 0,
    cost_usd                 NUMERIC(12,6) DEFAULT 0,

    created_at               TIMESTAMPTZ DEFAULT NOW(),
    updated_at               TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE conviction_debates_v2 DROP CONSTRAINT IF EXISTS cd_v2_status_domaine;
ALTER TABLE conviction_debates_v2 ADD CONSTRAINT cd_v2_status_domaine
    CHECK (status IN ('open', 'closed_pass', 'closed_monitor', 'closed_proceed', 'failed'));

ALTER TABLE conviction_debates_v2 DROP CONSTRAINT IF EXISTS cd_v2_resolution_domaine;
ALTER TABLE conviction_debates_v2 ADD CONSTRAINT cd_v2_resolution_domaine
    CHECK (resolution_suggeree IS NULL
           OR resolution_suggeree IN ('closed_pass', 'closed_monitor', 'closed_proceed'));

-- ⚠ LE GARDE-FOU STRUCTURANT DE CETTE MIGRATION (G2 anti-complaisance, en base).
-- Le contrat Pydantic interdit déjà `closed_proceed` sous invalidation — mais il
-- juge le payload du modèle, où les seuils sont DÉCLARÉS : un modèle qui recopie un
-- seuil d'invalidation faux le désarme sans jamais violer le contrat (trou H7
-- transposé). `invalidation_franchie` est, elle, dérivée des seuils figés de la
-- thèse. La contrainte porte donc sur la seule valeur non falsifiable par l'agent.
-- Elle ne contraint QUE la suggestion de l'agent : la clôture reste à l'humain.
ALTER TABLE conviction_debates_v2 DROP CONSTRAINT IF EXISTS cd_v2_anti_complaisance;
ALTER TABLE conviction_debates_v2 ADD CONSTRAINT cd_v2_anti_complaisance
    CHECK (
        NOT invalidation_franchie
        OR resolution_suggeree IS NULL
        OR (resolution_suggeree = 'closed_pass')
        OR (resolution_suggeree = 'closed_monitor' AND escalade_recommandee)
    );

CREATE INDEX IF NOT EXISTS idx_cd_v2_thesis  ON conviction_debates_v2(thesis_v2_id);
CREATE INDEX IF NOT EXISTS idx_cd_v2_ticker  ON conviction_debates_v2(ticker_id);
CREATE INDEX IF NOT EXISTS idx_cd_v2_ouverts ON conviction_debates_v2(thesis_v2_id)
    WHERE status = 'open';

-- ─────────────────────────────────────────────────────────────────────────────
-- 7. portfolio_positions.exit_status (défaut 4) — fait du monde, colonne (#34)
-- ─────────────────────────────────────────────────────────────────────────────
ALTER TABLE portfolio_positions
    ADD COLUMN IF NOT EXISTS exit_status TEXT;

ALTER TABLE portfolio_positions DROP CONSTRAINT IF EXISTS pp_exit_status_domaine;
ALTER TABLE portfolio_positions ADD CONSTRAINT pp_exit_status_domaine
    CHECK (exit_status IS NULL
           OR exit_status IN ('plan_created', 'partially_exited', 'closed', 'accelerated_exit'));

-- `exit_status` est un artefact du flux V2 (il n'existe que parce qu'un ExitPlan
-- existe). Le poser sur une position V1 ferait croire à un plan de sortie que rien
-- n'a produit — pendant exact de `pp_thesis_flow_exclusif` (migration 030).
ALTER TABLE portfolio_positions DROP CONSTRAINT IF EXISTS pp_exit_status_flux_v2;
ALTER TABLE portfolio_positions ADD CONSTRAINT pp_exit_status_flux_v2
    CHECK (exit_status IS NULL OR thesis_v2_id IS NOT NULL);

-- ─────────────────────────────────────────────────────────────────────────────
-- 8. price_alerts : rattachement au plan de sortie (défaut 5)
-- ─────────────────────────────────────────────────────────────────────────────
ALTER TABLE price_alerts
    ADD COLUMN IF NOT EXISTS exit_plan_id INT REFERENCES exit_plans(id) ON DELETE CASCADE;
ALTER TABLE price_alerts
    ADD COLUMN IF NOT EXISTS alert_type TEXT NOT NULL DEFAULT 'manual';

ALTER TABLE price_alerts DROP CONSTRAINT IF EXISTS pa_alert_type_domaine;
ALTER TABLE price_alerts ADD CONSTRAINT pa_alert_type_domaine
    CHECK (alert_type IN ('manual', 'exit_tranche', 'exit_accelere'));

-- Une alerte de sortie sans plan est un ordre de vente sans cause de thèse — soit
-- exactement ce que §11 interdit. Et un plan attaché à une alerte 'manual' rendrait
-- le rattachement inexploitable. Les deux sens sont donc verrouillés.
ALTER TABLE price_alerts DROP CONSTRAINT IF EXISTS pa_alert_type_coherent;
ALTER TABLE price_alerts ADD CONSTRAINT pa_alert_type_coherent
    CHECK ((alert_type = 'manual' AND exit_plan_id IS NULL)
           OR (alert_type <> 'manual' AND exit_plan_id IS NOT NULL));

CREATE INDEX IF NOT EXISTS idx_price_alerts_exit_plan ON price_alerts(exit_plan_id)
    WHERE exit_plan_id IS NOT NULL;

-- ─────────────────────────────────────────────────────────────────────────────
-- 9. Snapshot des refs pour un débat (A1/A2) — défaut 6
-- ─────────────────────────────────────────────────────────────────────────────
-- Même raison qu'au lot 8 : les entries sont versionnées et append-only. Relire
-- dans deux ans un débat dont les contre-arguments citaient l'entry #57 doit rendre
-- l'entry #57 TELLE QU'ELLE ÉTAIT — sinon la calibration A5 juge une décision sur
-- des faits qu'elle n'avait pas.
--
-- 'post_mortem' n'est délibérément PAS ajouté. Les trois contrats du lot 9 ne
-- portent AUCUN `source_entry_refs` (vérifié : ni ExitPlan, ni PostMortem, ni
-- CalibrationEntry) : `collect_refs` y rendrait toujours l'ensemble vide. Ouvrir le
-- domaine à une valeur qu'aucun chemin ne peut écrire, c'est le champ infondable
-- de la convention #32 — un lecteur futur croirait la traçabilité assurée là où
-- elle n'existe pas. Le jour où le post-mortem citera des entries, il aura sa ligne.
ALTER TABLE analysis_knowledge_refs DROP CONSTRAINT IF EXISTS analysis_refs_kind_domain;
ALTER TABLE analysis_knowledge_refs ADD CONSTRAINT analysis_refs_kind_domain
    CHECK (analysis_kind IN ('analysis', 'research_memo', 'readiness', 'grounding',
                             'monitoring', 'debate'));

-- ─────────────────────────────────────────────────────────────────────────────
-- 10. Permissions (le backend tourne en portfolio_user, pas en admin)
-- ─────────────────────────────────────────────────────────────────────────────
GRANT SELECT, INSERT, UPDATE, DELETE ON exit_plans            TO portfolio_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON exit_executions       TO portfolio_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON post_mortems_v2       TO portfolio_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON calibration_registry  TO portfolio_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON conviction_debates_v2 TO portfolio_user;

GRANT USAGE, SELECT ON SEQUENCE exit_plans_id_seq            TO portfolio_user;
GRANT USAGE, SELECT ON SEQUENCE exit_executions_id_seq       TO portfolio_user;
GRANT USAGE, SELECT ON SEQUENCE post_mortems_v2_id_seq       TO portfolio_user;
GRANT USAGE, SELECT ON SEQUENCE calibration_registry_id_seq  TO portfolio_user;
GRANT USAGE, SELECT ON SEQUENCE conviction_debates_v2_id_seq TO portfolio_user;

COMMIT;
