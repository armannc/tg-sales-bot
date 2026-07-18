#Content is user-generated and unverified.
"""
Расчет зарплаты сотрудников: оклад + % от личных продаж за произвольный период.

Премии/бонусы из отчетов (строка "Бонус") в зарплату не входят — считаются
отдельно как разовая выплата.
"""
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, Message

from bot.database.engine import async_session_factory
from bot.services.employee_service import get_employee_by_name
from bot.services.stats_service import SalaryResult, calculate_salary, calculate_salary_for_all
from bot.utils.dates import DateParseError, parse_date_arg
from bot.utils.formatting import format_date, format_money
from bot.utils.keyboards import back_to_menu_keyboard

router = Router(name="salary")

SALARY_USAGE = (
    "💰 <b>Расчет зарплаты</b>\n\n"
    "Формула: оклад за смену × отработанные смены + % от личных продаж.\n"
    "Процент от продаж определяется автоматически по проценту выполнения "
    "плана за период:\n"
    "≤80% → 1%, 81-90% → 2%, 91-109% → 3%, ≥110% → 4%.\n"
    "Премии из отчетов сюда не входят — считаются отдельно.\n\n"
    "<b>Использование:</b>\n"
    "/salary Имя ДД.ММ.ГГГГ ДД.ММ.ГГГГ — зарплата одного сотрудника\n"
    "/salary_all ДД.ММ.ГГГГ ДД.ММ.ГГГГ — зарплата всех сотрудников\n\n"
    "Например: /salary Алина 01.07.2026 31.07.2026\n\n"
    "Оклад за смену задает администратор командой /set_salary."
)


def _format_salary_block(result: SalaryResult) -> str:
    return (
        f"<b>{result.employee.name}</b>\n"
        f"Смен отработано: {result.shifts}\n"
        f"Личные продажи: {format_money(result.total_sales)}\n"
        f"Выполнение плана: {result.plan_percent:.0f}%\n"
        f"Оклад за смену: {format_money(result.shift_rate)} × {result.shifts} = "
        f"{format_money(result.base_salary_total)}\n"
        f"% от продаж ({result.sales_percent:g}%, по шкале плана): {format_money(result.sales_bonus)}\n"
        f"<b>Итого: {format_money(result.total_salary)}</b>"
    )


@router.message(Command("salary"))
async def cmd_salary(message: Message, command: CommandObject) -> None:
    if not command.args:
        await message.answer(SALARY_USAGE)
        return

    parts = command.args.split()
    if len(parts) != 3:
        await message.answer(SALARY_USAGE)
        return

    name, date_from_raw, date_to_raw = parts
    try:
        date_from = parse_date_arg(date_from_raw)
        date_to = parse_date_arg(date_to_raw)
    except DateParseError as exc:
        await message.answer(f"❌ {exc}")
        return

    if date_from > date_to:
        date_from, date_to = date_to, date_from

    async with async_session_factory() as session:
        employee = await get_employee_by_name(session, name)
        if employee is None:
            await message.answer(f"Сотрудник {name!r} не найден.")
            return
        result = await calculate_salary(session, employee, date_from, date_to)

    reply = (
        f"💰 <b>Зарплата: {employee.name}</b>\n"
        f"Период: {format_date(date_from)} — {format_date(date_to)}\n\n"
        f"{_format_salary_block(result)}\n\n"
        f"<i>Премии/бонусы из отчетов сюда не входят.</i>"
    )
    await message.answer(reply)


@router.message(Command("salary_all"))
async def cmd_salary_all(message: Message, command: CommandObject) -> None:
    if not command.args or len(command.args.split()) != 2:
        await message.answer(
            "Использование: /salary_all ДД.ММ.ГГГГ ДД.ММ.ГГГГ\n"
            "Например: /salary_all 01.07.2026 31.07.2026"
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
        results = await calculate_salary_for_all(session, date_from, date_to)

    if not results:
        await message.answer("Нет данных за указанный период.")
        return

    total_payout = sum(r.total_salary for r in results)
    blocks = [_format_salary_block(r) for r in results]
    header = (
        f"💰 <b>Зарплата всех сотрудников</b>\n"
        f"Период: {format_date(date_from)} — {format_date(date_to)}\n\n"
    )
    footer = f"\n\n<b>Итого фонд оплаты труда: {format_money(total_payout)}</b>"
    await message.answer(header + "\n\n----------------------\n\n".join(blocks) + footer)


@router.callback_query(F.data == "menu:salary")
async def cb_salary_help(callback: CallbackQuery) -> None:
    await callback.message.edit_text(SALARY_USAGE, reply_markup=back_to_menu_keyboard())
    await callback.answer()
