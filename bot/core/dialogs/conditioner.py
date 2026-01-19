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

from aiogram.fsm.context import FSMContext
from aiogram.types import (InlineKeyboardButton, InlineKeyboardMarkup,
                           ReplyKeyboardMarkup, KeyboardButton)
from aiogram import Router, Bot, F
from aiogram.enums import ParseMode, ContentType
from aiogram.types import Message, CallbackQuery, FSInputFile, PhotoSize, Document
from aiogram_dialog import Dialog, DialogManager, Window, StartMode, ShowMode
from aiogram_dialog.api.entities import MediaAttachment, MediaId
from aiogram_dialog.widgets.input import TextInput, MessageInput
from aiogram_dialog.widgets.kbd import Button, Row, Next, Back, SwitchTo, ScrollingGroup, Select, Start
from aiogram_dialog.widgets.media import DynamicMedia
from aiogram_dialog.widgets.text import Const, Format
from asgiref.sync import sync_to_async

from config import config
from bot.core.states import *
from web.panel.models import Settings, User


router = Router()


async def save_purchase_date_handler(message: Message, widget: TextInput, dialog_manager: DialogManager, text: str):
    dialog_manager.dialog_data['purchase_date'] = text
    await dialog_manager.next()

async def save_model_name_handler(message: Message, message_input: MessageInput, dialog_manager: DialogManager):
    if message.text:
        dialog_manager.dialog_data['model_name'] = message.text
    if message.photo:
        dialog_manager.dialog_data['model_photo_id'] = message.photo[-1].file_id
    await dialog_manager.next()

async def save_barcode_handler(message: Message, message_input: MessageInput, dialog_manager: DialogManager):
    if message.text:
        dialog_manager.dialog_data['barcode'] = message.text
    if message.photo:
        dialog_manager.dialog_data['barcode_photo_id'] = message.photo[-1].file_id
    await dialog_manager.next()

