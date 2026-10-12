-- 053 — `cumul_publie`, cinquième valeur de PERIODES (convention #119, arbitrage utilisateur du
-- 2026-10-12).
--
-- #113 (migration 052) avait donné à la DEMANDE le mot pour une fenêtre que LE SYSTÈME reconstruit
-- (`douze_mois_glissants`, depuis des concepts XBRL de flux). Mesuré le 2026-10-12 (NVDA qf_6,
-- réponse #1270, retirée) : le même mot a été employé pour demander autre chose — un cumul que
-- L'ÉMETTEUR PUBLIE DÉJÀ dans son dépôt intermédiaire (le semestre écoulé, avec son comparatif à la
-- même période l'an dernier), que le système n'a aucune raison de recalculer. Confondre les deux a
-- fait recopier la colonne « trois mois » d'un tableau de rapprochement GAAP/non-GAAP sous l'étiquette
-- « six mois », et inventer un comparatif absent du tableau réel (vérifié contre le dépôt EDGAR).
--
-- `cumul_publie` nomme la seconde chose. Elle ne concerne que les lignes routées vers le WEB (un
-- rapprochement non-GAAP, une note de segment — jamais un concept XBRL de flux, que le système sait
-- déjà agréger lui-même sous `douze_mois_glissants`) : `appariement_feed.appliquer_periode` ne la
-- traite pas, elle tombe dans sa branche « inchangé » comme `dernier_bilan`/`sans_periode` — c'est le
-- comportement voulu, pas un oubli.
--
-- ADDITIVE sur une colonne déjà nullable (052) : aucune ligne existante n'est touchée.
BEGIN;

ALTER TABLE public.collection_plan_items DROP CONSTRAINT collection_plan_items_periode;
ALTER TABLE public.collection_plan_items ADD CONSTRAINT collection_plan_items_periode CHECK (
    periode IS NULL
    OR (statut = 'traduit'
        AND periode IN ('exercice_clos', 'douze_mois_glissants', 'dernier_bilan', 'sans_periode',
                         'cumul_publie'))
);

DO $$ DECLARE n int; def text; BEGIN
  SELECT count(*) INTO n FROM pg_constraint WHERE conname = 'collection_plan_items_periode';
  IF n <> 1 THEN RAISE EXCEPTION '053/K1 : contrainte collection_plan_items_periode absente (%)', n; END IF;
  SELECT pg_get_constraintdef(oid) INTO def FROM pg_constraint WHERE conname = 'collection_plan_items_periode';
  IF def NOT LIKE '%cumul_publie%' THEN
    RAISE EXCEPTION '053/K2 : cumul_publie absente de la définition de la contrainte (%)', def;
  END IF;
END $$;

COMMIT;
