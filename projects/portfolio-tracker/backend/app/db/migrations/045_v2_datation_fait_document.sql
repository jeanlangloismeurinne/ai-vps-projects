-- 045 — LA DATATION D'UNE PIÈCE : deux dates nommées, `source_date` dérivée (#79)
--
-- POURQUOI
-- --------
-- `source_date` est la colonne sur laquelle les machines trient : elle élit la pièce « en vigueur »
-- dans `dossier._rang`, elle nourrit l'axe `actualite` (#53), elle décote l'âge dans
-- `compute_reliability`. Jusqu'ici elle était DÉCLARÉE, et une seule case accueillait deux choses
-- qui ne sont pas la même : la date du FAIT et celle du DOCUMENT qui le rapporte.
--
-- Mesuré sur RVMD avant d'écrire la migration :
--   • 21 des 54 entries courantes datées portent le tampon du papier alors que leur propre prose
--     nomme une date antérieure ;
--   • 6 des 8 chemises à plusieurs versions élisent « en vigueur » une pièce collectée AVANT celle
--     qu'elle bat ;
--   • #309 — « six mois clos le 2025-06-30 », la colonne COMPARATIVE d'un 10-Q — porte le tampon
--     le plus frais du dossier (2026-08-05) ;
--   • #296 porte `source_date = 2026-09-01`, une date absente de sa propre prose : ni le fait
--     (2026-06-30), ni le dépôt (2026-08-05). Un tampon de greffier posé au classement. Ce n'est
--     plus un problème de fraîcheur, c'est un problème de traçabilité.
--
-- Aucune garde ne pouvait les distinguer : deux dates sont structurellement indiscernables, et une
-- garde vérifie la structure, jamais le sens (#68). C'est donc la FORME de la réponse qui change —
-- deux cases nommées rendent la confusion inexprimable — et pas la sévérité du contrôle.
--
-- CE QUI NE CHANGE PAS
-- --------------------
-- `source_date` reste, et reste la colonne de tri. Elle cesse seulement d'être reçue :
-- `store_knowledge` la DÉRIVE de la portée (`constatee` → date du fait ; `prospective` → date de
-- l'annonce ; `indatable` → NULL). Aucun lecteur n'est modifié.
--
-- LE QUATRIÈME CAS N'EST PAS UN QUATRIÈME ÉTAT
-- --------------------------------------------
-- `portee_temporelle IS NULL` désigne les lignes ANTÉRIEURES à cette migration : un constat
-- d'héritage, pas un membre du vocabulaire. Elles ne sont PAS backfillées — « quelle date cette
-- phrase affirme-t-elle ? » n'est pas un vocabulaire fermé, donc ce n'est pas dérivable, et un
-- backfill par modèle fabriquerait 139 jugements invérifiables. Elles sont RE-COLLECTÉES
-- (arbitrage du 2026-09-22 : à l'initialisation et en test, on rachète tout). Le CHECK ci-dessous
-- est donc écrit pour TOLÉRER le NULL et pour être impitoyable dès qu'une portée est déclarée.

BEGIN;

ALTER TABLE knowledge_entries
    ADD COLUMN IF NOT EXISTS portee_temporelle TEXT,
    ADD COLUMN IF NOT EXISTS date_du_fait      DATE,
    ADD COLUMN IF NOT EXISTS date_du_document  DATE,
    ADD COLUMN IF NOT EXISTS periode_visee     DATE,
    ADD COLUMN IF NOT EXISTS datation_motif    TEXT;

COMMENT ON COLUMN knowledge_entries.portee_temporelle IS
    'constatee | prospective | indatable — vocabulaire FERMÉ (app/knowledge/datation.py). '
    'NULL = ligne antérieure à la migration 045, à re-collecter (pas un état du vocabulaire).';
COMMENT ON COLUMN knowledge_entries.date_du_fait IS
    'De quel INSTANT (bilan) ou de quelle FIN D''EXERCICE (flux) l''assertion est vraie. '
    'Convention de bornage #42/#48 : toujours la borne de FIN.';
COMMENT ON COLUMN knowledge_entries.date_du_document IS
    'Quand le document a été publié / déposé. Distincte du fait : un 10-Q déposé le 2026-08-05 '
    'décrit un bilan au 2026-06-30.';
COMMENT ON COLUMN knowledge_entries.periode_visee IS
    'Borne de FIN de la période annoncée — prospective seulement. C''est elle qui rendra possible '
    'la confrontation ultérieure du réalisé à l''annoncé (module « qualité des prévisions »).';
COMMENT ON COLUMN knowledge_entries.datation_motif IS
    'Pourquoi cette pièce n''est pas datable — obligatoire si portee_temporelle = indatable. '
    'Persisté (contrairement au motif de `nature`) parce qu''un jugement ne se rejoue pas.';

-- Le vocabulaire, fermé. Le NULL passe : il nomme l'héritage, pas un état.
ALTER TABLE knowledge_entries
    DROP CONSTRAINT IF EXISTS knowledge_entries_portee_temporelle_check;
ALTER TABLE knowledge_entries
    ADD CONSTRAINT knowledge_entries_portee_temporelle_check
    CHECK (portee_temporelle IS NULL
           OR portee_temporelle IN ('constatee', 'prospective', 'indatable'));

-- L'EXCLUSIVITÉ et la COHÉRENCE, en base et pas seulement en Python. Le contrat `Datation` valide
-- déjà à la construction : ce CHECK n'est pas un doublon de la règle, c'est la garantie que
-- personne ne contourne le guichet par un INSERT direct — un `psql` de maintenance, un backfill
-- futur, une migration pressée. La règle a un détenteur unique en Python (#46) ; la base garde la
-- FORME, ce qui est précisément son rôle.
ALTER TABLE knowledge_entries
    DROP CONSTRAINT IF EXISTS knowledge_entries_datation_coherente_check;
ALTER TABLE knowledge_entries
    ADD CONSTRAINT knowledge_entries_datation_coherente_check
    CHECK (
        portee_temporelle IS NULL
        OR (portee_temporelle = 'constatee'
            AND date_du_fait IS NOT NULL
            AND date_du_document IS NOT NULL
            AND date_du_fait <= date_du_document
            AND periode_visee IS NULL)
        OR (portee_temporelle = 'prospective'
            AND date_du_document IS NOT NULL
            AND periode_visee IS NOT NULL
            AND periode_visee > date_du_document
            AND date_du_fait IS NULL)
        OR (portee_temporelle = 'indatable'
            AND date_du_fait IS NULL
            AND periode_visee IS NULL
            AND datation_motif IS NOT NULL
            AND btrim(datation_motif) <> '')
    );

-- `source_date` est DÉRIVÉE : ce CHECK l'énonce en base, pour que la dérivation soit contrôlable
-- sans relire le Python. Il ne la calcule pas — il refuse qu'elle contredise la portée déclarée.
ALTER TABLE knowledge_entries
    DROP CONSTRAINT IF EXISTS knowledge_entries_source_date_derivee_check;
ALTER TABLE knowledge_entries
    ADD CONSTRAINT knowledge_entries_source_date_derivee_check
    CHECK (
        portee_temporelle IS NULL
        OR (portee_temporelle = 'constatee'   AND source_date = date_du_fait)
        OR (portee_temporelle = 'prospective' AND source_date = date_du_document)
        OR (portee_temporelle = 'indatable'   AND source_date IS NULL)
    );

-- Le tri par fraîcheur reste sur `source_date` (aucun lecteur ne change) ; l'index sur
-- `date_du_fait` sert la confrontation réalisé/annoncé à venir, qui joindra sur la période.
CREATE INDEX IF NOT EXISTS idx_knowledge_entries_date_du_fait
    ON knowledge_entries (ticker_id, date_du_fait DESC NULLS LAST)
    WHERE superseded_by IS NULL;
CREATE INDEX IF NOT EXISTS idx_knowledge_entries_periode_visee
    ON knowledge_entries (ticker_id, periode_visee)
    WHERE portee_temporelle = 'prospective' AND superseded_by IS NULL;

COMMIT;
