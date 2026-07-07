from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from app.core.config import Settings


@dataclass(frozen=True)
class Database:
    engine: AsyncEngine
    session_factory: async_sessionmaker


async def init_database(settings: Settings) -> Database:
    engine = create_async_engine(settings.database_url, pool_pre_ping=True, pool_size=5, max_overflow=10)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.execute(text("SELECT 1"))
    return Database(engine=engine, session_factory=session_factory)


async def close_database(database: Database) -> None:
    await database.engine.dispose()


async def database_ready(database: Database) -> bool:
    try:
        async with database.engine.begin() as connection:
            await connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False

