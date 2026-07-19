"""
ORM-модели базы данных.
"""
from __future__ import annotations

import datetime as dt
import enum

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class RoleEnum(str, enum.Enum):
    consultant = "consultant"
    online = "online"


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    role: Mapped[RoleEnum] = mapped_column(Enum(RoleEnum), nullable=False, default=RoleEnum.consultant)
    daily_plan: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    base_salary: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    shifts_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now())

    reports: Mapped[list["EmployeeReport"]] = relationship(
        back_populates="employee", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<Employee id={self.id} name={self.name!r} role={self.role.value}>"


class DailyReport(Base):
    """Общий (сводный) отчет за одну смену/день."""

    __tablename__ = "daily_reports"
    __table_args__ = (UniqueConstraint("report_date", name="uq_daily_reports_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    report_date: Mapped[dt.date] = mapped_column(Date, nullable=False)

    checks_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cashless: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    cash: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    revenue_fact: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    avg_check: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    conversion: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    online_sales: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_revenue: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_clients: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    items_sold: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    shift_open_time: Mapped[str | None] = mapped_column(String(16), nullable=True)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now())

    employee_reports: Mapped[list["EmployeeReport"]] = relationship(
        back_populates="daily_report", cascade="all, delete-orphan"
    )


class EmployeeReport(Base):
    """Результат конкретного сотрудника в рамках одного дневного отчета."""

    __tablename__ = "employee_reports"
    __table_args__ = (UniqueConstraint("daily_report_id", "employee_id", name="uq_report_employee"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    daily_report_id: Mapped[int] = mapped_column(ForeignKey("daily_reports.id", ondelete="CASCADE"))
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id", ondelete="CASCADE"))

    sales: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    bonus: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    plan: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    percent: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    is_online_source: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now())

    daily_report: Mapped[DailyReport] = relationship(back_populates="employee_reports")
    employee: Mapped[Employee] = relationship(back_populates="reports")