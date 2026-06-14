-- Tracking du brief J-2 séparé du triggered J+1
ALTER TABLE calendar_events
  ADD COLUMN brief_triggered BOOLEAN NOT NULL DEFAULT FALSE;

-- Lien explicite session → événement calendrier déclencheur
-- NULL pour sessions manuelles, renseigné pour sessions auto-scheduler
ALTER TABLE monitoring_sessions
  ADD COLUMN calendar_event_id INTEGER REFERENCES calendar_events(id) ON DELETE SET NULL;
