-- Suivi NASDAQ — valeur du temps passé (2026-11-22). Sous-projet indépendant : tables nasdaq_* seulement.
-- À appliquer à la main (#17) : docker cp … shared-postgres:/tmp/ && docker exec shared-postgres psql -U admin -d db_portfolio -f /tmp/nasdaq_03_valeur.sql

-- Par titre : mois, cours brut, cours ajusté des dividendes, bénéfice des 12 derniers mois connu à chaque mois,
-- contrôle croisé avec Yahoo. Recalculé à chaque passage (rien d'historisé : la SEC garde la date de dépôt).
CREATE TABLE IF NOT EXISTS nasdaq_valeur_series (
    ticker      TEXT PRIMARY KEY,
    payload     JSONB,
    note        TEXT,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Inflation américaine (décalée d'un mois de publication) et S&P 500 dividendes réinvestis, mois par mois.
CREATE TABLE IF NOT EXISTS nasdaq_macro (
    series      TEXT PRIMARY KEY,
    payload     JSONB NOT NULL,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Photo hebdomadaire du consensus des analystes (exercice suivant) : la seule façon d'avoir un historique.
CREATE TABLE IF NOT EXISTS nasdaq_forward (
    ticker      TEXT NOT NULL,
    as_of       DATE NOT NULL,
    price       DOUBLE PRECISION,
    fwd_eps     DOUBLE PRECISION,
    fwd_lo      DOUBLE PRECISION,
    fwd_hi      DOUBLE PRECISION,
    n_analysts  INTEGER,
    cur_eps     DOUBLE PRECISION,
    growth      DOUBLE PRECISION,
    currency    TEXT,
    PRIMARY KEY (ticker, as_of)
);
