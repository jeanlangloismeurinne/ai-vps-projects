-- Arbitrage utilisateur du 2026-10-17 (#137 point 12) : ma_2 se juge sur des INDICES OBSERVABLES (prix
-- payé, devenir de l'activité acquise, dépréciations et abandons), jamais sur « ce qu'une acquisition a
-- rapporté », que personne ne publie. L'ingrédient `resultat_obtenu` quitte le référentiel ;
-- `devenir_de_l_activite_acquise` le remplace. Ses 11 liens d'index suivent la pièce, lue une à une
-- (aucune pièce n'est touchée) :
--   → acquisitions_realisees (prix payé, ce qui a été acquis) : RVMD 1385/1386 (EQRx : ~1,1 Md$ de
--     trésorerie, programmes arrêtés à la clôture), 1387 (Warp Drive 2018, prix) ; NVDA 1492/1493
--     (licence Groq), 1494/1495 (historique des acquisitions), 1496/1497 (Groq : 17 Md$, écart
--     d'acquisition 14,4 Md$) ;
--   → devenir_de_l_activite_acquise : RVMD 1383/1384 (T2 2026 : programmes RAS(ON) issus de Warp Drive,
--     dossier daraxonrasib accepté par la FDA).
-- Le mandat 2975 (NVDA, plan 267, `resultat_obtenu`, ouvert) demande un ingrédient qui n'existe plus :
-- abandonné, jamais supprimé. `framework_version` non montée (précédent #100/#114/#131) : les réponses
-- #1452 (RVMD) et #1500 (NVDA) restent l'historique de ma_2, refaites au prochain passage.
BEGIN;
DO $$ DECLARE n int; m int; BEGIN
  SELECT count(*) INTO n FROM public.question_coverage
   WHERE framework_id = 'management_capital' AND question_id = 'ma_2' AND ingredient_id = 'resultat_obtenu';
  SELECT count(*) INTO m FROM public.framework_mandates WHERE id = 2975 AND statut = 'ouvert'
     AND question_id = 'ma_2' AND ingredient_id = 'resultat_obtenu';
  IF n <> 11 OR m <> 1 THEN
    RAISE EXCEPTION 'reformulation ma_2 : % lien(s) resultat_obtenu (11 attendus), mandat 2975 ouvert : % (1 attendu)', n, m;
  END IF;
END $$;
UPDATE public.question_coverage SET ingredient_id = 'devenir_de_l_activite_acquise'
 WHERE framework_id = 'management_capital' AND question_id = 'ma_2' AND ingredient_id = 'resultat_obtenu'
   AND entry_id IN (1383, 1384);
UPDATE public.question_coverage SET ingredient_id = 'acquisitions_realisees'
 WHERE framework_id = 'management_capital' AND question_id = 'ma_2' AND ingredient_id = 'resultat_obtenu'
   AND entry_id IN (1385, 1386, 1387, 1492, 1493, 1494, 1495, 1496, 1497);
UPDATE public.framework_mandates SET statut = 'abandonne' WHERE id = 2975 AND statut = 'ouvert';
DO $$ DECLARE n int; a int; d int; BEGIN
  SELECT count(*) INTO n FROM public.question_coverage
   WHERE framework_id = 'management_capital' AND question_id = 'ma_2' AND ingredient_id = 'resultat_obtenu';
  SELECT count(*) INTO a FROM public.question_coverage
   WHERE framework_id = 'management_capital' AND question_id = 'ma_2' AND ingredient_id = 'acquisitions_realisees';
  SELECT count(*) INTO d FROM public.question_coverage
   WHERE framework_id = 'management_capital' AND question_id = 'ma_2' AND ingredient_id = 'devenir_de_l_activite_acquise';
  IF n <> 0 OR a <> 12 OR d <> 2 THEN
    RAISE EXCEPTION 'reformulation ma_2 incomplète : resultat_obtenu %, acquisitions_realisees % (12), devenir % (2)', n, a, d;
  END IF;
END $$;
COMMIT;
