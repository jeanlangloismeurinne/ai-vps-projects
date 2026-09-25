-- Migration 046 — L'ARCHÉTYPE DE L'ÉMETTEUR ENTRE AU DOSSIER (chantier v3, lot 5).
--
-- ADDITIVE et RÉVERSIBLE : une table neuve, aucune colonne retirée, aucune ligne existante touchée.
--
-- L'ÉCART MESURÉ (2026-09-24, par `tools/montrer_memo_projete.sh RVMD`). Le manager ne PERSISTE pas
-- son verdict : `manager_persist.assemble_verdict` le dit en toutes lettres — « NON persisté
-- (arbitrage : l'avis se recalcule) ». L'arbitrage est juste : les 4 contrôles dépendent du corpus
-- et des dispenses, qui bougent ; un acquittement figé servirait le verdict d'avant la rétractation
-- d'une pièce (#54, `feedback_controle_au_point_de_lecture`).
--
-- Mais son PRÉ-REQUIS manquait. Recalculer l'avis exige de savoir quelles questions sont
-- APPLICABLES, donc l'archétype de l'émetteur (`reviser_framework(..., archetype=...)`). Or
-- l'archétype n'était nulle part : il se tapait à la main sur la ligne de commande
-- d'`executer_chaine.sh`, et disparaissait avec le terminal. Résultat mesuré sur RVMD : la note
-- projetée sortait `financials` en « 6 réponses au dossier, aucune acquittée par le manager » —
-- **faux**, puisque aucune revue n'avait pu avoir lieu. Un décideur sans producteur ne décide
-- jamais, et son absence se lisait comme un refus.
--
-- DE QUOI L'ARCHÉTYPE EST-IL UNE PROPRIÉTÉ ? (`feedback_rigidite_revocabularisee`)
-- De l'ÉMETTEUR, DANS LE TEMPS — jamais du framework (un seul jeu d'archétypes sert les deux
-- pilotes), jamais d'une exécution. Une société pré-revenus devient rentable : c'est un fait daté,
-- pas une correction. D'où une table par (émetteur, date d'effet) plutôt qu'une colonne sur
-- `tickers`, qu'un reclassement écraserait. C'est l'arbitrage utilisateur du 2026-09-22 appliqué
-- ici : **on n'écrase pas, on empile**, et on répond sur la plus récente en gardant l'historique.
--
-- ⚠️ AUCUN CHECK SUR LE VOCABULAIRE, ET C'EST VOULU. La liste des archétypes est déclarée une fois,
-- dans `frameworks.yaml` (`archetypes:`), et le contrat l'y garde. Un `CHECK (archetype IN (...))`
-- ici en ferait un JUMEAU, divergent le jour où le référentiel gagne un archétype : la base
-- refuserait une valeur que le référentiel déclare licite, et le correctif naturel serait de
-- desserrer le CHECK plutôt que de comprendre (#46, `feedback_correctif_regle_jumeaux`). La
-- validation vit dans `framework_persist.read_archetype`, qui confronte à `load_frameworks()`.
--
-- ORDRE DU CHANTIER — le LECTEUR dicte la table. `projection_memo.servir_memo()` a besoin de
-- l'archétype pour recalculer l'avis à la lecture ; cette table est la projection de ce besoin,
-- pas une conception de schéma indépendante.

BEGIN;

CREATE TABLE IF NOT EXISTS public.ticker_archetypes (
    id              bigserial PRIMARY KEY,
    ticker_id       text        NOT NULL REFERENCES public.tickers(id),
    archetype       text        NOT NULL,
    -- La date à laquelle ce classement PREND EFFET dans le monde, distincte de `created_at` (la
    -- date à laquelle on l'a su). Sans elle, un reclassement saisi en retard daterait du jour de
    -- la saisie, et toute note antérieure serait relue sous le mauvais archétype.
    effective_from  date        NOT NULL,
    -- Obligatoire, sans défaut : un classement sans motif ne se distingue pas d'un réglage par
    -- défaut, et c'est lui qui décide quelles questions sont hors-sujet. Un hors-sujet sans motif
    -- est un trou déguisé (contrôle ① du manager, même règle que `SansObjet.motif`).
    motif           text        NOT NULL CHECK (length(btrim(motif)) > 0),
    created_at      timestamptz NOT NULL DEFAULT now()
);

-- Append-only : rien ne se met à jour, tout s'empile. L'unicité porte sur (émetteur, date d'effet)
-- parce que deux classements au même jour d'effet rendraient l'ordre de lecture dépendant de
-- `id` — une note qui change sans qu'aucune donnée ne change.
CREATE UNIQUE INDEX IF NOT EXISTS uq_ticker_archetypes_effet
    ON public.ticker_archetypes (ticker_id, effective_from);

-- La lecture est toujours « le plus récent à une date donnée » : l'index sert exactement ce
-- parcours, dans son ordre.
CREATE INDEX IF NOT EXISTS idx_ticker_archetypes_courant
    ON public.ticker_archetypes (ticker_id, effective_from DESC);

COMMENT ON TABLE public.ticker_archetypes IS
    'Archétype d''un émetteur, daté et append-only (migration 046, chantier v3 lot 5). '
    'Vocabulaire détenu par app/frameworks/frameworks.yaml, jamais par un CHECK ici.';

COMMIT;
