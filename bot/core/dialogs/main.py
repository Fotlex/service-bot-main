from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram_dialog import Dialog, DialogManager, Window, StartMode
from aiogram_dialog.widgets.kbd import Button, Row
from aiogram_dialog.widgets.text import Const

from bot.core.states import MainSG, DealerSG, ConditionerSG
from web.panel.models import User

router = Router()


@router.message(Command("start"))
async def start(message: Message, dialog_manager: DialogManager, user: User):
    await message.delete()
    await dialog_manager.start(MainSG.main, mode=StartMode.RESET_STACK)


async def on_dealer_click(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    await dialog_manager.start(DealerSG.main)


async def on_conditioner_click(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    await dialog_manager.start(ConditionerSG.main)


main_window = Window(
    Const(text='ГЛАВНАЯ СТРАНИЦА'),
    Row(
        Button(text=Const('Стать дилером'), id='be_a_dealer', on_click=on_dealer_click),
        Button(text=Const('Не работает кондиционер'), id='conditioner_broken', on_click=on_conditioner_click),
    ),
    state=MainSG.main
)

dialog = Dialog(
    main_window
)

router.include_router(dialog)
