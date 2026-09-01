-- ============================================================================
-- 031_v2_monitoring_flow.sql — LOT 8 : le monitoring V2 (modes 1 à 6)
--
-- POURQUOI CETTE MIGRATION EXISTE (CLAUDE.md annonçait « le lot 8 n'en demande
-- pas a priori » — c'est FAUX, et voici la vérification qui le montre) :
--
--     monitoring_sessions_thesis_id_fkey FOREIGN KEY (thesis_id) REFERENCES theses(id)
--
-- `monitoring_sessions.thesis_id` pointe la table V1. Une session de monitoring
-- portant sur une thèse V2 (#4, MSFT) ne peut PAS s'y écrire : la clé étrangère
-- rejette, ou — pire si on l'avait laissée nullable et vide — la session serait
-- orpheline de sa thèse. Et une session de monitoring est un JUGEMENT (l'avis
-- d'un agent sur une thèse), pas un fait du monde : par la convention #34, les
-- jugements sont DISJOINTS. D'où `monitoring_sessions_v2`, sœur de `theses_v2`.
--
-- Symétriquement, `calendar_events` est un FAIT DU MONDE partagé : il reçoit une
-- colonne discriminante `session_v2_id` (sœur nullable de `session_id`) et un
-- CHECK d'exclusivité, exactement comme `thesis_v2_id` en migration 030.
--
-- CE QUE CETTE MIGRATION N'A PAS FAIT, ET POURQUOI :
--   * pas de `monitoring_messages_v2`. En V1 cette table porte l'historique de
--     chat d'une session (l'utilisateur relance l'agent Dust). Le monitoring V2
--     est un tour unique, sans conversation : ce qu'il faut pouvoir rejouer,
--     c'est le CONTEXTE ENVOYÉ et le TEXTE BRUT RENDU. Les deux sont des
--     colonnes de la session (`context_sent`, `raw_content`). Une table de
--     messages vide, indexée et jointe, serait un coût sans lecteur. Si un chat
--     de monitoring apparaît un jour, il aura sa migration.
--   * pas de colonne d'hypothèses. Les statuts revus vivent dans `result_json`
--     (le contrat) et sont reportés sur `theses_v2.hypotheses` par l'agent.
--
-- Idempotente : rejouable sans effet de bord.
-- ============================================================================

BEGIN;

-- ─────────────────────────────────────────────────────────────────────────────
-- 1. monitoring_sessions_v2 — le jugement de suivi, disjoint (convention #34)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS monitoring_sessions_v2 (
    id                  SERIAL PRIMARY KEY,
    thesis_v2_id        INT  NOT NULL REFERENCES theses_v2(id),
    ticker_id           TEXT NOT NULL REFERENCES tickers(id),
    mode                INT  NOT NULL,
    trigger_type        TEXT NOT NULL DEFAULT 'manual',   -- scheduled | manual
    trigger_label       TEXT NOT NULL DEFAULT '',
    calendar_event_id   INT  REFERENCES calendar_events(id) ON DELETE SET NULL,

    -- Sortie de l'agent : le contrat du mode (Mode1..Mode5 | Mode6Review), validé
    -- avant écriture. `raw_content` garde le texte brut même quand la validation a
    -- demandé une réparation — c'est ce qui permet d'auditer ce que le modèle a
    -- réellement dit, pas seulement ce qu'on a bien voulu retenir.
    result_json         JSONB,
    context_sent        TEXT,
    raw_content         TEXT,

    -- Dénormalisations que le ROUTEUR lit (il ne parse pas le JSON pour décider).
    alert_level         TEXT,
    verdict             TEXT,
    routing_suggestion  TEXT,

    status              TEXT NOT NULL DEFAULT 'completed',
    provider_used       TEXT,
    model_used          TEXT,
    prompt_snapshot     TEXT,
    tokens_in           INT     DEFAULT 0,
    tokens_out          INT     DEFAULT 0,
    cost_usd            NUMERIC(12,6) DEFAULT 0,

    created_at          TIMESTAMPTZ DEFAULT NOW(),
    completed_at        TIMESTAMPTZ,
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

-- Les 6 modes, et rien d'autre.
ALTER TABLE monitoring_sessions_v2 DROP CONSTRAINT IF EXISTS ms_v2_mode_domaine;
ALTER TABLE monitoring_sessions_v2 ADD CONSTRAINT ms_v2_mode_domaine
    CHECK (mode BETWEEN 1 AND 6);

ALTER TABLE monitoring_sessions_v2 DROP CONSTRAINT IF EXISTS ms_v2_status_domaine;
ALTER TABLE monitoring_sessions_v2 ADD CONSTRAINT ms_v2_status_domaine
    CHECK (status IN ('running', 'completed', 'failed', 'pending_manual'));

-- ⚠ LE GARDE-FOU STRUCTURANT DE CETTE MIGRATION.
-- « Le mode 4 (sector pulse) n'escalade JAMAIS seul » et « les modes 1/5/6 ne
-- produisent pas de niveau d'alerte » sont, dans les cartes figées, des règles de
-- CONTRAT — donc opposables à l'agent, mais pas au code qui écrit la ligne. Or
-- c'est `alert_level` que le routeur lit pour décider d'escalader (mode 5). Une
-- écriture directe posant `alert_level='CRITICAL'` sur un pulse sectoriel
-- déclencherait une escalade que la carte interdit, sans qu'aucun contrat ne soit
-- consulté. On l'interdit donc EN BASE : seul le mode 2 porte un alert_level.
ALTER TABLE monitoring_sessions_v2 DROP CONSTRAINT IF EXISTS ms_v2_alert_level_mode2;
ALTER TABLE monitoring_sessions_v2 ADD CONSTRAINT ms_v2_alert_level_mode2
    CHECK (
        alert_level IS NULL
        OR (mode = 2 AND alert_level IN ('RAS', 'REVIEW_REQUIRED', 'CRITICAL'))
    );

-- Même esprit pour le verdict : seuls les modes 3 (décision review) et 6 (revue
-- annuelle) produisent un verdict de plein droit — les modes trimestriels 1/2/4
-- flaguent, ils ne jugent pas (anti-churn, audit §1.3). Et les deux vocabulaires
-- sont distincts : RE_SYNTHESE n'existe qu'au mode 3, RENFORCER/CONFIRMER qu'au 6.
ALTER TABLE monitoring_sessions_v2 DROP CONSTRAINT IF EXISTS ms_v2_verdict_par_mode;
ALTER TABLE monitoring_sessions_v2 ADD CONSTRAINT ms_v2_verdict_par_mode
    CHECK (
        verdict IS NULL
        OR (mode = 6 AND verdict IN ('CONFIRMER', 'RENFORCER', 'REDUIRE', 'SORTIR'))
        OR (mode = 3 AND verdict IN ('MAINTENIR', 'REDUIRE', 'SORTIR', 'RE_SYNTHESE'))
    );

CREATE INDEX IF NOT EXISTS idx_ms_v2_thesis    ON monitoring_sessions_v2(thesis_v2_id);
CREATE INDEX IF NOT EXISTS idx_ms_v2_ticker    ON monitoring_sessions_v2(ticker_id);
CREATE INDEX IF NOT EXISTS idx_ms_v2_event     ON monitoring_sessions_v2(calendar_event_id)
    WHERE calendar_event_id IS NOT NULL;

-- ─────────────────────────────────────────────────────────────────────────────
-- 2. calendar_events — fait du monde PARTAGÉ : colonne discriminante (#34)
-- ─────────────────────────────────────────────────────────────────────────────
ALTER TABLE calendar_events
    ADD COLUMN IF NOT EXISTS session_v2_id INT REFERENCES monitoring_sessions_v2(id);

-- Un événement est traité par UN flux. Pendant exact de `ce_thesis_flow_exclusif`
-- (migration 030) : sans lui, un même événement pourrait porter la trace d'une
-- session V1 et d'une session V2, et l'historique de suivi deviendrait illisible.
ALTER TABLE calendar_events DROP CONSTRAINT IF EXISTS ce_session_flow_exclusif;
ALTER TABLE calendar_events ADD CONSTRAINT ce_session_flow_exclusif
    CHECK (session_id IS NULL OR session_v2_id IS NULL);

CREATE INDEX IF NOT EXISTS idx_ce_session_v2 ON calendar_events(session_v2_id)
    WHERE session_v2_id IS NOT NULL;

-- ─────────────────────────────────────────────────────────────────────────────
-- 3. Interrupteur de dépense automatique du flux V2
-- ─────────────────────────────────────────────────────────────────────────────
-- `dust_auto_enabled` gouverne l'automatisme V1 ; il est nommé « dust » et il est
-- à FALSE en prod. Le réutiliser pour la V2 ferait mentir son nom (la V2 n'appelle
-- pas Dust) et lierait deux flux qu'on a délibérément disjoints.
--
-- DEFAULT FALSE, et c'est délibéré : à la minute où cette migration est appliquée,
-- il existe déjà des événements V2 échus en attente (#65 le 2026-10-28, #66 le
-- 2027-08-31) sur une position en argent réel. Un routeur neuf qui se met à
-- dépenser tout seul le lendemain de son déploiement, sans avoir jamais tourné une
-- fois sous supervision, est exactement ce qu'on ne veut pas. L'automatisme
-- s'active par un UPDATE explicite, après le dry-run.
ALTER TABLE portfolio_settings
    ADD COLUMN IF NOT EXISTS v2_auto_enabled BOOLEAN NOT NULL DEFAULT FALSE;

-- ─────────────────────────────────────────────────────────────────────────────
-- 4. Snapshot des refs pour une session de monitoring (A1/A2)
-- ─────────────────────────────────────────────────────────────────────────────
-- Le contrat impose des `source_entry_refs` non vides sur chaque statut
-- d'hypothèse revu (« pas de changement de statut au feeling »). Mais les entries
-- sont VERSIONNÉES et append-only : sans snapshot, relire une session d'il y a un
-- an renverrait le contenu d'AUJOURD'HUI de l'entry citée — on ne saurait plus sur
-- quoi le statut avait réellement basculé. Le domaine de `analysis_kind` s'ouvre
-- donc à 'monitoring'.
ALTER TABLE analysis_knowledge_refs DROP CONSTRAINT IF EXISTS analysis_refs_kind_domain;
ALTER TABLE analysis_knowledge_refs ADD CONSTRAINT analysis_refs_kind_domain
    CHECK (analysis_kind IN ('analysis', 'research_memo', 'readiness', 'grounding', 'monitoring'));

-- ─────────────────────────────────────────────────────────────────────────────
-- 5. Permissions (le backend tourne en portfolio_user, pas en admin)
-- ─────────────────────────────────────────────────────────────────────────────
GRANT SELECT, INSERT, UPDATE, DELETE ON monitoring_sessions_v2 TO portfolio_user;
GRANT USAGE, SELECT ON SEQUENCE monitoring_sessions_v2_id_seq TO portfolio_user;

COMMIT;
