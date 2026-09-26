-- Migration 049 — LE REGISTRE DES PIÈCES ÉCARTÉES : une pièce déposée au dossier d'un émetteur alors
-- qu'elle porte sur une AUTRE société en sort, et la trace reste (chantier v3, lot 7).
--
-- CE QUE FERAIT UN VRAI FONDS (arbitrage de l'utilisateur, 2026-09-26)
--   Un document classé par erreur dans le dossier d'une valeur n'y reste pas — l'analyste qui le
--   relirait prendrait la concurrence de Ryvu Therapeutics pour celle de Revolution Medicines — mais il
--   n'est pas détruit non plus : il part au registre des pièces écartées, avec QUI l'a écarté, QUAND et
--   POURQUOI, pour qu'un contrôle ultérieur puisse relire l'erreur et sa correction.
--   « C'est normal en phase de debug » : l'écart est un acte de tenue du dossier, pas une sanction.
--
-- LE CAS (plan de collecte 103, 2026-09-25, cause corrigée par la convention #86) : le traducteur et la
-- requête web ne recevaient que le sigle « RVMD » ; la défendabilité de Revolution Medicines a été
-- cherchée sur RVU120 / CDK8/19, les programmes de Ryvu Therapeutics. Cinq pièces sur Ryvu et ses
-- concurrents ont été persistées au dossier RVMD : #665, #666, #667, #671, #672. La #664 (« RVMD n'a
-- aucun programme CDK8/19 ») est JUSTE sur RVMD et reste.
--
-- FORME, PAS GARDE. Écarter se fait en DÉPLAÇANT la ligne, pas en posant un drapeau : tous les lecteurs
-- du corpus filtrent `superseded_by IS NULL`, et un drapeau neuf exigerait que chacun apprenne à le
-- lire (un lecteur oublié ferait fuir la pièce). Hors de `knowledge_entries`, elle n'est lisible par
-- AUCUN agent, par construction. `superseded_by` n'est PAS employé : il dit « remplacée par une version
-- plus récente du même fait », ce qui serait faux ici (#43).
-- La pièce est conservée ENTIÈRE en JSONB (`piece`, moins l'embedding, recalculable), ce qui évite un
-- jumeau de schéma de `knowledge_entries` à tenir à jour (#46) ; ses rattachements aux questions
-- (`question_coverage`) partent avec elle dans `couvertures`.
--
-- Le registre est APPEND-ONLY (comme le PV du comité, 048) : le rôle applicatif ne fait que LIRE.
-- Éprouvée en négatif AVANT application par `checks/negatif_049.sh` (copie de `db_portfolio`).

BEGIN;

CREATE TABLE public.pieces_ecartees (
    entry_id     integer     PRIMARY KEY,
    ticker_id    text        NOT NULL,
    ecartee_le   timestamptz NOT NULL DEFAULT now(),
    ecartee_par  text        NOT NULL,
    motif        text        NOT NULL,
    piece        jsonb       NOT NULL,
    couvertures  jsonb       NOT NULL DEFAULT '[]'::jsonb,
    CONSTRAINT pieces_ecartees_texte CHECK (btrim(ecartee_par) <> '' AND btrim(motif) <> ''),
    CONSTRAINT pieces_ecartees_piece CHECK ((piece->>'id')::int = entry_id AND piece ? 'content')
);

CREATE OR REPLACE FUNCTION public.pieces_ecartees_immuable() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  RAISE EXCEPTION 'pieces_ecartees est un registre : un écart ne se modifie ni ne se supprime '
                  '(migration 049)';
END $$;

CREATE TRIGGER pieces_ecartees_immuable
    BEFORE UPDATE OR DELETE ON public.pieces_ecartees
    FOR EACH ROW EXECUTE FUNCTION public.pieces_ecartees_immuable();

REVOKE ALL ON public.pieces_ecartees FROM portfolio_user;
GRANT SELECT ON public.pieces_ecartees TO portfolio_user;

-- ── 049/K1 : le rôle applicatif ne fait que lire le registre ──────────────────────────────────────
DO $$
BEGIN
  IF has_table_privilege('portfolio_user', 'public.pieces_ecartees', 'INSERT')
     OR has_table_privilege('portfolio_user', 'public.pieces_ecartees', 'UPDATE')
     OR has_table_privilege('portfolio_user', 'public.pieces_ecartees', 'DELETE')
     OR has_table_privilege('portfolio_user', 'public.pieces_ecartees', 'TRUNCATE') THEN
    RAISE EXCEPTION '049/K1 : le rôle applicatif peut écrire au registre des pièces écartées — '
                    'écarter une pièce est un acte humain';
  END IF;
END $$;

-- ── 049/K2 : l'état d'avant est exactement celui qu'on a mesuré ───────────────────────────────────
-- Les cinq pièces existent, sont COURANTES, au dossier RVMD, et aucune pièce ne les cite comme
-- remplaçante (sinon la déplacer casserait une lignée). Un écart ne se joue pas à l'aveugle.
DO $$
DECLARE n int; m int;
BEGIN
  SELECT count(*) INTO n FROM public.knowledge_entries
   WHERE id IN (665, 666, 667, 671, 672) AND ticker_id = 'RVMD' AND superseded_by IS NULL;
  IF n <> 5 THEN
    RAISE EXCEPTION '049/K2 : % pièce(s) courante(s) RVMD sur les 5 attendues (#665-667, #671, #672) '
                    '— l''état a changé depuis la mesure, relire avant d''écarter', n;
  END IF;
  SELECT count(*) INTO m FROM public.knowledge_entries WHERE superseded_by IN (665, 666, 667, 671, 672);
  IF m <> 0 THEN
    RAISE EXCEPTION '049/K2 : % pièce(s) désignent une pièce à écarter comme remplaçante', m;
  END IF;
END $$;

-- ── L'écart ──────────────────────────────────────────────────────────────────────────────────────
INSERT INTO public.pieces_ecartees (entry_id, ticker_id, ecartee_par, motif, piece, couvertures)
SELECT ke.id, ke.ticker_id,
       'utilisateur (arbitrage du 2026-09-26)',
       'Pièce sur une AUTRE société : collectée pour Ryvu Therapeutics (RVU120, inhibiteurs CDK8/19) '
       'par le plan de collecte 103 du 2026-09-25, qui avait confondu le sigle RVMD avec Ryvu. Revolution '
       'Medicines développe des inhibiteurs de RAS. Cause corrigée par la convention #86.',
       to_jsonb(ke) - 'embedding',
       COALESCE((SELECT jsonb_agg(to_jsonb(qc) ORDER BY qc.question_id, qc.ingredient_id)
                   FROM public.question_coverage qc WHERE qc.entry_id = ke.id), '[]'::jsonb)
  FROM public.knowledge_entries ke
 WHERE ke.id IN (665, 666, 667, 671, 672);

DELETE FROM public.question_coverage WHERE entry_id IN (665, 666, 667, 671, 672);
DELETE FROM public.knowledge_entries WHERE id IN (665, 666, 667, 671, 672);

-- ── 049/K3 : l'état d'après — tout est au registre, rien au dossier ──────────────────────────────
-- (Un rattachement laissé derrière n'a pas besoin de garde ici : la clé étrangère
-- `question_coverage_entry_id_fkey` refuse déjà de supprimer une pièce encore rattachée.)
DO $$
DECLARE reg int; restant int; couv int;
BEGIN
  SELECT count(*) INTO reg FROM public.pieces_ecartees WHERE entry_id IN (665, 666, 667, 671, 672);
  SELECT count(*) INTO restant FROM public.knowledge_entries WHERE id IN (665, 666, 667, 671, 672);
  SELECT coalesce(sum(jsonb_array_length(couvertures)), 0) INTO couv FROM public.pieces_ecartees;
  IF reg <> 5 OR restant <> 0 THEN
    RAISE EXCEPTION '049/K3 : registre=% (attendu 5), restées au dossier=% (attendu 0)', reg, restant;
  END IF;
  IF couv <> 2 THEN
    RAISE EXCEPTION '049/K3 : % rattachement(s) conservé(s) au registre, 2 attendus (#667 et #671 '
                    'rattachées à mo_3) — un rattachement perdu est une trace perdue', couv;
  END IF;
END $$;

COMMENT ON TABLE public.pieces_ecartees IS
    'Registre des pièces écartées d''un dossier (migration 049) : la pièce entière et ses rattachements, '
    'qui/quand/pourquoi. Append-only, lecture seule pour l''application. Hors de knowledge_entries, '
    'aucun agent ne la lit.';

COMMIT;
