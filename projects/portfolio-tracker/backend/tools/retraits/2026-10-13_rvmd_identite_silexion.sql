-- Retrait : passage RVMD × defendabilite du 2026-10-13 (plan #238) joué sur l'HORLOGE DE SILEXION (#122).
--
-- `resolve_cik_for_ticker` déduisait le CIK de l'émetteur de la pièce EDGAR la plus récente du dossier.
-- La collecte du maillon 1 a rangé sous RVMD un communiqué de Silexion Therapeutics (CIK 2022416,
-- pièce #917, 2026-09-30, légitime en soi : un concurrent cité au 10-K). Au maillon 2, l'horloge de
-- RVMD a donc été celle de Silexion : ses 11 8-K (dont deux avis de radiation Nasdaq, item 3.01) ont
-- été lus et écrits comme « lectures de dépôts » DE RVMD (#932-#942) et joints d'office au dossier de
-- l'analyste comme faits postérieurs de l'émetteur ; l'approbation FDA de RVMD (8-K du 26/08) et ses
-- baux (27/08) ne figuraient plus dans l'horloge. Les six réponses #1304-#1309 sont nées de ce dossier
-- (mo_3/mo_5 fondent une « érosion » sur Silexion ; mo_3 se contredit : « la barrière s'élargit » / en
-- érosion). Code corrigé (#122 : CIK lu au registre SEC depuis le symbole) ; ce script retire les
-- écrits, il ne corrige rien.
--
-- Retirés : réponses #1304-#1309 (restaure #689-#694 comme courantes) ; pièces #932-#942.
-- Conservés : #917/#920 (communiqué Silexion, pièce de CONCURRENT légitime pour mo_3/mo_5) et les
-- autres pièces collectées par le plan #238 (#912-#931), liens et mandats du plan.
-- Trace : 2026-10-13_rvmd_identite_silexion_reponses.json, ..._pieces.txt.
BEGIN;

DO $$ DECLARE n int; BEGIN
  SELECT count(*) INTO n FROM public.framework_answers
   WHERE id BETWEEN 1304 AND 1309 AND ticker_id = 'RVMD' AND framework = 'defendabilite' AND superseded_by IS NULL;
  IF n <> 6 THEN RAISE EXCEPTION 'retrait #122 : % réponse(s) courante(s) parmi #1304-#1309 au lieu de 6', n; END IF;
  SELECT count(*) INTO n FROM public.framework_answers WHERE id BETWEEN 689 AND 694 AND superseded_by BETWEEN 1304 AND 1309;
  IF n <> 6 THEN RAISE EXCEPTION 'retrait #122 : % des réponses #689-#694 supersédées par #1304-#1309 au lieu de 6', n; END IF;
  SELECT count(*) INTO n FROM public.knowledge_entries
   WHERE id BETWEEN 932 AND 942 AND ticker_id = 'RVMD' AND 'lecture_du_depot' = ANY(tags)
     AND source_url LIKE '%/edgar/data/2022416/%';
  IF n <> 11 THEN RAISE EXCEPTION 'retrait #122 : % pièce(s) Silexion parmi #932-#942 au lieu de 11', n; END IF;
  SELECT count(*) INTO n FROM public.comite_decisions WHERE answer_id BETWEEN 1304 AND 1309;
  IF n <> 0 THEN RAISE EXCEPTION 'retrait #122 : % décision(s) du comité sur ces réponses — ne pas retirer', n; END IF;
END $$;

-- ordre load-bearing : la FK `framework_answers_superseded_by_fkey` refuse de supprimer une réponse
-- tant qu'une autre la référence.
UPDATE public.framework_answers SET superseded_by = NULL WHERE id BETWEEN 689 AND 694;
DELETE FROM public.framework_answers WHERE id BETWEEN 1304 AND 1309;
DELETE FROM public.knowledge_entries WHERE id BETWEEN 932 AND 942;

DO $$ DECLARE n int; BEGIN
  SELECT count(*) INTO n FROM public.framework_answers WHERE id BETWEEN 1304 AND 1309;
  IF n <> 0 THEN RAISE EXCEPTION 'retrait #122 : réponses encore présentes'; END IF;
  SELECT count(*) INTO n FROM public.framework_answers
   WHERE ticker_id = 'RVMD' AND framework = 'defendabilite' AND superseded_by IS NULL;
  IF n <> 6 THEN RAISE EXCEPTION 'retrait #122 : % réponse(s) défendabilité RVMD courante(s) au lieu de 6', n; END IF;
  SELECT count(*) INTO n FROM public.knowledge_entries
   WHERE ticker_id = 'RVMD' AND 'lecture_du_depot' = ANY(tags) AND source_url LIKE '%/edgar/data/2022416/%';
  IF n <> 0 THEN RAISE EXCEPTION 'retrait #122 : lectures Silexion encore au dossier RVMD'; END IF;
END $$;

COMMIT;
