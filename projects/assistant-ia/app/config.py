from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    SLACK_BOT_TOKEN: str
    BANK_REVIEW_CHANNEL_ID: str
    BANK_REVIEW_BASE_URL: str = "https://bank.jlmvpscode.duckdns.org"
    BANK_REVIEW_API_KEY: str
    ASSISTANT_BASE_URL: str = "https://assistant.jlmvpscode.duckdns.org"

    class Config:
        env_file = ".env"


settings = Settings()
