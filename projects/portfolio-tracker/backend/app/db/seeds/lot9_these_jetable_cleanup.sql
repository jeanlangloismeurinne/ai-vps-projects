-- LOT 9 — suppression de TOUT ce que la thèse V2 jetable a créé.
-- Pendant de `lot9_these_jetable_seed.sql` : on rejoue la chaîne complète (débat → clôture →
-- plan de sortie → tranches → post-mortem → calibration) sur une thèse fabriquée, puis on efface.
--
-- INVOCATION (l'id de la thèse est OBLIGATOIRE, il n'a pas de défaut) :
--   docker cp lot9_these_jetable_cleanup.sql shared-postgres:/tmp/
--   docker exec shared-postgres psql -U admin -d db_portfolio \
--     -v ON_ERROR_STOP=1 -v thesis_id=5 -f /tmp/lot9_these_jetable_cleanup.sql
--
-- Si `thesis_id` n'est pas passé, psql échoue sur variable non définie : c'est voulu. Un script
-- de DELETE ne prend pas de valeur par défaut.
--
-- ⚠️ AUCUN ID EN DUR. La version précédente listait `knowledge_entries (121,122,123)` et
-- `cash_movements (10,11,12)` — les ids du run de la veille. Au run suivant les leçons sont
-- parties en 124/125/126 et la trésorerie en 13/14/15 : le script aurait supprimé trois entrées
-- de connaissance appartenant à un autre exercice ET laissé derrière lui les mouvements de
-- trésorerie factices du run courant, dans un solde de cash PARTAGÉ avec le flux V1 réel
-- (convention #34). Tout est donc dérivé de `thesis_v2_id`.
--
-- Ne touche NI la thèse MSFT #4, NI la position #8, NI aucune ligne du flux V1.
-- Ordre imposé par les FK : on capture les ids des faits rattachés AVANT d'effacer ce qui les porte.

BEGIN;

-- Les leçons versées en base de connaissance ne sont atteignables que par le tableau
-- `lesson_entry_ids` du bilan : on les capture avant de supprimer le bilan.
CREATE TEMP TABLE _lot9_lessons ON COMMIT DROP AS
SELECT DISTINCT unnest(lesson_entry_ids) AS entry_id
FROM post_mortems_v2
WHERE thesis_v2_id = :thesis_id
  AND lesson_entry_ids IS NOT NULL;

-- Même raison pour la trésorerie : le lien tranche → mouvement vit sur `exit_executions`,
-- qui part en CASCADE avec le plan.
CREATE TEMP TABLE _lot9_cash ON COMMIT DROP AS
SELECT DISTINCT cash_movement_id AS id
FROM exit_executions
WHERE exit_plan_id IN (SELECT id FROM exit_plans WHERE thesis_v2_id = :thesis_id)
  AND cash_movement_id IS NOT NULL;

-- Registre A5 → post_mortems_v2
DELETE FROM calibration_registry WHERE thesis_v2_id = :thesis_id;

-- Alertes et exécutions → exit_plans (les deux sont ON DELETE CASCADE ; explicite pour la trace)
DELETE FROM price_alerts    WHERE exit_plan_id IN (SELECT id FROM exit_plans WHERE thesis_v2_id = :thesis_id);
DELETE FROM exit_executions WHERE exit_plan_id IN (SELECT id FROM exit_plans WHERE thesis_v2_id = :thesis_id);

-- Bilans (dont une éventuelle ligne `failed` d'un refus tracé)
DELETE FROM post_mortems_v2 WHERE thesis_v2_id = :thesis_id;

-- Leçons versées en base de connaissance par le post-mortem
DELETE FROM analysis_knowledge_refs WHERE entry_id IN (SELECT entry_id FROM _lot9_lessons);
DELETE FROM knowledge_entries       WHERE id       IN (SELECT entry_id FROM _lot9_lessons);

-- Trésorerie des tranches vendues
DELETE FROM cash_movements WHERE id IN (SELECT id FROM _lot9_cash);

DELETE FROM exit_plans             WHERE thesis_v2_id = :thesis_id;
DELETE FROM conviction_debates_v2  WHERE thesis_v2_id = :thesis_id;
DELETE FROM portfolio_positions    WHERE thesis_v2_id = :thesis_id;
DELETE FROM calendar_events        WHERE thesis_v2_id = :thesis_id;
DELETE FROM monitoring_sessions_v2 WHERE thesis_v2_id = :thesis_id;
DELETE FROM theses_v2              WHERE id = :thesis_id;

COMMIT;
