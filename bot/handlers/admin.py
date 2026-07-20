"""
Админ-команды: /add_employee, /remove_employee, /set_role, /set_plan.

/add_employee поддерживает два варианта использования:
  1) Короткая форма одной строкой:
     /add_employee Иван consultant 483000
  2) Пошаговый диалог (FSM), если аргументы не переданы:
     /add_employee -> бот спросит имя -> роль -> план
"""
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.database.engine import async_session_factory
from bot.database.models import RoleEnum
from bot.handlers.states import AddEmployeeStates
from bot.services.employee_service import (
    EmployeeServiceError,
    add_employee,
    get_employee_by_name,
    remove_employee,
    set_employee_role,
    set_plan_for_employee,
    set_plan_for_role,
    set_salary_for_employee,
    set_salary_for_role,
)
from bot.services.invite_service import create_invite_code
from bot.utils.access import is_admin
from bot.utils.formatting import format_money

router = Router(name="admin")


def _parse_role(raw: str) -> RoleEnum:
    raw = raw.strip().lower()
    try:
        return RoleEnum(raw)
    except ValueError as exc:
        raise EmployeeServiceError(
            f"Неизвестная роль {raw!r}. Допустимые значения: consultant, online."
        ) from exc


async def _require_admin(message: Message) -> bool:
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Эта команда доступна только администратору.")
        return False
    return True


@router.message(Command("add_employee"))
async def cmd_add_employee(message: Message, command: CommandObject, state: FSMContext) -> None:
    if not await _require_admin(message):
        return

    if command.args:
        parts = command.args.split()
        if len(parts) != 3:
            await message.answer(
                "Использование: /add_employee Имя consultant|online план\n"
                "Например: /add_employee Иван consultant 483000"
            )
            return
        name, role_raw, plan_raw = parts
        try:
            role = _parse_role(role_raw)
            plan = float(plan_raw)
        except (EmployeeServiceError, ValueError) as exc:
            await message.answer(f"❌ {exc}")
            return

        async with async_session_factory() as session:
            try:
                await add_employee(session, name, role, plan)
            except EmployeeServiceError as exc:
                await message.answer(f"❌ {exc}")
                return

        await message.answer(f"✅ Сотрудник {name} добавлен (роль: {role.value}, план: {format_money(plan)}).")
        return

    await state.set_state(AddEmployeeStates.waiting_for_name)
    await message.answer("Введите имя нового сотрудника:")


@router.message(AddEmployeeStates.waiting_for_name, F.text)
async def add_employee_name(message: Message, state: FSMContext) -> None:
    await state.update_data(name=message.text.strip())
    await state.set_state(AddEmployeeStates.waiting_for_role)
    await message.answer("Введите роль сотрудника: consultant или online")


@router.message(AddEmployeeStates.waiting_for_role, F.text)
async def add_employee_role(message: Message, state: FSMContext) -> None:
    try:
        role = _parse_role(message.text)
    except EmployeeServiceError as exc:
        await message.answer(f"❌ {exc}\nПопробуйте еще раз: consultant или online")
        return

    await state.update_data(role=role.value)
    await state.set_state(AddEmployeeStates.waiting_for_plan)
    await message.answer("Введите дневной план (число, например 483000):")


@router.message(AddEmployeeStates.waiting_for_plan, F.text)
async def add_employee_plan(message: Message, state: FSMContext) -> None:
    try:
        plan = float(message.text.strip().replace(" ", "").replace(",", ""))
    except ValueError:
        await message.answer("❌ План должен быть числом. Попробуйте еще раз:")
        return

    data = await state.get_data()
    name = data["name"]
    role = RoleEnum(data["role"])
    await state.clear()

    async with async_session_factory() as session:
        try:
            await add_employee(session, name, role, plan)
        except EmployeeServiceError as exc:
            await message.answer(f"❌ {exc}")
            return

    await message.answer(f"✅ Сотрудник {name} добавлен (роль: {role.value}, план: {format_money(plan)}).")


@router.message(Command("remove_employee"))
async def cmd_remove_employee(message: Message, command: CommandObject) -> None:
    if not await _require_admin(message):
        return

    if not command.args:
        await message.answer("Использование: /remove_employee Имя")
        return

    name = command.args.strip()
    async with async_session_factory() as session:
        try:
            await remove_employee(session, name)
        except EmployeeServiceError as exc:
            await message.answer(f"❌ {exc}")
            return

    await message.answer(f"🗑 Сотрудник {name} удален.")


