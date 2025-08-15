from aiogram import Router
from aiogram.types import Message, CallbackQuery
from aiogram_dialog import Dialog, DialogManager, Window, StartMode
from aiogram_dialog.widgets.input import TextInput
from aiogram_dialog.widgets.kbd import Button, Row, Back
from aiogram_dialog.widgets.text import Const

from bot.core.states import DealerSG, MainSG

router = Router()


async def on_conditioner_choice(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    user = dialog_manager.middleware_data['user']
    user.data['conditioner_type'] = button.widget_id
    await user.asave()

    await dialog_manager.next()


async def on_menu_choice(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    await dialog_manager.start(MainSG.main, mode=StartMode.RESET_STACK)


main_window = Window(
    Const(text='Стать дилером'),
    Row(
        Button(text=Const('GREE'), id='GREE', on_click=on_conditioner_choice),
        Button(text=Const('KITANO'), id='KITANO', on_click=on_conditioner_choice),
        Button(text=Const('ROVER'), id='ROVER', on_click=on_conditioner_choice),
    ),
    Button(text=Const('Назад в меню'), id='menu', on_click=on_menu_choice),
    state=DealerSG.main
)


async def on_text_input_success(message: Message, widget: TextInput, dialog_manager: DialogManager, text: str):
    user = dialog_manager.middleware_data['user']
    user.data[widget.widget_id] = text
    await user.asave()

    if widget.widget_id == 'site':
        await message.answer(text='Менеджер с вами свяжется в ближайшее время')
        await dialog_manager.start(state=MainSG.main, mode=StartMode.RESET_STACK)
        return

    await dialog_manager.next()


async def on_text_input_error(message: Message, widget: TextInput, dialog_manager: DialogManager, text: str):
    await message.answer(text='Укажите валидные данные')


def get_input_window(text: str, id: str, state: DealerSG, filter=None):
    return Window(
        Const(text=text),
        Back(text=Const('Назад')),
        Button(text=Const('Назад в меню'), id='menu', on_click=on_menu_choice),
        TextInput(on_success=on_text_input_success, on_error=on_text_input_error, id=id, filter=filter),
        state=state
    )


dialog = Dialog(
    main_window,
    get_input_window('Укажите название компании', 'company_name', state=DealerSG.company_name_input),
    get_input_window('Укажите адрес компании', 'company_address', state=DealerSG.company_address_input),
    get_input_window('Укажите ФИО', 'fio', state=DealerSG.fio_input),
    get_input_window(
        'Укажите номер телефона', 'phone_number', state=DealerSG.phone_number_input,
        filter=lambda x: len(list(filter(str.isdigit, x.text))) == 11
    ),
    get_input_window(
        'Укажите ссылку на сайт (если нет, то укажите прочерк "-")', 'site',
        state=DealerSG.site_url_input
    )
)

router.include_router(dialog)
