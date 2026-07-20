"""
Базовые команды: /start, /help, а также обработка главного меню (inline-кнопки).
"""
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.handlers.states import ImportStates
from bot.utils.keyboards import back_to_menu_keyboard, main_menu_keyboard

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
    "/export — выгрузить статистику в Excel\n"
    "/salary Имя ДД.ММ.ГГГГ ДД.ММ.ГГГГ — зарплата сотрудника за период\n"
    "/salary_all ДД.ММ.ГГГГ ДД.ММ.ГГГГ — зарплата всех сотрудников\n\n"
    "<b>Команды администратора:</b>\n"
    "/add_employee — добавить сотрудника\n"
    "/remove_employee &lt;имя&gt; — удалить сотрудника\n"
    "/set_role &lt;имя&gt; &lt;consultant|online&gt; — изменить роль\n"
    "/set_plan &lt;consultant|online|имя&gt; &lt;сумма&gt; — изменить план\n"
    "/set_salary &lt;имя|consultant|online&gt; &lt;оклад_за_смену&gt; — оклад за смену (% от продаж — автоматически)\n\n"
    "Также доступно меню с кнопками — отправьте /menu."
)


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(
        "Привет! Я бот для учета продаж сотрудников магазина.\n\n"
        "Выберите действие ниже или отправьте /help, чтобы увидеть список команд.",
        reply_markup=main_menu_keyboard(),
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(HELP_TEXT, reply_markup=main_menu_keyboard())


@router.message(Command("menu"))
async def cmd_menu(message: Message) -> None:
    await message.answer("Главное меню:", reply_markup=main_menu_keyboard())


# ------------------------------------------------------------------
# Обработчики кнопок главного меню, которые не относятся к статистике
# ------------------------------------------------------------------

@router.callback_query(F.data == "menu:root")
async def cb_menu_root(callback: CallbackQuery) -> None:
    await callback.message.edit_text("Главное меню:", reply_markup=main_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data == "menu:help")
async def cb_menu_help(callback: CallbackQuery) -> None:
    await callback.message.edit_text(HELP_TEXT, reply_markup=back_to_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data == "menu:import")
async def cb_menu_import(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(ImportStates.waiting_for_text)
    await callback.message.answer(
        "Пришлите текст отчета одним сообщением.\nЧтобы отменить, отправьте /cancel."
    )
    await callback.answer()