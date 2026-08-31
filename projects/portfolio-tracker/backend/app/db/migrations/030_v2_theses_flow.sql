-- Migration 030 — V2 Theses Flow (Lot 7 : décision & validation)
--
-- Spec 01-spec-v2-unifiee.md §9 (y nommée "026_theses_flow" ; la COLLISION 023 a décalé toute la
-- séquence V2 de +1 → cette migration est la 030). Matérialise le support de l'acte de décision :
-- POST /v2/theses/{id}/validate fige une ThesisValidation (contrat decision_validate_schema.py,
-- 17 garde-fous) puis exécute la transaction atomique d'entrée en position.
--
-- ── POURQUOI UNE TABLE NEUVE ET NON `theses +=` ──────────────────────────────
-- La carte decision_validate_card.md (2026-08-21) annonçait `theses += colonnes`. Elle PRÉCÈDE
-- d'un jour le principe des deux espaces disjoints V1/V2 (acté le 2026-08-22) et a été AMENDÉE le
-- 2026-08-31 en conséquence. `theses` est la table pivot du flux V1 en production (positions,
-- calendrier, monitoring, débats y pointent tous) et `POST /theses/{id}/validate` y existe déjà
-- avec un corps `ValidateThesisBody` DÉPOURVU des garde-fous G2 (api/thesis_v2.py:733 — où « v2 »
-- désigne la 2ᵉ version du fichier V1, pas le flux V2 : piège de nommage). Les migrations 026 ont
-- créé des tables NEUVES (research_memos, investment_analyses) ; on ne fait pas l'exception ici,
-- sur la table la plus chargée. Le CONTRAT JSON est inchangé — seul son support bouge.
--
-- ── CE QUI EST DISJOINT ET CE QUI NE L'EST PAS (clarification du principe) ───
-- `portfolio_positions.thesis_id` et `calendar_events.thesis_id` portent des FK DURES vers
-- `theses(id)` : une thèse V2 ne peut pas y être référencée sans violer la contrainte. On NE
-- duplique PAS ces tables pour autant. Une position détenue et un événement de calendrier sont des
-- FAITS DU MONDE, pas des artefacts de flux : deux tables `portfolio_positions` concurrentes
-- donneraient deux portefeuilles, donc deux soldes de cash et deux vues d'allocation — l'incohérence
-- serait silencieuse et porterait sur de l'argent réel. C'est d'ailleurs la raison pour laquelle
-- `tickers` était déjà partagé.
--   Règle qui s'en dégage, et qui vaut pour les lots 8 et 9 :
--   **les JUGEMENTS sont disjoints (theses | theses_v2), les FAITS DU MONDE sont partagés
--   (tickers, portfolio_positions, cash_movements, calendar_events) avec un discriminant de
--   provenance.** D'où `thesis_v2_id` en colonne sœur, nullable, exclusive de `thesis_id`.
--
-- Rappels DB projet : asyncpg $1 (pas %s) ; JSONB auto-décodé (pas de json.dumps avant INSERT) ;
-- migration appliquée MANUELLEMENT via `docker cp` + `psql -f` — le heredoc `psql << EOF` via
-- `docker exec` échoue SILENCIEUSEMENT (convention #17). Idempotente au rejeu.

-- ── 1. theses_v2 — la thèse issue du flux V2, figée à la validation (§9) ─────
-- validation_json = la ThesisValidation INTÉGRALE telle qu'elle a passé le contrat (auditabilité
-- P0, immuable — même esprit que result_json_original en 026). Les colonnes qui suivent en sont des
-- PROJECTIONS requêtables, écrites dans la MÊME transaction : elles ne sont jamais la source de
-- vérité, elles évitent d'avoir à déballer le JSONB pour filtrer/joindre.
CREATE TABLE IF NOT EXISTS theses_v2 (
    id                    SERIAL PRIMARY KEY,
    ticker_id             TEXT NOT NULL REFERENCES tickers(id),
    schema_version        TEXT NOT NULL DEFAULT 'v2.0.0',
    validation_json       JSONB,                   -- ThesisValidation figée (NULL tant que draft)
    -- lignée d'auditabilité : de quelle analyse cette décision procède ---------
    research_memo_id      INT REFERENCES research_memos(id),
    synthesis_analysis_id INT REFERENCES investment_analyses(id),
    -- acquittements (§9) — la décision n'est pas « saisie », elle est acquittée
    pre_mortem_acked      BOOLEAN NOT NULL DEFAULT FALSE,
    risk_matrix_acked     BOOLEAN NOT NULL DEFAULT FALSE,
    risk_acks             JSONB,                   -- [{risk_index, accepted:true}] bijection §9
    -- décision figée ----------------------------------------------------------
    verdict               TEXT CHECK (verdict IN ('PROCEED','PROCEED_AVEC_CONDITIONS')),
    position_sizing_pct   NUMERIC(7,4),            -- sizing FINAL retenu (≤ pct_max, cap Kelly Q6)
    valuation_range       JSONB,                   -- {low, base, high} avec low ≤ base ≤ high
    conditions_entree     TEXT[] NOT NULL DEFAULT '{}',   -- non vide si PROCEED_AVEC_CONDITIONS
    -- falsifiabilité : H1-Hn figées, elles pilotent le monitoring (modes 2/3/6)
    hypotheses            JSONB,                   -- [Hypothese] — chaque risque accepté → 1 hypothèse
    -- cycle de vie ------------------------------------------------------------
    status                TEXT NOT NULL DEFAULT 'draft'
                          CHECK (status IN ('draft','active','under_review','superseded','invalidated')),
    validated_at          TIMESTAMPTZ,
    created_at            TIMESTAMPTZ DEFAULT NOW(),
    updated_at            TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_theses_v2_ticker ON theses_v2(ticker_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_theses_v2_status ON theses_v2(status);

-- Une thèse ACTIVE porte forcément sa décision : les champs du contrat ne peuvent pas être NULL
-- une fois la validation passée. Le contrat Pydantic le garantit en amont ; ce CHECK est le filet
-- côté base — si un jour un chemin d'écriture contourne la route, il échoue ici au lieu de créer
-- une position sans décision traçable.
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'theses_v2_active_complete') THEN
    ALTER TABLE theses_v2 ADD CONSTRAINT theses_v2_active_complete CHECK (
      status <> 'active' OR (
            validation_json       IS NOT NULL
        AND synthesis_analysis_id IS NOT NULL
        AND verdict               IS NOT NULL
        AND position_sizing_pct   IS NOT NULL
        AND valuation_range       IS NOT NULL
        AND hypotheses            IS NOT NULL
        AND pre_mortem_acked      IS TRUE
        AND risk_matrix_acked     IS TRUE
        AND (verdict <> 'PROCEED_AVEC_CONDITIONS' OR cardinality(conditions_entree) > 0)
      )
    );
  END IF;
END$$;

-- ── 2. Discriminant de provenance sur les FAITS DU MONDE (voir en-tête) ──────
-- Colonne sœur nullable + exclusivité. « Au plus une » et non « exactement une » : des lignes
-- historiques V0/V1 existent avec thesis_id NULL (positions saisies hors flux) — les rejeter
-- rendrait la migration inapplicable sur la base réelle.
ALTER TABLE portfolio_positions ADD COLUMN IF NOT EXISTS thesis_v2_id INT REFERENCES theses_v2(id);
ALTER TABLE calendar_events     ADD COLUMN IF NOT EXISTS thesis_v2_id INT REFERENCES theses_v2(id);

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'pp_thesis_flow_exclusif') THEN
    ALTER TABLE portfolio_positions ADD CONSTRAINT pp_thesis_flow_exclusif
      CHECK (thesis_id IS NULL OR thesis_v2_id IS NULL);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ce_thesis_flow_exclusif') THEN
    ALTER TABLE calendar_events ADD CONSTRAINT ce_thesis_flow_exclusif
      CHECK (thesis_id IS NULL OR thesis_v2_id IS NULL);
  END IF;
