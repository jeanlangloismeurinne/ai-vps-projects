-- Retrait : NVDA qf_6 #1270 (2026-10-12) — chiffres de cumul semestriel FAUX, vérifiés contre le
-- vrai dépôt EDGAR (8-K accession 0001045810-26-000073, EX-99.1 q2fy27pr.htm, table
-- « RECONCILIATION OF GAAP TO NON-GAAP FINANCIAL MEASURES »).
--
-- #1270 affirmait : retraitements_cumul_en_cours = 222 M$ (« cumul S1 FY2027 »),
-- retraitements_cumul_an_passe = 0 M$ (« cumul S1 FY2026 »).
--
-- Le vrai tableau a CINQ colonnes (Three Months Ended : 2026-07-26, 2026-04-26, 2025-07-27 ;
-- Six Months Ended : 2026-07-26, 2025-07-27) ; la ligne « Total impact of non-GAAP adjustments to
-- operating income » vaut 222 / 247 / 101 / 469 / 263. La valeur « 222 » citée par #1270 est la
-- colonne TROIS MOIS (Q2 FY2027), pas SIX MOIS ; la vraie valeur Six Months 2026-07-26 est 469. La
-- valeur « 0 » pour le cumul an passé n'existe NULLE PART dans le tableau réel (la vraie valeur Six
-- Months 2025-07-27 est 263) — ce n'est pas une pièce mal lue, c'est un chiffre sans aucun support.
--
-- Même défaut que #78 (« tous les nombres justes, le fait faux ») : les quatre contrôles du manager
-- gardent la structure (citation présente, pont [E]/[K] satisfaits), jamais le sens. Cause probable :
-- l'entry collectée (#896) ne porte que la colonne trimestrielle du tableau — le plan de collecte
-- (item qf_6.ecart_publie_ajuste, `periode: douze_mois_glissants`) ne demandait pas explicitement le
-- cumul semestriel que l'encadré (#100/#105/#118) exige réellement. Root cause non corrigée ici
-- (dette nommée dans 00-REPRISE.md) — ce retrait ne fait que retirer le chiffre faux du corpus.
--
-- On restaure #1269 (« non établi », honnête, incomplet mais pas fabriqué) comme réponse courante.
BEGIN;

DO $$ DECLARE n int; BEGIN
  SELECT count(*) INTO n FROM public.framework_answers WHERE id = 1270 AND superseded_by IS NULL;
  IF n <> 1 THEN RAISE EXCEPTION 'retrait NVDA qf_6 : #1270 absent ou déjà supersédée (% ligne(s))', n; END IF;
  SELECT count(*) INTO n FROM public.framework_answers WHERE id = 1269 AND superseded_by = 1270;
  IF n <> 1 THEN RAISE EXCEPTION 'retrait NVDA qf_6 : #1269 n''est pas supersédée par #1270 (% ligne(s))', n; END IF;
END $$;

-- ordre load-bearing : la FK `framework_answers_superseded_by_fkey` refuse de supprimer #1270
-- tant qu'une ligne la référence encore.
UPDATE public.framework_answers SET superseded_by = NULL WHERE id = 1269;
DELETE FROM public.framework_answers WHERE id = 1270;

DO $$ DECLARE n int; BEGIN
  SELECT count(*) INTO n FROM public.framework_answers WHERE id = 1270;
  IF n <> 0 THEN RAISE EXCEPTION 'retrait NVDA qf_6 : #1270 toujours présente'; END IF;
  SELECT count(*) INTO n FROM public.framework_answers WHERE id = 1269 AND superseded_by IS NULL;
  IF n <> 1 THEN RAISE EXCEPTION 'retrait NVDA qf_6 : #1269 n''est pas redevenue courante'; END IF;
END $$;

COMMIT;
