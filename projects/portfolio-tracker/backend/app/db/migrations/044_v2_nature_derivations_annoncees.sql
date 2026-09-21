-- 044 — V2 : rejeu de `derive_nature` après l'entrée de `content` dans la règle
--       (garde du guichet, #78). GÉNÉRÉ par `_gen_044.py`, ne pas éditer à la main :
--       la requalification est calculée par `derive_nature`, détenteur unique (#46).
--
-- CE QUE CETTE MIGRATION CORRIGE, et pourquoi c'était invisible. Un producteur qui
-- CALCULE un chiffre à partir de chiffres déposés le rangeait sous `fact_financial` ×
-- source officielle, donc sous `mesure`, donc sous l'autorité du dépôt. Les entries
-- concernées sont HONNÊTES dans leur prose — elles écrivent leur calcul en toutes
-- lettres. C'est le tampon qui était faux, pas le texte : rien ne pouvait le voir, et
-- une réponse fondée dessus (#475, supprimée le 2026-09-21) passait les quatre
-- contrôles du manager.
--
-- Lignes examinées : 242 · inchangées : 226 · REQUALIFIÉES : 16
--   marqueur « calcul : » : 11
--   marqueur « en déduisant » : 1
--   marqueur « estimée à environ » : 1
--   marqueur « soit environ » : 1
--   marqueur « par différence » : 1
--   marqueur « s'en déduit » : 1
--
-- ⚠️ `reliability_tier` et `reliability_score` ne sont PAS touchés : la fiabilité est
-- une propriété de la SOURCE, la nature une propriété de l'ASSERTION (#50).

BEGIN;

-- → `interpretation` (16 lignes)
--   #312 : `mesure` → `interpretation` (« en déduisant »)
--   #313 : `mesure` → `interpretation` (« estimée à environ »)
--   #314 : `mesure` → `interpretation` (« soit environ »)
--   #355 : `mesure` → `interpretation` (« calcul : »)
--   #357 : `mesure` → `interpretation` (« calcul : »)
--   #358 : `mesure` → `interpretation` (« calcul : »)
--   #359 : `mesure` → `interpretation` (« calcul : »)
--   #360 : `mesure` → `interpretation` (« calcul : »)
--   #361 : `mesure` → `interpretation` (« calcul : »)
--   #362 : `mesure` → `interpretation` (« calcul : »)
--   #385 : `mesure` → `interpretation` (« par différence »)
--   #390 : `mesure` → `interpretation` (« calcul : »)
--   #403 : `mesure` → `interpretation` (« calcul : »)
--   #405 : `mesure` → `interpretation` (« calcul : »)
--   #432 : `mesure` → `interpretation` (« s'en déduit »)
--   #433 : `mesure` → `interpretation` (« calcul : »)
UPDATE knowledge_entries SET nature = 'interpretation', updated_at = NOW()
 WHERE id IN (312, 313, 314, 355, 357, 358, 359, 360, 361, 362, 385, 390, 403, 405, 432, 433);

-- Garde : invariant GLOBAL, pas un accusé de réception de l'UPDATE ci-dessus.
-- Le total de `mesure` en base doit être celui que le rejeu de la règle prédit : une
-- ligne oubliée le fait dépasser, un UPDATE trop large le fait manquer.
DO $$
DECLARE n int;
BEGIN
  SELECT count(*) INTO n FROM knowledge_entries WHERE nature = 'mesure';
  IF n <> 213 THEN
    RAISE EXCEPTION '044 : % entries `mesure` en base, 213 prédites par le rejeu de derive_nature — des lignes ont été oubliées ou requalifiées à tort', n;
  END IF;
END $$;

COMMIT;
