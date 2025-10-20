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
        method = "crm.lead.fields.json" 
        url = config.BITRIX24_WEBHOOK_URL + method

        print(f"Отправляем запрос на: {url}")
        try:
            async with session.post(url) as response:
                response.raise_for_status() 
                data = await response.json()

                if data and 'result' in data:
                    print("Поля Лида успешно получены:")
                    for field_code, field_info in data['result'].items():
                      
                        if field_code.startswith('UF_CRM_') or field_info.get('title') == 'Файл из Telegram':
                            print(f"  Код поля: {field_code}, Название: '{field_info.get('title')}', Тип: '{field_info.get('type')}'")
                            if field_info.get('title') == 'Файл из Telegram' and field_info.get('type') == 'file':
                                print(f"!!! НАЙДЕН НУЖНЫЙ ID ПОЛЯ: {field_code} !!!")
                                return field_code 
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
    object_info = user.data.get('object_info', "Не указано")
    complaint_text = manager.dialog_data.get('complaint_text', "")

    text = f'''
<b>Новая заявка: монтажная компания, дилер, акт</b>

Название компании: {user.company_name}
Адрес компании: {user.company_address}
ФИО: {user.fio}
Номер телефона: {user.phone_number}
Электронная почта: {user.email}

Адрес и название объекта: {object_info}
<i>Обращение:</i>
'''
    user_id_to_reply = user.id

    reply_callback_data = f"answer_user:{user_id_to_reply}"

    await bot.send_message(
        chat_id=manager_id,
        text=text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Ответить на вопрос", callback_data=reply_callback_data)],
        ]),
        parse_mode=ParseMode.HTML,
    )


    await message.forward(chat_id=manager_id)

    bitrix_payload = {
        "fields": {
            "TITLE": f"Заявка из Telegram: Дилер, Акт о неисправности",
            "NAME": fio.split()[0] if fio and len(fio.split()) > 0 else "",
            "LAST_NAME": fio.split()[-1] if fio and len(fio.split()) > 1 else "",
            "COMPANY_TITLE": company_name,
            "PHONE": [{"VALUE": phone_number, "VALUE_TYPE": "WORK"}],
            "EMAIL": [{"VALUE": email, "VALUE_TYPE": "WORK"}],
            "SOURCE_ID": "TELEGRAM", 
            "COMMENTS": f'''
<b>Новая заявка: монтажная компания, дилер, акт</b>

Название компании: {user.company_name}
Адрес компании: {user.company_address}
ФИО: {user.fio}
Номер телефона: {user.phone_number}
Электронная почта: {user.email}

Адрес и название объекта: {object_info}
<i>Обращение:</i>
''',
            "OPENED": "Y",
            "STATUS_ID": "NEW",
            "UF_CRM_1755788093": str(user.id),
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
                
                user.bitrix_lead_id = lead_id
                await user.asave()
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
    await manager.start(state=MainSG.main, mode=StartMode.RESET_STACK, show_mode=ShowMode.SEND)


async def on_user_question(message: Message, message_input: MessageInput, manager: DialogManager):
    user_question_text = message.text
    user: User = manager.middleware_data['user']
    bot: Bot = manager.middleware_data['bot']
    manager_id = (await sync_to_async(Settings.get_solo)()).manager_id

    if not user.bitrix_lead_id:
        await message.answer("Извините, не могу найти связанный Лид для вашего вопроса. Пожалуйста, начните новую заявку.")
        await manager.start(MainSG.main, mode=StartMode.RESET_STACK, show_mode=ShowMode.SEND)
        return

    try:
        async with aiohttp.ClientSession() as session:
            add_comment_url = f"{config.BITRIX24_WEBHOOK_URL}crm.timeline.comment.add"
            comment_payload = {
                "fields": {
                    "ENTITY_ID": user.bitrix_lead_id,
                    "ENTITY_TYPE": "lead",
                    "COMMENT": f"Вопрос от пользователя Telegram ({user.fio}): {user_question_text}"
                }
            }
            print(f"Отправляем комментарий в Битрикс24: {comment_payload}")
            async with session.post(add_comment_url, json=comment_payload) as comment_response:
                comment_response.raise_for_status()
                comment_result = await comment_response.json()
                if comment_result.get('result'):
                    print(f"Вопрос пользователя успешно добавлен к Лиду {user.bitrix_lead_id} как комментарий.")
                    await message.answer("Ваш вопрос передан менеджеру. Ожидайте ответа.")

                    if manager_id and manager_id != -1:
                        user_id_to_reply = user.id
                        
                        reply_callback_data = f"answer_user:{user_id_to_reply}"

                        await bot.send_message(
                            chat_id=manager_id,
                            text=f"<b>Новый вопрос от пользователя (ID:{user.id}, Лид ID:{user.bitrix_lead_id})</b>\n\n<i>Вопрос:</i>",
                            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                                [InlineKeyboardButton(text="Ответить на вопрос", callback_data=reply_callback_data)],
                            ]),
                            parse_mode=ParseMode.HTML,
                        )

                        await message.forward(chat_id=manager_id)
                    else:
                        print("Manager ID is not set or invalid. Cannot forward user question.")


                else:
                    error_desc = comment_result.get('error_description', 'Нет описания')
                    print(f"Ошибка Битрикс24 при добавлении комментария пользователя: {comment_result['error']} - {error_desc}")
                    await message.answer("Произошла ошибка при отправке вашего вопроса. Попробуйте позже.")

    except Exception as e:
        print(f"!!! НЕПРЕДВИДЕННАЯ ОШИБКА при добавлении комментария пользователя в Битрикс24: {e}")
        await message.answer("Произошла непредвиденная ошибка. Попробуйте позже.")

    await manager.start(MainSG.main, mode=StartMode.RESET_STACK, show_mode=ShowMode.SEND)



