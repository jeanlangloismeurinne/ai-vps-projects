-- 029_v2_entry_covers_array.sql — `covers` devient multi-valué ET porte le CHEMIN COMPLET.
--
-- Motif (2026-08-30) : la 028 a fermé le trou de SUR-crédit (une entry tier A hors-sujet ne fonde
-- plus un champ), mais pas celui de SOUS-crédit : `recompute_coverage` filtre les entry_ids que le
-- LLM a CITÉS, il n'interroge pas la base. Une citation manquée = faux creux, à corpus figé — d'où
-- l'oscillation mesurée sur NVDA (#11 not_ready / #13 thin_qualitative / #14 not_ready, données
-- STRICTEMENT identiques). Le curator passe donc à un INDEX INDÉPENDANT : pour chaque champ requis,
-- le backend SÉLECTIONNE les entries qui le portent. Le LLM ne sert plus qu'à la synthèse narrative.
--
-- Deux changements, pour deux raisons distinctes :
--
--  1. TEXT → TEXT[] : une entry porte réellement PLUSIEURS champs (#19 « Data Center FY2026 » fonde
--     les drivers de revenus ; #21 « ASIC hyperscalers » fonde à la fois la position vs pairs et la
--     menace de substituts des 5 forces). Mono-valué, il fallait choisir un champ et perdre les
--     autres — ou dupliquer le contenu dans une base append-only, donc définitivement.
--
--  2. nom nu → chemin complet `dimension.champ` : `description` est un champ requis de business_model
--     ET de produits. Avec un gate piloté par l'index, un tag nu `description` posé pour produits
--     ferait passer business_model.description — exactement le sur-crédit que la 028 ferme. Le tag
--     doit être aussi discriminant que le champ qu'il prétend fonder.
--
-- Idempotent (garde sur le type réel + garde `covers IS NULL` sur le backfill). Appliqué
-- manuellement (docker cp + psql -f), cf. CLAUDE.md #17.

-- ── 1. TEXT → TEXT[] ─────────────────────────────────────────────────────────
-- Garde par le TYPE RÉEL, pas par une heuristique : cf. convention #23 (le réflexe `atttypmod - 4`
-- sur pgvector avait fait rejouer la 027 et effacer le corpus d'embeddings). `format_type` ne ment pas.
DO $$
BEGIN
    IF (SELECT format_type(a.atttypid, a.atttypmod)
          FROM pg_attribute a
         WHERE a.attrelid = 'knowledge_entries'::regclass
           AND a.attname = 'covers'
           AND NOT a.attisdropped) = 'text' THEN
        ALTER TABLE knowledge_entries
            ALTER COLUMN covers TYPE TEXT[]
            USING (CASE WHEN covers IS NULL THEN NULL ELSE ARRAY[covers] END);
    END IF;
END $$;

COMMENT ON COLUMN knowledge_entries.covers IS
  'Champs MVDD (chemins COMPLETS `dimension.champ`) que cette entry fonde. Index de couverture lu '
  'par le curator (SELECT ... covers && ARRAY[champ]) — le verdict de readiness en dépend, donc il '
  'est écrit par les chemins DÉTERMINISTES (feeds, mandat du worker, backfill relu), jamais par une '
  'déclaration libre du modèle (#24). NULL = entry qui ne fonde aucun champ requis (elle reste dans '
  'le corpus narratif et le context_pack).';

-- ── 2. noms nus → chemins complets (entries taguées par la 028 et les feeds) ──
-- LEFT JOIN + COALESCE : un tag sans correspondance est CONSERVÉ tel quel (jamais supprimé
-- silencieusement — un tag perdu est un faux creux de couverture).
UPDATE knowledge_entries e
SET covers = ARRAY(
        SELECT COALESCE(m.path, c)
          FROM unnest(e.covers) AS c
          LEFT JOIN (VALUES
              ('prix_actuel',         'valorisation.prix_actuel'),
              ('relatif_multiple',    'valorisation.relatif_multiple'),
              ('base_rate_anchor',    'valorisation.base_rate_anchor'),
              ('roic_pct',            'financials.roic_pct'),
              ('fcf_conversion_pct',  'financials.fcf_conversion_pct'),
              ('intensite_capex_pct', 'financials.intensite_capex_pct'),
              ('levier',              'financials.levier'),
              ('unit_economics',      'produits.unit_economics'),
              ('moat_preuves',        'positionnement.moat_preuves'),
              ('position_vs_pairs',   'positionnement.position_vs_pairs'),
              ('structure_5forces',   'marche.structure_5forces'),
              ('croissance_marche_historique', 'marche.croissance_marche_historique'),
              ('incitations',         'management_allocation.incitations'),
              ('skin_in_game_pct',    'management_allocation.skin_in_game_pct'),
              ('risques_cles',        'risques.risques_cles'),
              ('drivers_revenus',     'business_model.drivers_revenus'),
              ('recurrence_pct',      'business_model.recurrence_pct')
          ) AS m(bare, path) ON m.bare = c
    )
