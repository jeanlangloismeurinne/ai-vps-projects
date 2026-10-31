-- Suivi NASDAQ : liste de suivi (cartes de l'accueil) + modèle de probabilité de nouveau plus haut à 12 mois.
-- Appliquée à la main : docker cp f.sql shared-postgres:/tmp/ && docker exec shared-postgres psql -U admin -d db_portfolio -f /tmp/f.sql

CREATE TABLE IF NOT EXISTS nasdaq_watchlist (
    ticker    TEXT PRIMARY KEY,
    added_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Un modèle par année Y, appris UNIQUEMENT sur des observations dont le résultat était connu au 1er janvier de Y.
CREATE TABLE IF NOT EXISTS nasdaq_proba_model (
    fit_year    INTEGER PRIMARY KEY,
    cutoff_day  INTEGER NOT NULL,             -- jours depuis 1970 : toute observation d'apprentissage a son résultat connu à cette date
    n_train     INTEGER NOT NULL,
    n_pos       INTEGER NOT NULL,
    mu          JSONB NOT NULL,
    sd          JSONB NOT NULL,
    coef        JSONB NOT NULL,               -- [intercept, un coefficient par variable standardisée]
    fitted_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Qualité mesurée hors échantillon (chaque observation notée par le modèle de son année) : une seule ligne.
CREATE TABLE IF NOT EXISTS nasdaq_proba_calib (
    id          SMALLINT PRIMARY KEY DEFAULT 1,
    computed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    payload     JSONB NOT NULL
);