global_manager_id = None
async def init_global_manager_id():
    global global_manager_id
    if global_manager_id is None:
        try:
            settings = await sync_to_async(Settings.objects.get)(pk=1)
            global_manager_id = settings.manager_id
            print(f"Global manager ID initialized: {global_manager_id}")
        except Settings.DoesNotExist:
            print("Settings object not found. Please create one in Django admin.")
            global_manager_id = -1 
        except Exception as e:
            print(f"Error initializing global manager ID: {e}. Ensure manager_id is set.")
            global_manager_id = -1 


@router.callback_query(F.data.startswith('answer_user:'))
async def ask_manager_for_reply(callback: CallbackQuery, dialog_manager: DialogManager):
    user_id = int(callback.data.split(':')[1])
    parts = callback.data.split(':')
    
    is_final_reply = "is_final_reply=1" in parts
    
    await callback.message.edit_reply_markup(reply_markup=None)
    
    await dialog_manager.start(
        state=ManagerReplySG.text_input, 
        data={'user_id_to_reply': user_id, 'is_final_reply': is_final_reply,},
        mode=StartMode.RESET_STACK,
        show_mode=ShowMode.SEND
    )
    await callback.answer()




async def handle_manager_reply_dialog(message: Message, widget: TextInput, dialog_manager: DialogManager, text: str):
    start_data = dialog_manager.start_data
    original_telegram_user_id = start_data.get('user_id_to_reply')
    
    is_final_reply = start_data.get('is_final_reply', False)
    
    manager_id = message.from_user.id
    bot = dialog_manager.middleware_data['bot']

    if not original_telegram_user_id:
        await message.answer("Произошла ошибка: не найден ID пользователя для ответа. Пожалуйста, начните снова.")
        await dialog_manager.done()
        return

    try:
        user: User = await sync_to_async(User.objects.get)(id=original_telegram_user_id)
        if not user.bitrix_lead_id:
            await bot.send_message(manager_id, "Ошибка: не удалось найти связанный Лид для этого пользователя.")
            await dialog_manager.done()
            return

        lead_id = user.bitrix_lead_id
        manager_reply_text = text 

        if manager_reply_text:
            try:
                async with aiohttp.ClientSession() as session:
                    add_comment_url = f"{config.BITRIX24_WEBHOOK_URL}crm.timeline.comment.add" 
                    comment_payload = {
                        "fields": {
                            "ENTITY_ID": lead_id,
                            "ENTITY_TYPE": "lead",
                            "COMMENT": f"Ответ менеджера в Telegram: {manager_reply_text}"
                        }
                    }
                    print(f"Отправляем комментарий в Битрикс24 (таймлайн): {comment_payload}")
                    async with session.post(add_comment_url, json=comment_payload) as comment_response:
                        comment_response.raise_for_status()
                        comment_result = await comment_response.json()
                        if comment_result.get('result'):
                            print(f"Текстовый ответ менеджера успешно добавлен к Лиду {lead_id} как комментарий.")
                        else:
                            error_desc = comment_result.get('error_description', 'Нет описания')
                            print(f"Ошибка Битрикс24 при добавлении текстового комментария менеджера: {comment_result['error']} - {error_desc}")
            except Exception as e:
                print(f"!!! ОШИБКА при добавлении текстового комментария менеджера в Битрикс24: {e}")
        keyboard = None
        if is_final_reply:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="Понятно", callback_data="reply_understood"),
                ]
            ])
        else:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="Понятно", callback_data="reply_understood"),
                    InlineKeyboardButton(text="Задать еще вопрос", callback_data="reply_ask_more")
                ]
            ])

        await bot.send_message(
            chat_id=original_telegram_user_id,
            text=f"Ответ от менеджера:\n\n{manager_reply_text}",
            reply_markup=keyboard
        )

        await bot.send_message(manager_id, f"Ответ отправлен пользователю {original_telegram_user_id} и сохранен в Лиде {lead_id}.")
        
    except Exception as e:
        print(f"!!! ГЛОБАЛЬНАЯ ОШИБКА в handle_manager_reply_dialog для пользователя {original_telegram_user_id}: {e}")
        await message.answer(f"Произошла непредвиденная ошибка при обработке вашего ответа: {e}")
    finally:
        await dialog_manager.done()


