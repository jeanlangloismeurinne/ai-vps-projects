-- Point 14 (spec de séance, 2026-10-18) : « une demande de recherche se ferme quand la réponse est
-- livrée ». Diagnostic : 0 ligne `servi`/`abandonne` en base avant ce correctif — les mandats
-- manager/comité (`origine IN ('manager_renvoi','comite')`) n'étaient servis QUE par le bouclage
-- (`bouclage.py`), jamais par la chaîne (`tools/executer_chaine.py`), le chemin réel de toutes les
-- réponses. `persist_answer` (app/agents/v2/framework_persist.py) sert désormais lui-même le mandat
-- ouvert de sa lignée — ce fichier applique RÉTROACTIVEMENT la même règle aux 6 mandats manager/
-- comité ouverts mesurés le 2026-10-18 : 983, 984, 985, 986 (RVMD, framework `defendabilite`,
-- mo_1/mo_3/mo_4/mo_5), 2849 (NVDA, `defendabilite`, mo_2) et 2918 (RVMD, `secteur_concurrence`,
-- se_3).
--
-- RÈGLE (même convention que `persist_answer` / `bouclage._statuts_avant`) : pour chaque mandat dont
-- la lignée (ticker_id, framework_id, framework_version, question_id — SANS filtre analyste, un
-- mandat n'est pas rattaché à un analyste) porte au moins une réponse écrite APRÈS son `created_at`,
-- le mandat passe `servi` avec :
--   statut_avant = statut de la DERNIÈRE réponse de la lignée écrite AVANT created_at (sinon
--                  'non_fondable' — aucune réponse n'existait encore) ;
--   statut_apres = statut de la PREMIÈRE réponse écrite APRÈS created_at ;
--   consomme_at  = created_at de cette réponse ;
--   entry_ids_produits = ses cited_entry_ids.
-- Le CTE ci-dessous DÉRIVE ces valeurs de la base elle-même (aucune ne sort codée en dur) : un
-- mandat sans réponse postérieure (2918 — framework `secteur_concurrence`, aucune réponse écrite sur
-- se_3/RVMD à ce jour) n'a pas de ligne dans `apres` et n'est donc PAS mis à jour — il reste ouvert.
--
-- Mesuré le 2026-10-18 par la requête de contrôle (lecture seule, reproductible) :
--   983  mo_1 RVMD  avant=non_fondable (#597, 2026-09-25)                 après=#690  repondu   2026-09-26 11:23:12.146329+00  cités {679,694,673}
--   984  mo_3 RVMD  avant=non_fondable (#599, 2026-09-25)                 après=#692  approxime 2026-09-26 11:23:12.146329+00  cités {695,694}
--   985  mo_4 RVMD  avant=non_fondable (#600, 2026-09-25)                 après=#693  approxime 2026-09-26 11:23:12.146329+00  cités {679,694}
--   986  mo_5 RVMD  avant=non_fondable (#601, 2026-09-25)                 après=#694  repondu   2026-09-26 11:23:12.146329+00  cités {695,696}
--   2849 mo_2 NVDA  avant=non_fondable (aucune réponse avant #2849)       après=#1435 approxime 2026-10-15 20:19:25.47675+00   cités {1191,1043}
--   2918 se_3 RVMD  AUCUNE réponse sur sa lignée → PAS mis à jour, reste ouvert.
--
-- ⚠️ CE FICHIER N'A PAS ÉTÉ EXÉCUTÉ EN PROD (interdit de la spec). Testé uniquement sous
-- `BEGIN … ROLLBACK` contre la vraie base le 2026-10-18 — sortie rapportée dans la conversation qui
-- a produit ce fichier, pas committée ici. Pour l'appliquer réellement : rejouer ce fichier tel
-- quel, il se termine par `COMMIT` ; réexécuter d'abord la requête de contrôle ci-dessus pour
-- vérifier que la base n'a pas bougé depuis (sinon les ids cibles ne sont plus les bons).
BEGIN;

-- Contrôle AVANT : exactement les 6 mandats attendus sont encore 'ouvert' (sinon la base a bougé
-- depuis le diagnostic — on s'arrête plutôt que d'agir sur une hypothèse périmée, #decision-figee).
DO $$ DECLARE n int; BEGIN
  SELECT count(*) INTO n FROM public.framework_mandates
   WHERE id IN (983,984,985,986,2849,2918) AND origine IN ('manager_renvoi','comite') AND statut = 'ouvert';
  IF n <> 6 THEN
    RAISE EXCEPTION 'rattrapage 2026-10-18 : % mandat(s) ouverts au lieu de 6 — base déjà changée '
      'depuis le diagnostic, on s''arrête', n;
  END IF;
END $$;

WITH cible AS (
  SELECT m.id AS mandat_id, m.ticker_id, m.framework_id, m.framework_version, m.question_id,
         m.created_at AS mandat_created
    FROM public.framework_mandates m
   WHERE m.id IN (983, 984, 985, 986, 2849, 2918)
     AND m.origine IN ('manager_renvoi', 'comite') AND m.statut = 'ouvert'
),
avant AS (
  SELECT c.mandat_id, a.statut
    FROM cible c
    JOIN LATERAL (
      SELECT a.statut FROM public.framework_answers a
       WHERE a.ticker_id = c.ticker_id AND a.framework = c.framework_id
         AND a.framework_version = c.framework_version AND a.question_id = c.question_id
         AND a.created_at < c.mandat_created
       ORDER BY a.created_at DESC LIMIT 1
    ) a ON true
),
apres AS (
  SELECT c.mandat_id, a.statut, a.created_at, a.cited_entry_ids
    FROM cible c
    JOIN LATERAL (
      SELECT a.statut, a.created_at, a.cited_entry_ids FROM public.framework_answers a
       WHERE a.ticker_id = c.ticker_id AND a.framework = c.framework_id
         AND a.framework_version = c.framework_version AND a.question_id = c.question_id
         AND a.created_at > c.mandat_created
       ORDER BY a.created_at ASC LIMIT 1
    ) a ON true
)
UPDATE public.framework_mandates m
   SET statut = 'servi',
       statut_avant = COALESCE(av.statut, 'non_fondable'),
       statut_apres = ap.statut,
       consomme_at = ap.created_at,
       entry_ids_produits = COALESCE(ap.cited_entry_ids, '{}'::int[])
  FROM apres ap
  LEFT JOIN avant av ON av.mandat_id = ap.mandat_id
 WHERE m.id = ap.mandat_id AND m.statut = 'ouvert';

-- Contrôle APRÈS : exactement 983, 984, 985, 986, 2849 sont 'servi' avec une trace complète ;
-- 2918 reste 'ouvert', intact (aucune réponse sur sa lignée).
DO $$ DECLARE n_servis int; n_2918 int; BEGIN
  SELECT count(*) INTO n_servis FROM public.framework_mandates
   WHERE id IN (983, 984, 985, 986, 2849) AND statut = 'servi'
     AND statut_avant IS NOT NULL AND statut_apres IS NOT NULL AND consomme_at IS NOT NULL;
  IF n_servis <> 5 THEN
    RAISE EXCEPTION 'rattrapage 2026-10-18 : % mandat(s) servi(s) avec trace complète au lieu de 5', n_servis;
  END IF;
  SELECT count(*) INTO n_2918 FROM public.framework_mandates WHERE id = 2918 AND statut = 'ouvert';
  IF n_2918 <> 1 THEN
    RAISE EXCEPTION 'rattrapage 2026-10-18 : #2918 n''est plus ouvert — hors périmètre (se_3, aucune réponse)';
  END IF;
END $$;

COMMIT;
