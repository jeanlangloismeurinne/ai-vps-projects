-- Retrait : passage défendabilité du 2026-10-14 (RVMD plan #253, NVDA plan #254) — arbitrage utilisateur du 2026-10-15.
--
-- Relues contre EDGAR, cinq fiches du collecteur disent PLUS que leur document (extrapolation, fausse
-- attribution, paraphrase inventée, trois documents dans une fiche). L'analyste les a recopiées
-- fidèlement ; les quatre contrôles du manager ne pouvaient pas le voir (#78, garde de structure, pas
-- de sens). Arbitrage : « tout retirer » — les fiches partent au registre des pièces écartées (#87),
-- les onze réponses qui s'appuient sur elles sont supprimées (#78 : une donnée fabriquée laissée en base
-- servirait de dossier réel à la suite). Remède de forme au collecteur (extraits littéraux vérifiés,
-- commentaire séparé) : convention #126.
--
-- Retirés : réponses #1399-#1404 (RVMD, restaure #1316-#1321 comme courantes) et #1405-#1409 (NVDA, aucune
-- réponse antérieure : le chapitre redevient non instruit) ; pièces #1025, #1028, #1069, #1086, #1087.
-- Conservés : les mandats ouverts (983-986 RVMD, 2849 NVDA — les questions restent à instruire), les
-- autres pièces des plans #253/#254. Trace : 2026-10-15_defendabilite_pieces_infideles_reponses.json.
BEGIN;

DO $$ DECLARE n int; BEGIN
  SELECT count(*) INTO n FROM public.framework_answers
   WHERE id BETWEEN 1399 AND 1409 AND framework = 'defendabilite' AND superseded_by IS NULL;
  IF n <> 11 THEN RAISE EXCEPTION 'retrait 2026-10-15 : % réponse(s) courante(s) parmi #1399-#1409 au lieu de 11', n; END IF;
  SELECT count(*) INTO n FROM public.framework_answers WHERE id BETWEEN 1316 AND 1321 AND superseded_by BETWEEN 1399 AND 1404;
  IF n <> 6 THEN RAISE EXCEPTION 'retrait 2026-10-15 : % des réponses #1316-#1321 supersédées par #1399-#1404 au lieu de 6', n; END IF;
  SELECT count(*) INTO n FROM public.framework_answers WHERE superseded_by BETWEEN 1405 AND 1409;
  IF n <> 0 THEN RAISE EXCEPTION 'retrait 2026-10-15 : % réponse(s) NVDA antérieure(s) à restaurer — script à revoir', n; END IF;
  SELECT count(*) INTO n FROM public.comite_decisions WHERE answer_id BETWEEN 1399 AND 1409;
  IF n <> 0 THEN RAISE EXCEPTION 'retrait 2026-10-15 : % décision(s) du comité sur ces réponses — ne pas retirer', n; END IF;
  SELECT count(*) INTO n FROM public.knowledge_entries
   WHERE id IN (1025, 1028, 1069, 1086, 1087) AND superseded_by IS NULL;
  IF n <> 5 THEN RAISE EXCEPTION 'retrait 2026-10-15 : % pièce(s) courante(s) au lieu de 5', n; END IF;
  SELECT count(*) INTO n FROM public.knowledge_entries WHERE superseded_by IN (1025, 1028, 1069, 1086, 1087);
  IF n <> 0 THEN RAISE EXCEPTION 'retrait 2026-10-15 : % pièce(s) supersédée(s) par une fiche retirée — à traiter avant', n; END IF;
  SELECT count(*) INTO n FROM public.framework_answers
   WHERE id NOT BETWEEN 1399 AND 1409 AND cited_entry_ids && ARRAY[1025, 1028, 1069, 1086, 1087];
  IF n <> 0 THEN RAISE EXCEPTION 'retrait 2026-10-15 : % autre(s) réponse(s) citent une fiche retirée', n; END IF;
END $$;

