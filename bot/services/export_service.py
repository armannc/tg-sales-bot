"""
Сервис экспорта статистики в Excel (.xlsx) с помощью pandas + openpyxl.
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from bot.services.stats_service import get_all_employee_stats

EXPORT_DIR = Path(__file__).resolve().parent.parent.parent / "exports"
EXPORT_DIR.mkdir(exist_ok=True)


async def export_stats_to_excel(
    session: AsyncSession,
    date_from: dt.date | None = None,
    date_to: dt.date | None = None,
) -> Path:
    """Строит Excel-файл со статистикой сотрудников за период и возвращает путь к файлу."""
    stats = await get_all_employee_stats(session, date_from, date_to)

    rows = []
    for s in stats:
        rows.append(
            {
                "Сотрудник": s.employee.name,
                "Роль": s.employee.role.value,
                "Смен": s.shifts,
                "Продажи": round(s.total_sales),
                "План": round(s.plan),
                "Выполнение, %": round(s.percent, 1),
                "Средняя касса": round(s.avg_kassa),
                "Бонусы": round(s.total_bonus),
            }
        )

    df = pd.DataFrame(rows)
    if not df.empty:
        df.sort_values(by="Выполнение, %", ascending=False, inplace=True)

    timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = EXPORT_DIR / f"stats_{timestamp}.xlsx"

    with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Статистика")
        worksheet = writer.sheets["Статистика"]
        for column_cells in worksheet.columns:
            max_length = max((len(str(cell.value)) for cell in column_cells if cell.value is not None), default=10)
            worksheet.column_dimensions[column_cells[0].column_letter].width = max_length + 4

    return file_path
