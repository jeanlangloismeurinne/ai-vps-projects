-- Arbitrage utilisateur du 2026-10-04 : retirer la pièce #774 du dossier RVMD (registre des pièces écartées, #87).
-- Libellé « consommation sur les quatre derniers trimestres », chiffre de l'EXERCICE 2025 (-897,74 MUSD) :
-- bon libellé, mauvais nombre. Produite par la carte du plan #202 (apparieur : `exact` au lieu de `[ttm]`, #112).
BEGIN;
DO $$ DECLARE n int; BEGIN
  SELECT count(*) INTO n FROM public.knowledge_entries WHERE id = 774 AND ticker_id = 'RVMD' AND superseded_by IS NULL;
  IF n <> 1 THEN RAISE EXCEPTION 'écart #774 : % pièce courante RVMD (1 attendue)', n; END IF;
  SELECT count(*) INTO n FROM public.knowledge_entries WHERE superseded_by = 774;
  IF n <> 0 THEN RAISE EXCEPTION 'écart #774 : % pièce(s) supersédée(s) par #774 — à traiter avant', n; END IF;
END $$;
INSERT INTO public.pieces_ecartees (entry_id, ticker_id, ecartee_par, motif, piece, couvertures)
SELECT ke.id, ke.ticker_id, 'utilisateur (arbitrage du 2026-10-04)',
       'Bon libellé, mauvais chiffre : intitulée « flux d''exploitation sur les quatre derniers trimestres », '
       'elle porte le flux de l''EXERCICE 2025 (-897,74 MUSD) ; les douze mois au 30/06/2026 valent -1 223 MUSD. '
       'Carte d''appariement du plan #202 classée `exact` au lieu de `[ttm]` (convention #112).',
       to_jsonb(ke) - 'embedding',
       COALESCE((SELECT jsonb_agg(to_jsonb(qc) ORDER BY qc.question_id, qc.ingredient_id)
                   FROM public.question_coverage qc WHERE qc.entry_id = ke.id), '[]'::jsonb)
  FROM public.knowledge_entries ke WHERE ke.id = 774;
DELETE FROM public.question_coverage WHERE entry_id = 774;
DELETE FROM public.knowledge_entries WHERE id = 774;
DO $$ DECLARE r int; k int; BEGIN
  SELECT count(*) INTO r FROM public.pieces_ecartees WHERE entry_id = 774;
  SELECT count(*) INTO k FROM public.knowledge_entries WHERE id = 774;
  IF r <> 1 OR k <> 0 THEN RAISE EXCEPTION 'écart #774 incomplet : registre %, restant %', r, k; END IF;
END $$;
COMMIT;
