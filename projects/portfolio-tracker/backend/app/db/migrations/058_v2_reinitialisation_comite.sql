-- Migration 058 — LA RÉINITIALISATION au procès-verbal du comité (séance d'arbitrages du 2026-10-17,
-- point 17-bis, CONVENTIONS #137).
--
-- ADDITIVE : deux CHECK élargis, aucune ligne existante touchée (le PV est vide au 2026-10-17, et une
-- ligne `acquitter`/`renvoyer` reste conforme aux nouvelles contraintes). Réversible en reposant les
-- CHECK de la 048.
--
-- CE QUE FERAIT UN VRAI FONDS. Une décision du comité fait foi : une relance de l'analyse ne refait
-- jamais une question close (à jour, acceptée, ou recherche arrêtée par le comité). Mais le gérant peut
-- REMETTRE À ZÉRO une question ou un chapitre de son choix — même accepté — et ce geste se trace comme
-- une décision : qui, quand, pourquoi. ⟹ une troisième action `reinitialiser`, qui n'ouvre aucun mandat
-- (la question repart par la relance bornée, pas par le bouclage) et peut citer la réponse courante
-- qu'elle met de côté (`answer_id` facultatif : on réinitialise aussi une question sans réponse).
--
-- ORDRE DU CHANTIER — l'AGENT dicte la table : `contracts/comite_schema.py` (`DecisionComite`) est
-- écrit AVANT ; ces CHECK en sont la projection. Éprouvée en négatif par `checks/negatif_058.sh`.

BEGIN;

ALTER TABLE public.comite_decisions DROP CONSTRAINT comite_decisions_action;
ALTER TABLE public.comite_decisions ADD CONSTRAINT comite_decisions_action
    CHECK (action IN ('acquitter', 'renvoyer', 'reinitialiser'));

-- Projection de `DecisionComite._chaque_action_porte_sa_forme`.
ALTER TABLE public.comite_decisions DROP CONSTRAINT comite_decisions_forme;
ALTER TABLE public.comite_decisions ADD CONSTRAINT comite_decisions_forme CHECK (
    (action = 'acquitter' AND answer_id IS NOT NULL AND mandat_id IS NULL
                          AND ancre_etat <> 'unavailable')
    OR
    (action = 'renvoyer' AND mandat_id IS NOT NULL)
    OR
    (action = 'reinitialiser' AND mandat_id IS NULL)
);

-- ── 058/K1 : le PV reste en lecture + ajout pour le rôle applicatif (la 048 l'a posé ; un ALTER ne
-- doit pas l'avoir rouvert) ──────────────────────────────────────────────────────────────────────
DO $$
BEGIN
  IF has_table_privilege('portfolio_user', 'public.comite_decisions', 'UPDATE')
     OR has_table_privilege('portfolio_user', 'public.comite_decisions', 'DELETE') THEN
    RAISE EXCEPTION '058/K1 : le rôle applicatif peut réécrire le procès-verbal du comité';
  END IF;
END $$;

COMMENT ON TABLE public.comite_decisions IS
    'Procès-verbal du comité (migrations 048, 058) : une ligne par décision acquitter/renvoyer/'
    'reinitialiser, append-only. La validité d''une acceptation et l''ouverture d''une question se '
    'recalculent à la lecture (agents/v2/comite.py, agents/v2/parcours.py), jamais stockées.';

COMMIT;
