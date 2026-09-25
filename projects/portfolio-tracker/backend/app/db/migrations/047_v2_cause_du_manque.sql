-- Migration 047 — LA CAUSE D'UN MANQUE DE COLLECTE (chantier v3, lot 6 maillon 2).
--
-- ADDITIVE : une colonne neuve sur `framework_mandates`, remplie pour l'historique, gardée par un
-- CHECK. Aucune ligne retirée, aucun motif réécrit.
--
-- L'ARBITRAGE QUI LA COMMANDE (comité, 2026-09-25, n°3). La page d'un titre répond d'abord à
-- « peut-on décider ? ». Quand le dossier est incomplet, l'alerte nomme ce qui manque ET POURQUOI le
-- système n'a pas pu l'obtenir : « recherche épuisée, source indisponible, question sans source
-- possible ». Un fonds distingue ces trois cas parce qu'ils appellent trois suites : on renonce
-- (la donnée n'est pas publiée), on relance (la base était en panne, le temps a manqué), on
-- reformule la question (elle n'a pas de source pour cette société).
--
-- L'ÉCART MESURÉ (2026-09-25). `origine` ne sépare que « le traducteur savait » (`inobtenable`) de
-- « la collecte a échoué » (`echec_collecte`). Sur les 28 échecs de collecte en base, 12 sont des
-- PANNES de notre outil (9 dépassements du budget de 180 s, 3 sorties non conformes du
-- search-worker) et 16 des recherches allées au bout. Les deux étaient confondus : l'écran aurait dit
-- « introuvable » pour une donnée qu'une simple relance aurait pu ramener.
--
-- DÉTENTEUR DE LA CAUSE : LE PRODUCTEUR (`collecte_executor`, contrat `cause_manque_schema`). La
-- reprise de l'historique ci-dessous est la SEULE lecture de la prose du motif, faite une fois, par
-- les préfixes exacts qu'écrit ce producteur — jamais un classement de modèle. La garde finale lève
-- si une seule ligne de collecte reste sans cause : un préfixe inconnu est une panne de la reprise,
-- pas une ligne à laisser vide.

BEGIN;

ALTER TABLE public.framework_mandates ADD COLUMN IF NOT EXISTS cause text;

-- ── Reprise de l'historique, par les préfixes exacts du producteur ─────────────────────────────
UPDATE public.framework_mandates SET cause = 'sans_source_possible'
 WHERE origine = 'inobtenable' AND cause IS NULL;

UPDATE public.framework_mandates SET cause = 'recherche_epuisee'
 WHERE origine = 'echec_collecte' AND cause IS NULL AND (
       motif LIKE 'search-worker n''a rien retenu pour %'
    OR motif LIKE 'search-worker: aucune entry persistée pour %'
    OR motif LIKE 'poste EDGAR ''%'' non fondé pour %'
    OR motif ~ '^appariement « .* » inexécutable sur le dépôt : ');

UPDATE public.framework_mandates SET cause = 'source_indisponible'
 WHERE origine = 'echec_collecte' AND cause IS NULL AND (
       motif LIKE 'collecte web abandonnée : budget de %'
    OR motif LIKE 'collecte web échouée (%'
    OR motif LIKE 'recherche web indisponible : %'
    OR motif LIKE 'socle EDGAR indisponible pour %'
    OR motif ~ '^appariement « .* » échoué \(');

-- ── 047/K1 : aucune ligne de collecte ne reste sans cause ──────────────────────────────────────
DO $$
DECLARE n int;
BEGIN
  SELECT count(*) INTO n FROM public.framework_mandates
   WHERE origine IN ('inobtenable', 'echec_collecte') AND cause IS NULL;
  IF n <> 0 THEN
    RAISE EXCEPTION '047/K1 : % mandat(s) de collecte sans cause après reprise — un préfixe de motif inconnu du producteur ; le classer à la main, jamais le laisser vide', n;
  END IF;
END $$;

-- ── Le contrat, en base : la cause est celle du collecteur, et seulement du collecteur ─────────
-- Un mandat manager/comité n'a pas de cause de collecte (il n'a rien collecté) ; un mandat du
-- collecteur en a toujours une ; « sans source possible » est exactement `inobtenable`.
ALTER TABLE public.framework_mandates DROP CONSTRAINT IF EXISTS framework_mandates_cause;
ALTER TABLE public.framework_mandates ADD CONSTRAINT framework_mandates_cause CHECK (
      (origine IN ('inobtenable', 'echec_collecte')) = (cause IS NOT NULL)
  AND (origine = 'inobtenable') = (cause IS NOT DISTINCT FROM 'sans_source_possible')
  AND (cause IS NULL OR cause IN ('recherche_epuisee', 'source_indisponible', 'sans_source_possible'))
);

COMMENT ON COLUMN public.framework_mandates.cause IS
    'Pourquoi la collecte n''a pas obtenu l''ingrédient (migration 047) : recherche_epuisee | '
    'source_indisponible | sans_source_possible. Déclarée par collecte_executor ; NULL pour un '
    'mandat manager/comité.';

COMMIT;
