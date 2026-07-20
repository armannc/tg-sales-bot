"""
Личный кабинет сотрудника: /me, /my_stats, /my_salary.

Доступ определяется по привязанному telegram_id (см. bot/services/invite_service.py) -
сотрудник видит только свою собственную статистику и зарплату, без доступа
к данным других сотрудников и без админских команд.
"""
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, Message

from bot.database.engine import async_session_factory
from bot.database.models import Employee
from bot.services.employee_service import get_employee_by_telegram_id
from bot.services.stats_service import calculate_salary, get_employee_stats, get_period_bounds
from bot.utils.dates import DateParseError, parse_date_arg
from bot.utils.formatting import format_date, format_money, format_percent
from bot.utils.keyboards import back_to_menu_keyboard

router = Router(name="employee")

NOT_LINKED_TEXT = (
    "Ваш аккаунт пока не привязан ни к одному сотруднику. "
    "Попросите администратора выдать вам ссылку-приглашение (команда /invite)."
)


async def _get_own_employee_or_none(telegram_id: int) -> Employee | None:
    async with async_session_factory() as session:
        return await get_employee_by_telegram_id(session, telegram_id)


def _format_stats_reply(employee: Employee, stats) -> str:
    return (
        f"📊 <b>Моя статистика: {employee.name}</b>\n\n"
        f"Смен отработано: {stats.shifts}\n"
        f"Продажи всего: {format_money(stats.total_sales)}\n"
        f"План: {format_money(stats.plan)}\n"
        f"Выполнение: {format_percent(stats.percent)}\n"
        f"Средняя касса: {format_money(stats.avg_kassa)}\n"
        f"Бонусы (из отчетов): {format_money(stats.total_bonus)}"
    )


def _format_salary_reply(employee: Employee, result, date_from, date_to) -> str:
    return (
        f"💰 <b>Моя зарплата: {employee.name}</b>\n"
        f"Период: {format_date(date_from)} — {format_date(date_to)}\n\n"
        f"Смен отработано: {result.shifts}\n"
        f"Личные продажи: {format_money(result.total_sales)}\n"
        f"Выполнение плана: {result.plan_percent:.0f}%\n"
        f"Оклад за смену: {format_money(result.shift_rate)} × {result.shifts} = "
        f"{format_money(result.base_salary_total)}\n"
        f"% от продаж ({result.sales_percent:g}%, по шкале плана): {format_money(result.sales_bonus)}\n\n"
        f"<b>Итого: {format_money(result.total_salary)}</b>\n\n"
        f"<i>Премии/бонусы из отчетов сюда не входят.</i>"
    )


@router.message(Command("me"))
async def cmd_me(message: Message) -> None:
    employee = await _get_own_employee_or_none(message.from_user.id)
    if employee is None:
        await message.answer(NOT_LINKED_TEXT)
        return

    async with async_session_factory() as session:
        date_from, date_to = await get_period_bounds("month")
        stats = await get_employee_stats(session, employee, date_from, date_to)

    reply = (
        f"👋 <b>{employee.name}</b> ({employee.role.value})\n\n"
        f"Статистика за текущий месяц:\n"
        f"Смен: {stats.shifts}, продажи: {format_money(stats.total_sales)}, "
        f"выполнение плана: {format_percent(stats.percent)}"
    )
    await message.answer(reply)


@router.message(Command("my_stats"))
async def cmd_my_stats(message: Message) -> None:
    employee = await _get_own_employee_or_none(message.from_user.id)
    if employee is None:
        await message.answer(NOT_LINKED_TEXT)
        return

    async with async_session_factory() as session:
        stats = await get_employee_stats(session, employee)

    await message.answer(_format_stats_reply(employee, stats))


@router.message(Command("my_salary"))
async def cmd_my_salary(message: Message, command: CommandObject) -> None:
    employee = await _get_own_employee_or_none(message.from_user.id)
    if employee is None:
        await message.answer(NOT_LINKED_TEXT)
        return

    if not command.args or len(command.args.split()) != 2:
        await message.answer(
            "Использование: /my_salary ДД.ММ.ГГГГ ДД.ММ.ГГГГ\n"
            "Например: /my_salary 01.07.2026 31.07.2026"
        )
        return

    date_from_raw, date_to_raw = command.args.split()
    try:
        date_from = parse_date_arg(date_from_raw)
        date_to = parse_date_arg(date_to_raw)
    except DateParseError as exc:
        await message.answer(f"❌ {exc}")
        return

    if date_from > date_to:
        date_from, date_to = date_to, date_from

    async with async_session_factory() as session:
        result = await calculate_salary(session, employee, date_from, date_to)

    await message.answer(_format_salary_reply(employee, result, date_from, date_to))


# ------------------------------------------------------------------
# Кнопки личного меню (me:*)
# ------------------------------------------------------------------

@router.callback_query(F.data == "me:stats")
async def cb_me_stats(callback: CallbackQuery) -> None:
    employee = await _get_own_employee_or_none(callback.from_user.id)
    if employee is None:
        await callback.message.edit_text(NOT_LINKED_TEXT)
        await callback.answer()
        return

    async with async_session_factory() as session:
        stats = await get_employee_stats(session, employee)

    await callback.message.edit_text(
        _format_stats_reply(employee, stats), reply_markup=back_to_menu_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "me:salary_month")
async def cb_me_salary_month(callback: CallbackQuery) -> None:
    employee = await _get_own_employee_or_none(callback.from_user.id)
    if employee is None:
        await callback.message.edit_text(NOT_LINKED_TEXT)
        await callback.answer()
        return

    async with async_session_factory() as session:
        date_from, date_to = await get_period_bounds("month")
        result = await calculate_salary(session, employee, date_from, date_to)

    await callback.message.edit_text(
        _format_salary_reply(employee, result, date_from, date_to),
        reply_markup=back_to_menu_keyboard(),
    )
    await callback.answer()