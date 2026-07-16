"""
Хендлеры статистики: /stats, /employee, /day, /month, /year, /top, /export.
"""
from __future__ import annotations

import datetime as dt
import logging

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import BufferedInputFile, Message

from bot.database.engine import async_session_factory
from bot.services.export_service import export_stats_to_excel
from bot.services.employee_service import get_employee_by_name
from bot.services.stats_service import (
    EmployeeStats,
    get_all_employee_stats,
    get_period_bounds,
    get_top_employees,
)
from bot.utils.formatting import format_money, format_percent, medal_for_place

logger = logging.getLogger(__name__)

router = Router(name="stats")


def _format_employee_block(place: int, stats: EmployeeStats) -> str:
    return (
        f"{medal_for_place(place)} <b>{stats.employee.name}</b>\n\n"
        f"Продажи\n{format_money(stats.total_sales)}\n\n"
        f"Смен\n{stats.shifts}\n\n"
        f"План\n{format_money(stats.plan)}\n\n"
        f"Выполнение\n{format_percent(stats.percent)}\n\n"
        f"Средняя касса\n{format_money(stats.avg_kassa)}\n"
        "----------------------"
    )


@router.message(Command("stats"))
async def cmd_stats(message: Message) -> None:
    async with async_session_factory() as session:
        stats = await get_all_employee_stats(session)

    if not stats:
        await message.answer("Пока нет данных для статистики. Импортируйте хотя бы один отчет.")
        return

    stats.sort(key=lambda s: s.percent, reverse=True)
    blocks = [_format_employee_block(i + 1, s) for i, s in enumerate(stats)]
    await message.answer("\n\n".join(blocks))


@router.message(Command("employee"))
async def cmd_employee(message: Message, command: CommandObject) -> None:
    if not command.args:
        await message.answer("Использование: /employee Имя")
        return

    name = command.args.strip()
    async with async_session_factory() as session:
        employee = await get_employee_by_name(session, name)
        if employee is None:
            await message.answer(f"Сотрудник {name!r} не найден.")
            return

        from bot.services.stats_service import get_employee_stats

        stats = await get_employee_stats(session, employee)

    reply = (
        f"<b>{employee.name}</b> ({employee.role.value})\n\n"
        f"Продажи всего: {format_money(stats.total_sales)}\n"
        f"Смен: {stats.shifts}\n"
        f"План: {format_money(stats.plan)}\n"
        f"Выполнение: {format_percent(stats.percent)}\n"
        f"Средняя касса: {format_money(stats.avg_kassa)}\n"
        f"Бонусы: {format_money(stats.total_bonus)}\n"
        f"Дневной план (за смену): {format_money(employee.daily_plan)}"
    )
    await message.answer(reply)


async def _period_stats_reply(period: str, title: str) -> str:
    date_from, date_to = await get_period_bounds(period)
    async with async_session_factory() as session:
        stats = await get_all_employee_stats(session, date_from, date_to)

    if not stats:
        return f"Нет данных за {title.lower()}."

    stats.sort(key=lambda s: s.percent, reverse=True)
    blocks = [_format_employee_block(i + 1, s) for i, s in enumerate(stats)]
    header = f"📊 <b>Статистика: {title}</b>\n\n"
    return header + "\n\n".join(blocks)


@router.message(Command("day"))
async def cmd_day(message: Message) -> None:
    reply = await _period_stats_reply("day", "сегодня")
    await message.answer(reply)


@router.message(Command("month"))
async def cmd_month(message: Message) -> None:
    reply = await _period_stats_reply("month", "текущий месяц")
    await message.answer(reply)


@router.message(Command("year"))
async def cmd_year(message: Message) -> None:
    reply = await _period_stats_reply("year", "текущий год")
    await message.answer(reply)


@router.message(Command("top"))
async def cmd_top(message: Message, command: CommandObject) -> None:
    limit = 5
    if command.args and command.args.strip().isdigit():
        limit = int(command.args.strip())

    async with async_session_factory() as session:
        top = await get_top_employees(session, limit=limit)

    if not top:
        await message.answer("Нет данных для топа сотрудников.")
        return

    blocks = [_format_employee_block(i + 1, s) for i, s in enumerate(top)]
    await message.answer("🏆 <b>Топ сотрудников по выполнению плана</b>\n\n" + "\n\n".join(blocks))


@router.message(Command("export"))
async def cmd_export(message: Message) -> None:
    async with async_session_factory() as session:
        file_path = await export_stats_to_excel(session)

    with open(file_path, "rb") as f:
        data = f.read()

    document = BufferedInputFile(data, filename=file_path.name)
    await message.answer_document(document, caption="📥 Статистика по всем сотрудникам")
