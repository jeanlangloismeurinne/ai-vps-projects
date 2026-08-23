-- Migration 027 — Embeddings : vector(768) → vector(1024) (DÉCISION #4, 3ᵉ révision)
--
-- POURQUOI CE CHANGEMENT DE DIMENSION
--
-- Historique de la décision d'embeddings :
--   v1 (024) : nomic-embed-text via Ollama auto-hébergé, 768 dims.
--              → abandonné : ~1 Go de RAM sur un VPS à 3 819 Mo / 2 vCPU déjà saturé.
--   v2 (2026-08-23) : BAAI/bge-base-en-v1.5 via DeepInfra, 768 dims.
--              → choisi pour coller à vector(768) sans toucher au schéma. ERREUR : ce modèle est
--                entraîné sur l'ANGLAIS SEUL, or 100 % du corpus est en français (lang='fr' sur
--                15/15 entrées du seed NVDA, et les sources EU le resteront).
--   v3 (CETTE MIGRATION) : BAAI/bge-m3 via DeepInfra, 1024 dims, multilingue.
--
-- MESURE qui tranche (bench sur le corpus NVDA réel, 7 requêtes FR sémantiques, 15 entrées) :
--
--   configuration                              MRR     hit@1   hit@3
--   ILIKE lexical seul (l'existant)            0.352   1/7     3/7
--   bge-base-en-v1.5 768d, vectoriel           0.644   4/7     4/7
--   bge-m3 1024d, vectoriel                    0.905   6/7     7/7
--
-- Le 768d anglais échoue précisément sur les requêtes FINANCIÈRES (rentabilité, génération de cash,
-- endettement) — donc sur les entrées EDGAR Tier A, les plus fiables du corpus : la bonne entrée
-- ressortait aux rangs 5, 6 et 7 sur 15. Mode de panne SILENCIEUX : l'agent reçoit des entrées
-- pleines mais hors-sujet, le curator conclut à une dimension non couverte (readiness faux négatif)
-- et le garde-fou A2 (groundedness) ne voit rien puisque les refs citées existent bel et bien.
--
-- Aucun modèle multilingue en 768 dims n'est servi par DeepInfra (multilingual-e5-base et
-- gte-multilingual-base répondent 404) : la montée en dimension n'est pas évitable.
--
-- POURQUOI MAINTENANT : les 15 lignes ont toutes embedding IS NULL → DROP/ALTER/CREATE est
-- instantané et sans perte. Une fois le corpus rempli (étapes 2-3 : search-worker, ingestion-agent),
-- ce même changement imposerait de ré-embedder tout le corpus. C'est maintenant ou c'est cher.
--
-- SÉQUENCE V2 : la spec §14 réservait 027 à theses_flow. Cette migration prend 027 (règle §18 :
-- on écrit chaque migration juste avant son lot, et le lot embeddings passe avant) →
-- theses_flow décale en 028, exit/calibration en 029.
--
-- Rappels DB projet : migration appliquée MANUELLEMENT via `docker cp` + `psql -f`
-- (le heredoc `docker exec psql << EOF` échoue SILENCIEUSEMENT — pas d'erreur, pas de changement).

BEGIN;

-- 1+2. Changement de dimension, IDEMPOTENT.
--
-- L'idempotence n'est pas cosmétique ici : l'ALTER convertit en NULL (aucune conversion 768d→1024d
-- n'a de sens, et un vecteur produit par un AUTRE modèle n'est de toute façon pas comparable dans
-- le nouvel espace). Une migration rejouée par réflexe EFFACERAIT donc tout le corpus d'embeddings
-- déjà calculé. On ne fait le travail que si la colonne n'est pas déjà en 1024.
--
-- L'index HNSW est typé par la dimension de la colonne → il doit tomber avant l'ALTER.
-- NB sur la détection du type : ne PAS calculer la dimension par arithmétique sur `atttypmod`.
-- pgvector y stocke la dimension TELLE QUELLE, alors que les types natifs (varchar…) y ajoutent
-- VARHDRSZ (+4). Un `atttypmod - 4` réflexe lit donc 1020 pour un vector(1024), la garde ne
-- reconnaît pas l'état cible, et la migration rejouée EFFACE le corpus qu'elle devait protéger
-- (constaté en test le 2026-08-23). On compare la chaîne rendue par format_type : robuste et
-- indépendante des conventions internes du type.
DO $$
DECLARE
    type_actuel TEXT;
    n_non_null  INTEGER;
