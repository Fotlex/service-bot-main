from aiogram import Router
from aiogram.types import Message, CallbackQuery
from aiogram_dialog import Dialog, DialogManager, Window, StartMode
from aiogram_dialog.widgets.input import TextInput
from aiogram_dialog.widgets.kbd import Button, Row, Back
from aiogram_dialog.widgets.text import Const

from aiogram import Router
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram_dialog import Dialog, DialogManager, Window, StartMode, ShowMode
from aiogram_dialog.widgets.input import TextInput
from aiogram_dialog.widgets.kbd import Button, Row, Next, Back, SwitchTo, ScrollingGroup, Select
from aiogram_dialog.widgets.text import Const, Format
from asgiref.sync import sync_to_async

from bot.core.states import MainSG, ConditionerSG, CompanySG, ComplaintSG, FinalConsumerSG
from web.panel.models import GreeModel, KitanoModel, RoverModel, ActualModel, ErrorCode

import aiohttp
import json
import io
import base64
from config import config

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
        conditioner_type = user.data.get('conditioner_type', 'Не указано')
        company_name = user.data.get('company_name', 'Не указано')
        company_address = user.data.get('company_address', 'Не указано')
        fio = user.data.get('fio', 'Не указано')
        phone_number = user.data.get('phone_number', 'Не указано')
        site_url = user.data.get('site', 'Не указано')

        comments_for_bitrix = f'''
<b>Новая заявка на дилерство</b>

<b>Выбранный бренд:</b> {conditioner_type}
<b>Название компании:</b> {company_name}
<b>Адрес компании:</b> {company_address}
<b>ФИО:</b> {fio}
<b>Телефон:</b> {phone_number}
<b>Сайт:</b> {site_url}
'''

        bitrix_payload = {
            "fields": {
                "TITLE": f"Заявка на дилерство: {fio} ({company_name})",
                "NAME": fio.split()[0] if fio and len(fio.split()) > 0 else "",
                "LAST_NAME": fio.split()[-1] if fio and len(fio.split()) > 1 else "",
                "COMPANY_TITLE": company_name,
                "PHONE": [{"VALUE": phone_number, "VALUE_TYPE": "WORK"}],
                "SOURCE_ID": "TELEGRAM", 
                "COMMENTS": comments_for_bitrix,
                "OPENED": "Y",
                "STATUS_ID": "NEW",
                "UF_CRM_1755788093": str(user.id),
            },
            "params": {"REGISTER_SONET_EVENT": "Y"}
        }

        
        if site_url and site_url.strip() != '-':
             bitrix_payload["fields"]["WEB"] = [{"VALUE": site_url, "VALUE_TYPE": "WORK"}]

        try:
            async with aiohttp.ClientSession() as session:
                lead_creation_url = config.BITRIX24_WEBHOOK_URL + "crm.lead.add.json"
                
                async with session.post(lead_creation_url, json=bitrix_payload) as response:
                    response.raise_for_status()
                    bitrix_result = await response.json()

                if bitrix_result.get('result'):
                    lead_id = bitrix_result['result']
                    print(f"Лид (заявка на дилерство) успешно создан. ID: {lead_id}")
                elif bitrix_result.get('error'):
                    error_desc = bitrix_result.get('error_description', 'Нет описания')
                    print(f"Ошибка Битрикс24 при создании Лида (дилерство): {bitrix_result['error']} - {error_desc}")
                else:
                    print(f"Неизвестный ответ от Битрикс24 при создании Лида (дилерство): {bitrix_result}")

        except aiohttp.ClientError as e:
            print(f"!!! ОШИБКА HTTP-запроса к Битрикс24 (дилерство): {e}")
        except Exception as e:
            print(f"!!! НЕПРЕДВИДЕННАЯ ОШИБКА при отправке Лида в Битрикс24 (дилерство): {e}")
        
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
