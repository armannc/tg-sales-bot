"""
Настройка асинхронного подключения к базе данных.
"""
from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from bot.config import config
from bot.database.models import Base

logger = logging.getLogger(__name__)

# asyncpg (используется для PostgreSQL/Supabase) не читает "?sslmode=require"
# из URL так же, как psycopg2 - SSL нужно включить явно через connect_args.
# Для SQLite этот параметр не нужен и не передается.
_connect_args: dict = {}
if config.database_url.startswith("postgresql"):
    _connect_args["ssl"] = "require"

engine = create_async_engine(
    config.database_url,
    echo=False,
    future=True,
    connect_args=_connect_args,
    pool_pre_ping=True,   # проверяет соединение перед использованием - избегает зависаний
                           # на "протухших" соединениях через пулер Supabase
    pool_recycle=300,     # пересоздает соединения старше 5 минут (пулеры часто
                           # сами закрывают долго простаивающие соединения)
)

async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def init_db() -> None:
    """Создать таблицы, если их еще нет."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("База данных инициализирована (%s)", config.database_url)
