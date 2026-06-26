from __future__ import annotations

import secrets

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import BotConfig, PasarGuardPanel
from app.schemas import BotConfigUpdate, PasarGuardPanelCreate
from app.services.pasarguard_client import PasarGuardClient


async def list_panels(session: AsyncSession) -> list[PasarGuardPanel]:
    result = await session.execute(select(PasarGuardPanel).order_by(PasarGuardPanel.id.desc()))
    return list(result.scalars().all())


async def get_panel(session: AsyncSession, panel_id: int | None) -> PasarGuardPanel | None:
    if panel_id:
        return await session.get(PasarGuardPanel, panel_id)
    result = await session.execute(select(PasarGuardPanel).where(PasarGuardPanel.is_active.is_(True)).order_by(PasarGuardPanel.id.asc()))
    return result.scalars().first()


async def create_panel(session: AsyncSession, data: PasarGuardPanelCreate) -> PasarGuardPanel:
    panel = PasarGuardPanel(**data.model_dump())
    session.add(panel)
    await session.commit()
    await session.refresh(panel)
    return panel


async def test_panel(panel: PasarGuardPanel) -> bool:
    client = PasarGuardClient(panel.base_url, panel.admin_username, panel.admin_secret)
    try:
        await client.test_connection()
        return True
    finally:
        await client.close()


async def get_bot_config(session: AsyncSession) -> BotConfig:
    config = await session.get(BotConfig, 1)
    if config:
        return config
    config = BotConfig(id=1, webhook_secret=secrets.token_urlsafe(24))
    session.add(config)
    await session.commit()
    await session.refresh(config)
    return config


async def update_bot_config(session: AsyncSession, data: BotConfigUpdate) -> BotConfig:
    config = await get_bot_config(session)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(config, key, value)
    if not config.webhook_secret:
        config.webhook_secret = secrets.token_urlsafe(24)
    session.add(config)
    await session.commit()
    await session.refresh(config)
    return config


async def telegram_get_me(bot_token: str) -> dict:
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(f'https://api.telegram.org/bot{bot_token}/getMe')
        response.raise_for_status()
        payload = response.json()
        if not payload.get('ok'):
            raise RuntimeError(str(payload))
        return payload['result']


async def telegram_set_webhook(bot_token: str, webhook_url: str, secret_token: str | None = None) -> dict:
    data = {'url': webhook_url}
    if secret_token:
        data['secret_token'] = secret_token
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(f'https://api.telegram.org/bot{bot_token}/setWebhook', json=data)
        response.raise_for_status()
        payload = response.json()
        if not payload.get('ok'):
            raise RuntimeError(str(payload))
        return payload


async def telegram_delete_webhook(bot_token: str) -> dict:
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(f'https://api.telegram.org/bot{bot_token}/deleteWebhook')
        response.raise_for_status()
        payload = response.json()
        if not payload.get('ok'):
            raise RuntimeError(str(payload))
        return payload
