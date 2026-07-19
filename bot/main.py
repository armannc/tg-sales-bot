"""
Точка входа в приложение.

Запуск: python -m bot.main
"""
from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ErrorEvent

from bot.config import config
from bot.database.engine import init_db
from bot.handlers import admin, common, import_report, salary, stats

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    await init_db()

    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dispatcher = Dispatcher(storage=MemoryStorage())

    dispatcher.include_router(common.router)
    dispatcher.include_router(import_report.router)
    dispatcher.include_router(admin.router)
    dispatcher.include_router(stats.router)
    dispatcher.include_router(salary.router)

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