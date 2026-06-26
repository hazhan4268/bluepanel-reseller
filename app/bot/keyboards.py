from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu(panel_url: str | None = None) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text='Balance', callback_data='balance')],
        [InlineKeyboardButton(text='Usage status', callback_data='usage_status')],
    ]
    if panel_url:
        buttons.append([InlineKeyboardButton(text='Open reseller panel', url=panel_url)])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
