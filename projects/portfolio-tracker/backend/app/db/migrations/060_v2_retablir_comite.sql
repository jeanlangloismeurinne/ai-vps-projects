-- Migration 060 — RÉTABLIR au procès-verbal du comité : point 13, arbitrage de l'utilisateur du
-- 2026-10-18 (« la dernière analyse fait foi, mais toute baisse est signalée au comité … le comité
-- peut rétablir l'ancienne d'un geste signé au PV »). S'inspire de la 058 (réinitialisation).
--
-- ADDITIVE : une colonne nullable + deux CHECK élargis, aucune ligne existante touchée (une ligne
-- acquitter/renvoyer/reinitialiser reste conforme : `retablie_depuis_id` y est NULL par construction).
-- Réversible en reposant les CHECK de la 058 et en droppant la colonne.
--
-- CE QUE FERAIT UN VRAI FONDS. Un changement de recommandation d'analyste est PUBLIÉ ; le gérant voit
-- la variation et peut la contester. Une réponse courante dont le fondement a BAISSÉ par rapport à sa
-- précédente immédiate (`agents/v2/revision.baisse_a_lire`, recalculé à la lecture, jamais stocké) est
-- signalée au comité, qui peut RÉTABLIR la précédente : elle est réécrite comme réponse NEUVE (la
-- lignée reste append-only — jamais de `superseded_by` remis à NULL), et le PV garde les DEUX ids :
-- `answer_id` = la copie désormais en vigueur, `retablie_depuis_id` = la précédente qu'elle reprend.
-- Ce n'est PAS une acceptation : aucun mandat, et la copie repasse les contrôles et la fraîcheur
-- comme toute réponse écrite.
--
-- ORDRE DU CHANTIER — comme pour la 058 : l'AGENT dicte la table (`contracts/comite_schema.py`,
-- `DecisionComite.retablie_depuis_id`) est écrit AVANT ; ce CHECK en est la projection. Éprouvée en
-- négatif par `checks/negatif_060.sh`, sur COPIE de la base, jamais appliquée à la vraie.

BEGIN;

ALTER TABLE public.comite_decisions
    ADD COLUMN IF NOT EXISTS retablie_depuis_id integer REFERENCES public.framework_answers(id);

ALTER TABLE public.comite_decisions DROP CONSTRAINT comite_decisions_action;
ALTER TABLE public.comite_decisions ADD CONSTRAINT comite_decisions_action
    CHECK (action IN ('acquitter', 'renvoyer', 'reinitialiser', 'retablir'));

-- Projection de `DecisionComite._chaque_action_porte_sa_forme` : `retablir` exige `answer_id`
-- (la copie) ET `retablie_depuis_id` (la précédente), jamais de `mandat_id` (ce n'est pas une
-- recherche) ; toute AUTRE action porte `retablie_depuis_id` NULL (seul `retablir` rétablit).
ALTER TABLE public.comite_decisions DROP CONSTRAINT comite_decisions_forme;
ALTER TABLE public.comite_decisions ADD CONSTRAINT comite_decisions_forme CHECK (
    (action = 'acquitter' AND answer_id IS NOT NULL AND mandat_id IS NULL
                          AND ancre_etat <> 'unavailable' AND retablie_depuis_id IS NULL)
    OR
    (action = 'renvoyer' AND mandat_id IS NOT NULL AND retablie_depuis_id IS NULL)
    OR
    (action = 'reinitialiser' AND mandat_id IS NULL AND retablie_depuis_id IS NULL)
    OR
    (action = 'retablir' AND answer_id IS NOT NULL AND retablie_depuis_id IS NOT NULL
                         AND mandat_id IS NULL)
);

-- ── 060/K1 : le PV reste en lecture + ajout pour le rôle applicatif (comme 048/058 : un ALTER ne
-- doit pas l'avoir rouvert) ──────────────────────────────────────────────────────────────────────
DO $$
BEGIN
  IF has_table_privilege('portfolio_user', 'public.comite_decisions', 'UPDATE')
     OR has_table_privilege('portfolio_user', 'public.comite_decisions', 'DELETE') THEN
    RAISE EXCEPTION '060/K1 : le rôle applicatif peut réécrire le procès-verbal du comité';
  END IF;
END $$;

COMMENT ON TABLE public.comite_decisions IS
    'Procès-verbal du comité (migrations 048, 058, 060) : une ligne par décision acquitter/renvoyer/'
    'reinitialiser/retablir, append-only. La validité d''une acceptation, l''ouverture d''une question '
    'et le fait qu''une révision à la baisse reste à lire se recalculent à la lecture '
    '(agents/v2/comite.py, agents/v2/parcours.py, agents/v2/revision.py), jamais stockées.';

COMMIT;
