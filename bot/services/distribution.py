"""
Логика распределения суммы онлайн-продаж между онлайн-менеджерами.

Вынесена в отдельную функцию, чтобы алгоритм распределения можно было
легко поменять в будущем (например, распределять пропорционально КПИ),
не трогая остальной код сервиса импорта отчетов.
"""
from __future__ import annotations


def distribute_online_sales(online_managers: list[str], online_sales: float) -> dict[str, float]:
    """Равномерно делит сумму онлайн-продаж между онлайн-менеджерами.

    Args:
        online_managers: имена сотрудников, отсутствующих в блоке "Касса".
        online_sales: сумма из строки "Онлайн продажи".

    Returns:
        Словарь {имя_сотрудника: сумма}. Пустой словарь, если менеджеров нет.
    """
    if not online_managers:
        return {}

    share = online_sales / len(online_managers)
    return {name: share for name in online_managers}
