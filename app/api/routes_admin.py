from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin_api_key
from app.config import settings
from app.db.models import WalletTransactionType
from app.db.session import get_session
from app.schemas import ResellerProvisionRequest, ResellerResponse, UsageRunResponse, WalletAdjustRequest
from app.services.reseller_service import adjust_wallet, get_reseller_by_id, list_resellers, provision_reseller
from app.services.usage_monitor import run_usage_monitor_once

router = APIRouter(prefix='/api/admin', tags=['admin'], dependencies=[Depends(require_admin_api_key)])


def to_response(reseller) -> ResellerResponse:
    return ResellerResponse.model_validate(reseller).model_copy(update={'panel_url': settings.pasarguard_dashboard_url or None})


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
