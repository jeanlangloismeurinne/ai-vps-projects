-- 015 — Piste d'audit des appels d'outils de l'agent (#1787579840504, roadmap agent-outillage §5).
--
-- Pourquoi une table et non un log. Le chantier `agent-consignes` est auditable parce que *tout*
-- le comportement de l'agent tient dans des versions de doc relues (`agent_system_doc`). Les
-- outils créent un chemin d'effet **hors** de cette piste : un rappel apparaît en base sans
-- qu'aucune version de doc n'ait changé. Sans cette table, « pourquoi ce rappel existe-t-il ? »
-- n'a pas de réponse.
--
-- Logfire a été évalué (demande du ticket) et écarté : il instrumente des traces applicatives,
-- pas un registre requêtable joignable à `cards` et à `agent_system_doc`, et il exporterait chez
-- un tiers des arguments qui contiennent le contenu des messages de l'utilisateur. Le coût évité
-- serait d'une quarantaine de lignes SQL.
--
-- Les appels **refusés** sont journalisés au même titre que les autres : un refus répété est le
-- signal d'une tentative d'injection, et c'est précisément ce qu'on veut pouvoir constater.

CREATE TABLE IF NOT EXISTS agent_tool_calls (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tool_name         TEXT NOT NULL,

  -- Arguments produits par le modèle, verbatim — jamais nettoyés : c'est la pièce à conviction.
  arguments         JSONB NOT NULL DEFAULT '{}'::jsonb,
  -- Payload réellement résolu par le code (dates en TIMESTAMPTZ, destination…). Figé au moment
  -- de l'affichage d'une confirmation : c'est lui qui sera écrit au clic, pas une re-résolution.
  resolved_payload  JSONB,

  -- 'ok' | 'confirmation_requise' | 'refused'
  verdict           TEXT NOT NULL,
  verdict_reason    TEXT,

  result_excerpt    TEXT,

  -- Rattachement au fil d'origine.
  channel_id        TEXT,
  slack_ts          TEXT,
  thread_ts         TEXT,
  user_id           TEXT,
  -- ts du message de confirmation, pour pouvoir l'éditer au clic.
  confirm_ts        TEXT,

  -- Version du doc système active au moment de l'appel : rattache l'appel au comportement audité
  -- en vigueur. Sans elle, on ne sait pas *quelle* consigne a mené à cette action.
  doc_version       INTEGER,

  -- Tableau des sources non fiables présentes dans le contexte : ["web:exemple.com", …].
  -- Un booléen ne dirait pas *laquelle* — inexploitable en incident dès qu'il y a plus d'un
  -- outil taintant, et il ne couvrirait que le web (roadmap §2.2).
  taint_sources     JSONB NOT NULL DEFAULT '[]'::jsonb,

  user_confirmed    BOOLEAN NOT NULL DEFAULT false,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  resolved_at       TIMESTAMPTZ
);

-- Quota journalier par outil (`rate_limit.per_day`) : compte les appels `ok` des dernières 24 h.
CREATE INDEX IF NOT EXISTS idx_agent_tool_calls_tool_created
  ON agent_tool_calls (tool_name, created_at DESC);

-- Reconstitution d'un fil : « qu'a fait l'agent dans cette conversation ? »
CREATE INDEX IF NOT EXISTS idx_agent_tool_calls_thread
  ON agent_tool_calls (channel_id, thread_ts);