END$$;

CREATE INDEX IF NOT EXISTS idx_pp_thesis_v2 ON portfolio_positions(thesis_v2_id)
    WHERE thesis_v2_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_ce_thesis_v2 ON calendar_events(thesis_v2_id)
    WHERE thesis_v2_id IS NOT NULL;

-- `calendar_events.source` est un TEXT libre côté V1 ('thesis_agent'|'monitoring_agent'|'manual'|
-- 'conviction_override'). Le flux V2 y écrit 'thesis_agent_v2' (pas de CHECK à étendre, il n'y en
-- a pas).
--
-- ⚠ PARTAGER calendar_events IMPOSE UN FILTRE CÔTÉ V1 — vérifié, pas supposé.
-- On aurait pu croire que `_daily_check_v1` ignore nativement les lignes V2 parce qu'elles n'ont
-- pas de `thesis_id`. C'EST FAUX : les 4 requêtes d'`EventRouterV1` (modes 1, 2, 4, 3) font un
-- `LEFT JOIN theses th ON th.id = ce.thesis_id` — un LEFT JOIN ramène la ligne même sans thèse
-- jointe, et aucune garde ne teste `thesis_json IS NULL` ensuite. Sans correctif, le scheduler V1
-- aurait ramassé les événements V2, construit un contexte avec une thèse vide et APPELÉ L'AGENT
-- DUST V1 dessus (dépense réelle, session de monitoring sur une thèse inexistante), en silence.
-- → `AND ce.thesis_v2_id IS NULL` ajouté aux 4 requêtes d'event_router_v1.py. Le filtre est
-- strictement additif pour V1 : toutes ses lignes ont thesis_v2_id à NULL.
-- C'est le prix du partage des faits du monde, et il se paie explicitement.

-- ── Permissions ──────────────────────────────────────────────────────────────
GRANT SELECT, INSERT, UPDATE, DELETE ON theses_v2 TO portfolio_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO portfolio_user;
