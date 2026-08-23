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

    # V1 — Agents Dust
    DUST_OPPORTUNITY_AGENT_ID: str = ""
    DUST_THESIS_AGENT_ID: str = ""
    DUST_MONITORING_AGENT_ID: str = ""

    # V1 — Slack Webhook (notifications légères sans Socket Mode)
    SLACK_WEBHOOK_URL: str = ""
    SLACK_ALERT_CHANNEL: str = "#portfolio-alerts"

    # V2 — Provider DeepInfra (endpoint OpenAI-compatible, agents flow_version='v2')
    DEEPINFRA_API_KEY: str = ""
    DEEPINFRA_API_BASE: str = "https://api.deepinfra.com/v1/openai"

    # V2 — Embeddings (DÉCISION #4, 3ᵉ révision — migration 027)
    # bge-m3 est MULTILINGUE : le corpus est en français, et bge-base-en-v1.5 (anglais seul)
    # ratait les entrées financières Tier A (hit@3 4/7 contre 7/7). Voir 027_v2_embeddings_1024.sql.
    # EMBEDDING_DIM doit rester synchronisé avec knowledge_entries.embedding vector(N) : le
    # changer seul ferait échouer toute écriture. Changer de modèle = migration + backfill complet.
    EMBEDDING_MODEL: str = "BAAI/bge-m3"
    EMBEDDING_DIM: int = 1024

    class Config:
        env_file = None  # Coolify injecte les variables


settings = Settings()
