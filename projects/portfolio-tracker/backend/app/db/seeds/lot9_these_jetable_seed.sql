-- DRY-RUN LOT 9 — thèse V2 JETABLE #5 sur NVDA (2e ticker), supprimée en fin d'exercice.
-- Ne touche NI la thèse MSFT #4 NI la position #8 (argent réel).
-- La fourchette FIGÉE au validate (validation_json) est délibérément DIFFÉRENTE de la
-- valuation_range courante : c'est ce qui permet de vérifier, sur un vrai run, que la calibration
-- relit le figé (120) et non l'opinion réactualisée (140).
BEGIN;

INSERT INTO theses_v2 (
    id, ticker_id, schema_version, validation_json, research_memo_id, synthesis_analysis_id,
    pre_mortem_acked, risk_matrix_acked, risk_acks, verdict, position_sizing_pct,
    valuation_range, conditions_entree, hypotheses, status, validated_at)
VALUES (
    5, 'NVDA', 'v2.0.0',
    '{"schema_version":"v2.0.0","verdict":"PROCEED","valuation_range":{"low":90.0,"base":120.0,"high":150.0}}'::jsonb,
    3, 7, TRUE, TRUE, '[]'::jsonb, 'PROCEED', 4.0,
    '{"low":100.0,"base":140.0,"high":180.0}'::jsonb,   -- réactualisée par la revue annuelle
    '{}',
    '[
      {"id":"H1","enonce":"la croissance du segment Data Center reste au-dessus de 40 % en glissement annuel",
       "kpi":"croissance Data Center YoY","unite":"%","statut":"invalidee",
       "seuil_alerte":40.0,"seuil_invalidation":25.0,
       "derniere_observation":"18 % au dernier trimestre publie",
       "base_rate":{"taux":0.35,"reference_class":"cycles de capex semiconducteurs"},
       "source_entry_refs":[]},
      {"id":"H2","enonce":"la marge brute se maintient au-dessus de 70 %",
       "kpi":"marge brute","unite":"%","statut":"alerte",
       "seuil_alerte":72.0,"seuil_invalidation":68.0,
       "derniere_observation":"71 % au dernier trimestre",
       "base_rate":{"taux":0.5,"reference_class":"fondeurs sans fab en position dominante"},
       "source_entry_refs":[]},
      {"id":"H3","enonce":"la concentration client reste sous 40 % du chiffre d affaires",
       "kpi":"part des 4 premiers clients","unite":"%","statut":"active",
       "seuil_alerte":40.0,"seuil_invalidation":50.0,
       "base_rate":{"taux":0.3,"reference_class":"fournisseurs d hyperscalers"},
       "source_entry_refs":[]}
     ]'::jsonb,
    'active', '2026-02-10T09:00:00+00');

SELECT setval('theses_v2_id_seq', GREATEST(5, (SELECT MAX(id) FROM theses_v2)));

-- Position V2 jetable. NVDA porte DÉJÀ une position V1 (#3) : l'exclusivité du CHECK est
-- par LIGNE, pas par ticker (convention #34) — c'est exactement le cas qu'elle autorise.
INSERT INTO portfolio_positions (ticker_id, shares, purchase_price, purchase_price_eur,
                                 purchase_date, status, thesis_v2_id)
VALUES ('NVDA', 10, 100, 100, DATE '2026-02-10', 'open', 5);

-- L'ANTÉCÉDENT que le pont de sortie exige : la revue annuelle (mode 6) qui a conclu SORTIR et
-- routé vers le plan de sortie. C'est le point d'entrée posé par le lot 8.
INSERT INTO monitoring_sessions_v2 (thesis_v2_id, ticker_id, mode, trigger_type, trigger_label,
                                    result_json, context_sent, raw_content, verdict,
                                    routing_suggestion, status, provider_used, model_used,
                                    tokens_in, tokens_out, cost_usd, completed_at)
VALUES (5, 'NVDA', 6, 'manual', 'dry-run lot 9 — revue annuelle',
        '{"schema_version":"v2.0.0","thesis_id":5,"verdict":"SORTIR","exit_trigger":"hypothese_invalidee",
          "rationale":"H1 invalidee : la croissance Data Center est passee sous le seuil pre-enregistre",
          "hypotheses_reviewed":[],
          "rendement_prospectif":{"iv_reactualisee":140.0,"rendement_attendu_pct":3.0,
                                  "cout_opportunite":"vs le reste du portefeuille","suffisant":false}}'::jsonb,
        '(seed dry-run)', '(seed dry-run)', 'SORTIR', 'exit_plan', 'completed',
        'deepinfra', 'seed', 0, 0, 0, NOW());

COMMIT;

SELECT id, ticker_id, status, verdict FROM theses_v2 WHERE id = 5;
SELECT id, ticker_id, shares, thesis_v2_id FROM portfolio_positions WHERE thesis_v2_id = 5;
SELECT id, mode, verdict, routing_suggestion FROM monitoring_sessions_v2 WHERE thesis_v2_id = 5;
