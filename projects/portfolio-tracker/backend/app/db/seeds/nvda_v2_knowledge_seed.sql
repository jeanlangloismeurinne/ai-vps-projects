-- Seed — NVDA cas-pilote Knowledge Platform V2 (spec KP §3.2, reprise cartes de provenance)
--
-- Rend la couche 3 (migration 024) VIVANTE sur un vrai titre : le readiness_derivation et le
-- groundedness-checker deviennent exécutables sur des entries réelles.
--
-- Sourcing HONNÊTE (constitution G3 / P2) :
--   • Financials = données XBRL RÉELLES tirées d'EDGAR (10-K FY2026, accession 0001045810-26-000021,
--     déposé 2026-02-25) → Tier A, source_type='edgar_official', reliability 0.95.
--   • Qualitatif (moat, marché, management, risques) = pas de document source ici → filet tracé
--     cold-start (§6.6) : source_type='llm_memory', reliability 0.40, requires_human_review=TRUE,
--     model_cutoff='2026-01'. Sous le plancher qualitatif → le readiness doit sortir
--     `thin_qualitative`, PAS `ready` : le garde-fou anti-faux-complet démontré sur un cas réel.
--
-- Idempotent : ne seed que si NVDA n'a encore aucune knowledge_entry.
-- Append-only : aucune mutation ; version=1 pour toutes les entrées initiales.

DO $$
DECLARE
    v_doc_id INT;
    v_exists INT;
