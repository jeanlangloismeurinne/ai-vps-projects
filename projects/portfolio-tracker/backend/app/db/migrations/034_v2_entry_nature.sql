-- 034 — V2 : l'axe `nature` d'une knowledge_entry (capacité 1 de
--       roadmap/02-spec-autorite-vs-actualite.md). GÉNÉRÉ par `_gen_034.py`, ne pas éditer
--       à la main : le backfill est calculé par `derive_nature`, détenteur unique (#46).
--
-- Un fait a TROIS propriétés indépendantes qu'on ne recombine jamais (#50) : fiabilité
-- (stockée, colonne `reliability_*`), actualité (calculée à la LECTURE, capacité 3 — la
-- stocker la figerait, c'est le défaut qu'on corrige) et nature. La nature est STOCKÉE :
-- c'est une propriété de l'assertion, pas une relation au présent.
--
-- ⚠️ `nature` d'une ENTRY ≠ `nature` dominante d'un CHAMP (`FIELD_PROFILES`). La première
-- dit ce que l'assertion prétend être, la seconde ce qui a AUTORITÉ pour fonder le champ.
-- Le vocabulaire des entries est strictement plus large : `evenement` n'est la nature
-- dominante d'aucun des 19 champs (résultat de la capacité 0) mais reste une nature
-- d'entry parfaitement légitime. Les confronter est le travail de la porte (capacité 4).
--
-- Backfill : 180 lignes (toutes versions, y compris superseded — cf. en-tête du
-- générateur), d'où le NOT NULL posé dans la même migration.
--
-- Répartition dérivée, par (entry_type, source_type) :
--   agent_synthesis   agent_synthesis       → interpretation     8
--   analysis          agent_synthesis       → interpretation     8
--   base_rate         financial_press       → mesure             7
--   fact_financial    edgar_official        → mesure            78
--   fact_financial    yfinance              → mesure             6
--   fact_qualitative  company_ir_official   → interpretation     4
--   fact_qualitative  company_ir_official   → mesure             1
--   fact_qualitative  edgar_official        → interpretation    43
--   fact_qualitative  edgar_official        → mesure            11
--   fact_qualitative  financial_press       → interpretation     2
--   fact_qualitative  financial_press       → mesure             1
--   fact_qualitative  llm_memory            → interpretation     4
--   fact_qualitative  web_search_reputable  → mesure             6
--   risk              llm_memory            → interpretation     1
--
-- ⚠️ AUCUNE entry n'est `evenement` après backfill, et ce n'est pas un bug : aucun
-- producteur n'écrit encore d'entry adossée à un 8-K/6-K (`material_events` SIGNALE et
-- n'écrit rien, #49). Le seul chemin vers `evenement` est une déclaration d'agent que
-- `derive_nature` accepte parce qu'elle RESSERRE. Une classe vide et déclarée vaut mieux
-- qu'une classe remplie par une heuristique de contenu.

ALTER TABLE knowledge_entries ADD COLUMN IF NOT EXISTS nature TEXT;

-- interpretation : 70 lignes
UPDATE knowledge_entries SET nature = 'interpretation' WHERE id IN (
    11, 12, 13, 14, 15, 19, 20, 21, 22, 25, 27, 28, 29, 30, 31, 32, 33, 34, 35, 53,
    54, 55, 56, 57, 58, 59, 60, 61, 62, 78, 79, 80, 81, 89, 90, 91, 92, 93, 94, 95,
    96, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 112, 113, 114, 115, 116, 120, 173, 174, 175,
    176, 177, 178, 179, 180, 181, 182, 183, 184, 185
);

-- mesure : 110 lignes
UPDATE knowledge_entries SET nature = 'mesure' WHERE id IN (
    1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 23, 24, 26, 36, 37, 38, 39, 40, 41, 42,
    43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72,
    73, 74, 75, 76, 77, 82, 83, 84, 85, 86, 87, 88, 97, 98, 109, 110, 111, 117, 118, 119,
    127, 128, 129, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 145, 146,
    147, 148, 149, 150, 151, 152, 153, 154, 155, 156, 157, 158, 159, 160, 161, 162, 163, 164, 165, 166,
    167, 168, 169, 170, 171, 172, 186, 189, 190, 191
);

-- Domaine FERMÉ : une nature hors vocabulaire n'est pas « inconnue », elle est fausse —
-- et le seul lecteur de cette colonne (la porte, capacité 4) n'aurait aucune branche
-- pour elle. Le CHECK est nommé pour qu'une violation dise QUOI, pas seulement OÙ.
ALTER TABLE knowledge_entries DROP CONSTRAINT IF EXISTS knowledge_entries_nature_check;
ALTER TABLE knowledge_entries ADD CONSTRAINT knowledge_entries_nature_check
    CHECK (nature IN ('evenement', 'interpretation', 'mesure'));
ALTER TABLE knowledge_entries ALTER COLUMN nature SET NOT NULL;

-- Index PARTIEL sur les entrées courantes : la porte ne lit jamais une entry superseded,
-- et l'index partiel suit la même clause que `_CURRENT` dans `knowledge/service.py`.
CREATE INDEX IF NOT EXISTS idx_knowledge_entries_nature
    ON knowledge_entries (ticker_id, nature)
    WHERE superseded_by IS NULL AND is_deleted = FALSE;
