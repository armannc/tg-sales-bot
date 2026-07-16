"""
Утилиты форматирования чисел и текста для сообщений бота.
"""
from __future__ import annotations

import datetime as dt


def format_money(value: float, currency: str = "₸") -> str:
    """Форматирует число как '798 900 ₸'."""
    rounded = int(round(value))
    formatted = f"{rounded:,}".replace(",", " ")
    return f"{formatted} {currency}"


def format_number(value: float) -> str:
    """Форматирует число с разделителем разрядов без валюты."""
    rounded = int(round(value))
    return f"{rounded:,}".replace(",", " ")


def format_percent(value: float) -> str:
    return f"{value:.0f}%"


def format_date(value: dt.date) -> str:
    return value.strftime("%d.%m.%Y")


def medal_for_place(place: int) -> str:
    medals = {1: "🥇", 2: "🥈", 3: "🥉"}
    return medals.get(place, f"{place}.")
