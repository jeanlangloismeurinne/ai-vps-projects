-- Arbitrage utilisateur du 2026-10-04 (#114) : qf_4 est scindée — le tableau de la dette reste à qf_4
-- (question de mesure), la revue des clauses passe à qf_8 (jugement sur documents officiels).
-- L'ingrédient `clauses_de_sauvegarde` quitte qf_4 pour qf_8 dans le référentiel : ses liens d'index
-- suivent, tels quels (même pièce, même ingrédient, autre question). Aucune pièce n'est touchée.
-- Avant : 13 liens qf_4.clauses_de_sauvegarde (RVMD 298 299 341 342 712 713 746 779 780 781 ;
-- NVDA 394 395 ; MSFT 397), 0 lien qf_8.
BEGIN;
DO $$ DECLARE n int; m int; BEGIN
  SELECT count(*) INTO n FROM public.question_coverage
   WHERE framework_id = 'qualite_financiere' AND question_id = 'qf_4' AND ingredient_id = 'clauses_de_sauvegarde';
  SELECT count(*) INTO m FROM public.question_coverage
   WHERE framework_id = 'qualite_financiere' AND question_id = 'qf_8';
  IF n <> 13 OR m <> 0 THEN RAISE EXCEPTION 'scission qf_4/qf_8 : % lien(s) à déplacer (13 attendus), % déjà sous qf_8 (0 attendu)', n, m; END IF;
END $$;
UPDATE public.question_coverage SET question_id = 'qf_8'
 WHERE framework_id = 'qualite_financiere' AND question_id = 'qf_4' AND ingredient_id = 'clauses_de_sauvegarde';
DO $$ DECLARE n int; m int; BEGIN
  SELECT count(*) INTO n FROM public.question_coverage
   WHERE framework_id = 'qualite_financiere' AND question_id = 'qf_4' AND ingredient_id = 'clauses_de_sauvegarde';
  SELECT count(*) INTO m FROM public.question_coverage
   WHERE framework_id = 'qualite_financiere' AND question_id = 'qf_8' AND ingredient_id = 'clauses_de_sauvegarde';
  IF n <> 0 OR m <> 13 THEN RAISE EXCEPTION 'scission qf_4/qf_8 incomplète : restant qf_4 %, sous qf_8 %', n, m; END IF;
END $$;
COMMIT;
