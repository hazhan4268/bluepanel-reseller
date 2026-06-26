from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin_api_key
from app.config import settings
from app.db.models import WalletTransactionType
from app.db.session import get_session
from app.schemas import BotConfigResponse, BotConfigUpdate, PasarGuardPanelCreate, PasarGuardPanelResponse, ResellerProvisionRequest, ResellerResponse, UsageRunResponse, WalletAdjustRequest
from app.services.panel_service import create_panel, get_bot_config, list_panels, telegram_delete_webhook, telegram_get_me, telegram_set_webhook, test_panel, update_bot_config
from app.services.reseller_service import adjust_wallet, get_reseller_by_id, list_resellers, provision_reseller
from app.services.usage_monitor import run_usage_monitor_once

router = APIRouter(prefix='/api/admin', tags=['admin'], dependencies=[Depends(require_admin_api_key)])


def to_response(reseller) -> ResellerResponse:
    return ResellerResponse.model_validate(reseller).model_copy(update={'panel_url': settings.pasarguard_dashboard_url or None})


def bot_config_response(config) -> BotConfigResponse:
    return BotConfigResponse.model_validate(config).model_copy(update={'has_bot_token': bool(config.bot_token)})


@router.get('/ping')
async def admin_ping() -> dict[str, str]:
    return {'status': 'admin-ok'}


@router.post('/resellers/provision')
async def provision(data: ResellerProvisionRequest, session: AsyncSession = Depends(get_session)):
    try:
        reseller, panel_access = await provision_reseller(session, data)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {'reseller': to_response(reseller), 'panel_access': panel_access, 'panel_url': settings.pasarguard_dashboard_url or None}


@router.get('/resellers', response_model=list[ResellerResponse])
async def resellers(session: AsyncSession = Depends(get_session)):
    rows = await list_resellers(session)
    return [to_response(row) for row in rows]


@router.post('/resellers/{reseller_id}/wallet', response_model=ResellerResponse)
async def wallet_adjust(reseller_id: int, data: WalletAdjustRequest, session: AsyncSession = Depends(get_session)):
    reseller = await get_reseller_by_id(session, reseller_id)
    if not reseller:
        raise HTTPException(status_code=404, detail='Reseller not found')
    tx_type = WalletTransactionType.manual_credit if data.amount_toman >= 0 else WalletTransactionType.manual_debit
    updated = await adjust_wallet(session, reseller, data.amount_toman, tx_type, data.description)
    return to_response(updated)


@router.post('/usage/run-once', response_model=UsageRunResponse)
async def usage_run_once(session: AsyncSession = Depends(get_session)):
    return await run_usage_monitor_once(session)


@router.get('/pasarguard-panels', response_model=list[PasarGuardPanelResponse])
async def pasarguard_panels(session: AsyncSession = Depends(get_session)):
    return await list_panels(session)


@router.post('/pasarguard-panels', response_model=PasarGuardPanelResponse)
async def pasarguard_panel_create(data: PasarGuardPanelCreate, session: AsyncSession = Depends(get_session)):
    return await create_panel(session, data)


@router.post('/pasarguard-panels/{panel_id}/test')
async def pasarguard_panel_test(panel_id: int, session: AsyncSession = Depends(get_session)):
    from app.services.panel_service import get_panel
    panel = await get_panel(session, panel_id)
    if not panel:
        raise HTTPException(status_code=404, detail='Panel not found')
    ok = await test_panel(panel)
    return {'ok': ok}


@router.get('/bot-config', response_model=BotConfigResponse)
async def bot_config_get(session: AsyncSession = Depends(get_session)):
    return bot_config_response(await get_bot_config(session))


@router.post('/bot-config', response_model=BotConfigResponse)
async def bot_config_update(data: BotConfigUpdate, session: AsyncSession = Depends(get_session)):
    config = await update_bot_config(session, data)
    if config.bot_token:
        try:
            me = await telegram_get_me(config.bot_token)
            config.bot_username = me.get('username')
            session.add(config)
            await session.commit()
            await session.refresh(config)
        except Exception:
            pass
    return bot_config_response(config)


@router.post('/bot-config/set-webhook')
async def bot_set_webhook(session: AsyncSession = Depends(get_session)):
    config = await get_bot_config(session)
    if not config.bot_token or not config.webhook_url:
        raise HTTPException(status_code=400, detail='Bot token and webhook URL are required')
    result = await telegram_set_webhook(config.bot_token, config.webhook_url, config.webhook_secret)
    config.webhook_enabled = True
    session.add(config)
    await session.commit()
    return result


@router.post('/bot-config/delete-webhook')
async def bot_delete_webhook(session: AsyncSession = Depends(get_session)):
    config = await get_bot_config(session)
    if not config.bot_token:
        raise HTTPException(status_code=400, detail='Bot token is required')
    result = await telegram_delete_webhook(config.bot_token)
    config.webhook_enabled = False
    session.add(config)
    await session.commit()
    return result
