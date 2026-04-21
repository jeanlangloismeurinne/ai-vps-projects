-- F5: Remove FK constraint on transactions.category so categories can be renamed
-- per year without cross-year cascade.
-- categories table remains as a soft reference.

ALTER TABLE transactions DROP CONSTRAINT IF EXISTS transactions_category_fkey;
