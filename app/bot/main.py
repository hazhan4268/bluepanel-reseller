import asyncio
import logging

from aiogram import Bot, Dispatcher

from app.bot.handlers import router
from app.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('bot')


async def main() -> None:
    if not settings.telegram_bot_token:
        raise RuntimeError('TELEGRAM_BOT_TOKEN is not configured')
    bot = Bot(token=settings.telegram_bot_token)
    dp = Dispatcher()
    dp.include_router(router)
    logger.info('BluePanel reseller bot started')
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
