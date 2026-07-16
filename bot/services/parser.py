"""
Парсер текстовых отчетов, присылаемых администратором магазина.

Пример входного текста см. в README.md.
"""
from __future__ import annotations

import datetime as dt
import logging
import re
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


class ReportParseError(Exception):
    """Ошибка разбора текста отчета."""


@dataclass(slots=True)
class ParsedReport:
    report_date: dt.date
    checks_count: int
    cashless: float
    cash: float
    revenue_fact: float
    avg_check: float
    conversion: float
    online_sales: float
    total_revenue: float
    total_clients: int
    items_sold: int
    shift_open_time: str | None
    shift_employees: list[str] = field(default_factory=list)
    kassa: dict[str, float] = field(default_factory=dict)
    bonuses: dict[str, float] = field(default_factory=dict)
    raw_text: str = ""


def _to_number(raw: str) -> float:
    """Преобразует '798.900' или '13.741' или '51' в float, где точка - разделитель тысяч."""
    cleaned = raw.strip().replace(" ", "")
    # Уберем возможный знак процента/валюты
    cleaned = cleaned.replace("%", "").replace("₸", "")
    # В отчетах точка используется как разделитель тысяч (798.900 = 798900)
    cleaned = cleaned.replace(".", "").replace(",", "")
    if not cleaned:
        raise ReportParseError(f"Не удалось распознать число: {raw!r}")
    return float(cleaned)


def _search_number(pattern: str, text: str, required: bool = True) -> float | None:
    match = re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
    if not match:
        if required:
            raise ReportParseError(f"Не найдено поле по шаблону: {pattern}")
        return None
    return _to_number(match.group(1))


def _parse_date(raw: str) -> dt.date:
    raw = raw.strip()
    parts = raw.split(".")
    today = dt.date.today()
    if len(parts) == 2:
        day, month = int(parts[0]), int(parts[1])
        year = today.year
        candidate = dt.date(year, month, day)
        # Если дата "из будущего" больше, чем на 1 день - скорее всего это прошлый год
        if candidate > today + dt.timedelta(days=1):
            candidate = dt.date(year - 1, month, day)
        return candidate
    if len(parts) == 3:
        day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
        if year < 100:
            year += 2000
        return dt.date(year, month, day)
    raise ReportParseError(f"Не удалось распознать дату: {raw!r}")


def _extract_block(text: str, keyword: str) -> list[str]:
    """Возвращает список непустых строк-элементов блока с заголовком `keyword`.

    Поддерживает два формата:
      Смена: Камила, Арман, Алина          (содержимое сразу после заголовка)
      Смена:
      Камила, Арман, Алина                 (содержимое на следующих строках)
    """
    lines = text.splitlines()
    # Заголовок с содержимым на той же строке: "Ключевое слово: содержимое"
    inline_re = re.compile(rf"^{keyword}\s*:\s*(.+)$", flags=re.IGNORECASE)
    # Заголовок без содержимого на той же строке: "Ключевое слово" или "Ключевое слово:"
    header_only_re = re.compile(rf"^{keyword}\s*:?\s*$", flags=re.IGNORECASE)

    known_headers = ("бонус", "смена открыта", "смена", "касса")
    collected: list[str] = []
    collecting = False

    for line in lines:
        stripped = line.strip()
        if not collecting:
            inline_match = inline_re.match(stripped)
            if inline_match:
                collecting = True
                collected.append(inline_match.group(1).strip())
                continue
            if header_only_re.match(stripped):
                collecting = True
            continue
        if not stripped:
            if collected:
                break
            continue
        lowered = stripped.lower().rstrip(":")
        if any(lowered.startswith(h) for h in known_headers):
            break
        collected.append(stripped)
    return collected


_NAME_AMOUNT_RE = re.compile(r"^(?P<name>[^\d\-–:]+?)\s*[-–:]?\s*(?P<amount>[\d][\d.,\s]*)\s*$")


def _parse_name_amount_lines(lines: list[str]) -> dict[str, float]:
    result: dict[str, float] = {}
    for line in lines:
        match = _NAME_AMOUNT_RE.match(line)
        if not match:
            logger.warning("Не удалось разобрать строку сотрудника: %r", line)
            continue
        name = match.group("name").strip(" ,.-")
        amount = _to_number(match.group("amount"))
        result[name] = amount
    return result


def _parse_names(lines: list[str]) -> list[str]:
    """Разбирает имена сотрудников: одной строкой через запятую или по одному в строке."""
    joined = ", ".join(lines)
    names = [part.strip(" ,.-") for part in joined.split(",")]
    return [name for name in names if name]


def parse_report(text: str) -> ParsedReport:
    """Разбирает текст отчета администратора и возвращает структурированные данные."""
    if not text or not text.strip():
        raise ReportParseError("Пустой текст отчета.")

    date_match = re.search(r"Дата\s*:?\s*([0-9.]+)", text, flags=re.IGNORECASE)
    if not date_match:
        raise ReportParseError("Не найдена строка 'Дата'.")
    report_date = _parse_date(date_match.group(1))

    checks_count = int(_search_number(r"Количество чеков\s*-?\s*([\d.,]+)", text))
    cashless = _search_number(r"Безнал\s*-?\s*([\d.,]+)", text)
    cash = _search_number(r"Наличными\s*-?\s*([\d.,]+)", text)
    revenue_fact = _search_number(r"План\s*/\s*Факт\s*-?\s*([\d.,]+)", text)
    avg_check = _search_number(r"Средний чек\s*-?\s*([\d.,]+)", text)
    conversion = _search_number(r"Конверсия\s*-?\s*([\d.,]+)\s*%", text)
    online_sales = _search_number(r"Онлайн продажи\s*:?\s*([\d.,]+)", text)
    total_revenue = _search_number(r"(?<!Клиентов )[Вв]ообщем\s*:?\s*([\d.,]+)", text)
    total_clients = int(_search_number(r"Клиентов вообщем\s*:?\s*([\d.,]+)", text))
    items_sold = int(_search_number(r"Товара продано\s*:?\s*([\d.,]+)", text))

    shift_open_match = re.search(r"Смена открыта\s*:?\s*(\d{1,2}:\d{2})", text, flags=re.IGNORECASE)
    shift_open_time = shift_open_match.group(1) if shift_open_match else None

    bonus_lines = _extract_block(text, "Бонус")
    bonuses = _parse_name_amount_lines(bonus_lines)

    shift_lines = _extract_block(text, "Смена")
    shift_employees = _parse_names(shift_lines)

    kassa_lines = _extract_block(text, "Касса")
    kassa = _parse_name_amount_lines(kassa_lines)

    if not shift_employees:
        raise ReportParseError("Не найден блок 'Смена' со списком сотрудников.")

    return ParsedReport(
        report_date=report_date,
        checks_count=checks_count,
        cashless=cashless,
        cash=cash,
        revenue_fact=revenue_fact,
        avg_check=avg_check,
        conversion=conversion,
        online_sales=online_sales,
        total_revenue=total_revenue,
        total_clients=total_clients,
        items_sold=items_sold,
        shift_open_time=shift_open_time,
        shift_employees=shift_employees,
        kassa=kassa,
        bonuses=bonuses,
        raw_text=text,
    )
