"""
Сервис управления сотрудниками (используется админ-командами).
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import Employee, RoleEnum


class EmployeeServiceError(Exception):
    """Ошибка операции над сотрудником."""


async def get_employee_by_name(session: AsyncSession, name: str) -> Employee | None:
    result = await session.execute(select(Employee).where(Employee.name.ilike(name)))
    return result.scalar_one_or_none()


async def add_employee(
    session: AsyncSession, name: str, role: RoleEnum, daily_plan: float
) -> Employee:
    existing = await get_employee_by_name(session, name)
    if existing is not None:
        raise EmployeeServiceError(f"Сотрудник {name!r} уже существует.")

    employee = Employee(name=name, role=role, daily_plan=daily_plan, is_active=True)
    session.add(employee)
    await session.commit()
    return employee


async def remove_employee(session: AsyncSession, name: str) -> None:
    employee = await get_employee_by_name(session, name)
    if employee is None:
        raise EmployeeServiceError(f"Сотрудник {name!r} не найден.")
    await session.delete(employee)
    await session.commit()


async def set_employee_role(session: AsyncSession, name: str, role: RoleEnum) -> Employee:
    employee = await get_employee_by_name(session, name)
    if employee is None:
        raise EmployeeServiceError(f"Сотрудник {name!r} не найден.")
    employee.role = role
    await session.commit()
    return employee


async def set_plan_for_role(session: AsyncSession, role: RoleEnum, daily_plan: float) -> int:
    """Устанавливает дневной план для всех сотрудников с указанной ролью.

    Returns:
        Количество обновленных сотрудников.
    """
    result = await session.execute(select(Employee).where(Employee.role == role))
    employees = result.scalars().all()
    for employee in employees:
        employee.daily_plan = daily_plan
    await session.commit()
    return len(employees)


async def set_plan_for_employee(session: AsyncSession, name: str, daily_plan: float) -> Employee:
    employee = await get_employee_by_name(session, name)
    if employee is None:
        raise EmployeeServiceError(f"Сотрудник {name!r} не найден.")
    employee.daily_plan = daily_plan
    await session.commit()
    return employee


async def set_base_salary_for_role(
    session: AsyncSession, role: RoleEnum, base_salary: float
) -> int:
    """Устанавливает оклад за смену для всех сотрудников с указанной ролью.

    Returns:
        Количество обновленных сотрудников.
    """
    result = await session.execute(select(Employee).where(Employee.role == role))
    employees = result.scalars().all()
    for employee in employees:
        employee.base_salary = base_salary
    await session.commit()
    return len(employees)


async def set_base_salary_for_employee(
    session: AsyncSession, name: str, base_salary: float
) -> Employee:
    employee = await get_employee_by_name(session, name)
    if employee is None:
        raise EmployeeServiceError(f"Сотрудник {name!r} не найден.")
    employee.base_salary = base_salary
    await session.commit()
    return employee


async def list_employees(session: AsyncSession, only_active: bool = True) -> list[Employee]:
    query = select(Employee)
    if only_active:
        query = query.where(Employee.is_active.is_(True))
    result = await session.execute(query.order_by(Employee.name))
    return list(result.scalars().all())