-- RETRAIT PROPOSÉ — NON APPLIQUÉ — du passage de réémission du 2026-09-29
-- (`tools/executer_chaine.sh RVMD qualite_financiere pre_revenus --sans-collecte`, après le déploiement 50286e2).
--
-- Pourquoi : le passage devait réémettre qf_4/qf_6 avec l'encadré de chiffres clés sur les mêmes pièces.
-- Il a au contraire remplacé qf_6 (#474, approximée) par un « non fondable » (#897), fait refuser qf_4 et
-- qf_7 par la règle de nature (#78) et ouvert deux demandes de recherche à tort (#1582 sur qf_4, qui a une
-- réponse ; #1583 sur qf_7). Règle du projet (#78) : retirer par l'inventaire, corriger en amont, réessayer.
-- Les lignes retirées sont sauvegardées à côté (JSON).
--
-- À appliquer SEULEMENT sur décision de l'utilisateur :
--   docker cp <ce fichier> shared-postgres:/tmp/r.sql
--   docker exec shared-postgres psql -U admin -d db_portfolio -f /tmp/r.sql
BEGIN;
UPDATE framework_answers SET superseded_by = NULL
 WHERE id IN (469, 470, 471, 472, 474) AND superseded_by IN (893, 894, 895, 896, 897);
DELETE FROM framework_answers WHERE id IN (893, 894, 895, 896, 897);
DELETE FROM framework_mandates WHERE id IN (1582, 1583);
DO $$ BEGIN
  IF (SELECT count(*) FROM framework_answers
       WHERE ticker_id = 'RVMD' AND framework = 'qualite_financiere' AND superseded_by IS NULL) <> 6 THEN
    RAISE EXCEPTION 'état inattendu après retrait — rien n''est appliqué';
  END IF;
END $$;
COMMIT;