@router.callback_query(F.data == "reply_ask_more")
async def process_ask_more_callback(callback: CallbackQuery, dialog_manager: DialogManager):

    await dialog_manager.start(state=QuestionSG.question_text, mode=StartMode.RESET_STACK)
    await callback.answer()


@router.callback_query(F.data == "reply_understood")
async def process_understood_callback(callback: CallbackQuery, dialog_manager: DialogManager, user: User):
    user_id = callback.from_user.id
    bot: Bot = dialog_manager.middleware_data['bot']
    manager_id = global_manager_id

    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer("Рад был помочь! Если возникнут новые вопросы, обращайтесь.")
    await callback.answer()


    if user.bitrix_lead_id:
        lead_id = user.bitrix_lead_id
        
        user.bitrix_lead_id = None
        await user.asave()
        
    try:
        await dialog_manager.start(state=MainSG.main, mode=StartMode.RESET_STACK, show_mode=ShowMode.SEND)
    except Exception as e: 
        print(f"Ошибка при попытке перейти в MainSG.main для пользователя {user_id}: {e}")
        


async def yes_dealer_done(message: Message, widget: TextInput, dialog_manager: DialogManager, text: str):
    user: User = dialog_manager.middleware_data['user']
    bot: Bot = dialog_manager.middleware_data['bot']
    manager_id = (await sync_to_async(Settings.get_solo)()).manager_id

    brand = dialog_manager.find('brand').get_value()
    what_do = dialog_manager.find('what_do').get_value()
    diagnostic_results = dialog_manager.find('diagnostic_results').get_value()
    date = dialog_manager.find('date').get_value()
    error_code = dialog_manager.find('error_code').get_value() or dialog_manager.find('error_code1').get_value()

    company_name = user.company_name or "Не указано"
    company_address = user.company_address or "Не указано"
    fio = user.fio or "Не указано"
    phone_number = user.phone_number or "Не указано"
    email = user.email or "Не указано"
    object_info = user.data.get('object_info', "Не указано")
    
    text = f'''
<b>Новая заявка: монтажная компания, дилер, без акта</b>

Название компании: {user.company_name}
Адрес компании: {user.company_address}
ФИО: {user.fio}
Номер телефона: {user.phone_number}
Электронная почта: {user.email}

Адрес и название объекта: {object_info}

Марка и модель кондиционера: {brand}
Что делали:
{what_do or 'Ничего'}
Результаты диагностики:
{diagnostic_results or 'Ничего'}
Код ошибки: {error_code}
Дата покупки оборудования или номер счета: {date}
    '''
    reply_callback_data = f"answer_user:{user.id}"
    
    await bot.send_message(
        chat_id=manager_id,
        text=text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Ответить на вопрос", callback_data=reply_callback_data)],
        ]),
        parse_mode=ParseMode.HTML,
    )

    bitrix_payload = {
        "fields": {
            "TITLE": f"Заявка из Telegram: Дилер, Без акта",
            "NAME": fio.split()[0] if fio and len(fio.split()) > 0 else "",
            "LAST_NAME": fio.split()[-1] if fio and len(fio.split()) > 1 else "",
            "COMPANY_TITLE": company_name,
            "PHONE": [{"VALUE": phone_number, "VALUE_TYPE": "WORK"}],
            "EMAIL": [{"VALUE": email, "VALUE_TYPE": "WORK"}],
            "SOURCE_ID": "TELEGRAM", 
            "COMMENTS": f'''
<b>Новая заявка: монтажная компания, дилер, без акта</b>

Название компании: {user.company_name}
Адрес компании: {user.company_address}
ФИО: {user.fio}
Номер телефона: {user.phone_number}
Электронная почта: {user.email}

Адрес и название объекта: {object_info}

Марка и модель кондиционера: {brand}
Что делали:
{what_do or 'Ничего'}
Результаты диагностики:
{diagnostic_results or 'Ничего'}
Код ошибки: {error_code}
Дата покупки оборудования или номер счета: {date}
    ''',
            "OPENED": "Y",
            "STATUS_ID": "NEW",
            "UF_CRM_1755788093": str(user.id),
            "UF_CRM_1760933453": "Сервис"
        },
        "params": {"REGISTER_SONET_EVENT": "Y"}
    }
    
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
                
                user.bitrix_lead_id = lead_id
                await user.asave()
                
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

    await dialog_manager.start(state=MainSG.main, mode=StartMode.RESET_STACK, show_mode=ShowMode.SEND)


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
        Const('Если есть возможость пришлите номер штрихкода, фотографию штрихкода.'),
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


