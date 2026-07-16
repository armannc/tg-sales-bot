"""
Сервис импорта отчетов: связывает парсер, алгоритм распределения онлайн-продаж
и запись данных в базу.
"""
from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import config
from bot.database.models import DailyReport, Employee, EmployeeReport, RoleEnum
from bot.services.distribution import distribute_online_sales
from bot.services.parser import ParsedReport, ReportParseError, parse_report

logger = logging.getLogger(__name__)


class ReportImportError(Exception):
    """Ошибка на уровне импорта отчета (не связанная напрямую с парсингом)."""


async def _get_or_create_employee(
    session: AsyncSession, name: str, default_role: RoleEnum
) -> Employee:
    result = await session.execute(select(Employee).where(Employee.name == name))
    employee = result.scalar_one_or_none()
    if employee is not None:
        return employee

    daily_plan = (
        config.default_plans.online
        if default_role == RoleEnum.online
        else config.default_plans.consultant
    )
    employee = Employee(name=name, role=default_role, daily_plan=daily_plan, is_active=True)
    session.add(employee)
    await session.flush()
    logger.info("Создан новый сотрудник %r с ролью %s", name, default_role.value)
    return employee


async def _delete_existing_report_for_date(session: AsyncSession, parsed: ParsedReport) -> None:
    result = await session.execute(
        select(DailyReport).where(DailyReport.report_date == parsed.report_date)
    )
    existing = result.scalar_one_or_none()
    if existing is None:
        return

    # Откатываем счетчик смен для сотрудников этого отчета перед удалением
    for emp_report in existing.employee_reports:
        employee = await session.get(Employee, emp_report.employee_id)
        if employee is not None and employee.shifts_count > 0:
            employee.shifts_count -= 1

    await session.delete(existing)
    await session.flush()
    logger.info("Заменен существующий отчет за %s", parsed.report_date)


async def import_report_text(session: AsyncSession, text: str) -> DailyReport:
    """Полный цикл импорта: парсинг текста + запись в БД.

    Raises:
        ReportParseError: если текст отчета не удалось разобрать.
        ReportImportError: если данные разобраны, но не согласованы (например,
            "Касса" содержит сотрудника не из смены).
    """
    try:
        parsed = parse_report(text)
    except ReportParseError:
        raise

    kassa_names = set(parsed.kassa.keys())
    shift_names = set(parsed.shift_employees)

    unknown_in_kassa = kassa_names - shift_names
    if unknown_in_kassa:
        raise ReportImportError(
            "В блоке 'Касса' указаны сотрудники, отсутствующие в 'Смена': "
            + ", ".join(sorted(unknown_in_kassa))
        )

    online_managers = [name for name in parsed.shift_employees if name not in kassa_names]
    online_shares = distribute_online_sales(online_managers, parsed.online_sales)

    sales_by_employee: dict[str, float] = dict(parsed.kassa)
    sales_by_employee.update(online_shares)

    # Удаляем предыдущий отчет за эту дату, если он есть (повторный импорт = перезапись)
    await _delete_existing_report_for_date(session, parsed)

    daily_report = DailyReport(
        report_date=parsed.report_date,
        checks_count=parsed.checks_count,
        cashless=parsed.cashless,
        cash=parsed.cash,
        revenue_fact=parsed.revenue_fact,
        avg_check=parsed.avg_check,
        conversion=parsed.conversion,
        online_sales=parsed.online_sales,
        total_revenue=parsed.total_revenue,
        total_clients=parsed.total_clients,
        items_sold=parsed.items_sold,
        shift_open_time=parsed.shift_open_time,
        raw_text=parsed.raw_text,
    )
    session.add(daily_report)
    await session.flush()

    for name in parsed.shift_employees:
        is_online_manager = name in online_managers
        default_role = RoleEnum.online if is_online_manager else RoleEnum.consultant
        employee = await _get_or_create_employee(session, name, default_role)

        employee.shifts_count += 1
        sales = sales_by_employee.get(name, 0.0)
        bonus = parsed.bonuses.get(name, 0.0)
        plan = employee.daily_plan
        percent = (sales / plan * 100) if plan > 0 else 0.0

        employee_report = EmployeeReport(
            daily_report_id=daily_report.id,
            employee_id=employee.id,
            sales=sales,
            bonus=bonus,
            plan=plan,
            percent=percent,
            is_online_source=is_online_manager,
        )
        session.add(employee_report)

    await session.commit()
    logger.info("Отчет за %s успешно импортирован", parsed.report_date)
    return daily_report
