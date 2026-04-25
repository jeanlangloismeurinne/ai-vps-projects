from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    SLACK_BOT_TOKEN: str
    SLACK_APP_TOKEN: str          # xapp-... Socket Mode (scope connections:write)
    STORAGE_BASE: Path = Path("/storage/Documents")
    DB_PATH: str = "/data/intake-db/intake.db"
    AGENT_WEBHOOK_URL: str = ""
    MAX_FILE_SIZE_MB: int = 50

    model_config = {"env_file": ".env"}


settings = Settings()

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "text/plain",
    "text/csv",
    "text/markdown",
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
    "application/zip",
    "application/json",
}
