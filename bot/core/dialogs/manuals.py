import aiohttp
from aiogram import Router, Bot
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.enums import ParseMode
from aiogram_dialog import Dialog, DialogManager, Window, StartMode, ShowMode
from aiogram_dialog.widgets.input import TextInput
from aiogram_dialog.widgets.kbd import Button, Row, Back, SwitchTo, ScrollingGroup, Select
from aiogram_dialog.widgets.text import Const, Format

from asgiref.sync import sync_to_async
from config import config
from bot.core.states import MainSG, ManualsSG
from web.panel.models import GreeModel, KitanoModel, RoverModel, Settings, User

router = Router()


async def models_getter(dialog_manager: DialogManager, **kwargs):
    user_data = dialog_manager.dialog_data
    brand = user_data.get('brand')
    c_type = user_data.get('c_type')

    model_class = None
    if brand == 'GREE':
        model_class = GreeModel
    elif brand == 'KITANO':
        model_class = KitanoModel
    elif brand == 'ROVER':
        model_class = RoverModel

    models_list = []
    if model_class:
        objs = await sync_to_async(list)(model_class.objects.filter(type=c_type))
        for m in objs:
            models_list.append({'id': m.id, 'name': m.model})

    return {'models': models_list}


async def manuals_list_getter(dialog_manager: DialogManager, **kwargs):
    user_data = dialog_manager.dialog_data
    brand = user_data.get('brand')
    model_id = user_data.get('model_id')
    
    model_instance = None
    if brand == 'GREE':
        model_instance = await sync_to_async(GreeModel.objects.get)(id=model_id)
    elif brand == 'KITANO':
        model_instance = await sync_to_async(KitanoModel.objects.get)(id=model_id)
    elif brand == 'ROVER':
        model_instance = await sync_to_async(RoverModel.objects.get)(id=model_id)

    manuals = []
    model_name = "Неизвестно"

    if model_instance:
        model_name = model_instance.model
        if model_instance.manual_user:
            manuals.append({'id': 'user', 'name': 'Инструкция пользователя'})
        if model_instance.manual_install:
            manuals.append({'id': 'install', 'name': 'Инструкция по монтажу'})

    has_manuals = len(manuals) > 0
    
    return {
        'manuals': manuals, 
        'has_manuals': has_manuals,
        'model_name': model_name
    }


async def on_brand_click(callback: CallbackQuery, button: Button, manager: DialogManager):
    manager.dialog_data['brand'] = button.widget_id
    await manager.next()

async def on_type_click(callback: CallbackQuery, button: Button, manager: DialogManager):
    manager.dialog_data['c_type'] = button.widget_id
    await manager.next()

async def on_model_click(callback: CallbackQuery, select: Select, manager: DialogManager, item_id: str):
    manager.dialog_data['model_id'] = item_id
    await manager.next()

async def on_download_manual(callback: CallbackQuery, select: Select, manager: DialogManager, item_id: str):
    brand = manager.dialog_data.get('brand')
    model_id = manager.dialog_data.get('model_id')

    if brand == 'GREE':
        model = await sync_to_async(GreeModel.objects.get)(id=model_id)
    elif brand == 'KITANO':
        model = await sync_to_async(KitanoModel.objects.get)(id=model_id)
    elif brand == 'ROVER':
        model = await sync_to_async(RoverModel.objects.get)(id=model_id)
    else:
        return

    try:
        file_path = None
        if item_id == 'user':
            file_path = model.manual_user.path
        elif item_id == 'install':
            file_path = model.manual_install.path
        
        if file_path:
            await callback.message.answer_document(FSInputFile(file_path))
        else:
            await callback.answer("Файл физически отсутствует на сервере", show_alert=True)
            
    except Exception as e:
        print(f"Ошибка отправки файла: {e}")
        await callback.answer("Ошибка при отправке файла", show_alert=True)


async def on_date_input(message: Message, widget: TextInput, manager: DialogManager, text: str):
    manager.dialog_data['purchase_date'] = text
    await manager.next()


