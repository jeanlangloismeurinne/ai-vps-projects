-- Migration 041 — le POSTE nommé par le traducteur (chantier v3, lot 3 maillon 4).
--
-- ADDITIVE : une colonne NULLABLE sur une table neuve du lot 2c, aucune donnée existante touchée,
-- aucune colonne retirée. Réversible par `ALTER TABLE … DROP COLUMN poste`.
--
-- POURQUOI CETTE COLONNE (mesure du 2026-09-14, `tools/cartographier_xbrl.py` + 3 plans réels)
-- ------------------------------------------------------------------------------------------
-- L'appariement d'une ligne de plan vers un poste du socle EDGAR se faisait en AVAL, par
-- sous-chaînes cherchées dans `metrique` — une phrase écrite pour un humain. Sur les 3 plans réels
-- de `qualite_financiere` (NVDA / MSFT / RVMD), 5 des 7 lignes routées vers EDGAR l'étaient à tort :
-- des « clauses de sauvegarde en cas de cession d'actifs » liées au chiffre d'affaires parce que la
-- phrase contenait « ventes ». Le lien de couverture aurait porté le bon libellé en face du MAUVAIS
-- nombre — tous les nombres justes, le fait faux (#43).
--
-- Le correctif ne consiste pas à affiner la table de sous-chaînes mais à ne plus DEVINER : le
-- traducteur, seul à savoir ce qu'il a voulu désigner, NOMME le poste dans un vocabulaire fermé
-- (`edgar_feed.POSTES`), et l'aval ne fait plus qu'une égalité.
--
-- ORDRE DU CHANTIER — l'AGENT dicte la table, comme en 039 : `CollectionPlanItem.poste` et
-- `poste_retenu()` sont écrits avant cette migration ; la colonne est la projection de l'objet.
--
-- POURQUOI PAS DE CHECK D'APPARTENANCE AU CATALOGUE
-- -------------------------------------------------
-- La liste des postes est détenue par `edgar_feed.POSTES` (#46). L'énumérer ici en `CHECK (poste IN
-- (…))` fabriquerait un second détenteur, d'accord avec le premier aujourd'hui et divergent au
-- prochain poste ajouté — et la divergence serait SILENCIEUSE côté base (un INSERT refusé pour un
-- poste parfaitement valide). L'appartenance se vérifie contre le détenteur, dans `poste_retenu()`,
-- qui route au web un poste inconnu au lieu de lever : une manque coûte un appel web, un faux
-- appariement corrompt (#60).
--
-- Ce que la base garde, en revanche, c'est l'INVARIANT DE STATUT, qui ne dépend d'aucun vocabulaire :
-- une ligne `inobtenable` ne peut pas porter de poste. Si l'on sait exactement où prendre le
-- chiffre, on ne déclare pas qu'aucune source ne le produit — les deux ensemble sont une ligne qui
-- se contredit. C'est le prolongement exact de `collection_plan_items_charge` (039), et il est
-- éprouvé en négatif par `checks/check_collecte_persist.py`.

BEGIN;

ALTER TABLE public.collection_plan_items
    ADD COLUMN IF NOT EXISTS poste text;

COMMENT ON COLUMN public.collection_plan_items.poste IS
    'Poste du socle EDGAR nommé par le traducteur (vocabulaire fermé `edgar_feed.POSTES`), ou NULL '
    'si l''ingrédient n''est pas un niveau brut déposé tel quel. Remplace l''appariement par '
    'sous-chaînes supprimé le 2026-09-14 (5 faux appariements sur 7 mesurés).';

-- L'ancienne contrainte de charge ne connaît pas `poste` : on la remplace par la même, étendue.
ALTER TABLE public.collection_plan_items
    DROP CONSTRAINT IF EXISTS collection_plan_items_charge;

ALTER TABLE public.collection_plan_items
    ADD CONSTRAINT collection_plan_items_charge CHECK (
        (statut = 'traduit'
            AND metrique IS NOT NULL AND source_pressentie IS NOT NULL AND ancre IS NOT NULL
            AND motif IS NULL)
        OR
        (statut = 'inobtenable'
            AND motif IS NOT NULL
            AND metrique IS NULL AND source_pressentie IS NULL AND ancre IS NULL
            AND poste IS NULL)
    );

COMMIT;
