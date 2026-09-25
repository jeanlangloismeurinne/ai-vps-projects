from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


engine = create_async_engine(settings.DATABASE_URL, echo=False, pool_pre_ping=True)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session


# `create_all` crée les tables neuves mais n'ajoute JAMAIS de colonne à une table existante :
# ces ALTER sont donc explicites. Tous additifs et nullables (ou avec défaut) → l'ancien code
# tourne encore sur le nouveau schéma, un rollback n'exige aucun retour de schéma.
_MIGRATIONS = [
    "ALTER TABLE emails ADD COLUMN IF NOT EXISTS alias_id INTEGER",
    "ALTER TABLE emails ADD COLUMN IF NOT EXISTS attempts INTEGER NOT NULL DEFAULT 0",
    "ALTER TABLE emails ADD COLUMN IF NOT EXISTS last_error TEXT",
    "ALTER TABLE emails ADD COLUMN IF NOT EXISTS claimed_at TIMESTAMP",
    "ALTER TABLE prompt_versions ADD COLUMN IF NOT EXISTS alias_id INTEGER",
    "CREATE INDEX IF NOT EXISTS ix_emails_alias_id ON emails (alias_id)",
    "CREATE INDEX IF NOT EXISTS ix_prompt_versions_alias_id ON prompt_versions (alias_id)",
]


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        for stmt in _MIGRATIONS:
            await conn.exec_driver_sql(stmt)
