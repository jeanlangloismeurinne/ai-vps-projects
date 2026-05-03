from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DUST_API_KEY: str
    DUST_WORKSPACE_ID: str = "plm-siege"
    DUST_RESEARCH_AGENT_ID: str
    DUST_PORTFOLIO_AGENT_ID: str
    DUST_MONTHLY_BUDGET_USD: float = 5.0
    DATABASE_URL: str
    # postgresql+asyncpg://admin:PASSWORD@shared-postgres:5432/db_portfolio
    REDIS_URL: str = "redis://shared-redis:6379"
    SLACK_BOT_TOKEN: str
    SLACK_APP_TOKEN: str
    SLACK_PORTFOLIO_CHANNEL_ID: str
    FMP_API_KEY: str
    FRED_API_KEY: str = ""
    BASE_CURRENCY: str = "EUR"
    MAX_SECTOR_CONCENTRATION_PCT: float = 20.0
    PULSE_ESCALATION_THRESHOLD: int = -3

    class Config:
        env_file = None  # Coolify injecte les variables


settings = Settings()
