from aiogram import Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select

from app.bot.keyboards import main_menu
from app.config import settings
from app.db.models import Reseller
from app.db.session import AsyncSessionLocal

router = Router()


def format_balance(reseller: Reseller) -> str:
    return (
        f'Reseller: {reseller.pasar_username}\n'
        f'Status: {reseller.status}\n'
        f'Balance: {reseller.balance_toman:,} Toman\n'
        f'Price per GB: {reseller.price_per_gb_toman:,} Toman\n'
        f'Panel: {settings.pasarguard_dashboard_url or "not configured"}'
    )


async def find_reseller(telegram_id: int) -> Reseller | None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Reseller).where(Reseller.telegram_id == telegram_id))
        return result.scalar_one_or_none()


@router.message(Command('start'))
async def start(message: Message) -> None:
    reseller = await find_reseller(message.from_user.id)
    if not reseller:
        await message.answer('Your reseller panel is not active yet. Please buy a reseller panel first.')
        return
    await message.answer(format_balance(reseller), reply_markup=main_menu(settings.pasarguard_dashboard_url or None))


@router.message(Command('balance'))
async def balance(message: Message) -> None:
    reseller = await find_reseller(message.from_user.id)
    if not reseller:
        await message.answer('Reseller account not found.')
        return
    await message.answer(format_balance(reseller), reply_markup=main_menu(settings.pasarguard_dashboard_url or None))


@router.message(Command('panel'))
async def panel(message: Message) -> None:
    reseller = await find_reseller(message.from_user.id)
    if not reseller:
        await message.answer('Reseller account not found.')
        return
    await message.answer(f'Panel URL: {settings.pasarguard_dashboard_url or "not configured"}')


@router.callback_query()
async def callbacks(query: CallbackQuery) -> None:
    if query.data in {'balance', 'usage_status'}:
        reseller = await find_reseller(query.from_user.id)
        if not reseller:
            await query.message.answer('Reseller account not found.')
        else:
            await query.message.answer(format_balance(reseller), reply_markup=main_menu(settings.pasarguard_dashboard_url or None))
    await query.answer()
