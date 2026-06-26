from aiogram import Bot, Dispatcher
from aiogram.types import Update
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.handlers import router as bot_router
from app.db.session import get_session
from app.services.panel_service import get_bot_config

router = APIRouter(tags=['telegram'])


@router.post('/telegram/webhook/{secret}')
async def telegram_webhook(secret: str, request: Request, x_telegram_bot_api_secret_token: str | None = Header(default=None), session: AsyncSession = Depends(get_session)):
    config = await get_bot_config(session)
    if not config.bot_token:
        raise HTTPException(status_code=400, detail='Bot token is not configured')
    if config.webhook_secret and secret != config.webhook_secret:
        raise HTTPException(status_code=401, detail='Invalid webhook path')
    if config.webhook_secret and x_telegram_bot_api_secret_token and x_telegram_bot_api_secret_token != config.webhook_secret:
        raise HTTPException(status_code=401, detail='Invalid webhook secret header')
    payload = await request.json()
    bot = Bot(token=config.bot_token)
    dp = Dispatcher()
    dp.include_router(bot_router)
    try:
        update = Update.model_validate(payload, context={'bot': bot})
        await dp.feed_update(bot, update)
    finally:
        await bot.session.close()
    return {'ok': True}
