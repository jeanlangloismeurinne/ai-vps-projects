-- Migration 015 — devise de reporting par ticker

ALTER TABLE tickers ADD COLUMN IF NOT EXISTS reporting_currency TEXT;

UPDATE tickers SET reporting_currency = CASE
    WHEN id LIKE '%.PA' OR id LIKE '%.AS' OR id LIKE '%.MI' OR id LIKE '%.DE'
         OR id LIKE '%.BR' OR id LIKE '%.LS' OR id LIKE '%.MC' OR id LIKE '%.AT'
         OR id LIKE '%.CO' OR id LIKE '%.HE' OR id LIKE '%.OL' OR id LIKE '%.ST' THEN 'EUR'
    WHEN id LIKE '%.L'                                                            THEN 'GBP'
    WHEN id LIKE '%.T'                                                            THEN 'JPY'
    WHEN id LIKE '%.HK'                                                           THEN 'HKD'
    WHEN id LIKE '%.TO' OR id LIKE '%.V'                                          THEN 'CAD'
    WHEN id LIKE '%.AX'                                                           THEN 'AUD'
    WHEN id LIKE '%.SS' OR id LIKE '%.SZ'                                         THEN 'CNY'
    WHEN id LIKE '%.SA'                                                           THEN 'BRL'
    ELSE 'USD'
END
WHERE reporting_currency IS NULL;
