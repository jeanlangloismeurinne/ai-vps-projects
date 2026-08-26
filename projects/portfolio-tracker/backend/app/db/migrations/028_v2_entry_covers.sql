-- 028_v2_entry_covers.sql — colonne `covers` (champ MVDD porté) sur knowledge_entries.
--
-- Motif (2026-08-26) : le curator option C vérifie le TIER des entries citées, mais pas la
-- PERTINENCE de leur contenu — une entry tier A HORS-SUJET peut « fonder » un champ (constaté :
-- croissance_marche_historique « fondée » par la croissance de NVDA #19). `covers` = le champ MVDD
-- (nom nu, ex. 'unit_economics') que l'entry porte réellement. Le curator exige `covers == champ`
-- quand il est renseigné ; fallback tier-only quand NULL (entries legacy non taguées → pas de
-- régression). Les producteurs (synthèse, feeds, search-worker) le remplissent désormais à l'écriture.
--
-- Idempotent. Appliqué manuellement (docker cp + psql -f), cf. CLAUDE.md #17.

ALTER TABLE knowledge_entries ADD COLUMN IF NOT EXISTS covers TEXT;

COMMENT ON COLUMN knowledge_entries.covers IS
  'Champ MVDD (nom nu) que cette entry fonde — vérifié par le curator (covers==champ) ; NULL = legacy';

-- Backfill depuis content_structured pour les entries structurées / de synthèse (champ explicite) :
--   • synthèse : content_structured.field_path (ex 'produits.unit_economics') → segment final
--   • feeds    : content_structured.field (financials: 'roic_pct'… ) tel quel
--   • à défaut : content_structured.metric SI c'est un champ MVDD connu (valuation/base_rate)
UPDATE knowledge_entries
SET covers = CASE
    WHEN content_structured ? 'field_path'
        THEN regexp_replace(content_structured->>'field_path', '^.*\.', '')
    WHEN content_structured ? 'field'
        THEN content_structured->>'field'
    WHEN content_structured ? 'metric'
         AND content_structured->>'metric' IN
             ('prix_actuel','relatif_multiple','base_rate_anchor',
              'roic_pct','fcf_conversion_pct','intensite_capex_pct','levier')
        THEN content_structured->>'metric'
    ELSE covers
END
WHERE covers IS NULL AND content_structured IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_knowledge_entries_covers
    ON knowledge_entries (ticker_id, covers) WHERE covers IS NOT NULL;
