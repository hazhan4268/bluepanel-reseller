from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def guest_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text='Buy reseller panel', callback_data='buy_reseller')],
            [InlineKeyboardButton(text='Help', callback_data='reseller_help')],
        ]
    )


def reseller_menu(panel_url: str | None = None) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text='Balance', callback_data='balance')],
        [InlineKeyboardButton(text='Usage status', callback_data='usage_status')],
    ]
    if panel_url:
        buttons.append([InlineKeyboardButton(text='Open PasarGuard panel', url=panel_url)])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
