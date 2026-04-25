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

    # Web auth (shared entre /journal et /kanban)
    WEB_USERNAME: str
    WEB_PASSWORD: str

    class Config:
        env_file = ".env"


settings = Settings()
