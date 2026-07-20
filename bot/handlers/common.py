"""
Базовые команды: /start, /help, а также обработка главного меню (inline-кнопки).
"""
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandStart, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.database.engine import async_session_factory
from bot.handlers.states import ImportStates
from bot.services.invite_service import use_invite_code, InviteError
from bot.utils.access import is_admin
from bot.utils.keyboards import back_to_menu_keyboard, main_menu_keyboard, employee_menu_keyboard

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

EMPLOYEE_HELP_TEXT = (
    "🤖 <b>Бот учета продаж</b>\n\n"
    "<b>Доступные команды:</b>\n"
    "/me — краткая информация о себе\n"
    "/my_stats — моя статистика\n"
    "/my_salary ДД.ММ.ГГГГ ДД.ММ.ГГГГ — моя зарплата за период\n\n"
    "Также доступно меню с кнопками — отправьте /menu."
)


def _menu_for(user_id: int):
    return main_menu_keyboard() if is_admin(user_id) else employee_menu_keyboard()


def _help_for(user_id: int) -> str:
    return HELP_TEXT if is_admin(user_id) else EMPLOYEE_HELP_TEXT


@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject) -> None:
    code = command.args  # значение после ?start=<code>

    if code:
        async with async_session_factory() as session:
            try:
                employee = await use_invite_code(session, code, message.from_user.id)
                await message.answer(f"Готово! Вы привязаны как <b>{employee.name}</b>.")
            except InviteError as e:
                await message.answer(f"⚠️ {e}")

    await message.answer(
        "Привет! Я бот для учета продаж сотрудников магазина.\n\n"
        "Выберите действие ниже или отправьте /help, чтобы увидеть список команд.",
        reply_markup=_menu_for(message.from_user.id),
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(_help_for(message.from_user.id), reply_markup=_menu_for(message.from_user.id))


@router.message(Command("menu"))
async def cmd_menu(message: Message) -> None:
    await message.answer("Главное меню:", reply_markup=_menu_for(message.from_user.id))


# ------------------------------------------------------------------
# Обработчики кнопок главного меню, которые не относятся к статистике
# ------------------------------------------------------------------

@router.callback_query(F.data == "menu:root")
async def cb_menu_root(callback: CallbackQuery) -> None:
    await callback.message.edit_text("Главное меню:", reply_markup=_menu_for(callback.from_user.id))
    await callback.answer()


@router.callback_query(F.data == "menu:help")
async def cb_menu_help(callback: CallbackQuery) -> None:
    await callback.message.edit_text(_help_for(callback.from_user.id), reply_markup=back_to_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data == "menu:import")
async def cb_menu_import(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(ImportStates.waiting_for_text)
    await callback.message.answer(
        "Пришлите текст отчета одним сообщением.\nЧтобы отменить, отправьте /cancel."
    )
    await callback.answer()