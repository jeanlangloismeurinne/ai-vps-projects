from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    SESSION_SECRET: str  # partagé avec la homepage pour hub_session
    SLACK_BOT_TOKEN: str = ""
    SLACK_ALERT_CHANNEL: str = "C0AUFGZNBGT"

    class Config:
        env_file = ".env"


settings = Settings()
