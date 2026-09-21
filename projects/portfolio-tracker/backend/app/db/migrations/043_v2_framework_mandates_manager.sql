-- Migration 043 — RÉCONCILIER `framework_mandates` avec le mandat du MANAGER (chantier v3, lot 4).
--
-- ADDITIVE et RÉVERSIBLE : aucune donnée touchée, aucune colonne retirée, aucune ligne existante
-- rejetée par les CHECK neufs (les 16 lignes du chemin collecteur — origine `inobtenable`/
-- `echec_collecte`, `statut='ouvert'`, `ingredient_id` renseigné — satisfont `forme` ET `trace`).
--
-- L'ÉCART À RÉSOUDRE (#76). La table (039) est née pour le TRADUCTEUR : un mandat par INGRÉDIENT
-- (`ingredient_id NOT NULL`), sans texte de mandat exécutable. Le contrat `FrameworkMandate`
-- (manager/comité) est par QUESTION, porte un `mandat` EXÉCUTABLE, un `ticker_id`, et un cycle de
-- vie `ouvert → servi` avec l'avant/après du statut de la réponse (T8). Un `ingredient_id` bidon sur
-- un mandat manager serait un faux (#76) : `ingredient_id` devient donc NULLABLE, et un CHECK par
-- ORIGINE dit laquelle des deux formes chaque ligne doit porter.
--
-- ORDRE DU CHANTIER — l'AGENT dicte la table. Le contrat `FrameworkMandate`, l'agent `manager.py`
-- et la persistance `manager_persist.py` sont écrits et éprouvés AVANT cette migration : ces
-- colonnes et ces CHECK sont la PROJECTION de `FrameworkMandate` (dont
-- `_un_etat_porte_exactement_sa_trace`), pas une conception de schéma indépendante. Éprouvés en
-- négatif par `checks/check_manager_persist.py` §5 (la base REFUSE une forme ou une trace interdite).
--
-- ⚠️ NOMMAGE. Le contrat appelle le cycle de vie `etat` ; la colonne 039 s'appelle `statut` et
-- l'index partiel `idx_framework_mandates_ouvert` la lit. On garde `statut` et la persistance mappe
-- `etat`↔`statut` — deux nomenclatures d'accord restent deux nomenclatures (#46), comme
-- `framework_answers` garde `rang_degrade`/`ingredients`.

BEGIN;

-- Un mandat MANAGER est par QUESTION, sans ingrédient (§3.1). Le chemin collecteur continue de le
-- remplir ; un CHECK par origine (plus bas) le rend obligatoire là où il a un sens.
ALTER TABLE public.framework_mandates ALTER COLUMN ingredient_id DROP NOT NULL;

-- Le mandat EXÉCUTABLE (contrat `FrameworkMandate.mandat`) — ce qui remplace les sacs de mots-clefs
-- de `SYNTHESIS_TARGETS` (§5.1). Le ticker (le contrat le porte ; le chemin collecteur le résout via
-- `plan_id → collection_plans`, d'où NULLABLE côté colonne).
ALTER TABLE public.framework_mandates ADD COLUMN mandat    text;
ALTER TABLE public.framework_mandates ADD COLUMN ticker_id text REFERENCES public.tickers(id);

-- Le CYCLE DE VIE (T8) : la trace de consommation, projection de `FrameworkMandate`
-- (`statut_avant`/`statut_apres`/`consomme_at`/`entry_ids_produits`). Le tableau est NON NULL à '{}'
-- pour qu'« aucune entry produite » soit une valeur mesurée (un tableau NULL se lirait comme un oubli
-- du producteur) et que le CHECK `trace` sur un mandat `ouvert` puisse l'exiger vide.
ALTER TABLE public.framework_mandates ADD COLUMN statut_avant       text;
ALTER TABLE public.framework_mandates ADD COLUMN statut_apres       text;
ALTER TABLE public.framework_mandates ADD COLUMN consomme_at        timestamptz;
ALTER TABLE public.framework_mandates ADD COLUMN entry_ids_produits integer[] NOT NULL DEFAULT '{}';

-- `comite` rejoint le vocabulaire des origines : un renvoi du comité (§8.2) produit le MÊME mandat
-- qu'un renvoi manager — un seul canal, deux émetteurs (contrat `FrameworkMandate.origine`).
ALTER TABLE public.framework_mandates DROP CONSTRAINT framework_mandates_origine;
ALTER TABLE public.framework_mandates ADD CONSTRAINT framework_mandates_origine
    CHECK (origine IN ('inobtenable', 'echec_collecte', 'manager_renvoi', 'comite'));

-- La FORME par origine (#76) : le chemin collecteur NOMME un ingrédient (et n'a pas de mandat
-- exécutable) ; le chemin manager/comité porte un mandat + un ticker et JAMAIS d'ingrédient.
ALTER TABLE public.framework_mandates ADD CONSTRAINT framework_mandates_forme CHECK (
    (origine IN ('inobtenable', 'echec_collecte') AND ingredient_id IS NOT NULL)
    OR
    (origine IN ('manager_renvoi', 'comite')
        AND mandat IS NOT NULL AND ticker_id IS NOT NULL AND ingredient_id IS NULL)
);

-- La TRACE par état — projection EXACTE de `FrameworkMandate._un_etat_porte_exactement_sa_trace` :
-- un `ouvert` n'a pas de suite (pas d'après, pas d'instant, aucune entry produite) ; un `servi`
-- porte l'avant, l'après ET l'instant. `statut_apres == statut_avant` reste licite (une recherche
-- qui ne trouve rien laisse la question non_fondable — c'est une information, pas une violation, T8).
-- `abandonne` n'est contraint par rien, comme dans le contrat.
ALTER TABLE public.framework_mandates ADD CONSTRAINT framework_mandates_trace CHECK (
    (statut = 'ouvert'
        AND statut_apres IS NULL AND consomme_at IS NULL
        AND coalesce(array_length(entry_ids_produits, 1), 0) = 0)
    OR
    (statut = 'servi'
        AND statut_avant IS NOT NULL AND statut_apres IS NOT NULL AND consomme_at IS NOT NULL)
    OR
    (statut = 'abandonne')
);

COMMIT;