async def send_manual_request_bitrix(message: Message, widget: TextInput, manager: DialogManager, text: str):
    """Отправка заявки, если модели/инструкции нет"""
    user: User = manager.middleware_data['user']
    bot: Bot = manager.middleware_data['bot']
    settings = await sync_to_async(Settings.get_solo)()
    
    brand = manager.dialog_data.get('brand', 'Не указано')
    purchase_date = manager.dialog_data.get('purchase_date', 'Не указано')
    model_input = text
    
    comment = f'''
<b>Запрос инструкции (Нет в списке)</b>

ФИО: {user.fio or "-"}
Компания: {user.company_name or "-"}
Телефон: {user.phone_number or "-"}

Бренд: {brand}
Искомая модель: {model_input}
Дата покупки / Счет: {purchase_date}
'''

    if settings.manager_id:
        try:
            await bot.send_message(
                chat_id=settings.manager_id,
                text=comment,
                parse_mode=ParseMode.HTML,
                reply_markup=None 
            )
        except Exception as e:
            print(f"Ошибка отправки менеджеру: {e}")

    bitrix_payload = {
        "fields": {
            "TITLE": f"Запрос инструкции: {model_input}",
            "NAME": user.fio.split()[0] if user.fio else "User",
            "LAST_NAME": user.fio.split()[-1] if user.fio and len(user.fio.split()) > 1 else "",
            "COMPANY_TITLE": user.company_name or "Telegram User",
            "PHONE": [{"VALUE": user.phone_number, "VALUE_TYPE": "WORK"}] if user.phone_number else [],
            "SOURCE_ID": "TELEGRAM",
            "COMMENTS": comment,
            "OPENED": "Y",
            "STATUS_ID": "NEW",
            "UF_CRM_1755788093": str(user.id),
            "UF_CRM_1760933453": "Сервис"
        },
        "params": {"REGISTER_SONET_EVENT": "Y"}
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            url = config.BITRIX24_WEBHOOK_URL + "crm.lead.add.json"
            async with session.post(url, json=bitrix_payload) as response:
                if response.status == 200:
                    res = await response.json()
                    if res.get('result'):
                        user.bitrix_lead_id = res['result']
                        await user.asave()
    except Exception as e:
        print(f"Ошибка Битрикс: {e}")

    await message.answer("Ваш запрос передан менеджеру. Мы найдем инструкцию и свяжемся с вами.")
    await manager.start(MainSG.main, mode=StartMode.RESET_STACK, show_mode=ShowMode.SEND)


async def go_to_main(callback: CallbackQuery, button: Button, manager: DialogManager):
    await manager.start(MainSG.main, mode=StartMode.RESET_STACK, show_mode=ShowMode.SEND)



win_brand = Window(
    Const('Выберите бренд кондиционера'),
    Row(
        Button(Const('GREE'), id='GREE', on_click=on_brand_click),
        Button(Const('KITANO'), id='KITANO', on_click=on_brand_click),
        Button(Const('ROVER'), id='ROVER', on_click=on_brand_click),
    ),
    Button(Const('Назад в меню'), id='menu', on_click=go_to_main),
    state=ManualsSG.brand
)

win_type = Window(
    Const('Выберите тип кондиционера'),
    Row(
        Button(Const('Бытовые кондиционеры'), id='byt', on_click=on_type_click),
        Button(Const('Полупромышленные кондиционеры'), id='prom', on_click=on_type_click),
    ),
    Button(Const('Мультизональное оборудование'), id='mult', on_click=on_type_click),
    Back(Const('Назад')),
    state=ManualsSG.type
)

win_model = Window(
    Const('Выберите серию кондиционера'),
    ScrollingGroup(
        Select(
            Format('{item[name]}'),
            id='s_mod',
            item_id_getter=lambda x: x['id'],
            items='models',
            on_click=on_model_click
        ),
        id='scr_mod',
        width=1,
        height=7,
        hide_on_single_page=True
    ),
    SwitchTo(Const('Варианта нет в списке'), id='no_model', state=ManualsSG.input_date),
    Back(Const('Назад')),
    state=ManualsSG.model,
    getter=models_getter
)

win_select_manual = Window(
    Format('Модель: {model_name}\nВыберите инструкцию для скачивания:'),
    Select(
        Format('{item[name]}'),
        id='s_man',
        item_id_getter=lambda x: x['id'],
        items='manuals',
        on_click=on_download_manual
    ),
    SwitchTo(Const('В списке нет нужной инструкции'), id='missing', state=ManualsSG.input_date),
    Back(Const('Назад')),
    state=ManualsSG.select_manual,
    getter=manuals_list_getter
)

win_date = Window(
    Const('Укажите дату покупки оборудования или номер счета'),
    TextInput(id='date', on_success=on_date_input),
    Back(Const('Назад')),
    state=ManualsSG.input_date
)

win_input_model = Window(
    Const('Укажите модель кондиционера'),
    TextInput(id='inp_mod', on_success=send_manual_request_bitrix),
    Back(Const('Назад')),
    state=ManualsSG.input_model
)

dialog = Dialog(
    win_brand,
    win_type,
    win_model,
    win_select_manual,
    win_date,
    win_input_model
)