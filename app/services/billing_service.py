from __future__ import annotations

import math

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Reseller, ResellerStatus, UsageSnapshot, WalletTransaction, WalletTransactionType

BYTES_PER_GB = 1024 ** 3


def usage_cost_toman(delta_bytes: int, price_per_gb_toman: int) -> int:
    if delta_bytes <= 0 or price_per_gb_toman <= 0:
        return 0
    return math.ceil(delta_bytes * price_per_gb_toman / BYTES_PER_GB)


async def apply_usage_bill(session: AsyncSession, reseller: Reseller, total_usage_bytes: int) -> tuple[int, int]:
    old_usage = reseller.last_total_usage_bytes or 0
    delta = max(0, total_usage_bytes - old_usage)
    cost = usage_cost_toman(delta, reseller.price_per_gb_toman)

    if delta <= 0:
        reseller.last_total_usage_bytes = max(old_usage, total_usage_bytes)
        await session.commit()
        return 0, 0

    before = reseller.balance_toman
    after = before - cost
    reseller.balance_toman = after
    reseller.last_total_usage_bytes = total_usage_bytes

    if after < 0:
        reseller.status = ResellerStatus.limited.value

    session.add(UsageSnapshot(reseller_id=reseller.id, old_usage_bytes=old_usage, total_usage_bytes=total_usage_bytes, delta_usage_bytes=delta, cost_toman=cost))
    session.add(WalletTransaction(reseller_id=reseller.id, type=WalletTransactionType.usage_charge.value, amount_toman=-cost, balance_before_toman=before, balance_after_toman=after, description=f'Usage bill for {delta} bytes'))
    await session.commit()
    await session.refresh(reseller)
    return delta, cost


def debt_limit_reached(reseller: Reseller) -> bool:
    return reseller.balance_toman < -abs(reseller.debt_limit_toman)