-- ordre load-bearing : la FK `framework_answers_superseded_by_fkey` refuse de supprimer une réponse
-- tant qu'une autre la référence.
UPDATE public.framework_answers SET superseded_by = NULL WHERE id BETWEEN 1316 AND 1321;
DELETE FROM public.framework_answers WHERE id BETWEEN 1399 AND 1409;

INSERT INTO public.pieces_ecartees (entry_id, ticker_id, ecartee_par, motif, piece, couvertures)
SELECT ke.id, ke.ticker_id, 'utilisateur (arbitrage du 2026-10-15)', m.motif,
       to_jsonb(ke) - 'embedding',
       COALESCE((SELECT jsonb_agg(to_jsonb(qc) ORDER BY qc.question_id, qc.ingredient_id)
                   FROM public.question_coverage qc WHERE qc.entry_id = ke.id), '[]'::jsonb)
  FROM public.knowledge_entries ke
  JOIN (VALUES
    (1025, 'Fausse attribution : présentée comme tirée du 10-Q du 30/06/2026, elle porte les échéances de brevets '
           '2031-2045, qui figurent au 10-K 2025 et non au 10-Q ; elle ajoute « la société indique NCE 2031 / ODE 2033 », '
           'impossible avant l''approbation du 26/08. Une fausse attribution est une fausse fraîcheur (#79).'),
    (1028, 'Extrapolation du collecteur sous l''autorité du document : la R&D de 738,9 M$ est juste, mais « un programme '
           'complet représenterait de l''ordre de 2 à 4 Md$ sur 6-8 ans » n''est pas dans le 10-Q ; présentée comme '
           'relevé tier A, reprise par mo_1/mo_2.'),
    (1069, 'Une fiche, trois documents (article Reuters, 10-K, pièce #1019) sous une seule adresse (#28) ; la charge '
           'Chine de 4,5 Md$ y revient sans sa pièce (dette D-me6).'),
    (1086, 'Paraphrase inventée : « elevated memory and systems prices » (prix des composants achetés) est lu comme une '
           'réaction des volumes aux prix de NVIDIA ; mo_6 en tire un raisonnement faux.'),
    (1087, 'Paraphrase inventée : « ASP plus élevé » et « demande excédant l''offre » sont absents du CFO Commentary '
           'que la fiche cite.')
  ) AS m(id, motif) ON m.id = ke.id;
DELETE FROM public.question_coverage WHERE entry_id IN (1025, 1028, 1069, 1086, 1087);
DELETE FROM public.knowledge_entries WHERE id IN (1025, 1028, 1069, 1086, 1087);

DO $$ DECLARE n int; BEGIN
  SELECT count(*) INTO n FROM public.framework_answers WHERE id BETWEEN 1399 AND 1409;
  IF n <> 0 THEN RAISE EXCEPTION 'retrait 2026-10-15 : réponses encore présentes'; END IF;
  SELECT count(*) INTO n FROM public.framework_answers
   WHERE ticker_id = 'RVMD' AND framework = 'defendabilite' AND superseded_by IS NULL;
  IF n <> 6 THEN RAISE EXCEPTION 'retrait 2026-10-15 : % réponse(s) défendabilité RVMD courante(s) au lieu de 6', n; END IF;
  SELECT count(*) INTO n FROM public.framework_answers
   WHERE ticker_id = 'NVDA' AND framework = 'defendabilite' AND superseded_by IS NULL;
  IF n <> 0 THEN RAISE EXCEPTION 'retrait 2026-10-15 : % réponse(s) défendabilité NVDA courante(s) au lieu de 0', n; END IF;
  SELECT count(*) INTO n FROM public.pieces_ecartees WHERE entry_id IN (1025, 1028, 1069, 1086, 1087);
  IF n <> 5 THEN RAISE EXCEPTION 'retrait 2026-10-15 : registre % au lieu de 5', n; END IF;
  SELECT count(*) INTO n FROM public.knowledge_entries WHERE id IN (1025, 1028, 1069, 1086, 1087);
  IF n <> 0 THEN RAISE EXCEPTION 'retrait 2026-10-15 : pièces encore au dossier'; END IF;
END $$;

COMMIT;
