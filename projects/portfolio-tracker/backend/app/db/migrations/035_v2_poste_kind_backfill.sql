-- 035 — V2 : F16, un fait financier porte lui-même sa nature de poste (`poste_kind`).
--       GÉNÉRÉ par `_gen_035.py`, ne pas éditer à la main : le backfill est calculé par
--       `edgar_feed.POSTES`, détenteur unique de la règle flux/bilan (#46).
--
-- POURQUOI. La clef d'identité d'un fait (#43) dépend du type de poste. `_current_fact_ids`
-- le tient de la spec du PRODUCTEUR ; un LECTEUR du corpus n'a que la ligne. Mesuré avant
-- migration : 19 des 43 faits financiers courants (tout le socle NVDA et MSFT, écrit avant
-- F4) ne portaient pas leur `poste_kind` — donc toute garantie « une seule vérité chiffrée
-- à un instant donné » y était silencieusement aveugle.
--
-- PÉRIMÈTRE. Postes du socle EDGAR uniquement. Les métriques dérivées (roic, levier,
-- fcf_conversion…) et les données de marché (yfinance) ne relèvent pas de la clef #43 :
-- ce sont des grandeurs calculées ou d'actualité, pas la vérité réglementaire déposée.
--
-- Lignes écrites : 27 · flow=18 · stock=9
-- Lignes déjà conformes (laissées intactes) : 23 · flow=14 · stock=9
-- Lignes hors périmètre (aucune identité réglementaire) : 34
--     edgar_official/cash_burn : 4
--     edgar_official/fcf_conversion : 2
--     edgar_official/intensite_capex : 2
--     edgar_official/levier : 10
--     edgar_official/roic : 10
--     yfinance/prix_actuel : 3
--     yfinance/relatif_multiple : 3

BEGIN;

-- 18 fait(s) de type `flow`
UPDATE knowledge_entries
   SET content_structured = content_structured || '{"poste_kind": "flow"}'::jsonb
 WHERE id = ANY(ARRAY[1,2,3,4,5,6,7,48,64,65,66,67,69,128,129,130,132,148]::int[])
   AND NOT (content_structured ? 'poste_kind');

-- 9 fait(s) de type `stock`
UPDATE knowledge_entries
   SET content_structured = content_structured || '{"poste_kind": "stock"}'::jsonb
 WHERE id = ANY(ARRAY[8,9,10,63,68,70,127,131,133]::int[])
   AND NOT (content_structured ? 'poste_kind');

-- Vérification NOMMÉE, dans la transaction : si un poste du socle reste sans `poste_kind`,
-- la migration échoue au lieu de laisser le trou se refermer en silence sur un COMMIT vert.
DO $$
DECLARE restants INT;
BEGIN
  SELECT count(*) INTO restants FROM knowledge_entries
   WHERE entry_type = 'fact_financial' AND source_type = 'edgar_official'
     AND content_structured->>'metric' = ANY(ARRAY['capital_expenditure','cash_and_lt_debt','gross_profit','net_income','operating_cash_flow','revenue','stockholders_equity','total_assets'])
     AND NOT (content_structured ? 'poste_kind');
  IF restants > 0 THEN
    RAISE EXCEPTION '035 : % poste(s) du socle EDGAR sans poste_kind après backfill', restants;
  END IF;
END $$;

COMMIT;
