-- Migration 038 — le rôle applicatif peut LIRE `archive_v2`, et rien de plus.
--
-- POURQUOI. La 036 a déplacé les 15 tables V2 vers `archive_v2` par `SET SCHEMA`. Les privilèges de
-- TABLE suivent la table (`portfolio_user` garde son SELECT), mais l'`USAGE` sur le SCHÉMA neuf
-- n'existait pas : toute lecture échoue en `InsufficientPrivilegeError: permission denied for
-- schema archive_v2`. Deux privilèges, un seul déplacé — et le manquant ne se voit qu'à l'exécution.
--
-- CE QUE ÇA DÉBLOQUE. Cinq mesureurs ponctuels ont été repointés sur `archive_v2` par le balayage
-- du lot 2b (`tools/_corpus_archive.py`, détenteur unique du pointeur) : `mesure_conflits_capacite5`,
-- `qualif_couples_capacite5`, `ligne_de_base_frameworks`, `reconcilier_vocabulaires`,
-- `mesure_ingredients_capacite5`. Leurs chiffres sont CITÉS dans les décisions du projet (« 8 postes
-- servent 4 des 33 ingrédients essentiels ») ; les garder rejouables est la seule façon de vérifier
-- une affirmation citée plutôt que de la croire. Sans cet USAGE, ils ne rejouent pas — le balayage
-- les aurait laissés justes à la lecture et morts à l'exécution.
--
-- CE QUE ÇA N'OUVRE PAS. `USAGE` + `SELECT` : lecture seule. Aucun INSERT/UPDATE/DELETE, et aucun
-- privilège par défaut sur les objets FUTURS de `archive_v2` — le schéma est FIGÉ au 2026-09-10,
-- rien ne doit plus y naître. Une `ALTER DEFAULT PRIVILEGES` ici dirait le contraire.
BEGIN;

GRANT USAGE ON SCHEMA archive_v2 TO portfolio_user;
GRANT SELECT ON ALL TABLES IN SCHEMA archive_v2 TO portfolio_user;

-- ⚠️ LE REVOKE N'EST PAS UNE PRÉCAUTION DE STYLE. `SET SCHEMA` déplace la table AVEC ses
-- privilèges : les 15 tables archivées portaient INSERT/UPDATE/DELETE pour `portfolio_user`, parce
-- qu'elles étaient des tables applicatives. K2 l'a dit en rougissant au premier passage. « Le
-- corpus est figé » était donc une intention, pas un privilège — et un corpus de référence que le
-- runtime peut réécrire n'est plus une référence. On retire ce qui n'a pas été déplacé exprès.
REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON ALL TABLES IN SCHEMA archive_v2 FROM portfolio_user;
REVOKE USAGE, UPDATE ON ALL SEQUENCES IN SCHEMA archive_v2 FROM portfolio_user;

-- ⚠️ LES GARDES INTERROGENT `pg_class` PAR OID, PAS `information_schema` PAR NOM. La 1ʳᵉ version
-- faisait `has_table_privilege('portfolio_user', 'archive_v2.' || table_name, …)` en filtrant sur
-- `table_schema = 'archive_v2'` : le planificateur ne garantit pas que le filtre soit évalué AVANT
-- la fonction, qui a donc reçu `archive_v2.positions` — le nom d'une table de `public` recollé au
-- mauvais schéma — et la migration est morte sur « relation does not exist ». Un faux ROUGE, mais
-- il aurait pu être un faux VERT si le nom recollé avait par hasard existé des deux côtés.
-- L'OID ne se résout pas : il désigne.

-- K1 — la garde LIT le privilège, elle ne suppose pas que le GRANT a mordu. Un GRANT qui porte sur
-- autre chose que ce qu'on croit réussit en silence. Le point de lecture, c'est `has_*_privilege`.
DO $$
DECLARE manquantes text;
BEGIN
  IF NOT has_schema_privilege('portfolio_user', 'archive_v2', 'USAGE') THEN
    RAISE EXCEPTION '038/K1 : portfolio_user n''a toujours pas USAGE sur archive_v2';
  END IF;
  SELECT string_agg(c.relname, ', ' ORDER BY c.relname) INTO manquantes
    FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
   WHERE n.nspname = 'archive_v2' AND c.relkind = 'r'
     AND NOT has_table_privilege('portfolio_user', c.oid, 'SELECT');
  IF manquantes IS NOT NULL THEN
    RAISE EXCEPTION '038/K1 : SELECT manquant sur archive_v2.{%}', manquantes;
  END IF;
END $$;

-- K2 — la lecture seule est VRAIMENT seule. Un `GRANT ALL` posé par mégarde laisserait le rôle
-- applicatif réécrire un corpus dont toute la valeur est d'être figé.
DO $$
DECLARE ecrivables text;
BEGIN
  SELECT string_agg(c.relname, ', ' ORDER BY c.relname) INTO ecrivables
    FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
   WHERE n.nspname = 'archive_v2' AND c.relkind = 'r'
     AND has_table_privilege('portfolio_user', c.oid, 'INSERT');
  IF ecrivables IS NOT NULL THEN
    RAISE EXCEPTION '038/K2 : archive_v2 est ÉCRIVABLE par portfolio_user sur {%} — le corpus '
                    'archivé doit être figé', ecrivables;
  END IF;
END $$;

COMMIT;
