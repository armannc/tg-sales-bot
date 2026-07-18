"""
Разбор дат, введенных пользователем в формате ДД.ММ или ДД.ММ.ГГГГ.
"""
from __future__ import annotations

import datetime as dt


class DateParseError(Exception):
    """Не удалось разобрать дату из пользовательского ввода."""


def parse_date_arg(raw: str) -> dt.date:
    """Разбирает '13.07' (текущий/прошлый год определяется автоматически) или '13.07.2026'."""
    raw = raw.strip()
    parts = raw.split(".")
    today = dt.date.today()

    try:
        if len(parts) == 2:
            day, month = int(parts[0]), int(parts[1])
            year = today.year
            candidate = dt.date(year, month, day)
            if candidate > today + dt.timedelta(days=1):
                candidate = dt.date(year - 1, month, day)
            return candidate
        if len(parts) == 3:
            day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
            if year < 100:
                year += 2000
            return dt.date(year, month, day)
    except ValueError as exc:
        raise DateParseError(f"Некорректная дата: {raw!r}") from exc

    raise DateParseError(f"Не удалось распознать дату: {raw!r}. Используйте формат ДД.ММ.ГГГГ")