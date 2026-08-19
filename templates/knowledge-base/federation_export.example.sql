-- Vue d'export « enveloppe document commune » pour une KB adossée à Postgres.
-- À adapter au schéma réel du projet. Voir KNOWLEDGE_ARCHITECTURE.md §3 pour le contrat.
--
-- Principe : le stockage natif reste libre (ici une table `knowledge_entries` versionnée
-- append-only) ; cette vue le PROJETTE vers les colonnes normalisées de l'enveloppe.
-- Le connecteur fédéré lira cette vue en incrémental via `updated_at` / `content_hash`.
--
-- Exemple calibré sur portfolio-tracker (implémentation de référence).

CREATE OR REPLACE VIEW knowledge_federation_export AS
SELECT
    -- doc_id stable : {project}:{source}:{local_id}
    'portfolio-tracker:postgres:knowledge_entry/' || e.id        AS doc_id,
    'portfolio-tracker'                                          AS project,
    'postgres'                                                   AS source,
    'https://portfolio.jlmvpscode.duckdns.org/knowledge/entry/' || e.id AS uri,
    e.title                                                      AS title,
    e.content_md                                                 AS body,           -- pivot Markdown
    'fr'                                                         AS lang,
    e.tags                                                       AS tags,           -- text[]
    jsonb_build_object('tickers', e.tickers)                     AS entities,
    e.reliability_score                                          AS reliability,
    e.reliability_tier                                           AS reliability_tier,
    'public'                                                     AS visibility,     -- pas de données perso ici
    e.created_at                                                 AS created_at,
    e.updated_at                                                 AS updated_at,
    now()                                                        AS ingested_at,
    'sha256:' || encode(digest(e.content_md, 'sha256'), 'hex')   AS content_hash,   -- extension pgcrypto
    jsonb_build_object(
        'source_type',   e.source_type,
        'entry_version', e.version,
        'has_conflict',  e.has_conflict
    )                                                            AS metadata
FROM knowledge_entries e
WHERE e.is_current              -- ne pas exporter les versions obsolètes
  AND NOT e.is_deleted;         -- respecter le soft-delete
