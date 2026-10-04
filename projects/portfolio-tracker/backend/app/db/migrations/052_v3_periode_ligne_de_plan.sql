-- 052 — La PÉRIODE d'une ligne de plan de collecte (convention #113, arbitrage du 2026-10-04).
--
-- Un gérant écrit dans sa demande « sur douze mois glissants » ou « sur l'exercice clos » ; le système
-- l'écrivait dans la phrase (`metrique`) et laissait l'aval la deviner. Mesuré le 2026-10-03 (RVMD,
-- plans #200/#202) : « flux d'exploitation sur les quatre derniers trimestres » lu à l'exercice clos 2/2,
-- pièce #774 « bon libellé, mauvais chiffre ». La demande DÉCLARE désormais la période, vocabulaire fermé.
--
-- ADDITIVE : nullable, car les lignes des plans antérieurs n'en ont pas (NULL = plan d'avant #113, pas un
-- cinquième état). Une ligne `inobtenable` n'en porte jamais (elle n'a rien à lire).
BEGIN;

ALTER TABLE public.collection_plan_items ADD COLUMN periode TEXT NULL;
ALTER TABLE public.collection_plan_items ADD CONSTRAINT collection_plan_items_periode CHECK (
    periode IS NULL
    OR (statut = 'traduit'
        AND periode IN ('exercice_clos', 'douze_mois_glissants', 'dernier_bilan', 'sans_periode'))
);

DO $$ DECLARE n int; BEGIN
  SELECT count(*) INTO n FROM information_schema.columns
   WHERE table_schema = 'public' AND table_name = 'collection_plan_items' AND column_name = 'periode';
  IF n <> 1 THEN RAISE EXCEPTION '052/K1 : colonne periode absente (%)', n; END IF;
  SELECT count(*) INTO n FROM pg_constraint WHERE conname = 'collection_plan_items_periode';
  IF n <> 1 THEN RAISE EXCEPTION '052/K2 : contrainte collection_plan_items_periode absente (%)', n; END IF;
  SELECT count(*) INTO n FROM public.collection_plan_items WHERE periode IS NOT NULL;
  IF n <> 0 THEN RAISE EXCEPTION '052/K3 : % ligne(s) d''un plan antérieur portent une période', n; END IF;
END $$;

COMMIT;
