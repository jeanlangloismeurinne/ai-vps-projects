ALTER TABLE positions
  ADD COLUMN IF NOT EXISTS schema_json           JSONB,
  ADD COLUMN IF NOT EXISTS exit_price            DECIMAL(12,4),
  ADD COLUMN IF NOT EXISTS exit_date             DATE,
  ADD COLUMN IF NOT EXISTS exit_reason           VARCHAR(50),
  ADD COLUMN IF NOT EXISTS exit_notes            TEXT,
  ADD COLUMN IF NOT EXISTS quantity              DECIMAL(12,4);
