"""
Сервис расчета статистики: агрегация продаж/планов по сотрудникам за период.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import DailyReport, Employee, EmployeeReport
from bot.services.salary_tiers import get_sales_percent_by_plan


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


@dataclass(slots=True)
class SalaryResult:
    employee: Employee
    date_from: dt.date
    date_to: dt.date
    total_sales: float
    shifts: int
    shift_rate: float
    base_salary_total: float
    plan_percent: float
    sales_percent: float
    sales_bonus: float
    total_salary: float


async def calculate_salary(
    session: AsyncSession,
    employee: Employee,
    date_from: dt.date,
    date_to: dt.date,
) -> SalaryResult:
    """Считает зарплату сотрудника за период: оклад за смену × смены + % от продаж.

    Оклад начисляется за каждую отработанную смену (как и план), а не
    фиксированной суммой за весь период. Процент от продаж определяется
    автоматически по шкале выполнения плана (см.
    bot/services/salary_tiers.py). Премии/бонусы из отчетов (строка
    "Бонус") в расчет не входят — это отдельная выплата.
    """
    stats = await get_employee_stats(session, employee, date_from, date_to)
    sales_percent = get_sales_percent_by_plan(stats.percent)
    sales_bonus = stats.total_sales * sales_percent / 100
    base_salary_total = employee.base_salary * stats.shifts
    total_salary = base_salary_total + sales_bonus

    return SalaryResult(
        employee=employee,
        date_from=date_from,
        date_to=date_to,
        total_sales=stats.total_sales,
        shifts=stats.shifts,
        shift_rate=employee.base_salary,
        base_salary_total=base_salary_total,
        plan_percent=stats.percent,
        sales_percent=sales_percent,
        sales_bonus=sales_bonus,
        total_salary=total_salary,
    )


async def calculate_salary_for_all(
    session: AsyncSession,
    date_from: dt.date,
    date_to: dt.date,
    only_active: bool = True,
) -> list[SalaryResult]:
    from bot.services.employee_service import list_employees

    employees = await list_employees(session, only_active=only_active)
    results: list[SalaryResult] = []
    for employee in employees:
        result = await calculate_salary(session, employee, date_from, date_to)
        if result.shifts > 0:
            results.append(result)
    return results
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