BEGIN
    SELECT count(*) INTO v_exists FROM knowledge_entries WHERE ticker_id = 'NVDA';
    IF v_exists > 0 THEN
        RAISE NOTICE 'NVDA a déjà % knowledge_entries — seed ignoré (idempotent).', v_exists;
        RETURN;
    END IF;

    -- ── Document source : 10-K FY2026 (réel) ─────────────────────────────────
    INSERT INTO knowledge_documents
        (ticker_id, doc_type, title, source_url, source_type, published_date, fiscal_period,
         language, processing_status)
    VALUES
        ('NVDA', '10-K', 'NVIDIA Corporation Form 10-K FY2026',
         'https://www.sec.gov/Archives/edgar/data/1045810/000104581026000021/0001045810-26-000021-index.htm',
         'edgar', DATE '2026-02-25', 'FY-2026', 'en', 'done')
    RETURNING id INTO v_doc_id;

    -- ── Financials RÉELS (EDGAR) → Tier A ────────────────────────────────────
    -- fait, content_structured {metric,value,currency,period,period_end}
    INSERT INTO knowledge_entries
        (ticker_id, document_id, entry_type, title, content, content_structured, tags, lang,
         source_type, source_url, source_date, fiscal_period,
         reliability_score, reliability_tier, reliability_note)
    VALUES
    ('NVDA', v_doc_id, 'fact_financial', 'Chiffre d''affaires FY2026',
     'NVIDIA a réalisé un chiffre d''affaires de 215,938 Md$ sur l''exercice FY2026 (clos le 25/01/2026), en hausse de ~65% vs FY2025.',
     '{"metric":"revenue","value":215938000000,"currency":"USD","period":"FY2026","period_end":"2026-01-25"}',
     ARRAY['financials','revenue','edgar'], 'fr', 'edgar_official',
     'https://www.sec.gov/Archives/edgar/data/1045810/000104581026000021/0001045810-26-000021-index.htm',
     DATE '2026-01-25', 'FY-2026', 0.95, 'A', 'XBRL us-gaap:Revenues, 10-K FY2026'),

    ('NVDA', v_doc_id, 'fact_financial', 'Chiffre d''affaires FY2025',
     'Chiffre d''affaires FY2025 (clos le 26/01/2025) : 130,497 Md$.',
     '{"metric":"revenue","value":130497000000,"currency":"USD","period":"FY2025","period_end":"2025-01-26"}',
     ARRAY['financials','revenue','edgar'], 'fr', 'edgar_official',
     'https://www.sec.gov/Archives/edgar/data/1045810/000104581026000021/0001045810-26-000021-index.htm',
     DATE '2025-01-26', 'FY-2025', 0.95, 'A', 'XBRL us-gaap:Revenues, comparatif 10-K FY2026'),

    ('NVDA', v_doc_id, 'fact_financial', 'Chiffre d''affaires FY2024',
     'Chiffre d''affaires FY2024 (clos le 28/01/2024) : 60,922 Md$.',
     '{"metric":"revenue","value":60922000000,"currency":"USD","period":"FY2024","period_end":"2024-01-28"}',
     ARRAY['financials','revenue','edgar'], 'fr', 'edgar_official',
     'https://www.sec.gov/Archives/edgar/data/1045810/000104581026000021/0001045810-26-000021-index.htm',
     DATE '2024-01-28', 'FY-2024', 0.95, 'A', 'XBRL us-gaap:Revenues, comparatif 10-K FY2026'),

    ('NVDA', v_doc_id, 'fact_financial', 'Résultat net FY2026',
     'Résultat net FY2026 : 120,067 Md$ (marge nette ~55,6%).',
     '{"metric":"net_income","value":120067000000,"currency":"USD","period":"FY2026","period_end":"2026-01-25"}',
     ARRAY['financials','profitability','edgar'], 'fr', 'edgar_official',
     'https://www.sec.gov/Archives/edgar/data/1045810/000104581026000021/0001045810-26-000021-index.htm',
     DATE '2026-01-25', 'FY-2026', 0.95, 'A', 'XBRL us-gaap:NetIncomeLoss, 10-K FY2026'),

    ('NVDA', v_doc_id, 'fact_financial', 'Résultat net FY2025',
     'Résultat net FY2025 : 72,880 Md$.',
     '{"metric":"net_income","value":72880000000,"currency":"USD","period":"FY2025","period_end":"2025-01-26"}',
     ARRAY['financials','profitability','edgar'], 'fr', 'edgar_official',
     'https://www.sec.gov/Archives/edgar/data/1045810/000104581026000021/0001045810-26-000021-index.htm',
     DATE '2025-01-26', 'FY-2025', 0.95, 'A', 'XBRL us-gaap:NetIncomeLoss, comparatif 10-K FY2026'),

    ('NVDA', v_doc_id, 'fact_financial', 'Marge brute FY2026',
     'Profit brut FY2026 : 153,463 Md$, soit une marge brute de ~71,1% (153,463 / 215,938).',
     '{"metric":"gross_profit","value":153463000000,"currency":"USD","period":"FY2026","period_end":"2026-01-25","gross_margin_pct":71.1}',
     ARRAY['financials','margins','edgar'], 'fr', 'edgar_official',
     'https://www.sec.gov/Archives/edgar/data/1045810/000104581026000021/0001045810-26-000021-index.htm',
     DATE '2026-01-25', 'FY-2026', 0.95, 'A', 'XBRL us-gaap:GrossProfit, 10-K FY2026'),

    ('NVDA', v_doc_id, 'fact_financial', 'Flux de trésorerie opérationnel FY2026',
     'Cash-flow opérationnel FY2026 : 102,718 Md$ (conversion FCF élevée).',
     '{"metric":"operating_cash_flow","value":102718000000,"currency":"USD","period":"FY2026","period_end":"2026-01-25"}',
     ARRAY['financials','cash_flow','edgar'], 'fr', 'edgar_official',
     'https://www.sec.gov/Archives/edgar/data/1045810/000104581026000021/0001045810-26-000021-index.htm',
     DATE '2026-01-25', 'FY-2026', 0.95, 'A', 'XBRL us-gaap:NetCashProvidedByUsedInOperatingActivities, 10-K FY2026'),

    ('NVDA', v_doc_id, 'fact_financial', 'Capitaux propres FY2026',
     'Capitaux propres FY2026 : 157,293 Md$ (ROE ~76% : 120,067 / 157,293).',
     '{"metric":"stockholders_equity","value":157293000000,"currency":"USD","period":"FY2026","period_end":"2026-01-25"}',
     ARRAY['financials','balance_sheet','edgar'], 'fr', 'edgar_official',
     'https://www.sec.gov/Archives/edgar/data/1045810/000104581026000021/0001045810-26-000021-index.htm',
     DATE '2026-01-25', 'FY-2026', 0.95, 'A', 'XBRL us-gaap:StockholdersEquity, 10-K FY2026'),

    ('NVDA', v_doc_id, 'fact_financial', 'Total actif FY2026',
     'Total de l''actif FY2026 : 206,803 Md$.',
     '{"metric":"total_assets","value":206803000000,"currency":"USD","period":"FY2026","period_end":"2026-01-25"}',
     ARRAY['financials','balance_sheet','edgar'], 'fr', 'edgar_official',
     'https://www.sec.gov/Archives/edgar/data/1045810/000104581026000021/0001045810-26-000021-index.htm',
     DATE '2026-01-25', 'FY-2026', 0.95, 'A', 'XBRL us-gaap:Assets, 10-K FY2026'),

    ('NVDA', v_doc_id, 'fact_financial', 'Trésorerie et dette LT FY2026',
     'Trésorerie et équivalents 10,605 Md$ ; dette long terme (non courante) 7,469 Md$ → position de trésorerie nette positive (levier dette nette/EBITDA négatif).',
     '{"metric":"cash_and_lt_debt","cash":10605000000,"long_term_debt":7469000000,"currency":"USD","period":"FY2026","period_end":"2026-01-25"}',
     ARRAY['financials','balance_sheet','leverage','edgar'], 'fr', 'edgar_official',
     'https://www.sec.gov/Archives/edgar/data/1045810/000104581026000021/0001045810-26-000021-index.htm',
     DATE '2026-01-25', 'FY-2026', 0.95, 'A', 'XBRL us-gaap:CashAndCashEquivalentsAtCarryingValue + LongTermDebtNoncurrent, 10-K FY2026');

    -- ── Qualitatif → llm_memory (filet tracé cold-start, SOUS le plancher) ────
    INSERT INTO knowledge_entries
        (ticker_id, entry_type, title, content, tags, lang,
         source_type, source_date, reliability_score, reliability_tier, reliability_note,
         requires_human_review, model_cutoff)
    VALUES
    ('NVDA', 'fact_qualitative', 'Modèle économique (à vérifier)',
     'NVIDIA conçoit des GPU et plateformes de calcul accéléré ; le segment Data Center (GPU IA + réseau) domine le chiffre d''affaires. L''écosystème logiciel CUDA verrouille les développeurs. — Information issue du modèle, non sourcée, à confirmer.',
     ARRAY['business_model','llm_memory'], 'fr', 'llm_memory', DATE '2026-01-01',
     0.40, 'C', 'Mémoire modèle (cutoff 2026-01) — à remplacer par source primaire (10-K Item 1).',
     TRUE, '2026-01'),

    ('NVDA', 'fact_qualitative', 'Moat / avantage concurrentiel (à vérifier)',
     'Douves présumées : coûts de changement CUDA (switching costs), effets d''échelle et d''écosystème, avance technologique sur les accélérateurs IA. — Information issue du modèle, non sourcée, à confirmer.',
     ARRAY['moat','competitive_advantage','llm_memory'], 'fr', 'llm_memory', DATE '2026-01-01',
     0.40, 'C', 'Mémoire modèle — nécessite preuves sourcées (parts de marché, benchmarks, litiges).',
     TRUE, '2026-01'),

    ('NVDA', 'fact_qualitative', 'Structure & croissance du marché (à vérifier)',
     'Marché des accélérateurs IA / datacenter en forte croissance ; NVIDIA en position de leader sur le GPU datacenter. Concurrence : AMD, ASIC internes des hyperscalers (TPU, Trainium, etc.). — Information issue du modèle, non sourcée, à confirmer.',
     ARRAY['industry','market','llm_memory'], 'fr', 'llm_memory', DATE '2026-01-01',
     0.40, 'C', 'Mémoire modèle — chiffrer TAM et parts de marché depuis sources primaires.',
     TRUE, '2026-01'),

    ('NVDA', 'fact_qualitative', 'Management & allocation du capital (à vérifier)',
     'Société fondée et dirigée par Jensen Huang (founder-led). Allocation du capital : réinvestissement R&D fort, rachats d''actions, dividende symbolique. — Information issue du modèle, non sourcée, à confirmer.',
     ARRAY['management','capital_allocation','llm_memory'], 'fr', 'llm_memory', DATE '2026-01-01',
     0.40, 'C', 'Mémoire modèle — sourcer grille Outsiders + skin-in-the-game (proxy statement).',
     TRUE, '2026-01'),

    ('NVDA', 'risk', 'Risques principaux (à vérifier)',
     'Risques présumés : concentration client (hyperscalers), contrôles à l''export vers la Chine, cyclicité de la demande IA / risque de sur-commande, intensification concurrentielle (ASIC internes). — Information issue du modèle, non sourcée, à confirmer.',
     ARRAY['risk','llm_memory'], 'fr', 'llm_memory', DATE '2026-01-01',
     0.40, 'C', 'Mémoire modèle — sourcer Item 1A Risk Factors du 10-K.',
     TRUE, '2026-01');

    RAISE NOTICE 'Seed NVDA appliqué : document 10-K FY2026 (id=%) + 11 fact_financial Tier A + 5 entries qualitatives llm_memory.', v_doc_id;
END $$;
