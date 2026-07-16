"""
Базовые команды: /start, /help.
"""
from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

router = Router(name="common")


HELP_TEXT = (
    "🤖 <b>Бот учета продаж</b>\n\n"
    "<b>Основные команды:</b>\n"
    "/import — импортировать текстовый отчет за смену\n"
    "/stats — общий рейтинг сотрудников\n"
    "/employee &lt;имя&gt; — статистика по сотруднику\n"
    "/day — статистика за сегодня\n"
    "/month — статистика за текущий месяц\n"
    "/year — статистика за текущий год\n"
    "/top — топ сотрудников по выполнению плана\n"
    "/export — выгрузить статистику в Excel\n\n"
    "<b>Команды администратора:</b>\n"
    "/add_employee — добавить сотрудника\n"
    "/remove_employee &lt;имя&gt; — удалить сотрудника\n"
    "/set_role &lt;имя&gt; &lt;consultant|online&gt; — изменить роль\n"
    "/set_plan &lt;consultant|online|имя&gt; &lt;сумма&gt; — изменить план\n"
)


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(
        "Привет! Я бот для учета продаж сотрудников магазина.\n\n"
        "Отправь /help, чтобы увидеть список доступных команд."
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(HELP_TEXT)
