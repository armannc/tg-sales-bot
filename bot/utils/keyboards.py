"""
Inline-клавиатуры бота.
"""
from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_menu_keyboard() -> InlineKeyboardMarkup:
    """Главное меню с быстрыми действиями."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📊 Общий рейтинг", callback_data="menu:stats"),
        InlineKeyboardButton(text="🏆 Топ-5", callback_data="menu:top"),
    )
    builder.row(
        InlineKeyboardButton(text="📅 За сегодня", callback_data="menu:day"),
        InlineKeyboardButton(text="🗓 За месяц", callback_data="menu:month"),
    )
    builder.row(
        InlineKeyboardButton(text="📈 За год", callback_data="menu:year"),
        InlineKeyboardButton(text="📥 Excel-отчет", callback_data="menu:export"),
    )
    builder.row(
        InlineKeyboardButton(text="📝 Импорт отчета", callback_data="menu:import"),
        InlineKeyboardButton(text="💰 Зарплата", callback_data="menu:salary"),
    )
    builder.row(
        InlineKeyboardButton(text="❓ Помощь", callback_data="menu:help"),
    )
    return builder.as_markup()


def back_to_menu_keyboard() -> InlineKeyboardMarkup:
    """Кнопка возврата в главное меню (под результатом статистики)."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="⬅️ В меню", callback_data="menu:root"))
    return builder.as_markup()