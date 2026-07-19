"""
Inline- и reply-клавиатуры бота.
"""
from __future__ import annotations

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder


def main_menu_keyboard() -> InlineKeyboardMarkup:
    """Главное меню с быстрыми действиями (inline-кнопки под сообщением)."""
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


MENU_BUTTON_TEXT = "📋 Меню"


def persistent_menu_keyboard() -> ReplyKeyboardMarkup:
    """Постоянная кнопка меню рядом с полем ввода текста.

    В отличие от inline-клавиатуры (main_menu_keyboard), эта клавиатура
    не привязана к конкретному сообщению и остается видимой у пользователя
    всегда, пока он ее явно не скроет. Нажатие на кнопку присылает боту
    обычное текстовое сообщение с текстом MENU_BUTTON_TEXT, которое
    обрабатывается как любое другое сообщение (см. handle_menu_button
    в bot/handlers/common.py).
    """
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text=MENU_BUTTON_TEXT))
    return builder.as_markup(resize_keyboard=True, is_persistent=True)