async def send_service_center_request(callback: CallbackQuery, button: Button, manager: DialogManager):
    user: User = manager.middleware_data['user']
    bot: Bot = manager.middleware_data['bot']
    manager_id = global_manager_id

    company_name = user.company_name or "Не указано"
    company_address = user.company_address or "Не указано"
    fio = user.fio or "Не указано"
    phone_number = user.phone_number or "Не указано"
    email = user.email or "Не указано"
    object_info = user.data.get('object_info', "Не указано")

    brand_input = manager.find('brand').get_value()
    if not brand_input:
        brand_input = "Не указано (нет в списке моделей)"

    text_to_manager = f'''
<b>Новая заявка: Дилер - Запрос в сервисный центр (модель не найдена)</b>

Название компании: {user.company_name}
Адрес компании: {user.company_address}
ФИО: {user.fio}
Номер телефона: {user.phone_number}
Электронная почта: {user.email}

Адрес и название объекта: {object_info}

Марка/модель (которую искали): {brand_input}
<i>Запрос: Модель не найдена в списке, требуется отправить запрос по рекламации в сервисный центр.</i>
'''
    if manager_id != -1:
        await bot.send_message(
            chat_id=manager_id,
            text=text_to_manager,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Ответить на вопрос", callback_data=f"answer_user:{user.id}")],
            ]),
        )
    else:
        print("Manager ID is not set or invalid. Cannot send message to manager (service center request).")

    await callback.message.answer(f"Ваш запрос для сервисного центра принят. Менеджер свяжется с вами.")
    await callback.answer()


    bitrix_payload = {
        "fields": {
            "TITLE": f"Запрос СЦ (модель нет в списке)",
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
                print(f"Лид для запроса в СЦ успешно создан. ID Лида: {lead_id}")
                user.bitrix_lead_id = lead_id 
                await user.asave()
            elif bitrix_result.get('error'):
                error_desc = bitrix_result.get('error_description', 'Нет описания')
                print(f"Ошибка Битрикс24 при создании Лида для запроса в СЦ: {bitrix_result['error']} - {error_desc}")
            else:
                print(f"Неизвестный ответ от Битрикс24 при создании Лида для запроса в СЦ: {bitrix_result}")
    except Exception as e:
        print(f"!!! НЕПРЕДВИДЕННАЯ ОШИБКА при отправке Лида в Битрикс24 (запрос СЦ): {e}")

    await manager.start(state=MainSG.main, mode=StartMode.RESET_STACK, show_mode=ShowMode.SEND) 


async def no_message_handler(message: Message, message_input: MessageInput, manager: DialogManager):
    conditioner_brand = manager.find('input').get_value()
    manager_id = (await sync_to_async(Settings.get_solo)()).manager_id

    user: User = manager.middleware_data['user']
    bot: Bot = manager.middleware_data['bot']

    company_name = user.company_name or "Не указано"
    company_address = user.company_address or "Не указано"
    fio = user.fio or "Не указано"
    phone_number = user.phone_number or "Не указано"
    email = user.email or "Не указано"
    object_info = user.data.get('object_info', "Не указано")
    
    text = f'''
<b>Новая заявка: монтажная компания, не дилер</b>

Название компании: {user.company_name}
Адрес компании: {user.company_address}
ФИО: {user.fio}
Номер телефона: {user.phone_number}
Электронная почта: {user.email}

Адрес и название объекта: {object_info}

Марка и модель кондиционера: {conditioner_brand}
<i>Обращение: {message.text}</i>
'''
    await bot.send_message(
        chat_id=manager_id,
        text=text,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Ответить на вопрос", callback_data=f"answer_user:{user.id}:is_final_reply=1")],
            ]),
    )

    bitrix_payload = {
        "fields": {
            "TITLE": f"Заявка из Telegram: Не дилер",
            "NAME": fio.split()[0] if fio and len(fio.split()) > 0 else "",
            "LAST_NAME": fio.split()[-1] if fio and len(fio.split()) > 1 else "",
            "COMPANY_TITLE": company_name,
            "PHONE": [{"VALUE": phone_number, "VALUE_TYPE": "WORK"}],
            "EMAIL": [{"VALUE": email, "VALUE_TYPE": "WORK"}],
            "SOURCE_ID": "TELEGRAM", 
            "COMMENTS": f'''
<b>Новая заявка: монтажная компания, не дилер</b>

Название компании: {user.company_name}
Адрес компании: {user.company_address}
ФИО: {user.fio}
Номер телефона: {user.phone_number}
Электронная почта: {user.email}

Адрес и название объекта: {object_info}

Марка и модель кондиционера: {conditioner_brand}
<i>Обращение: {message.text}</i>
''',
            "OPENED": "Y",
            "STATUS_ID": "NEW",
            "UF_CRM_1755788093": str(user.id),
            "UF_CRM_1760933453": "Сервис"
        },
        "params": {"REGISTER_SONET_EVENT": "Y"}
    }
    
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
                
                user.bitrix_lead_id = lead_id
                await user.asave()
                
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

manager_reply_dialog = Dialog(
    Window(
        Const("Введите ответ для пользователя:"),
        TextInput(
            id='manager_reply_text',
            on_success=handle_manager_reply_dialog
        ),
        state=ManagerReplySG.text_input,
    )
)

question_dialog = Dialog(
    Window(
        Const("Пожалуйста, напишите ваш вопрос в сообщении ниже."),
        MessageInput(on_user_question),
        state=QuestionSG.question_text
    )
)



router.include_routers(
    dialog,
    yes_dealer_dialog,
    no_dealer_dialog,
    manager_reply_dialog,
    question_dialog,
)
