from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Slack
    SLACK_BOT_TOKEN: str
    SLACK_APP_TOKEN: str  # xapp-... requis pour Socket Mode

    # Bank review
    BANK_REVIEW_CHANNEL_ID: str = "C0AV2EJHR5H"        # #bank-review
    BANK_REVIEW_BASE_URL: str = "https://bank.jlmvpscode.duckdns.org"
    BANK_REVIEW_API_KEY: str
    BANK_REVIEW_FEEDBACK_CHANNEL_ID: str = "C0ATW9S0S7N"  # #features-bank-review

    ASSISTANT_BASE_URL: str = "https://assistant.jlmvpscode.duckdns.org"

    # Database
    DATABASE_URL: str  # postgresql://user:pass@shared-postgres:5432/db_assistant

    # Channels Slack par service (valeurs par défaut = IDs connus)
    JOURNAL_CHANNEL_ID: str = "C0B080X2ZBK"         # #journal
    TASKS_CHANNEL_ID: str = "C0AV5M6385T"            # #tasks (kanban)
    FEATURES_AI_CHANNEL_ID: str = "C0AUCE6NELT"      # #features-ai-assistant (déprécié)
    FEEDBACK_CHANNEL_ID: str = "C0AUCE6NELT"         # #feedback (canal unifié)

    # Feature 1 — Journal
    SLACK_CHANNEL_JOURNAL: str = "#journal"

    # Feature 2 — Kanban
    SLACK_CHANNEL_TASKS: str = "#tasks"

    # Sécurité webhook deploy
    DEPLOY_WEBHOOK_SECRET: str = ""  # si vide, pas d'auth sur /webhook/deploy-complete

    # Clé API interne pour les endpoints feedback d'assistant-ia
    ASSISTANT_INTERNAL_API_KEY: str = ""

    # Web auth
    WEB_USERNAME: str
    WEB_PASSWORD: str
    SESSION_SECRET: str  # partagé avec homepage pour le cookie hub_session

    class Config:
        env_file = ".env"


settings = Settings()
