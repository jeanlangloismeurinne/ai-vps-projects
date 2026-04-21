-- F1: Import sessions — each confirmed import creates one record.
-- Transactions are linked to their import session for history access.

CREATE TABLE IF NOT EXISTS import_sessions (
    id         SERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    filename   TEXT,
    row_count  INT,
    date_min   DATE,
    date_max   DATE,
    year_id    INT REFERENCES budget_years(id)
);

ALTER TABLE transactions ADD COLUMN IF NOT EXISTS import_session_id INT REFERENCES import_sessions(id);
