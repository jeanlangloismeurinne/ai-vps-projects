-- #126, correctif du 2026-10-15 : les 25 fiches écrites par le passage interrompu (plan #256) portent le
-- titre RÉDIGÉ par le collecteur (ex. #1133 « RASolute 302 n'a PAS échoué », que ses extraits ne disent pas).
-- Le titre d'une fiche nomme désormais son document (`worker.titre_de_fiche`) ; ces 25 lignes, citées par
-- aucune réponse, reçoivent ce titre. Anciens titres : 2026-10-15_titres_fiches_1093-1142.json (le titre du
-- collecteur survit aussi dans celui de sa ligne de lecture, sœur de la fiche).
BEGIN;
DO $$ DECLARE n int; BEGIN
  SELECT count(*) INTO n FROM public.knowledge_entries WHERE id BETWEEN 1093 AND 1142 AND source_type <> 'agent_synthesis' AND ticker_id='RVMD';
  IF n <> 25 THEN RAISE EXCEPTION 'titres #126 : % fiches au lieu de 25', n; END IF;
  SELECT count(*) INTO n FROM public.framework_answers WHERE cited_entry_ids && (SELECT array_agg(id) FROM public.knowledge_entries WHERE id BETWEEN 1093 AND 1142);
  IF n <> 0 THEN RAISE EXCEPTION 'titres #126 : % réponse(s) citent déjà ces fiches', n; END IF;
END $$;
UPDATE public.knowledge_entries SET title = 'Extraits — patents.us/assignees/revolution-medicines-inc' WHERE id = 1093;
UPDATE public.knowledge_entries SET title = 'Extraits — drugfuture.com/fda/drugview/220910' WHERE id = 1095;
UPDATE public.knowledge_entries SET title = 'Extraits — biocosm.io/drug/pipeline-daraxonrasib' WHERE id = 1097;
UPDATE public.knowledge_entries SET title = 'Extraits — sec.gov/Archives/edgar/data/1628171/000119312526071563/rvmd-20251231.htm' WHERE id = 1099;
UPDATE public.knowledge_entries SET title = 'Extraits — sec.gov/Archives/edgar/data/2022416/000117891326004136/exhibit_99-1.htm' WHERE id = 1101;
UPDATE public.knowledge_entries SET title = 'Extraits — roche.com/media/releases/med-cor-2026-07-02' WHERE id = 1103;
UPDATE public.knowledge_entries SET title = 'Extraits — biospace.com…analysts-eye-revmeds-pancreatic-cancer-launch-mercks-data-blitz-for-q3-earnings' WHERE id = 1105;
UPDATE public.knowledge_entries SET title = 'Extraits — finance.yahoo.com/healthcare/articles/revolution-medicines-apos-rasonque-launch-152408705.html' WHERE id = 1107;
UPDATE public.knowledge_entries SET title = 'Extraits — inflectionlabs.bio/reports/daraxonrasib-pdac-peak-sales' WHERE id = 1109;
UPDATE public.knowledge_entries SET title = 'Extraits — trialticker.com/news/jiangsu-hengrui-medicine-study-recruiting-nct07232875' WHERE id = 1111;
UPDATE public.knowledge_entries SET title = 'Extraits — clinicaltrials.gov/study/NCT07262567' WHERE id = 1113;
UPDATE public.knowledge_entries SET title = 'Extraits — investors.amgen.com/node/33236/pdf' WHERE id = 1115;
UPDATE public.knowledge_entries SET title = 'Extraits — news.bms.com…S-G12C-Mutated-Locally-Advanced-or-Metastatic-Non-Small-Cell-Lung-/default.aspx' WHERE id = 1117;
UPDATE public.knowledge_entries SET title = 'Extraits — apexonco.com/esmo-2026-preview-more-ras-contenders-emerge' WHERE id = 1119;
UPDATE public.knowledge_entries SET title = 'Extraits — insights.citeline.com…ivals-to-revolutions-rasonque-line-up-in-the-clinic-GKUKFQN5URDAJHQEUHMHFG3THY/' WHERE id = 1121;
UPDATE public.knowledge_entries SET title = 'Extraits — sec.gov/Archives/edgar/data/1628171/000119312526071563/rvmd-20251231.htm' WHERE id = 1123;
UPDATE public.knowledge_entries SET title = 'Extraits — sec.gov/Archives/edgar/data/1628171/000119312526071563/rvmd-20251231.htm' WHERE id = 1125;
UPDATE public.knowledge_entries SET title = 'Extraits — link.springer.com/article/10.1007/s43441-023-00562-w' WHERE id = 1127;
UPDATE public.knowledge_entries SET title = 'Extraits — sec.gov/Archives/edgar/data/1628171/000119312526366931/rvmd-20260826.htm' WHERE id = 1129;
UPDATE public.knowledge_entries SET title = 'Extraits — sec.gov/Archives/edgar/data/1628171/000119312526335104/rvmd-20260630.htm' WHERE id = 1131;
UPDATE public.knowledge_entries SET title = 'Extraits — ir.revmed.com/press-releases' WHERE id = 1133;
UPDATE public.knowledge_entries SET title = 'Extraits — fiercepharma.com…onque-review-documents-pressure-revmed-investors-jitter-over-kras-subgroup-data' WHERE id = 1135;
UPDATE public.knowledge_entries SET title = 'Extraits — apoapenews.com/articles/fda-fast-track-eras-0015-pan-ras-glue-pancreatic/' WHERE id = 1137;
UPDATE public.knowledge_entries SET title = 'Extraits — ir.revmed.com…elease-details/daraxonrasib-demonstrates-unprecedented-overall-survival-benefit' WHERE id = 1139;
UPDATE public.knowledge_entries SET title = 'Extraits — apoapenews.com/articles/rasonque-kras-subtype-fda-review-documents/' WHERE id = 1141;
DO $$ DECLARE n int; BEGIN
  SELECT count(*) INTO n FROM public.knowledge_entries WHERE id BETWEEN 1093 AND 1142 AND source_type <> 'agent_synthesis' AND title NOT LIKE 'Extraits — %';
  IF n <> 0 THEN RAISE EXCEPTION 'titres #126 : % fiche(s) gardent un titre rédigé', n; END IF;
END $$;
COMMIT;
