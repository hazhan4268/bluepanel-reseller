from aiogram import Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select

from app.bot.keyboards import guest_menu, reseller_menu
from app.config import settings
from app.db.models import Reseller
from app.db.session import AsyncSessionLocal
from app.schemas import ResellerProvisionRequest
from app.services.reseller_service import provision_reseller

router = Router()


def panel_url() -> str | None:
    return settings.pasarguard_dashboard_url or None


def format_reseller(reseller: Reseller) -> str:
    return (
        'Reseller panel status:\n\n'
        f'Panel username: {reseller.pasar_username}\n'
        f'Status: {reseller.status}\n'
        f'Balance: {reseller.balance_toman:,} Toman\n'
        f'Price per GB: {reseller.price_per_gb_toman:,} Toman\n'
        f'Usage: {reseller.last_total_usage_bytes / (1024 ** 3):,.2f} GB\n'
        f'Panel URL: {panel_url() or "not configured"}'
    )


async def find_reseller(telegram_id: int) -> Reseller | None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Reseller).where(Reseller.telegram_id == telegram_id))
        return result.scalar_one_or_none()


@router.message(Command('start'))
async def start(message: Message) -> None:
    reseller = await find_reseller(message.from_user.id)
    if not reseller:
        await message.answer('Welcome to BluePanel reseller bot. Use the button below to activate a reseller panel.', reply_markup=guest_menu())
        return
    await message.answer(format_reseller(reseller), reply_markup=reseller_menu(panel_url()))


@router.message(Command('balance'))
async def balance(message: Message) -> None:
    reseller = await find_reseller(message.from_user.id)
    if not reseller:
        await message.answer('No reseller panel found for your account.', reply_markup=guest_menu())
        return
    await message.answer(format_reseller(reseller), reply_markup=reseller_menu(panel_url()))


@router.message(Command('panel'))
async def panel(message: Message) -> None:
    reseller = await find_reseller(message.from_user.id)
    if not reseller:
        await message.answer('Activate your reseller panel from the bot first.', reply_markup=guest_menu())
        return
    await message.answer(f'PasarGuard panel URL:\n{panel_url() or "not configured"}')


async def create_reseller_from_bot(query: CallbackQuery) -> None:
    existing = await find_reseller(query.from_user.id)
    if existing:
        await query.message.answer(format_reseller(existing), reply_markup=reseller_menu(panel_url()))
        return

    async with AsyncSessionLocal() as session:
        data = ResellerProvisionRequest(
            telegram_id=query.from_user.id,
            telegram_username=query.from_user.username,
            initial_balance_toman=0,
            price_per_gb_toman=settings.default_price_per_gb_toman,
            debt_limit_toman=settings.default_debt_limit_toman,
            note='Created from Telegram bot reseller flow',
        )
        try:
            reseller, panel_code = await provision_reseller(session, data)
        except Exception as exc:
            await query.message.answer(
                'Reseller panel activation failed. Check PasarGuard panel settings and reseller role in the master panel.\n\n'
                f'Error: {exc}'
            )
            return

    await query.message.answer(
        'Your reseller panel is active.\n\n'
        f'Panel URL: {panel_url() or "not configured"}\n'
        f'Username: {reseller.pasar_username}\n'
        f'Login code: {panel_code}\n\n'
        'Save this login code now.',
        reply_markup=reseller_menu(panel_url()),
    )


@router.callback_query()
async def callbacks(query: CallbackQuery) -> None:
    if query.data == 'buy_reseller':
        await create_reseller_from_bot(query)
    elif query.data == 'reseller_help':
        await query.message.answer('Use this bot to activate your reseller panel and check balance, usage, and panel link.')
    elif query.data in {'balance', 'usage_status'}:
        reseller = await find_reseller(query.from_user.id)
        if not reseller:
            await query.message.answer('No reseller panel found.', reply_markup=guest_menu())
        else:
            await query.message.answer(format_reseller(reseller), reply_markup=reseller_menu(panel_url()))
    await query.answer()