async def skip_barcode_handler(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    dialog_manager.dialog_data['barcode'] = "Пропущено"  
    await dialog_manager.next()

async def skip_object_handler(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    user = dialog_manager.middleware_data['user']
    user.data['object_info'] = "Пропущено"
    await user.asave()
    
    await dialog_manager.switch_to(CompanySG.choosing_myself)

async def go_to_menu(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    await dialog_manager.start(state=MainSG.main, mode=StartMode.RESET_STACK, show_mode=ShowMode.SEND)


async def go_to_complaint(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    await dialog_manager.start(state=ComplaintSG.main)


async def go_to_conditioner(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    await dialog_manager.start(state=ConditionerSG.main)


async def on_company(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    if dialog_manager.middleware_data['user'].email:
        await dialog_manager.start(state=CompanySG.object_name)
        return

    await dialog_manager.start(state=CompanySG.main)


async def on_final_consumer(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    await dialog_manager.start(state=FinalConsumerSG.choice, mode=StartMode.RESET_STACK)

async def on_contact_myself(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    await callback.message.answer("Спасибо за обращение в нашу компанию!")
    await callback.answer()
    await dialog_manager.start(MainSG.main, mode=StartMode.RESET_STACK, show_mode=ShowMode.SEND)


async def save_consumer_info_handler(message: Message, widget: TextInput, dialog_manager: DialogManager, text: str):
    dialog_manager.dialog_data['consumer_info'] = text
    await dialog_manager.next()


async def send_final_consumer_request(message: Message, message_input: MessageInput, manager: DialogManager):
    user: User = manager.middleware_data['user']
    bot: Bot = manager.middleware_data['bot']


    consumer_info = manager.dialog_data.get('consumer_info', 'Не указано')
    
    file_for_bitrix = None
    if message.photo:
        try:
            file_id = message.photo[-1].file_id
            file_info = await bot.get_file(file_id)
            file_name = file_info.file_path.split('/')[-1] if file_info.file_path else f"barcode_{file_id}.jpg"

            file_content_io = io.BytesIO()
            await bot.download_file(file_info.file_path, destination=file_content_io)
            encoded_content = base64.b64encode(file_content_io.getvalue()).decode('utf-8')
            file_for_bitrix = [file_name, encoded_content]
            print(f"Фото штрихкода '{file_name}' подготовлено для загрузки в Битрикс24.")
        except Exception as e:
            print(f"!!! ОШИБКА при подготовке фото штрихкода для Битрикс24: {e}")
            file_for_bitrix = None

    fio_for_title = consumer_info.split(',')[0].strip() or "Не указано"
    
    text_to_manager_and_bitrix = f'''
<b>Новая заявка: Конечный потребитель</b>

Контактные данные (ФИО, телефон, email):
{consumer_info}

<i>Запрос: Пользователь оставил заявку, чтобы вы сами связались с компанией, у которой он приобрел оборудование. Фото штрихкода приложено.</i>
'''
    

    await message.answer("Спасибо за обращение в нашу компанию, ваша заявка будет передана в ближайшее время.")
    
    bitrix_payload = {
        "fields": {
            "TITLE": f"Заявка от Конечного потребителя: {fio_for_title}",
            "COMMENTS": text_to_manager_and_bitrix,
            "OPENED": "Y",
            "STATUS_ID": "NEW",
            "UF_CRM_1755788093": str(user.id),
            "UF_CRM_1760933453": "Сервис"
        },
        "params": {"REGISTER_SONET_EVENT": "Y"}
    }
    
    if file_for_bitrix:
        bitrix_payload["fields"]["UF_CRM_1755617658"] = {"fileData": file_for_bitrix}
        print(f"Фото штрихкода добавлено в payload Лидa.")
    
    try:
        async with aiohttp.ClientSession() as session:
            lead_creation_url = config.BITRIX24_WEBHOOK_URL + "crm.lead.add.json"
            async with session.post(lead_creation_url, json=bitrix_payload) as response:
                response.raise_for_status()
                bitrix_result = await response.json()

                if bitrix_result.get('result'):
                    lead_id = bitrix_result['result']
                    print(f"Лид (Конечный потребитель) успешно создан. ID Лида: {lead_id}")
                    user.bitrix_lead_id = lead_id
                    await user.asave()
                elif bitrix_result.get('error'):
                    error_desc = bitrix_result.get('error_description', 'Нет описания')
                    print(f"Ошибка Битрикс24 при создании Лида (Конечный потребитель): {bitrix_result['error']} - {error_desc}")
                else:
                    print(f"Неизвестный ответ от Битрикс24 при создании Лида (Конечный потребитель): {bitrix_result}")
    except Exception as e:
        print(f"!!! НЕПРЕДВИДЕННАЯ ОШИБКА при отправке Лида в Битрикс24 (Конечный потребитель): {e}")

    await manager.start(state=MainSG.main, mode=StartMode.RESET_STACK, show_mode=ShowMode.SEND)



main_window = Window(
    Const(text='Кем вы являетесь?'),
    Button(Const(text='Климатическая компания/монтажная организация'), id='company', on_click=on_company),
    Button(Const(text='Конечный потребитель'), id='final_consumer', on_click=on_final_consumer),
    Button(Const(text='Назад в меню'), id='menu', on_click=go_to_menu),
    state=ConditionerSG.main
)

person_window = Window(
    Const(
        'Если у вас не работает кондиционер, просим вас обратиться в компанию у которой вы приобретали оборудование.\n\nВсего наилучшего!'
    ),
    Next(text=Const('Назад')),
    Button(Const(text='Назад в меню'), id='menu', on_click=go_to_menu),
    state=ConditionerSG.person
)

dialog = Dialog(
    person_window,
    main_window,
)

router.include_router(dialog)





async def on_text_input_success(message: Message, widget: TextInput, dialog_manager: DialogManager, text: str):
    user = dialog_manager.middleware_data['user']

    match widget.widget_id:
        case 'company_name':
            user.company_name = text
        case 'company_address':
            user.company_address = text
        case 'fio':
            user.fio = text
        case 'phone_number':
            user.phone_number = text
        case 'email':
            user.email = text
        case _:
            user.data[widget.widget_id] = text

    await user.asave()
    await dialog_manager.next()


async def on_text_input_error(message: Message, widget: TextInput, dialog_manager: DialogManager, text: str):
    await message.answer(text='Укажите валидные данные')


def validate_phone(input_text: str) -> str:
    if len(list(filter(str.isdigit, input_text))) != 11:
        raise ValueError("Номер должен содержать 11 цифр!")
    return input_text


def get_input_window(text: str, id: str, state: CompanySG, type_factory=str):
    return Window(
        Const(text=text),
        Back(text=Const('Назад'), when=lambda *_: id not in ['company_name', 'object_name']),
        Button(text=Const('Назад в меню'), id='menu', on_click=go_to_menu),
        TextInput(on_success=on_text_input_success, on_error=on_text_input_error, id=id, type_factory=type_factory),
        state=state
    )


async def on_do_myself(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    user = dialog_manager.middleware_data['user']
    user.data['conditioner'] = button.widget_id
    await user.asave()
    await dialog_manager.next()


async def on_do_type(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    user = dialog_manager.middleware_data['user']
    user.data['c_type'] = button.widget_id
    await user.asave()
    await dialog_manager.next()


async def models_buttons_getter(dialog_manager: DialogManager, *args, **kwargs):
    user = dialog_manager.middleware_data['user']

    if user.data['conditioner'] == 'GREE':
        model = GreeModel
    elif user.data['conditioner'] == 'KITANO':
        model = KitanoModel
    elif user.data['conditioner'] == 'ROVER':
        model = RoverModel

    data = {'buttons': [{'text': m.model, 'id': m.id} async for m in model.objects.filter(type=user.data['c_type'])]}
    return data


async def models_error_codes_getter(dialog_manager: DialogManager, *args, **kwargs):
    user = dialog_manager.middleware_data['user']

    if user.data['conditioner'] == 'GREE':
        model = await GreeModel.objects.aget(id=user.data['model_id'])
    elif user.data['conditioner'] == 'KITANO':
        model = await KitanoModel.objects.aget(id=user.data['model_id'])
    elif user.data['conditioner'] == 'ROVER':
        model = await RoverModel.objects.aget(id=user.data['model_id'])

    data = {'buttons': [{'text': c.code, 'id': c.id} async for c in model.error_codes.all()]}
    return data


async def on_model_choose(callback: CallbackQuery, select: Select, dialog_manager: DialogManager, item_id):
    user = dialog_manager.middleware_data['user']
    user.data['model_id'] = item_id
    await user.asave()

    await dialog_manager.next()


async def on_err_code_choose(callback: CallbackQuery, select: Select, dialog_manager: DialogManager, item_id):
    user = dialog_manager.middleware_data['user']

    if user.data['conditioner'] == 'GREE':
        model = await GreeModel.objects.aget(id=user.data['model_id'])
    elif user.data['conditioner'] == 'KITANO':
        model = await KitanoModel.objects.aget(id=user.data['model_id'])
    elif user.data['conditioner'] == 'ROVER':
        model = await RoverModel.objects.aget(id=user.data['model_id'])

    err_code: ErrorCode = await model.error_codes.aget(id=item_id)

    await callback.message.answer_document(
        document=FSInputFile(path=err_code.manual.path)
    )

    await dialog_manager.switch_to(CompanySG.ask_for_more_errors)

    await dialog_manager.show(ShowMode.SEND)


async def send_model_removed_company_request(message: Message, message_input: MessageInput, manager: DialogManager):
    user: User = manager.middleware_data['user']
    bot: Bot = manager.middleware_data['bot']
    manager_id = (await sync_to_async(Settings.get_solo)()).manager_id

    date_purchase = manager.dialog_data.get('purchase_date', 'Не указано')
    model_name_input = manager.dialog_data.get('model_name', 'Не указано')
    barcode_input = manager.dialog_data.get('barcode', 'Не указано')
    
    error_code_display = message.text or ""
    if message.photo:
        manager.dialog_data['error_code_photo_id'] = message.photo[-1].file_id

    files_to_forward = []
    if 'model_photo_id' in manager.dialog_data:
        files_to_forward.append(manager.dialog_data['model_photo_id'])
    if 'barcode_photo_id' in manager.dialog_data:
        files_to_forward.append(manager.dialog_data['barcode_photo_id'])
    if 'error_code_photo_id' in manager.dialog_data:
        files_to_forward.append(manager.dialog_data['error_code_photo_id'])
    
    company_name = user.company_name or "Не указано"
    fio = user.fio or "Не указано"
    phone_number = user.phone_number or "Не указано"
    email = user.email or "Не указано"
    object_info = user.data.get('object_info', "Не указано")

    text_to_manager = f'''
<b>Новая заявка: Компания - Модель снята с производства</b>

Название компании: {company_name}
ФИО: {fio}
Номер телефона: {phone_number}
Электронная почта: {email}
Адрес и название объекта: {object_info}

Дата покупки / Номер счета: {date_purchase}
Указанная модель: {model_name_input}
Штрихкод: {barcode_input}
Код ошибки (на дисплее): {error_code_display or 'Не указано'}
'''
    if manager_id != -1:
        await bot.send_message(
            chat_id=manager_id,
            text=text_to_manager,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Ответить на вопрос", callback_data=f"answer_user:{user.id}:is_final_reply=1")],
            ]),
        )
        
        for file_id in files_to_forward:
            await bot.send_photo(chat_id=manager_id, photo=file_id) 
    else:
        print("Manager ID is not set or invalid. Cannot send message to manager (company model removed request).")

    await message.answer(f"Ваш запрос принят. Менеджер сервиса ответит вам в ближайшее время.")

    bitrix_payload = {
        "fields": {
            "TITLE": f"Запрос , модели нет в списке)",
            "NAME": fio.split()[0] if fio and len(fio.split()) > 0 else "",
            "LAST_NAME": fio.split()[-1] if fio and len(fio.split()) > 1 else "",
            "COMPANY_TITLE": company_name,
            "PHONE": [{"VALUE": phone_number, "VALUE_TYPE": "WORK"}],
            "EMAIL": [{"VALUE": email, "VALUE_TYPE": "WORK"}],
            "SOURCE_ID": "TELEGRAM",
            "COMMENTS": text_to_manager,
            "OPENED": "Y",
            "STATUS_ID": "NEW",
            "UF_CRM_1755788093": str(user.id),
            "UF_CRM_1760933453": "Сервис"
        },
        "params": {"REGISTER_SONET_EVENT": "Y"}
    }

    try:
        async with aiohttp.ClientSession() as session:
            lead_creation_url = config.BITRIX24_WEBHOOK_URL + "crm.lead.add.json"
            async with session.post(lead_creation_url, json=bitrix_payload) as response:
                response.raise_for_status()
                bitrix_result = await response.json()

            if bitrix_result.get('result'):
                lead_id = bitrix_result['result']
                print(f"Лид для запроса в СЦ (Компания) успешно создан. ID Лида: {lead_id}")
                user.bitrix_lead_id = lead_id
                await user.asave()
            elif bitrix_result.get('error'):
                error_desc = bitrix_result.get('error_description', 'Нет описания')
                print(f"Ошибка Битрикс24 при создании Лида для запроса в СЦ (Компания): {bitrix_result['error']} - {error_desc}")
            else:
                print(f"Неизвестный ответ от Битрикс24 при создании Лида для запроса в СЦ (Компания): {bitrix_result}")
    except Exception as e:
        print(f"!!! НЕПРЕДВИДЕННАЯ ОШИБКА при отправке Лида в Битрикс24 (запрос СЦ, Компания): {e}")

    await manager.start(state=MainSG.main, mode=StartMode.RESET_STACK, show_mode=ShowMode.SEND)


async def final_thanks_company(callback: CallbackQuery, button: Button, manager: DialogManager):
    await callback.message.answer(text='Спасибо за обращение в нашу компанию!')
    await callback.answer()

    await manager.start(state=MainSG.main, mode=StartMode.RESET_STACK, show_mode=ShowMode.SEND)


async def on_no_error_in_list(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    await callback.answer("Так как в списке нет нужнлй ошибки, мы предлагаем вам отправить запрос в сервисный центр", show_alert=True)

    await dialog_manager.start(state=ConditionerSG.main, mode=StartMode.RESET_STACK)


company_dialog = Dialog(
    get_input_window(text='Укажите название компании', id='company_name', state=CompanySG.main),
    get_input_window(text='Укажите адрес компании', id='company_address', state=CompanySG.address_input),
    get_input_window(text='Укажите ваше ФИО', id='fio', state=CompanySG.fio_input),
    get_input_window(
        text='Укажите номер телефона для связи', id='phone_number', state=CompanySG.phone_input,
        type_factory=validate_phone
    ),
    get_input_window(text='Укажите адрес электронной почты', id='email', state=CompanySG.email_input),
    Window(
        Const(text='Укажите адрес и название объекта'),
        Row(
            Back(text=Const('Назад')),
            Button(text=Const('Пропустить'), id='skip_object', on_click=skip_object_handler),
        ),
        Button(text=Const('Назад в меню'), id='menu', on_click=go_to_menu),

        TextInput(on_success=on_text_input_success, on_error=on_text_input_error, id='object_info'),
        state=CompanySG.object_name 
    ),
    Window(
        Const(text='Выберите'),
        Button(text=Const('Отправить запрос по рекламации в сервисный центр'), id='complaint',
               on_click=go_to_complaint),
        SwitchTo(text=Const('Коды ошибок.'), id='sami', state=CompanySG.by_myself),
        Start(
            text=Const('Инструкции'), 
            id='manuals_btn', 
            state=ManualsSG.brand
        ),
        Button(text=Const('Назад в меню'), id='menu', on_click=go_to_menu),
        state=CompanySG.choosing_myself
    ),
    Window(
        Const(text='Выберите бренд кондиционера'),
        Row(
            Button(text=Const('GREE'), id='GREE', on_click=on_do_myself),
            Button(text=Const('KITANO'), id='KITANO', on_click=on_do_myself),
            Button(text=Const('ROVER'), id='ROVER', on_click=on_do_myself),
        ),
        Back(text=Const('Назад'), id='back'),
        Button(text=Const('Назад в меню'), id='menu', on_click=go_to_menu),
        state=CompanySG.by_myself
    ),
    Window(
        Const(text='Выберите тип кондиционера'),
        Button(text=Const('Бытовые'), id='byt', on_click=on_do_type),
        Button(text=Const('Полупромышленные'), id='prom', on_click=on_do_type),
        Button(text=Const('Мультизональное оборудование'), id='mult', on_click=on_do_type),
        Back(text=Const('Назад'), id='back'),
        Button(text=Const('Назад в меню'), id='menu', on_click=go_to_menu),
        state=CompanySG.cond_type
    ),
    Window(
        Const(text='Выберите модель кондиционера'),
        ScrollingGroup(
            Select(
                Format(text='{item[text]}'),
                items='buttons',
                on_click=on_model_choose,
                item_id_getter=lambda x: x['id'],
                id='s_buttons'
            ),
            id='scroll_models',
            width=5, height=5, hide_on_single_page=True
        ),
        Row(
            Back(text=Const('Назад'), id='back_cond_model'),
            Button(text=Const('Варианта нет в списке'), id='continue_company_model_removed', on_click=lambda c, b, m: m.switch_to(CompanySG.company_model_removed_date)),
        ),
        Button(text=Const('Назад в меню'), id='menu', on_click=go_to_menu),
        state=CompanySG.cond_model,
        getter=models_buttons_getter
    ),
    Window(
        Const(text='Выберите код ошибки'),
        ScrollingGroup(
            Select(
                Format(text='{item[text]}'),
                items='buttons',
                on_click=on_err_code_choose,
                item_id_getter=lambda x: x['id'],
                id='s_buttons_error_codes'
            ),
            id='scroll_error_codes',
            width=5, height=5, hide_on_single_page=True
        ),
        Button(text=Const('Нет нужной ошибки'), id='zapros', on_click=on_no_error_in_list),
        Back(text=Const('Назад'), id='back_from_error_code_select'),
        Button(text=Const('Назад в меню'), id='menu', on_click=go_to_menu),
        state=CompanySG.cond_error_code,
        getter=models_error_codes_getter
    ),
    Window(
        Const('Варианта нет в списке (Модель снята с производства).\n'
              'Пожалуйста, предоставьте следующую информацию.'),
       
        Button(text=Const('Продолжить'), id='continue_company_model_removed', on_click=lambda c, b, m: m.switch_to(CompanySG.company_model_removed_date)),
        Back(Const('Назад'), id='back_from_no_model_company_info'),
        state=CompanySG.no_model_found_company,
    ),
    
    Window(
        Const('Укажите дату покупки оборудования или номер счета'),
        Back(text=Const('Назад'), id='back_company_model_removed_date'),
        TextInput(id='company_model_removed_date_input', on_success=save_purchase_date_handler), 
        state=CompanySG.company_model_removed_date,
    ),
    Window(
        Const('Укажите модель кондиционера. Если есть возможность, пришлите фото.'),
        Back(text=Const('Назад'), id='back_company_model_removed_model_name'),
        MessageInput(save_model_name_handler, content_types=(ContentType.TEXT, ContentType.PHOTO)),
        state=CompanySG.company_model_removed_model_name,
    ),
    Window(
        Const('Если есть возможость пришлите номер штрихкода, фотографию штрихкода.'),
        Button(text=Const('Пропустить'), id='skip_company_model_removed_barcode', on_click=skip_barcode_handler), 
        Back(text=Const('Назад'), id='back_company_model_removed_barcode'),
        MessageInput(save_barcode_handler, content_types=(ContentType.TEXT, ContentType.PHOTO)),  
        state=CompanySG.company_model_removed_barcode,
    ),
    Window(
        Const('Какой код ошибки высвечивается на дисплее кондиционера. Если есть возможность, пришлите фотографию.'),
        Back(text=Const('Назад'), id='back_company_model_removed_error_code'),
        
        MessageInput(send_model_removed_company_request, id='company_model_removed_error_code_input', content_types=(ContentType.TEXT, ContentType.PHOTO)),
        state=CompanySG.company_model_removed_error_code_input,
    ),
    Window( 
        Const('Есть ли у вас еще ошибки, по которым нужна информация?'),
        Row(
            Button(text=Const('Да'), id='more_errors_yes', on_click=lambda c, b, m: m.switch_to(CompanySG.by_myself)),
            Button(text=Const('Нет'), id='more_errors_no', on_click=final_thanks_company),
        ),
        Back(Const('Назад'), id='back_from_ask_more_errors'), 
        state=CompanySG.ask_for_more_errors,
    ),
    Window(
        Const('Отправить запрос по рекламации в сервисный центр'),
        Button(text=Const('Назад в меню'), id='menu', on_click=go_to_menu),
        state=CompanySG.zapros
    )
)

final_consumer_dialog = Dialog(
    Window(
        Const('Если у вас не работает кондиционер, вы можете обратиться в компанию у которой вы приобретали оборудование или оставить заявку в нашем сервисе и мы сами свяжемся с компанией у которой вы приобрели оборудование.'),
        Row(
            Button(Const('Свяжусь сам'), id='contact_myself', on_click=on_contact_myself),
            Next(text=Const('Оставлю заявку вам'), id='leave_request'),
        ),
        Start(text=Const("Назад"), state=ConditionerSG.main, id="back_to_conditioner_main", mode=StartMode.RESET_STACK),
        state=FinalConsumerSG.choice,
    ),
    Window(
        Const('Укажите ваше ФИО, номер телефона для связи и адрес электронной почты.'),
        Back(text=Const('Назад')),
        TextInput(id='final_consumer_info_input', on_success=save_consumer_info_handler),
        state=FinalConsumerSG.info_input,
    ),
    Window(
        Const('Пожалуйста, приложите фото штрих-кода с оборудования, которое вышло из строя.'),
        Back(text=Const('Назад')),
        MessageInput(send_final_consumer_request, content_types=ContentType.PHOTO),
        state=FinalConsumerSG.barcode,
    ),
)


router.include_routers(company_dialog, final_consumer_dialog)
