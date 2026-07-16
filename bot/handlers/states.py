"""
Состояния конечных автоматов (FSM) для диалогов бота.
"""
from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class ImportStates(StatesGroup):
    waiting_for_text = State()


class AddEmployeeStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_role = State()
    waiting_for_plan = State()
