-- 010_kb_export_view.sql
-- Vue d'export « enveloppe document commune » pour la KB journal.
-- Projette journal_kb_entries vers le contrat normalisé de
-- templates/knowledge-base/envelope.schema.json.
-- Idempotent : CREATE OR REPLACE VIEW.
-- Ne modifie AUCUNE table existante.
--
-- Reliability : contenu de première main saisi par l'utilisateur
-- → « Document confidentiel fourni par l'utilisateur » (KNOWLEDGE_ARCHITECTURE.md §6)
--   Tier B+, score 0.80
--
-- Tags de l'enveloppe = tags libres || contexte (0..1, axe fixe) || nature (0..n, axe fixe)
-- Null-safe : ARRAY_REMOVE(ARRAY_CAT(...), NULL) garantit un tableau sans éléments NULL.
-- Le champ tags de l'enveloppe ne peut jamais être NULL (COALESCE final → '{}').

CREATE OR REPLACE VIEW knowledge_federation_export AS
SELECT
    -- doc_id stable : {project}:{source}:{local_id}
    e.doc_id                                                        AS doc_id,

    e.project                                                       AS project,

    e.source                                                        AS source,

    e.uri                                                           AS uri,

    COALESCE(e.title, e.doc_id)                                     AS title,

    e.body                                                          AS body,

    'fr'                                                            AS lang,

    -- tags = tags libres || contexte (text, 0..1) || nature (text[], 0..n)
    -- ARRAY_REMOVE élimine les NULL insérés par COALESCE sur colonnes nullable
    COALESCE(
        ARRAY_REMOVE(
            e.tags
            || ARRAY[e.contexte]
            || COALESCE(e.nature, ARRAY[]::text[]),
            NULL
        ),
        ARRAY[]::text[]
    )                                                               AS tags,

    -- Tier B+, score 0.80 — « Document confidentiel fourni par l'utilisateur »
    -- (KNOWLEDGE_ARCHITECTURE.md §6 — contenu de première main, journal personnel)
    0.80::numeric(3,2)                                              AS reliability,
    'B+'                                                            AS reliability_tier,

    e.visibility                                                    AS visibility,

    e.created_at                                                    AS created_at,

    e.updated_at                                                    AS updated_at,

    -- ingested_at : posé ici par la vue (sera écrasé par le connecteur fédéré)
    now()                                                           AS ingested_at,

    e.content_hash                                                  AS content_hash,

    -- metadata : extras non contractuels — ne pas exposer à la couche fédérée
    jsonb_build_object(
        'slack_ts', e.slack_ts,
        'nature',   e.nature,
        'contexte', e.contexte
    )                                                               AS metadata

FROM journal_kb_entries e;
