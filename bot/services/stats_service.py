"""
Сервис расчета статистики: агрегация продаж/планов по сотрудникам за период.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import DailyReport, Employee, EmployeeReport


@dataclass(slots=True)
class EmployeeStats:
    employee: Employee
    total_sales: float
    total_bonus: float
    shifts: int
    plan: float
    percent: float
    avg_kassa: float


def _percent(sales: float, plan: float) -> float:
    return (sales / plan * 100) if plan > 0 else 0.0


async def get_period_bounds(period: str) -> tuple[dt.date, dt.date]:
    """Возвращает (начало, конец) периода: 'day' | 'month' | 'year'."""
    today = dt.date.today()
    if period == "day":
        return today, today
    if period == "month":
        start = today.replace(day=1)
        return start, today
    if period == "year":
        start = today.replace(month=1, day=1)
        return start, today
    raise ValueError(f"Неизвестный период: {period}")


async def get_employee_stats(
    session: AsyncSession,
    employee: Employee,
    date_from: dt.date | None = None,
    date_to: dt.date | None = None,
) -> EmployeeStats:
    query = (
        select(
            func.coalesce(func.sum(EmployeeReport.sales), 0.0),
            func.coalesce(func.sum(EmployeeReport.bonus), 0.0),
            func.coalesce(func.sum(EmployeeReport.plan), 0.0),
            func.count(EmployeeReport.id),
        )
        .join(DailyReport, EmployeeReport.daily_report_id == DailyReport.id)
        .where(EmployeeReport.employee_id == employee.id)
    )
    if date_from is not None:
        query = query.where(DailyReport.report_date >= date_from)
    if date_to is not None:
        query = query.where(DailyReport.report_date <= date_to)

    result = await session.execute(query)
    total_sales, total_bonus, plan, shifts = result.one()
    percent = _percent(total_sales, plan)
    avg_kassa = (total_sales / shifts) if shifts > 0 else 0.0

    return EmployeeStats(
        employee=employee,
        total_sales=total_sales,
        total_bonus=total_bonus,
        shifts=shifts,
        plan=plan,
        percent=percent,
        avg_kassa=avg_kassa,
    )


async def get_all_employee_stats(
    session: AsyncSession,
    date_from: dt.date | None = None,
    date_to: dt.date | None = None,
    only_active: bool = True,
) -> list[EmployeeStats]:
    emp_query = select(Employee)
    if only_active:
        emp_query = emp_query.where(Employee.is_active.is_(True))
    employees = (await session.execute(emp_query)).scalars().all()

    stats: list[EmployeeStats] = []
    for employee in employees:
        emp_stats = await get_employee_stats(session, employee, date_from, date_to)
        if emp_stats.shifts > 0:
            stats.append(emp_stats)
    return stats


async def get_top_employees(
    session: AsyncSession,
    date_from: dt.date | None = None,
    date_to: dt.date | None = None,
    limit: int = 10,
) -> list[EmployeeStats]:
    all_stats = await get_all_employee_stats(session, date_from, date_to)
    all_stats.sort(key=lambda s: s.percent, reverse=True)
    return all_stats[:limit]


async def get_daily_report_by_date(session: AsyncSession, date_: dt.date) -> DailyReport | None:
    result = await session.execute(select(DailyReport).where(DailyReport.report_date == date_))
    return result.scalar_one_or_none()


async def get_daily_reports_between(
    session: AsyncSession, date_from: dt.date, date_to: dt.date
) -> list[DailyReport]:
    result = await session.execute(
        select(DailyReport)
        .where(DailyReport.report_date >= date_from, DailyReport.report_date <= date_to)
        .order_by(DailyReport.report_date)
    )
    return list(result.scalars().all())
