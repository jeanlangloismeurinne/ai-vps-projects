-- Migration 059 — LE CLASSEMENT DE L'ÉMETTEUR DEVIENT UNE DÉCISION DU COMITÉ ADOSSÉE À UNE PIÈCE (#139).
--
-- ADDITIVE et RÉVERSIBLE : trois colonnes nullables, une contrainte de forme ; aucune ligne touchée.
--
-- L'ÉCART MESURÉ (2026-10-18, #138). « Pas encore observable » exige un fait déclencheur daté ET la
-- pièce du dossier qui le prouve. Pour RVMD, le fait qui rend la grille commerciale pertinente est
-- l'approbation du 26/08 — un fait de l'ÉMETTEUR, pas d'un chapitre. Or seul le modèle économique
-- rangeait sa pièce (#944, lecture du 8-K) : la qualité financière ne pouvait prouver aucune attente,
-- et chaque framework ne lit que ses sujets (#108). Le classement, lui, gouverne la grille de TOUS les
-- chapitres : c'est sa pièce qui doit les suivre tous.
--
-- COMME UN VRAI FONDS. Le stade de la société est écrit en tête de chaque dossier ; quand le directeur
-- de la recherche reclasse une biotech en « commerciale », il date sa décision, la signe et cite
-- l'événement qui la justifie. Le système RECOMMANDE (catalogue 1.7.0, `changement_de_stade`) ; le
-- comité reclasse ou maintient — jamais le code (arbitrage de l'utilisateur, 2026-10-18).
--
-- LES TROIS COLONNES.
--   piece_id              — la pièce du dossier qui fonde la décision (la lecture du dépôt déclencheur) ;
--                           jointe d'office au dossier de chaque chapitre tant que ce classement est en
--                           vigueur (`preparation.preparer_dossier_analyste`).
--   auteur                — qui a décidé (le membre du comité qui signe).
--   declencheur_accession — le dépôt EDGAR que la décision tranche : la recommandation se ferme quand
--                           un classement daté au plus tôt du fait est décidé (reclasser OU maintenir).
--
-- ⚠️ LES TROIS CLASSEMENTS D'ORIGINE (2026-09-24, outil `classer_emetteur`) n'ont ni pièce ni auteur :
-- ils restent lisibles tels quels (contrainte : tout ou rien). Un classement DÉCIDÉ porte les trois —
-- une décision sans pièce ne prouverait aucune attente, une décision sans auteur n'est pas une décision.

BEGIN;

ALTER TABLE public.ticker_archetypes
    ADD COLUMN IF NOT EXISTS piece_id integer REFERENCES public.knowledge_entries(id),
    ADD COLUMN IF NOT EXISTS auteur text,
    ADD COLUMN IF NOT EXISTS declencheur_accession text;

ALTER TABLE public.ticker_archetypes DROP CONSTRAINT IF EXISTS ticker_archetypes_decision;
ALTER TABLE public.ticker_archetypes ADD CONSTRAINT ticker_archetypes_decision CHECK (
    (piece_id IS NULL AND auteur IS NULL AND declencheur_accession IS NULL)
    OR
    (piece_id IS NOT NULL AND auteur IS NOT NULL AND length(btrim(auteur)) > 0
     AND declencheur_accession IS NOT NULL AND length(btrim(declencheur_accession)) > 0)
);

COMMENT ON TABLE public.ticker_archetypes IS
    'Archétype d''un émetteur, daté et append-only (migrations 046, 059). Un classement DÉCIDÉ par le '
    'comité porte sa pièce, son auteur et le dépôt qu''il tranche (#139) ; les classements d''origine '
    'n''en ont pas. Vocabulaire détenu par app/frameworks/frameworks.yaml, jamais par un CHECK ici.';

COMMIT;
