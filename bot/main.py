"""
Точка входа в приложение.

Запуск: python -m bot.main
"""
from __future__ import annotations

import asyncio
import logging

from aiogram import BaseMiddleware, Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ErrorEvent, TelegramObject, Update

from bot.config import config
from bot.database.engine import init_db
from bot.handlers import admin, common, employee, import_report, salary, stats

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


class DebugLoggingMiddleware(BaseMiddleware):
    """Временное логирование содержимого каждого апдейта - для диагностики
    случаев, когда апдейт не находит ни одного подходящего обработчика.
    Можно убрать после того, как проблема будет найдена."""

    async def __call__(self, handler, event: TelegramObject, data):
        try:
            if isinstance(event, Update):
                if event.message is not None:
                    logger.info(
                        "RAW UPDATE #%s: message text=%r chat_id=%s",
                        event.update_id,
                        event.message.text,
                        event.message.chat.id,
                    )
                elif event.callback_query is not None:
                    logger.info(
                        "RAW UPDATE #%s: callback_query data=%r chat_id=%s",
                        event.update_id,
                        event.callback_query.data,
                        event.callback_query.message.chat.id if event.callback_query.message else None,
                    )
                else:
                    logger.info("RAW UPDATE #%s: другой тип апдейта: %s", event.update_id, event.event_type)
        except Exception:  # noqa: BLE001
            logger.exception("Ошибка в DebugLoggingMiddleware")
        return await handler(event, data)


async def main() -> None:
    await init_db()

    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dispatcher = Dispatcher(storage=MemoryStorage())
    dispatcher.update.outer_middleware(DebugLoggingMiddleware())

    dispatcher.include_router(common.router)
    dispatcher.include_router(import_report.router)
    dispatcher.include_router(admin.router)
    dispatcher.include_router(stats.router)
    dispatcher.include_router(salary.router)
    dispatcher.include_router(employee.router)

    @dispatcher.errors()
    async def handle_errors(event: ErrorEvent) -> bool:
        """Глобальный обработчик ошибок.

        Без него необработанное исключение в любом хендлере "проглатывается"
        aiogram молча - апдейт помечается как is not handled, пользователь
        не получает вообще никакого ответа, а полный traceback уходит только
        в ERROR-лог (который легко пропустить). Теперь: полный traceback
        всегда пишется в лог, а пользователь всегда получает хоть какой-то
        ответ вместо тишины.
        """
        logger.exception(
            "Необработанная ошибка при обработке апдейта %s: %s",
            event.update.update_id,
            event.exception,
        )
        try:
            if event.update.message is not None:
                await event.update.message.answer(
                    "❌ Произошла ошибка при обработке запроса. Попробуйте еще раз "
                    "или отправьте /menu, чтобы вернуться в главное меню."
                )
            elif event.update.callback_query is not None:
                await event.update.callback_query.answer(
                    "❌ Произошла ошибка, попробуйте еще раз.", show_alert=True
                )
        except Exception:  # noqa: BLE001
            logger.exception("Не удалось отправить сообщение об ошибке пользователю")
        return True

    logger.info("Бот запущен, начинаем polling...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dispatcher.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен.")
