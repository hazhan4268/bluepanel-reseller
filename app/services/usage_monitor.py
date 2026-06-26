from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.models import Reseller, ResellerStatus
from app.schemas import UsageRunResponse
from app.services.billing_service import apply_usage_bill, debt_limit_reached
from app.services.pasarguard_client import PasarGuardClient


def extract_usage_bytes(payload: Any) -> int:
    if payload is None:
        return 0
    if isinstance(payload, int):
        return max(0, payload)
    if isinstance(payload, float):
        return max(0, int(payload))
    if isinstance(payload, list):
        return sum(extract_usage_bytes(item) for item in payload)
    if isinstance(payload, dict):
        for key in ('lifetime_used_traffic', 'used_traffic', 'total_usage', 'total'):
            value = payload.get(key)
            if isinstance(value, (int, float)):
                return max(0, int(value))
        return sum(extract_usage_bytes(value) for value in payload.values())
    return 0


async def run_usage_monitor_once(session: AsyncSession) -> UsageRunResponse:
    result = await session.execute(select(Reseller).where(Reseller.status != ResellerStatus.disabled.value))
    resellers = list(result.scalars().all())
    client = PasarGuardClient()
    checked = charged = restricted = 0
    errors: list[str] = []

    try:
        for reseller in resellers:
            checked += 1
            try:
                usage_payload = await client.get_admin_usage(reseller.pasar_username)
                total_usage = extract_usage_bytes(usage_payload)
                delta, cost = await apply_usage_bill(session, reseller, total_usage)
                if delta > 0 or cost > 0:
                    charged += 1
                if debt_limit_reached(reseller):
                    if settings.disable_users_when_debt_limit_reached:
                        await client.disable_admin_users(reseller.pasar_username)
                    if settings.disable_admin_when_debt_limit_reached:
                        await client.disable_admin(reseller.pasar_username)
                    reseller.status = ResellerStatus.disabled.value
                    session.add(reseller)
                    await session.commit()
                    restricted += 1
            except Exception as exc:
                errors.append(f'{reseller.pasar_username}: {exc}')
    finally:
        await client.close()

    return UsageRunResponse(checked=checked, charged=charged, restricted=restricted, errors=errors)
