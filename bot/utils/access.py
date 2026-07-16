"""
Проверка прав администратора.
"""
from __future__ import annotations

from bot.config import config


def is_admin(user_id: int) -> bool:
    if not config.admin_ids:
        # Если список админов не задан - разрешаем всем (удобно для первого запуска/теста).
        return True
    return user_id in config.admin_ids
