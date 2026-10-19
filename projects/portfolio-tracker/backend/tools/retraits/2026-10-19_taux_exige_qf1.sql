-- Arbitrage utilisateur du 2026-10-17 (#137 point 10) : UN taux exigé pour tout le fonds, 10 %, décision
-- du comité (`parametres_du_fonds.taux_exige` du référentiel). L'encadré de qf_1 le reçoit du code ;
-- l'ingrédient `qf_1.cout_du_capital` (estimation à collecter) quitte le référentiel. Les estimations de
-- tiers ne sont plus qu'un point de comparaison : leurs 5 liens d'index sont retirés, les PIÈCES restent
-- au dossier, intactes (MSFT 363/364, NVDA 833/834/835 — WACC 10,9 / 12,0 / 13,0 %, rang C+).
-- Liens retirés (question_coverage.id → entry_id) : 98→363, 289→364, 466→833, 467→834, 468→835.
-- Les mandats 108 (plan 56) et 2443 (plan 221), ouverts sur `cout_du_capital`, demandent un ingrédient
-- qui n'existe plus : abandonnés, jamais supprimés. `framework_version` non montée (précédent
-- #100/#114/#131) : #1209 (NVDA) et #1685 (RVMD) restent en vigueur avec leur coût du capital vide,
-- refaites au prochain passage.
BEGIN;
DO $$ DECLARE n int; m int; BEGIN
  SELECT count(*) INTO n FROM public.question_coverage
   WHERE framework_id = 'qualite_financiere' AND question_id = 'qf_1' AND ingredient_id = 'cout_du_capital'
     AND id IN (98, 289, 466, 467, 468);
  SELECT count(*) INTO m FROM public.framework_mandates
   WHERE id IN (108, 2443) AND statut = 'ouvert' AND question_id = 'qf_1' AND ingredient_id = 'cout_du_capital';
  IF n <> 5 OR m <> 2 THEN
    RAISE EXCEPTION 'taux exigé qf_1 : % lien(s) cout_du_capital (5 attendus), % mandat(s) ouverts (2 attendus)', n, m;
  END IF;
END $$;
DELETE FROM public.question_coverage
 WHERE framework_id = 'qualite_financiere' AND question_id = 'qf_1' AND ingredient_id = 'cout_du_capital'
   AND id IN (98, 289, 466, 467, 468);
UPDATE public.framework_mandates SET statut = 'abandonne' WHERE id IN (108, 2443) AND statut = 'ouvert';
DO $$ DECLARE n int; m int; BEGIN
  SELECT count(*) INTO n FROM public.question_coverage WHERE question_id = 'qf_1' AND ingredient_id = 'cout_du_capital';
  SELECT count(*) INTO m FROM public.framework_mandates
   WHERE question_id = 'qf_1' AND ingredient_id = 'cout_du_capital' AND statut = 'ouvert';
  IF n <> 0 OR m <> 0 THEN
    RAISE EXCEPTION 'taux exigé qf_1 incomplet : % lien(s), % mandat(s) ouverts restants', n, m;
  END IF;
END $$;
COMMIT;
