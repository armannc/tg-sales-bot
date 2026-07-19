"""
Статистика и рейтинг сотрудников: /stats, /employee, /day, /month, /year, /top, /export.
"""
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, FSInputFile, Message

from bot.database.engine import async_session_factory
from bot.services.employee_service import get_employee_by_name
from bot.services.export_service import export_stats_to_excel
from bot.services.stats_service import (
    EmployeeStats,
    get_all_employee_stats,
    get_employee_stats,
    get_period_bounds,
    get_top_employees,
)
from bot.utils.formatting import format_money
from bot.utils.keyboards import back_to_menu_keyboard

router = Router(name="stats")


def _format_employee_block(stats: EmployeeStats, index: int | None = None) -> str:
    prefix = f"{index}. " if index is not None else ""
    return (
        f"{prefix}<b>{stats.employee.name}</b>\n"
        f"Смен: {stats.shifts} | Продажи: {format_money(stats.total_sales)} | "
        f"План: {format_money(stats.plan)}\n"
        f"Выполнение: {stats.percent:.0f}% | Средняя касса: {format_money(stats.avg_kassa)}\n"
        f"Бонусы из отчетов: {format_money(stats.total_bonus)}"
    )


async def _build_stats_text() -> str:
    async with async_session_factory() as session:
        all_stats = await get_all_employee_stats(session)

    if not all_stats:
        return "Пока нет данных для статистики."

    all_stats.sort(key=lambda s: s.percent, reverse=True)
    blocks = [_format_employee_block(s, i + 1) for i, s in enumerate(all_stats)]
    return "📊 <b>Общий рейтинг сотрудников</b>\n\n" + "\n\n".join(blocks)


async def _build_period_text(period: str, title: str) -> str:
    date_from, date_to = await get_period_bounds(period)
    async with async_session_factory() as session:
        all_stats = await get_all_employee_stats(session, date_from, date_to)

    if not all_stats:
        return f"{title}: нет данных."

    all_stats.sort(key=lambda s: s.percent, reverse=True)
    blocks = [_format_employee_block(s, i + 1) for i, s in enumerate(all_stats)]
    return f"{title}\n\n" + "\n\n".join(blocks)


async def _build_top_text(limit: int) -> str:
    async with async_session_factory() as session:
        top_stats = await get_top_employees(session, limit=limit)

    if not top_stats:
        return "Пока нет данных для топа."

    blocks = [_format_employee_block(s, i + 1) for i, s in enumerate(top_stats)]
    return f"🏆 <b>Топ-{limit} по выполнению плана</b>\n\n" + "\n\n".join(blocks)


@router.message(Command("stats"))
async def cmd_stats(message: Message) -> None:
    await message.answer(await _build_stats_text())


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
        stats = await get_employee_stats(session, employee)

    await message.answer(
        f"👤 <b>Статистика: {employee.name}</b>\n\n{_format_employee_block(stats)}"
    )


@router.message(Command("day"))
async def cmd_day(message: Message) -> None:
    await message.answer(await _build_period_text("day", "📅 <b>Статистика за сегодня</b>"))


@router.message(Command("month"))
async def cmd_month(message: Message) -> None:
    await message.answer(await _build_period_text("month", "🗓 <b>Статистика за текущий месяц</b>"))


@router.message(Command("year"))
async def cmd_year(message: Message) -> None:
    await message.answer(await _build_period_text("year", "📈 <b>Статистика за текущий год</b>"))


@router.message(Command("top"))
async def cmd_top(message: Message, command: CommandObject) -> None:
    limit = 5
    if command.args:
        try:
            limit = int(command.args.strip())
        except ValueError:
            await message.answer("Использование: /top [N], например /top 10")
            return

    await message.answer(await _build_top_text(limit))


@router.message(Command("export"))
async def cmd_export(message: Message) -> None:
    await message.answer("⏳ Формирую Excel-отчет...")
    async with async_session_factory() as session:
        file_path = await export_stats_to_excel(session)

    await message.answer_document(FSInputFile(file_path))


# ------------------------------------------------------------------
# Обработчики кнопок главного меню
# ------------------------------------------------------------------

@router.callback_query(F.data == "menu:stats")
async def cb_menu_stats(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        await _build_stats_text(), reply_markup=back_to_menu_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "menu:top")
async def cb_menu_top(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        await _build_top_text(5), reply_markup=back_to_menu_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "menu:day")
async def cb_menu_day(callback: CallbackQuery) -> None:
    text = await _build_period_text("day", "📅 <b>Статистика за сегодня</b>")
    await callback.message.edit_text(text, reply_markup=back_to_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data == "menu:month")
async def cb_menu_month(callback: CallbackQuery) -> None:
    text = await _build_period_text("month", "🗓 <b>Статистика за текущий месяц</b>")
    await callback.message.edit_text(text, reply_markup=back_to_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data == "menu:year")
async def cb_menu_year(callback: CallbackQuery) -> None:
    text = await _build_period_text("year", "📈 <b>Статистика за текущий год</b>")
    await callback.message.edit_text(text, reply_markup=back_to_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data == "menu:export")
async def cb_menu_export(callback: CallbackQuery) -> None:
    await callback.answer("Формирую Excel-отчет...")
    async with async_session_factory() as session:
        file_path = await export_stats_to_excel(session)
    await callback.message.answer_document(FSInputFile(file_path))