@router.message(Command("set_role"))
async def cmd_set_role(message: Message, command: CommandObject) -> None:
    if not await _require_admin(message):
        return

    if not command.args or len(command.args.split()) != 2:
        await message.answer("Использование: /set_role Имя consultant|online")
        return

    name, role_raw = command.args.split()
    try:
        role = _parse_role(role_raw)
    except EmployeeServiceError as exc:
        await message.answer(f"❌ {exc}")
        return

    async with async_session_factory() as session:
        try:
            await set_employee_role(session, name, role)
        except EmployeeServiceError as exc:
            await message.answer(f"❌ {exc}")
            return

    await message.answer(f"✅ Роль сотрудника {name} изменена на {role.value}.")


@router.message(Command("set_plan"))
async def cmd_set_plan(message: Message, command: CommandObject) -> None:
    if not await _require_admin(message):
        return

    if not command.args or len(command.args.split()) != 2:
        await message.answer(
            "Использование:\n"
            "/set_plan consultant 483000  — план для всей роли\n"
            "/set_plan online 250000  — план для всей роли\n"
            "/set_plan Иван 500000  — план для конкретного сотрудника"
        )
        return

    target, plan_raw = command.args.split()
    try:
        plan = float(plan_raw)
    except ValueError:
        await message.answer("❌ План должен быть числом.")
        return

    async with async_session_factory() as session:
        if target.lower() in (RoleEnum.consultant.value, RoleEnum.online.value):
            role = RoleEnum(target.lower())
            updated_count = await set_plan_for_role(session, role, plan)
            await message.answer(
                f"✅ План для роли {role.value} установлен: {format_money(plan)} "
                f"(обновлено сотрудников: {updated_count})."
            )
            return

        try:
            await set_plan_for_employee(session, target, plan)
        except EmployeeServiceError as exc:
            await message.answer(f"❌ {exc}")
            return

    await message.answer(f"✅ План сотрудника {target} установлен: {format_money(plan)}.")


@router.message(Command("set_salary"))
async def cmd_set_salary(message: Message, command: CommandObject) -> None:
    if not await _require_admin(message):
        return

    if not command.args or len(command.args.split()) != 2:
        await message.answer(
            "Использование:\n"
            "/set_salary Имя оклад_за_смену — для конкретного сотрудника\n"
            "/set_salary consultant оклад_за_смену — для всей роли\n"
            "/set_salary online оклад_за_смену — для всей роли\n\n"
            "Например: /set_salary Алина 6666\n"
            "(6666 тг начисляется за каждую отработанную смену)\n\n"
            "Процент от продаж задавать не нужно — он считается автоматически "
            "по проценту выполнения плана за период:\n"
            "≤80% плана → 1%, 81-90% → 2%, 91-109% → 3%, ≥110% → 4%."
        )
        return

    target, salary_raw = command.args.split()
    try:
        base_salary = float(salary_raw)
    except ValueError:
        await message.answer("❌ Оклад должен быть числом.")
        return

    async with async_session_factory() as session:
        if target.lower() in (RoleEnum.consultant.value, RoleEnum.online.value):
            role = RoleEnum(target.lower())
            updated_count = await set_salary_for_role(session, role, base_salary)
            await message.answer(
                f"✅ Для роли {role.value} установлен оклад за смену {format_money(base_salary)} "
                f"(обновлено сотрудников: {updated_count})."
            )
            return

        try:
            await set_salary_for_employee(session, target, base_salary)
        except EmployeeServiceError as exc:
            await message.answer(f"❌ {exc}")
            return

    await message.answer(f"✅ Для {target} установлен оклад за смену {format_money(base_salary)}.")


@router.message(Command("invite"))
async def cmd_invite(message: Message, command: CommandObject) -> None:
    """Создает одноразовую ссылку-приглашение для личного кабинета сотрудника.

    Сотрудник переходит по ней -> его Telegram-аккаунт привязывается к
    записи в базе -> становится доступен /me, /my_stats, /my_salary.
    """
    if not await _require_admin(message):
        return

    if not command.args:
        await message.answer(
            "Использование: /invite Имя\n"
            "Например: /invite Алина\n\n"
            "Сотрудник должен быть уже добавлен через /add_employee."
        )
        return

    name = command.args.strip()

    async with async_session_factory() as session:
        employee = await get_employee_by_name(session, name)
        if employee is None:
            await message.answer(f"Сотрудник {name!r} не найден. Сначала добавьте его через /add_employee.")
            return
        if employee.telegram_id is not None:
            await message.answer(
                f"У сотрудника {employee.name} уже привязан Telegram-аккаунт. "
                "Повторное приглашение не требуется."
            )
            return

        code = await create_invite_code(session, employee)

    bot_info = await message.bot.get_me()
    link = f"https://t.me/{bot_info.username}?start={code}"

    await message.answer(
        f"✅ Ссылка-приглашение для {employee.name} готова:\n\n"
        f"{link}\n\n"
        "Отправьте её сотруднику — она одноразовая и работает только для "
        "того, кто перейдет по ней первым."
    )