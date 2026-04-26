"""
Registre central des services.

Pour ajouter un nouveau service :
1. Ajouter les variables d'env dans config.py (BASE_URL, CHANNEL_ID, API_KEY, FEEDBACK_CHANNEL_ID)
2. Ajouter une entrée dans _build_registry() ci-dessous
3. Inviter le bot dans le channel Slack correspondant
"""
from __future__ import annotations
from app.config import settings


def _build_registry() -> list[dict]:
    return [
        {
            "name": "bank-review",
            # URL de base du service (pour les appels API internes)
            "base_url": settings.BANK_REVIEW_BASE_URL,
            # Clé API partagée (X-Internal-Api-Key)
            "api_key": settings.BANK_REVIEW_API_KEY,
            # Channel Slack principal : reçoit les notifications de déploiement
            "slack_channel": settings.BANK_REVIEW_CHANNEL_ID,
            # Channel feedback : reçoit les alertes de nouveaux tickets
            "feedback_channel": settings.BANK_REVIEW_FEEDBACK_CHANNEL_ID,
            # UUID de l'app Coolify (pour la reconnaissance du webhook de déploiement)
            "coolify_uuid": "ji9jg7ngkva7j4d2uic05d3v",
            # Channels depuis lesquels /feedback est accepté
            "linked_channels": list(filter(None, [
                settings.BANK_REVIEW_CHANNEL_ID,
                settings.BANK_REVIEW_FEEDBACK_CHANNEL_ID,
            ])),
        },
        # ── Modèle pour un prochain service ──────────────────────────────────
        # {
        #     "name": "journal",
        #     "base_url": settings.JOURNAL_BASE_URL,
        #     "api_key": settings.JOURNAL_API_KEY,
        #     "slack_channel": settings.JOURNAL_CHANNEL_ID,
        #     "feedback_channel": settings.JOURNAL_FEEDBACK_CHANNEL_ID,
        #     "coolify_uuid": "<uuid>",
        #     "linked_channels": list(filter(None, [
        #         settings.JOURNAL_CHANNEL_ID,
        #         settings.JOURNAL_FEEDBACK_CHANNEL_ID,
        #     ])),
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
    return next((s for s in _build_registry() if s.get("coolify_uuid") == uuid), None)
