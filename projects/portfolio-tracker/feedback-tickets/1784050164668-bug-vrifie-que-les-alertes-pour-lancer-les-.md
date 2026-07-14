---
id: 1784050164668
type: bug
status: closed
priority: medium
date: 2026-07-14T17:29:24.668501
project: portfolio-tracker
url: 
closed_at: 2026-07-14T00:00:00Z
---

## 🐛 Bug

**Date** : 14/07/2026 17:29
**URL** : `N/A`

### Description

Vérifie que les alertes pour lancer les monitoring manuellement sont bien envoyées via Slack avec la création d’une page avec le prompt à envoyer dans Dust notamment quand l’envoi automatique est bloqué. Normalement cela fait partie des modifications réalisées dans des tickets précédents. Sinon cela veut dire qu’il faut qu’on construise une spec.

### Notes d’implémentation

**Vérification** :
- Flow scheduler-triggered (`_handle_manual_mode` dans `event_router_v1.py`) : ✅ complet — 2 notifs Slack envoyées (lien page + contexte à coller dans Dust), contexte sauvegardé en `monitoring_messages`, composant `PendingManualUpload` sur la page.
- Gap identifié : flow API-triggered (déclenchement manuel via `POST /tickers/{id}/monitoring` quand `dust_auto_enabled=FALSE`) — le `context_message` n’était pas sauvegardé en `monitoring_messages`, donc absent du chat sur la page.

**Correction** : ajout de l’INSERT dans `monitoring_messages` dans `monitoring_v2.py` (bloc `if not dust_enabled`) — le contexte Dust apparaît désormais dans la section chat de la page pour toutes les sessions `pending_manual`.
