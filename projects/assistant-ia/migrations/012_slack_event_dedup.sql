-- Déduplication des événements Slack entrants.
-- Slack redélivre un événement tant qu'il n'a pas reçu de 200 sous 3 s : sans garde, un message
-- parent peut être ingéré deux fois (branches 3 à 5 du dispatcher écrivent en base).
-- Une table plutôt qu'un cache mémoire : la garde doit survivre à un redéploiement Coolify.

CREATE TABLE IF NOT EXISTS slack_event_dedup (
    event_key   text PRIMARY KEY,           -- client_msg_id si présent, sinon "{channel}:{ts}"
    channel_id  text,
    created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_slack_event_dedup_created_at
    ON slack_event_dedup (created_at DESC);