BEGIN
    SELECT format_type(a.atttypid, a.atttypmod) INTO type_actuel
      FROM pg_attribute a
     WHERE a.attrelid = 'knowledge_entries'::regclass AND a.attname = 'embedding';

    IF type_actuel = 'vector(1024)' THEN
        RAISE NOTICE 'embedding est déjà en vector(1024) — ALTER ignoré (embeddings préservés).';
    ELSE
        SELECT count(embedding) INTO n_non_null FROM knowledge_entries;
        IF n_non_null > 0 THEN
            RAISE WARNING
                'ATTENTION : % embedding(s) non NULL vont être effacés — produits par un modèle '
                'différent (%), non comparables dans l''espace bge-m3. Backfill OBLIGATOIRE après.',
                n_non_null, type_actuel;
        END IF;
        DROP INDEX IF EXISTS idx_knowledge_entries_embedding;
        ALTER TABLE knowledge_entries
            ALTER COLUMN embedding TYPE vector(1024) USING NULL::vector(1024);
        RAISE NOTICE 'embedding migré de % vers vector(1024).', type_actuel;
    END IF;
END $$;

COMMENT ON COLUMN knowledge_entries.embedding IS
    'BAAI/bge-m3 (1024d, multilingue) via DeepInfra /v1/openai/embeddings. Calculé hors migration '
    'par app/knowledge/embeddings.py (à l''écriture dans store_knowledge, ou par backfill). '
    'NULL = pas encore embeddé → l''entrée reste visible via le fallback texte de query_knowledge.';

-- 3. Reconstruction de l'index. vector_cosine_ops (donc opérateur <=>) : bge-m3 est entraîné en
--    similarité cosinus, et c'est déjà l'opclass posée par 024 — query_knowledge n'a pas à changer
--    d'opérateur.
CREATE INDEX IF NOT EXISTS idx_knowledge_entries_embedding
    ON knowledge_entries USING hnsw (embedding vector_cosine_ops);

-- 4. Index PARTIEL sur les entrées pas encore embeddées.
--    query_knowledge fait systématiquement une passe de « rattrapage » lexicale restreinte à
--    embedding IS NULL : ces entrées sont invisibles à la recherche vectorielle, et si l'anti-doublon
--    du search-worker ne les voit pas, il recrée des doublons. Cette passe doit rester bon marché
--    quand le corpus grossit — sans cet index, elle deviendrait un seq scan à chaque requête.
--    En régime nominal l'index est quasi vide (une entrée naît avec son embedding).
CREATE INDEX IF NOT EXISTS idx_knowledge_entries_unembedded
    ON knowledge_entries (ticker_id)
 WHERE embedding IS NULL AND is_deleted = FALSE AND superseded_by IS NULL;

COMMIT;

-- Vérification post-migration (à lire dans la sortie de psql) :
--   - atttypmod-3 doit valoir 1024
--   - l'index HNSW doit être présent
--   - null_emb doit égaler total (backfill à lancer juste après)
SELECT format_type(a.atttypid, a.atttypmod) AS type_embedding
  FROM pg_attribute a
 WHERE a.attrelid = 'knowledge_entries'::regclass AND a.attname = 'embedding';

SELECT indexdef FROM pg_indexes
 WHERE tablename = 'knowledge_entries' AND indexname = 'idx_knowledge_entries_embedding';

SELECT count(*) AS total, count(embedding) AS with_emb,
       count(*) FILTER (WHERE embedding IS NULL) AS null_emb
  FROM knowledge_entries;