WHERE covers IS NOT NULL
  AND EXISTS (SELECT 1 FROM unnest(covers) AS c WHERE strpos(c, '.') = 0);

-- ── 3. Backfill des entries qualitatives legacy (NVDA #19-#35) ───────────────
-- Ces 17 entries tier A/B+ ne portaient AUCUN tag : le search-worker n'écrivait pas `covers`
-- (constaté `field=None`), et la 028 ne backfillait que depuis `content_structured`, absent ici.
-- Sous un gate piloté par l'index, elles ne fonderaient plus rien alors qu'elles sont la meilleure
-- matière du corpus. Le rattachement est un JUGEMENT : il est fait UNE FOIS, ici, relisible en revue
-- et versionné — plutôt que rejoué à chaque run par le LLM (c'est la cause même de l'oscillation).
--
-- Conservateur par construction : une entry n'est taguée que si elle porte le champ, pas si elle en
-- est un INTRANT. #32/#33/#34 (marges consolidées) alimentent la synthèse unit_economics #53 mais ne
-- SONT pas l'économie unitaire → non taguées. #25/#27 (retours au capital) documentent l'allocation
-- mais aucun champ REQUIS de management_allocation (incitations, skin_in_game_pct) → non taguées.
-- Conséquence assumée : `business_model.description` et `business_model.recurrence_pct` resteront
-- non fondés — ce sont de vrais creux, que le LLM comblait par intermittence avec #19 (un record de
-- revenus n'est pas une description de modèle économique). À combler par synthèse grounded.
--
-- Le garde-fou `title LIKE` empêche de taguer la mauvaise entry si les ids diffèrent d'un
-- environnement à l'autre ; `covers IS NULL` rend le rejeu inoffensif.
UPDATE knowledge_entries e
SET covers = m.paths
FROM (VALUES
    (19, ARRAY['business_model.drivers_revenus']::TEXT[],                            'Data Center segment FY2026'),
    (20, ARRAY['produits.description','positionnement.moat_preuves']::TEXT[],        'Plateforme Rubin'),
    (21, ARRAY['positionnement.position_vs_pairs','marche.structure_5forces']::TEXT[], 'Hyperscaler custom ASIC threat'),
    (22, ARRAY['marche.structure_5forces','risques.risques_cles']::TEXT[],           'NVIDIA customer concentration'),
    (23, ARRAY['management_allocation.skin_in_game_pct']::TEXT[],                    'Jensen Huang beneficial ownership'),
    (24, ARRAY['management_allocation.incitations']::TEXT[],                         'NVIDIA FY2026 executive compensation'),
    (26, ARRAY['management_allocation.incitations']::TEXT[],                         'Jensen Huang FY2025 compensation'),
    (28, ARRAY['risques.risques_cles']::TEXT[],                                      'NVIDIA FY2026 10-K: U.S. export controls'),
    (29, ARRAY['risques.risques_cles','positionnement.position_vs_pairs']::TEXT[],   'NVIDIA FY2026 10-K: Competition from AMD'),
    (30, ARRAY['risques.risques_cles','marche.structure_5forces']::TEXT[],           'NVIDIA FY2026 10-K: Supply chain concentrated'),
    (31, ARRAY['risques.risques_cles']::TEXT[],                                      'NVIDIA FY2026 10-K: Rapid technological change'),
    (35, ARRAY['business_model.drivers_revenus','produits.description']::TEXT[],     'NVIDIA Data Center segment revenue and Blackwell')
) AS m(entry_id, paths, title_prefix)
WHERE e.id = m.entry_id
  AND e.ticker_id = 'NVDA'
  AND e.covers IS NULL
  AND e.title LIKE m.title_prefix || '%';

-- ── 4. Index ─────────────────────────────────────────────────────────────────
-- Le btree (ticker_id, covers) de la 028 ne sait pas répondre à `covers && ARRAY[...]`.
DROP INDEX IF EXISTS idx_knowledge_entries_covers;
CREATE INDEX IF NOT EXISTS idx_knowledge_entries_covers_gin
    ON knowledge_entries USING GIN (covers);
