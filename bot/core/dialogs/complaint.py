import aiohttp
import json
import io
import base64

from aiogram import Router, Bot
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
from bot.core.states import MainSG, ConditionerSG, CompanySG, ComplaintSG, YesDealerSG, NoDealerSG
from web.panel.models import Settings, User

router = Router()

dialog = Dialog(
    Window(
        Const('Вы являетесь нашим дилером?'),
        Row(
            Start(text=Const(text='Да'), state=YesDealerSG.main, id='yes'),
            Start(text=Const(text='Нет'), state=NoDealerSG.main, id='no')
        ),
        Start(text=Const('Назад в меню'), state=ConditionerSG.main, id='go_back'),
        state=ComplaintSG.main
    )
)


async def get_act_data(*args, **kwargs):
    settings = await sync_to_async(Settings.get_solo)()
    act_file = MediaAttachment(
        ContentType.DOCUMENT,
        file_id=MediaId(settings.file_id) if settings.file_id else None,
        path=settings.act.path if not settings.file_id else None
    )
    return {'act': act_file}


async def get_lead_fields():
    async with aiohttp.ClientSession() as session:
        method = "crm.lead.fields.json" # Метод для получения всех полей Лида
        url = config.BITRIX24_WEBHOOK_URL + method

        print(f"Отправляем запрос на: {url}")
        try:
            async with session.post(url) as response:
                response.raise_for_status() # Вызовет ошибку для статусов 4xx/5xx
                data = await response.json()

                if data and 'result' in data:
                    print("Поля Лида успешно получены:")
                    for field_code, field_info in data['result'].items():
                        # Ищем пользовательские поля (UF_CRM_) и наше поле "Файл из Telegram"
                        if field_code.startswith('UF_CRM_') or field_info.get('title') == 'Файл из Telegram':
                            print(f"  Код поля: {field_code}, Название: '{field_info.get('title')}', Тип: '{field_info.get('type')}'")
                            if field_info.get('title') == 'Файл из Telegram' and field_info.get('type') == 'file':
                                print(f"!!! НАЙДЕН НУЖНЫЙ ID ПОЛЯ: {field_code} !!!")
                                return field_code # Возвращаем ID, если нашли
                    print("\nПоле 'Файл из Telegram' типа 'Файл' не найдено среди пользовательских полей.")
                    print("Возможно, оно имеет другое название или тип.")
                elif data and 'error' in data:
                    print(f"Ошибка Битрикс24: {data['error']} - {data['error_description']}")
                else:
                    print(f"Неизвестный ответ: {data}")

        except aiohttp.ClientError as e:
            print(f"Ошибка HTTP-запроса: {e}")
        except json.JSONDecodeError as e:
            print(f"Ошибка декодирования JSON: {e}")
        except Exception as e:
            print(f"Непредвиденная ошибка: {e}")
    return None


