"""
Registre central des services.

Pour ajouter un nouveau service :
1. Ajouter les variables d'env dans config.py si besoin (BASE_URL, API_KEY, channel IDs)
2. Ajouter une entrée dans _build_registry() ci-dessous
3. Si le service est externe (sa propre app) : implémenter GET /api/feedback/closed-since
4. Si le service est interne à assistant-ia : ajouter son project_id dans routes/feedback.py VALID_PROJECTS
5. Inviter le bot Slack dans les channels concernés
"""
from __future__ import annotations
from app.config import settings


def _build_registry() -> list[dict]:
    _assistant_url = settings.ASSISTANT_BASE_URL
    _assistant_key = settings.ASSISTANT_INTERNAL_API_KEY

    return [
        # ── Services externes (leur propre app Coolify) ───────────────────────
        {
            "name": "bank-review",
            "base_url": settings.BANK_REVIEW_BASE_URL,
            "feedback_path": "/api/feedback",        # POST pour soumettre
            "closed_since_path": "/api/feedback/closed-since",
            "api_key": settings.BANK_REVIEW_API_KEY,
            "slack_channel": settings.BANK_REVIEW_CHANNEL_ID,        # notif déploiement
            "feedback_channel": settings.BANK_REVIEW_FEEDBACK_CHANNEL_ID,  # nouveaux tickets
            "coolify_uuid": "ji9jg7ngkva7j4d2uic05d3v",
            "linked_channels": list(filter(None, [
                settings.BANK_REVIEW_CHANNEL_ID,
                settings.BANK_REVIEW_FEEDBACK_CHANNEL_ID,
            ])),
        },

        # ── Services internes (hébergés dans assistant-ia) ────────────────────
        {
            "name": "journal",
            "base_url": _assistant_url,
            "feedback_path": "/api/feedback/journal",
            "closed_since_path": "/api/feedback/journal/closed-since",
            "api_key": _assistant_key,
            "slack_channel": settings.JOURNAL_CHANNEL_ID,       # notif déploiement → #journal
            "feedback_channel": settings.FEATURES_AI_CHANNEL_ID,  # nouveaux tickets → #features-ai-assistant
            "coolify_uuid": "",  # même app que assistant-ia
            "linked_channels": list(filter(None, [
                settings.JOURNAL_CHANNEL_ID,
                settings.FEATURES_AI_CHANNEL_ID,
            ])),
        },
        {
            "name": "kanban",
            "base_url": _assistant_url,
            "feedback_path": "/api/feedback/kanban",
            "closed_since_path": "/api/feedback/kanban/closed-since",
            "api_key": _assistant_key,
            "slack_channel": settings.TASKS_CHANNEL_ID,         # notif déploiement → #tasks
            "feedback_channel": settings.FEATURES_AI_CHANNEL_ID,
            "coolify_uuid": "",  # même app que assistant-ia
            "linked_channels": list(filter(None, [
                settings.TASKS_CHANNEL_ID,
                settings.FEATURES_AI_CHANNEL_ID,
            ])),
        },

        # ── Modèle pour un prochain service externe ────────────────────────────
        # {
        #     "name": "mon-service",
        #     "base_url": settings.MON_SERVICE_BASE_URL,
        #     "feedback_path": "/api/feedback",
        #     "closed_since_path": "/api/feedback/closed-since",
        #     "api_key": settings.MON_SERVICE_API_KEY,
        #     "slack_channel": settings.MON_SERVICE_CHANNEL_ID,
        #     "feedback_channel": settings.MON_SERVICE_FEEDBACK_CHANNEL_ID,
        #     "coolify_uuid": "<uuid>",
        #     "linked_channels": [...],
        # },
    ]


def get_all() -> list[dict]:
    return _build_registry()


def by_name(name: str) -> dict | None:
    return next((s for s in _build_registry() if s["name"] == name), None)


def by_channel(channel_id: str) -> dict | None:
    return next(
        (s for s in _build_registry() if channel_id in s.get("linked_channels", [])),
        None,
    )


def by_coolify_uuid(uuid: str) -> dict | None:
    return next(
        (s for s in _build_registry() if s.get("coolify_uuid") == uuid),
        None,
    )
