"""
Проактивные уведомления и сравнение с прошлым днем после импорта отчета.

Пороги вынесены в константы вверху файла - чтобы поменять правило
уведомления (например порог низкой конверсии), достаточно поправить
значение здесь, не трогая остальной код.
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import DailyReport
from bot.services.stats_service import (
    get_employee_best_sales_excluding,
    get_employee_reports_for_daily_report,
    get_previous_daily_report,
)
from bot.utils.formatting import format_money, format_percent

# Порог, ниже которого конверсия считается тревожно низкой.
LOW_CONVERSION_THRESHOLD = 30.0

# Процент выполнения общего плана смены, при достижении которого шлется
# промежуточное уведомление (кроме полного выполнения - оно всегда отдельным
# сообщением с трофеем).
HALF_PLAN_MILESTONE = 50.0


async def build_import_notifications(session: AsyncSession, daily_report: DailyReport) -> list[str]:
    """Проактивные уведомления сразу после импорта отчета:
    - общий план смены выполнен на 50%+ / выполнен полностью
    - у кого-то из сотрудников личный рекорд по кассе
    - конверсия упала ниже порога
    """
    lines: list[str] = []

    employee_reports = await get_employee_reports_for_daily_report(session, daily_report.id)

    # --- Выполнение общего плана смены ---
    team_plan = sum(er.employee.daily_plan for er in employee_reports)
    if team_plan > 0:
        team_percent = daily_report.total_revenue / team_plan * 100
        if team_percent >= 100:
            lines.append(f"🏆 План выполнен ({format_percent(team_percent)}).")
        elif team_percent >= HALF_PLAN_MILESTONE:
            lines.append(f"🔔 План выполнен на {format_percent(team_percent)}.")

    # --- Личные рекорды по кассе (не считаем первую смену сотрудника рекордом) ---
    for er in employee_reports:
        if er.sales <= 0 or er.employee.shifts_count <= 1:
            continue
        best_before = await get_employee_best_sales_excluding(session, er.employee_id, daily_report.id)
        if er.sales > best_before:
            lines.append(f"🔥 {er.employee.name} побил свой рекорд ({format_money(er.sales)}).")

    # --- Низкая конверсия ---
    if daily_report.conversion < LOW_CONVERSION_THRESHOLD:
        lines.append(f"⚠️ Конверсия упала ниже {LOW_CONVERSION_THRESHOLD:g}% ({format_percent(daily_report.conversion)}).")

    return lines


def _pct_change(today: float, yesterday: float) -> float | None:
    """Относительное изменение в процентах. None, если вчера было 0 (деление на 0)."""
    if yesterday == 0:
        return None
    return (today - yesterday) / yesterday * 100


def _format_change(value: float | None) -> str:
    if value is None:
        return ""
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.0f}%"


async def build_previous_day_comparison(session: AsyncSession, daily_report: DailyReport) -> str | None:
    """Сравнение выручки и конверсии с последним предыдущим отчетом.
    Возвращает None, если сравнивать не с чем (это первый отчет в базе)."""
    previous = await get_previous_daily_report(session, daily_report.report_date)
    if previous is None:
        return None

    revenue_change = _pct_change(daily_report.total_revenue, previous.total_revenue)
    conversion_change = daily_report.conversion - previous.conversion

    lines = [
        "📊 <b>Сравнение с прошлым днем</b>",
        "",
        "Выручка",
        f"Сегодня: {format_money(daily_report.total_revenue)}",
        f"Прошлый раз: {format_money(previous.total_revenue)}",
    ]
    change_str = _format_change(revenue_change)
    if change_str:
        lines.append(change_str)

    lines += [
        "",
        "Конверсия",
        f"Сегодня: {format_percent(daily_report.conversion)}",
        f"Прошлый раз: {format_percent(previous.conversion)}",
        f"{'+' if conversion_change > 0 else ''}{conversion_change:.0f}%",
    ]

    return "\n".join(lines)