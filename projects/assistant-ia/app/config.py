from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Slack
    SLACK_BOT_TOKEN: str
    SLACK_APP_TOKEN: str  # xapp-... requis pour Socket Mode

    # Bank review (existing)
    BANK_REVIEW_CHANNEL_ID: str
    BANK_REVIEW_BASE_URL: str = "https://bank.jlmvpscode.duckdns.org"
    BANK_REVIEW_API_KEY: str
    ASSISTANT_BASE_URL: str = "https://assistant.jlmvpscode.duckdns.org"

    # Database
    DATABASE_URL: str  # postgresql://user:pass@shared-postgres:5432/db_assistant

    # Feature 1 — Journal
    SLACK_CHANNEL_JOURNAL: str = "#journal"

    # Feature 2 — Kanban
    SLACK_CHANNEL_TASKS: str = "#tasks"

    # Feedback routing — channel IDs associés à chaque service
    # Format : "CHANNEL_ID_1,CHANNEL_ID_2" → séparés par virgule si plusieurs par service
    FEEDBACK_CHANNELS_BANK_REVIEW: str = ""  # IDs des channels liés à bank-review

    # Web auth
    WEB_USERNAME: str
    WEB_PASSWORD: str
    SESSION_SECRET: str  # partagé avec homepage pour le cookie hub_session

    class Config:
        env_file = ".env"


settings = Settings()
