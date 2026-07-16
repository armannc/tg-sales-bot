"""
Конфигурация приложения.

Все настройки читаются из переменных окружения (.env файла).
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

# Загружаем .env из корня проекта
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _get_int_list(raw: str | None) -> list[int]:
    if not raw:
        return []
    result: list[int] = []
    for chunk in raw.split(","):
        chunk = chunk.strip()
        if chunk:
            result.append(int(chunk))
    return result


@dataclass(frozen=True, slots=True)
class DefaultPlans:
    """Планы по умолчанию для новых сотрудников (в тенге за смену)."""

    consultant: float = float(os.getenv("DEFAULT_PLAN_CONSULTANT", "483000"))
    online: float = float(os.getenv("DEFAULT_PLAN_ONLINE", "250000"))


@dataclass(frozen=True, slots=True)
class Config:
    bot_token: str = field(default_factory=lambda: os.getenv("BOT_TOKEN", ""))
    admin_ids: list[int] = field(default_factory=lambda: _get_int_list(os.getenv("ADMIN_IDS")))
    database_url: str = field(
        default_factory=lambda: os.getenv("DATABASE_URL", f"sqlite+aiosqlite:///{BASE_DIR / 'sales_bot.db'}")
    )
    timezone: str = field(default_factory=lambda: os.getenv("TIMEZONE", "Asia/Almaty"))
    default_plans: DefaultPlans = field(default_factory=DefaultPlans)

    def __post_init__(self) -> None:
        if not self.bot_token:
            raise RuntimeError(
                "BOT_TOKEN не найден. Убедитесь, что переменная окружения BOT_TOKEN задана в .env файле."
            )


config = Config()
