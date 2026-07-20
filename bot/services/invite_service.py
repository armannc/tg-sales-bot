"""
Сервис инвайт-кодов: привязка Telegram-аккаунта сотрудника к его записи в базе.

Поток:
1. Администратор: /invite Имя -> создается одноразовый код, бот присылает ссылку.
2. Сотрудник переходит по ссылке t.me/<bot>?start=<code>.
3. Бот находит код, проверяет, что не использован, привязывает telegram_id
   сотрудника к его Employee-записи, помечает код использованным.
"""
from __future__ import annotations

import secrets
import datetime as dt

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import Employee, InviteCode


class InviteError(Exception):
    """Ошибка при создании или использовании инвайт-кода."""


def _generate_code() -> str:
    # 8 символов, URL-safe, достаточно для бота с небольшим числом сотрудников.
    return secrets.token_urlsafe(6)


async def create_invite_code(session: AsyncSession, employee: Employee) -> str:
    """Создает новый одноразовый код для сотрудника (старые неиспользованные
    коды этого сотрудника остаются в базе, но использовать можно только
    последний - предыдущие просто не будут никому известны)."""
    code = _generate_code()
    invite = InviteCode(code=code, employee_id=employee.id)
    session.add(invite)
    await session.commit()
    return code


async def use_invite_code(session: AsyncSession, code: str, telegram_id: int) -> Employee:
    """Проверяет код и привязывает telegram_id к сотруднику.

    Raises:
        InviteError: код не найден, уже использован, либо этот Telegram-аккаунт
            уже привязан к другому сотруднику.
    """
    result = await session.execute(select(InviteCode).where(InviteCode.code == code))
    invite = result.scalar_one_or_none()
    if invite is None:
        raise InviteError("Код приглашения не найден или недействителен.")
    if invite.used_at is not None:
        raise InviteError("Этот код приглашения уже был использован.")

    existing = await session.execute(select(Employee).where(Employee.telegram_id == telegram_id))
    if existing.scalar_one_or_none() is not None:
        raise InviteError("Этот Telegram-аккаунт уже привязан к другому сотруднику.")

    employee = await session.get(Employee, invite.employee_id)
    if employee is None:
        raise InviteError("Сотрудник для этого кода не найден (возможно, был удален).")

    employee.telegram_id = telegram_id
    invite.used_at = dt.datetime.utcnow()
    invite.used_by_telegram_id = telegram_id
    await session.commit()
    return employee