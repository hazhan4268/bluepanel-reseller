from __future__ import annotations

import random
import string

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.models import Reseller, ResellerStatus, WalletTransaction, WalletTransactionType
from app.schemas import ResellerProvisionRequest
from app.services.panel_service import get_panel
from app.services.pasarguard_client import PasarGuardClient


class ResellerServiceError(RuntimeError):
    pass


ALPHABET = string.ascii_letters + string.digits


def generate_panel_key(length: int = 18) -> str:
    return ''.join(random.SystemRandom().choice(ALPHABET) for _ in range(length))


def default_username(telegram_id: int) -> str:
    return f'bp_{telegram_id}'[:32]


async def get_reseller_by_telegram_id(session: AsyncSession, telegram_id: int) -> Reseller | None:
    result = await session.execute(select(Reseller).where(Reseller.telegram_id == telegram_id))
    return result.scalar_one_or_none()


async def get_reseller_by_id(session: AsyncSession, reseller_id: int) -> Reseller | None:
    return await session.get(Reseller, reseller_id)


async def list_resellers(session: AsyncSession) -> list[Reseller]:
    result = await session.execute(select(Reseller).order_by(Reseller.id.desc()))
    return list(result.scalars().all())


async def provision_reseller(session: AsyncSession, data: ResellerProvisionRequest) -> tuple[Reseller, str]:
    existing = await get_reseller_by_telegram_id(session, data.telegram_id)
    if existing:
        raise ResellerServiceError('A reseller with this telegram_id already exists')

    panel = await get_panel(session, data.panel_id)
    role_id = data.pasar_role_id or (panel.default_role_id if panel else settings.default_pasarguard_role_id)
    if not role_id:
        raise ResellerServiceError('PasarGuard role id is not configured')

    pasar_username = data.pasar_username or default_username(data.telegram_id)
    panel_key = generate_panel_key()
    price_per_gb = data.price_per_gb_toman or settings.default_price_per_gb_toman
    debt_limit = data.debt_limit_toman if data.debt_limit_toman is not None else settings.default_debt_limit_toman

    if panel:
        client = PasarGuardClient(panel.base_url, panel.admin_username, panel.admin_secret)
    else:
        client = PasarGuardClient()

    try:
        admin_payload = {
            'username': pasar_username,
            'password': panel_key,
            'role_id': role_id,
            'telegram_id': data.telegram_id,
            'status': 'active',
            'data_limit': 0,
            'note': data.note or 'Created by BluePanel Reseller',
        }
        pasar_admin = await client.create_admin(admin_payload)
    finally:
        await client.close()

    reseller = Reseller(
        telegram_id=data.telegram_id,
        telegram_username=data.telegram_username,
        pasar_admin_id=pasar_admin.get('id'),
        pasar_username=pasar_username,
        pasar_role_id=role_id,
        panel_id=panel.id if panel else None,
        status=ResellerStatus.active.value,
        balance_toman=data.initial_balance_toman,
        price_per_gb_toman=price_per_gb,
        debt_limit_toman=debt_limit,
        note=data.note,
    )
    session.add(reseller)
    await session.flush()

    if data.initial_balance_toman:
        session.add(WalletTransaction(reseller_id=reseller.id, type=WalletTransactionType.manual_credit.value, amount_toman=data.initial_balance_toman, balance_before_toman=0, balance_after_toman=data.initial_balance_toman, description='Initial reseller balance'))

    await session.commit()
    await session.refresh(reseller)
    return reseller, panel_key


async def adjust_wallet(session: AsyncSession, reseller: Reseller, amount_toman: int, tx_type: WalletTransactionType, description: str | None = None) -> Reseller:
    before = reseller.balance_toman
    after = before + amount_toman
    reseller.balance_toman = after
    if after > settings.low_balance_threshold_toman:
        reseller.low_balance_alert_sent = False
    session.add(WalletTransaction(reseller_id=reseller.id, type=tx_type.value, amount_toman=amount_toman, balance_before_toman=before, balance_after_toman=after, description=description))
    await session.commit()
    await session.refresh(reseller)
    return reseller