async def on_act(message: Message, widget, manager: DialogManager):
    user: User = manager.middleware_data['user']
    bot: Bot = manager.middleware_data['bot']
    manager_id = (await sync_to_async(Settings.get_solo)()).manager_id

    company_name = user.company_name or "Не указано"
    company_address = user.company_address or "Не указано"
    fio = user.fio or "Не указано"
    phone_number = user.phone_number or "Не указано"
    email = user.email or "Не указано"
    object_address = user.data.get('object_address', "Не указано")
    object_name = user.data.get('object_name', "Не указано")
    complaint_text = manager.dialog_data.get('complaint_text', "")

    text = f'''
<b>Новая заявка: монтажная компания, дилер, акт</b>

Название компании: {user.company_name}
Адрес компании: {user.company_address}
ФИО: {user.fio}
Номер телефона: {user.phone_number}
Электронная почта: {user.email}

Адрес объекта: {user.data['object_address']}
Название объекта: {user.data['object_name']}
<i>Обращение:</i>
'''
    await bot.send_message(
        chat_id=manager_id,
        text=text,
        parse_mode=ParseMode.HTML,
    )

    await message.forward(chat_id=manager_id)

    bitrix_payload = {
        "fields": {
            "TITLE": f"Заявка из Telegram: {fio} ({company_name})",
            "NAME": fio.split()[0] if fio and len(fio.split()) > 0 else "",
            "LAST_NAME": fio.split()[-1] if fio and len(fio.split()) > 1 else "",
            "COMPANY_TITLE": company_name,
            "PHONE": [{"VALUE": phone_number, "VALUE_TYPE": "WORK"}],
            "EMAIL": [{"VALUE": email, "VALUE_TYPE": "WORK"}],
            "SOURCE_ID": "TELEGRAM", 
            "COMMENTS": f"Адрес объекта: {object_address}\nНазвание объекта: {object_name}\nОбращение: {complaint_text}",
            "OPENED": "Y",
            "STATUS_ID": "NEW",
        },
        "params": {"REGISTER_SONET_EVENT": "Y"}
    }
    
    file_for_bitrix = None
    if message.photo or message.document:
        try:
            if message.photo:
                file_id = message.photo[-1].file_id 
                file_info = await bot.get_file(file_id)
                file_name = file_info.file_path.split('/')[-1] if file_info.file_path else "photo.jpg"
            else: 
                file_id = message.document.file_id
                file_info = await bot.get_file(file_id)
                file_name = message.document.file_name

            
            file_content_io = io.BytesIO()
            await bot.download_file(file_info.file_path, destination=file_content_io)
            
            encoded_content = base64.b64encode(file_content_io.getvalue()).decode('utf-8')
            
            file_for_bitrix = [file_name, encoded_content]
            print(f"Файл '{file_name}' подготовлен для загрузки в Битрикс24.")

        except Exception as e:
            print(f"!!! ОШИБКА при подготовке файла для Битрикс24: {e}")
            file_for_bitrix = None

    if file_for_bitrix:
        bitrix_payload["fields"]["UF_CRM_1755617658"] = {"fileData": file_for_bitrix}
        print("Файл добавлен в payload Лида.")

    try:
        async with aiohttp.ClientSession() as session:
            method = "crm.lead.add.json"
            lead_creation_url = config.BITRIX24_WEBHOOK_URL + method
            
            async with session.post(lead_creation_url, json=bitrix_payload) as response:
                response.raise_for_status()
                bitrix_result = await response.json()

            if bitrix_result.get('result'):
                lead_id = bitrix_result['result']
                print(f"Лид успешно создан в Битрикс24. ID Лида: {lead_id}")
                if file_for_bitrix:
                    print("Файл успешно прикреплен к лиду через пользовательское поле.")
            elif bitrix_result.get('error'):
                error_desc = bitrix_result.get('error_description', 'Нет описания')
                print(f"Ошибка Битрикс24 при создании Лида: {bitrix_result['error']} - {error_desc}")
            else:
                print(f"Неизвестный ответ от Битрикс24 при создании Лида: {bitrix_result}")

    except aiohttp.ClientError as e:
        print(f"!!! ОШИБКА HTTP-запроса к Битрикс24 при создании Лида: {e}")
    except json.JSONDecodeError as e:
        try:
            error_response_text = await response.text()
        except Exception:
            error_response_text = "Не удалось получить текст ответа"
        print(f"!!! ОШИБКА декодирования JSON ответа от Битрикс24 при создании Лида: {e}. Ответ: {error_response_text}")
    except Exception as e:
        print(f"!!! НЕПРЕДВИДЕННАЯ ОШИБКА при отправке Лида в Битрикс24: {e}") 
    
    await message.answer(f"Ваш запрос в работе. Менеджер сервиса ответит вам в ближайшее время.")
    await manager.start(state=MainSG.main)


async def yes_dealer_done(message: Message, button: Button, dialog_manager: DialogManager, text: str):
    user: User = dialog_manager.middleware_data['user']
    bot: Bot = dialog_manager.middleware_data['bot']
    manager_id = (await sync_to_async(Settings.get_solo)()).manager_id

    brand = dialog_manager.find('brand').get_value()
    what_do = dialog_manager.find('what_do').get_value()
    diagnostic_results = dialog_manager.find('diagnostic_results').get_value()
    date = dialog_manager.find('date').get_value()
    error_code = dialog_manager.find('error_code').get_value() or dialog_manager.find('error_code1').get_value()

    text = f'''
<b>Новая заявка: монтажная компания, дилер, без акта</b>

Название компании: {user.company_name}
Адрес компании: {user.company_address}
ФИО: {user.fio}
Номер телефона: {user.phone_number}
Электронная почта: {user.email}

Адрес объекта: {user.data['object_address']}
Название объекта: {user.data['object_name']}

Марка и модель кондиционера: {brand}
Что делали:
{what_do or 'Ничего'}
Результаты диагностики:
{diagnostic_results or 'Ничего'}
Код ошибки: {error_code}
Дата покупки оборудования или номер счета: {date}
    '''
    await bot.send_message(
        chat_id=manager_id,
        text=text,
        parse_mode=ParseMode.HTML,
    )

    await message.answer(f"Ваш запрос в работе. Менеджер сервиса ответит вам в ближайшее время.")

    await dialog_manager.start(state=MainSG.main, mode=StartMode.RESET_STACK)


