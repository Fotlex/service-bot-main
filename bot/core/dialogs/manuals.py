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
from web.panel.models import (
    GreeModel, KitanoModel, RoverModel, Settings, User,
    GreeManual, KitanoManual, RoverManual
)

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
        async for m in model_class.objects.filter(type=c_type):
            models_list.append({'id': m.id, 'name': m.model})

    return {'models': models_list}

async def manuals_list_getter(dialog_manager: DialogManager, **kwargs):
    user_data = dialog_manager.dialog_data
    brand = user_data.get('brand')
    model_id = user_data.get('model_id')
    
    manuals = []
    model_name = "Неизвестно"
    
    try:
        model_instance = None
        if brand == 'GREE':
            model_instance = await GreeModel.objects.aget(id=model_id)
        elif brand == 'KITANO':
            model_instance = await KitanoModel.objects.aget(id=model_id)
        elif brand == 'ROVER':
            model_instance = await RoverModel.objects.aget(id=model_id)

        if model_instance:
            model_name = model_instance.model
            async for manual in model_instance.manuals.all():
                manuals.append({'id': manual.id, 'name': manual.title})
                
    except Exception as e:
        print(f"Error in manuals_list_getter: {e}")

    return {
        'manuals': manuals, 
        'has_manuals': len(manuals) > 0,
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
    try:
        manual_id = int(item_id)
        manual_obj = None
        if brand == 'GREE':
            manual_obj = await GreeManual.objects.aget(id=manual_id)
        elif brand == 'KITANO':
            manual_obj = await KitanoManual.objects.aget(id=manual_id)
        elif brand == 'ROVER':
            manual_obj = await RoverManual.objects.aget(id=manual_id)

        if manual_obj and manual_obj.file:
            await callback.message.answer_document(
                FSInputFile(manual_obj.file.path),
                caption=manual_obj.title
            )
        else:
            await callback.answer("Файл не найден", show_alert=True)
    except Exception as e:
        print(f"File send error: {e}")
        await callback.answer("Ошибка при отправке файла", show_alert=True)

async def on_date_input(message: Message, widget: TextInput, manager: DialogManager, text: str):
    manager.dialog_data['purchase_date'] = text
    await manager.next()

async def send_manual_request_bitrix(message: Message, widget: TextInput, manager: DialogManager, text: str):
    user: User = manager.middleware_data['user']
    bot: Bot = manager.middleware_data['bot']
    settings = await sync_to_async(Settings.get_solo)()
    
    brand = manager.dialog_data.get('brand', 'Не указано')
    purchase_date = manager.dialog_data.get('purchase_date', 'Не указано')
    model_input = text
    
    comment = f"<b>Запрос инструкции (Нет в списке)</b>\n\nФИО: {user.fio}\nКомпания: {user.company_name}\nТелефон: {user.phone_number}\nБренд: {brand}\nМодель: {model_input}\nДата/Счет: {purchase_date}"

    if settings.manager_id:
        try:
            await bot.send_message(chat_id=settings.manager_id, text=comment, parse_mode=ParseMode.HTML)
        except Exception as e:
            print(f"Manager notification error: {e}")

    bitrix_payload = {
        "fields": {
            "TITLE": f"Запрос инструкции: {model_input}",
            "NAME": user.fio.split()[0] if user.fio else "User",
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
        print(f"Bitrix error: {e}")

    await message.answer("Ваш запрос передан менеджеру. Мы свяжемся с вами.")
    await manager.start(MainSG.main, mode=StartMode.RESET_STACK, show_mode=ShowMode.SEND)

async def go_to_main(callback: CallbackQuery, button: Button, manager: DialogManager):
    await manager.start(MainSG.main, mode=StartMode.RESET_STACK, show_mode=ShowMode.SEND)

dialog = Dialog(
    Window(
        Const('Выберите бренд кондиционера'),
        Row(
            Button(Const('GREE'), id='GREE', on_click=on_brand_click),
            Button(Const('KITANO'), id='KITANO', on_click=on_brand_click),
            Button(Const('ROVER'), id='ROVER', on_click=on_brand_click),
        ),
        Button(Const('Назад в меню'), id='menu', on_click=go_to_main),
        state=ManualsSG.brand
    ),
    Window(
        Const('Выберите тип кондиционера'),
        Row(
            Button(Const('Бытовые кондиционеры'), id='byt', on_click=on_type_click),
            Button(Const('Полупромышленные кондиционеры'), id='prom', on_click=on_type_click),
        ),
        Button(Const('Мультизональное оборудование'), id='mult', on_click=on_type_click),
        Back(Const('Назад')),
        state=ManualsSG.type
    ),
    Window(
        Const('Выберите серию кондиционера'),
        ScrollingGroup(
            Select(
                Format('{item[name]}'), id='s_mod', item_id_getter=lambda x: x['id'],
                items='models', on_click=on_model_click
            ),
            id='scr_mod', width=1, height=7, hide_on_single_page=True
        ),
        SwitchTo(Const('Варианта нет в списке'), id='no_model', state=ManualsSG.input_date),
        Back(Const('Назад')),
        state=ManualsSG.model,
        getter=models_getter
    ),
    Window(
        Format('Модель: {model_name}\nВыберите инструкцию для скачивания:'),
        ScrollingGroup(
            Select(
                Format('{item[name]}'),
                id='s_man',
                item_id_getter=lambda x: x['id'],
                items='manuals',
                on_click=on_download_manual
            ),
            id='scroll_manuals',
            width=1,
            height=5,
            hide_on_single_page=True,
            when='has_manuals'
        ),
        Const("К этой модели инструкции пока не загружены.", when=lambda data, w, m: not data['has_manuals']),
        SwitchTo(Const('В списке нет нужной инструкции'), id='missing', state=ManualsSG.input_date),
        Back(Const('Назад')),
        state=ManualsSG.select_manual,
        getter=manuals_list_getter
    ),
    Window(
        Const('Укажите дату покупки оборудования или номер счета'),
        TextInput(id='date', on_success=on_date_input),
        Back(Const('Назад')),
        state=ManualsSG.input_date
    ),
    Window(
        Const('Укажите модель кондиционера'),
        TextInput(id='inp_mod', on_success=send_manual_request_bitrix),
        Back(Const('Назад')),
        state=ManualsSG.input_model
    )
)

router.include_router(dialog)