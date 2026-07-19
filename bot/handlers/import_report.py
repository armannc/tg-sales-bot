"""
Импорт отчета: /import запускает FSM, ожидающий текст отчета следующим сообщением.
"""
from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.database.engine import async_session_factory
from bot.handlers.states import ImportStates
from bot.services.report_service import ReportImportError, import_report_text
from bot.services.parser import ReportParseError
from bot.utils.access import is_admin
from bot.utils.formatting import format_date, format_money, format_percent

logger = logging.getLogger(__name__)

router = Router(name="import_report")


@router.message(Command("import"))
async def cmd_import(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Эта команда доступна только администратору.")
        return

    await state.set_state(ImportStates.waiting_for_text)
    await message.answer(
        "Пришлите текст отчета одним сообщением.\n"
        "Чтобы отменить, отправьте /cancel."
    )


@router.message(Command("cancel"), ImportStates.waiting_for_text)
async def cmd_cancel_import(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Импорт отменен.")


@router.message(ImportStates.waiting_for_text, F.text)
async def process_report_text(message: Message, state: FSMContext) -> None:
    text = message.text
    await state.clear()

    async with async_session_factory() as session:
        try:
            daily_report = await import_report_text(session, text)
        except ReportParseError as exc:
            await message.answer(f"❌ Не удалось разобрать отчет:\n{exc}")
            return
        except ReportImportError as exc:
            await message.answer(f"❌ Ошибка в данных отчета:\n{exc}")
            return
        except Exception:  # noqa: BLE001
            logger.exception("Неожиданная ошибка при импорте отчета")
            await message.answer("❌ Произошла непредвиденная ошибка при импорте отчета.")
            return

        # ВАЖНО: обращаемся к daily_report.employee_reports, пока сессия еще
        # открыта (мы внутри "async with"). После выхода из блока сессия
        # закрывается, и любое обращение к отложенно загружаемым атрибутам
        # объекта привело бы к DetachedInstanceError.
        employees_count = len(daily_report.employee_reports)
        report_date = daily_report.report_date
        total_revenue = daily_report.total_revenue
        online_sales = daily_report.online_sales
        conversion = daily_report.conversion

    reply = (
        f"✅ Отчет за {format_date(report_date)} успешно импортирован.\n\n"
        f"Выручка (Вообщем): {format_money(total_revenue)}\n"
        f"Онлайн продажи: {format_money(online_sales)}\n"
        f"Конверсия: {format_percent(conversion)}\n"
        f"Сотрудников в смене: {employees_count}"
    )
    await message.answer(reply)


@router.message(ImportStates.waiting_for_text)
async def process_report_wrong_type(message: Message) -> None:
    await message.answer("Пришлите отчет текстовым сообщением или отправьте /cancel.")