yes_dealer_dialog = Dialog(
    Window(
        Const('Заполните акт и отправьте его сюда'),
        DynamicMedia('act'),
        SwitchTo(text=Const('Назад'), state=YesDealerSG.main, id='go_back'),
        MessageInput(on_act, content_types=(ContentType.DOCUMENT,)),
        state=YesDealerSG.yes,
        getter=get_act_data
    ),
    Window(
        Const('У вас есть возможность заполнить и отправить акт о неисправности?'),
        Row(
            SwitchTo(text=Const(text='Да'), state=YesDealerSG.yes, id='yes'),
            Next(text=Const(text='Нет'), id='no')
        ),
        Start(text=Const('Назад в меню'), state=ConditionerSG.main, id='go_back'),
        state=YesDealerSG.main
    ),
    Window(
        Const('Укажите марку и модель кондиционера'),
        Back(text=Const('Назад'), id='go_back'),
        TextInput(id='brand', on_success=Next()),
        state=YesDealerSG.no,
    ),
    Window(
        Const('Если есть возможность, пришлите штрихкод или фото штрихкода'),
        Next(text=Const('Пропустить'), id='next'),
        Back(text=Const('Назад'), id='go_back'),
        MessageInput(Next(), id='code_image', content_types=ContentType.PHOTO),
        state=YesDealerSG.barcode,
    ),
    Window(
        Const('Укажите дату покупки оборудования или номер счета'),
        Back(text=Const('Назад'), id='go_back'),
        TextInput(id='date', on_success=Next()),
        state=YesDealerSG.date,
    ),
    Window(
        Const('Вы проводили первичную диагностику?'),
        Row(
            SwitchTo(text=Const('Да'), state=YesDealerSG.what_do, id='yes'),
            Next(text=Const('Нет'), id='no'),
        ),
        Back(text=Const('Назад'), id='go_back'),
        state=YesDealerSG.diagnostic,
    ),
    Window(
        Const('Какой код ошибки высвечивается на дисплее кондиционера. Если есть возможность, пришлите фотографию.'),
        TextInput(id='error_code', on_success=yes_dealer_done),
        Back(text=Const('Назад'), id='go_back'),
        state=YesDealerSG.error_code,
    ),
    Window(
        Const('Что вы делали?'),
        TextInput(id='what_do', on_success=Next()),
        SwitchTo(text=Const('Назад'), id='go_back', state=YesDealerSG.diagnostic),
        state=YesDealerSG.what_do,
    ),
    Window(
        Const('Какие результаты диагностики?'),
        TextInput(id='diagnostic_results', on_success=Next()),
        SwitchTo(text=Const('Назад'), id='go_back', state=YesDealerSG.diagnostic),
        state=YesDealerSG.diagnostic_results,
    ),
    Window(
        Const('Какой код ошибки высвечивается на дисплее кондиционера. Если есть возможность, пришлите фотографию.'),
        TextInput(id='error_code1', on_success=yes_dealer_done),
        Back(text=Const('Назад'), id='go_back'),
        state=YesDealerSG.error_code1,
    ),
)


async def no_message_handler(message: Message, message_input: MessageInput, manager: DialogManager):
    conditioner_brand = manager.find('input').get_value()
    manager_id = (await sync_to_async(Settings.get_solo)()).manager_id

    user: User = manager.middleware_data['user']
    bot: Bot = manager.middleware_data['bot']

    text = f'''
<b>Новая заявка: монтажная компания, не дилер</b>

Название компании: {user.company_name}
Адрес компании: {user.company_address}
ФИО: {user.fio}
Номер телефона: {user.phone_number}
Электронная почта: {user.email}

Адрес объекта: {user.data['object_address']}
Название объекта: {user.data['object_name']}

Марка и модель кондиционера: {conditioner_brand}
<i>Обращение:</i>
'''
    await bot.send_message(
        chat_id=manager_id,
        text=text,
        parse_mode=ParseMode.HTML,
    )

    await message.forward(chat_id=manager_id)

    await message.answer(f"Ваш запрос в работе. Менеджер сервиса ответит вам в ближайшее время.")
    await manager.start(state=ConditionerSG.main, mode=StartMode.RESET_STACK)


no_dealer_dialog = Dialog(
    Window(
        Const('Укажите марку и модель кондиционера'),
        TextInput(id='input', on_success=Next()),
        Start(text=Const('Назад'), state=ComplaintSG.main, id='go_back'),
        state=NoDealerSG.main
    ),

    Window(
        Const('Отправьте ваш запрос техническому специалисту'),
        MessageInput(no_message_handler),
        Start(text=Const('Назад'), state=ComplaintSG.main, id='go_back'),
        state=NoDealerSG.message
    ),
)

router.include_routers(
    dialog,
    yes_dealer_dialog,
    no_dealer_dialog
)
