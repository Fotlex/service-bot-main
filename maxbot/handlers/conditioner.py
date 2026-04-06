import aiohttp
import base64
import io
from asgiref.sync import sync_to_async

from maxapi import Router, F
from maxapi.types import MessageCreated, MessageCallback, InputMedia, CallbackButton
from maxapi.context import MemoryContext
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder

from maxbot.states import ConditionerSG, CompanySG, FinalConsumerSG, MainSG
from maxbot.keyboards.inline import (
    get_conditioner_main_kb, get_company_choosing_kb, get_skip_object_kb, get_back_menu_kb,
    get_brands_kb, get_cond_type_kb, get_skip_or_menu_kb
)
from config import config

from web.panel.models import Settings, GreeModel, KitanoModel, RoverModel, User

router = Router()

@router.message_callback(F.callback.payload == 'conditioner_main')
async def conditioner_main(event: MessageCallback, context: MemoryContext):
    await context.set_state(ConditionerSG.main)
    await event.message.answer("Кем вы являетесь?", attachments=[get_conditioner_main_kb()])

@router.message_callback(F.callback.payload == 'role_company')
async def role_company(event: MessageCallback, context: MemoryContext, user: User):
    if user.email:
        await context.set_state(CompanySG.object_name)
        await event.message.answer("Укажите адрес и название объекта", attachments=[get_skip_object_kb()])
    else:
        await context.set_state(CompanySG.main)
        await event.message.answer("Укажите название компании", attachments=[get_back_menu_kb()])

@router.message_callback(F.callback.payload == 'role_final_consumer')
async def role_final_consumer(event: MessageCallback, context: MemoryContext):
    await context.set_state(FinalConsumerSG.choice)
    await event.message.answer("Контактные данные (ФИО, телефон, email) или фото штрихкода (для связи с компанией, у которой покупали):", attachments=[get_back_menu_kb()])

@router.message_created(F.message.body.text, CompanySG.main)
async def company_name_input(event: MessageCreated, context: MemoryContext, user: User):
    user.company_name = event.message.body.text
    await sync_to_async(user.save)()
    await context.set_state(CompanySG.address_input)
    await event.message.answer("Укажите адрес компании", attachments=[get_back_menu_kb()])

@router.message_created(F.message.body.text, CompanySG.address_input)
async def company_address_input(event: MessageCreated, context: MemoryContext, user: User):
    user.company_address = event.message.body.text
    await sync_to_async(user.save)()
    await context.set_state(CompanySG.fio_input)
    await event.message.answer("Укажите ваше ФИО", attachments=[get_back_menu_kb()])

@router.message_created(F.message.body.text, CompanySG.fio_input)
async def fio_input(event: MessageCreated, context: MemoryContext, user: User):
    user.fio = event.message.body.text
    await sync_to_async(user.save)()
    await context.set_state(CompanySG.phone_input)
    await event.message.answer("Укажите номер телефона для связи", attachments=[get_back_menu_kb()])

@router.message_created(F.message.body.text, CompanySG.phone_input)
async def phone_input(event: MessageCreated, context: MemoryContext, user: User):
    phone = event.message.body.text
    if len(list(filter(str.isdigit, phone))) != 11:
        await event.message.answer("Номер должен содержать 11 цифр!", attachments=[get_back_menu_kb()])
        return
    user.phone_number = phone
    await sync_to_async(user.save)()
    await context.set_state(CompanySG.email_input)
    await event.message.answer("Укажите адрес электронной почты", attachments=[get_back_menu_kb()])

@router.message_created(F.message.body.text, CompanySG.email_input)
async def email_input(event: MessageCreated, context: MemoryContext, user: User):
    user.email = event.message.body.text
    await sync_to_async(user.save)()
    await context.set_state(CompanySG.object_name)
    await event.message.answer("Укажите адрес и название объекта", attachments=[get_skip_object_kb()])

@router.message_created(F.message.body.text, CompanySG.object_name)
async def object_name_input(event: MessageCreated, context: MemoryContext, user: User):
    user.data['object_info'] = event.message.body.text
    await sync_to_async(user.save)()
    await context.set_state(CompanySG.choosing_myself)
    await event.message.answer("Выберите действие", attachments=[get_company_choosing_kb()])

@router.message_callback(F.callback.payload == 'skip_object', CompanySG.object_name)
async def skip_object(event: MessageCallback, context: MemoryContext, user: User):
    user.data['object_info'] = "Пропущено"
    await sync_to_async(user.save)()
    await context.set_state(CompanySG.choosing_myself)
    await event.message.answer("Выберите", attachments=[get_company_choosing_kb()])

@router.message_callback(F.callback.payload == 'company_choosing_myself')
async def back_to_choosing_myself(event: MessageCallback, context: MemoryContext):
    await context.set_state(CompanySG.choosing_myself)
    await event.message.answer("Выберите", attachments=[get_company_choosing_kb()])

@router.message_callback(F.callback.payload == 'company_by_myself')
async def company_by_myself(event: MessageCallback, context: MemoryContext):
    await context.set_state(CompanySG.by_myself)
    await event.message.answer("Выберите бренд кондиционера", attachments=[get_brands_kb()])

@router.message_callback(F.callback.payload.startswith('brand_'))
async def choose_brand(event: MessageCallback, context: MemoryContext, user: User):
    brand = event.callback.payload.split('_')[1]
    user.data['conditioner'] = brand
    await sync_to_async(user.save)()
    await context.set_state(CompanySG.cond_type)
    await event.message.answer("Выберите тип кондиционера", attachments=[get_cond_type_kb()])

@router.message_callback(F.callback.payload.startswith('type_'))
async def choose_cond_type(event: MessageCallback, context: MemoryContext, user: User):
    c_type = event.callback.payload.split('_')[1]
    user.data['c_type'] = c_type
    await sync_to_async(user.save)()
    await context.set_state(CompanySG.model)
    
    brand = user.data.get('conditioner')
    model_class = GreeModel if brand == 'GREE' else KitanoModel if brand == 'KITANO' else RoverModel
    models = await sync_to_async(list)(model_class.objects.filter(type=c_type))
    
    builder = InlineKeyboardBuilder()
    for m in models:
        builder.row(CallbackButton(text=m.model, payload=f"model_{m.id}"))
    
    builder.row(CallbackButton(text="Нет нужной модели в списке", payload="not_found_model"))
    builder.row(CallbackButton(text="Назад", payload="company_by_myself"))
    
    await event.message.answer("Выберите модель кондиционера", attachments=[builder.as_markup()])

@router.message_callback(F.callback.payload.startswith('model_'))
async def choose_model(event: MessageCallback, context: MemoryContext, user: User):
    model_id = event.callback.payload.split('_')[1]
    user.data['model_id'] = model_id
    await sync_to_async(user.save)()
    await context.set_state(CompanySG.error_code)
    
    brand = user.data.get('conditioner')
    model_class = GreeModel if brand == 'GREE' else KitanoModel if brand == 'KITANO' else RoverModel
    
    model = await sync_to_async(model_class.objects.get)(id=model_id)
    error_codes = await sync_to_async(list)(model.error_codes.all())
    
    builder = InlineKeyboardBuilder()
    for e in error_codes:
        builder.row(CallbackButton(text=e.code, payload=f"err_{e.id}"))
    builder.row(CallbackButton(text="Нет ошибки в списке", payload="not_found_error"))
    builder.row(CallbackButton(text="Назад", payload=f"type_{user.data['c_type']}"))
    
    await event.message.answer("Выберите код ошибки", attachments=[builder.as_markup()])

@router.message_callback(F.callback.payload.startswith('err_'))
async def choose_err_code(event: MessageCallback, context: MemoryContext, user: User):
    if event.callback.payload == 'not_found_error':
        await event.answer(new_text="Так как в списке нет нужной ошибки, мы предлагаем вам отправить запрос в сервисный центр")
        await context.set_state(ConditionerSG.main)
        await event.message.answer("Кем вы являетесь?", attachments=[get_conditioner_main_kb()])
        return
        
    err_id = event.callback.payload.split('_')[1]
    brand = user.data.get('conditioner')
    model_class = GreeModel if brand == 'GREE' else KitanoModel if brand == 'KITANO' else RoverModel
        
    model = await sync_to_async(model_class.objects.get)(id=user.data['model_id'])
    err_code = await sync_to_async(model.error_codes.get)(id=err_id)
    
    await event.message.answer(
        text=f"Инструкция для ошибки {err_code.code}:",
        attachments=[InputMedia(path=err_code.manual.path)]
    )
    
    await context.set_state(CompanySG.ask_for_more_errors)
    builder = InlineKeyboardBuilder()
    builder.row(CallbackButton(text='В меню', payload='main_menu'))
    await event.message.answer("Если есть еще вопросы, вернитесь в главное меню", attachments=[builder.as_markup()])


@router.message_created(F.message.body, FinalConsumerSG.choice)
async def handle_final_consumer(event: MessageCreated, context: MemoryContext, user: User):
    consumer_info = event.message.body.text or "Не указано"
    
    file_for_bitrix = None
    if event.message.body.attachments:
        att = event.message.body.attachments[0]
        if hasattr(att, 'payload') and hasattr(att.payload, 'url'):
            file_url = att.payload.url
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(file_url) as resp:
                        if resp.status == 200:
                            content = await resp.read()
                            encoded_content = base64.b64encode(content).decode('utf-8')
                            file_for_bitrix = ["barcode.jpg", encoded_content]
            except Exception as e:
                print(f"Error fetching MAX media file: {e}")

    fio_for_title = consumer_info.split(',')[0].strip() or "Не указано"
    text_to_manager = f'''<b>Новая заявка: Конечный потребитель</b>
Контактные данные:
{consumer_info}
Запрос: Пользователь оставил заявку...'''
    
    bitrix_payload = {
        "fields": {
            "TITLE": f"Заявка от Конечного потребителя: {fio_for_title}",
            "COMMENTS": text_to_manager,
            "OPENED": "Y",
            "STATUS_ID": "NEW",
            "UF_CRM_1755788093": str(user.id),
            "UF_CRM_1760933453": "Сервис"
        },
        "params": {"REGISTER_SONET_EVENT": "Y"}
    }
    if file_for_bitrix:
        bitrix_payload["fields"]["UF_CRM_1755617658"] = {"fileData": file_for_bitrix}

    try:
        async with aiohttp.ClientSession() as session:
            url = config.BITRIX24_WEBHOOK_URL + "crm.lead.add.json"
            async with session.post(url, json=bitrix_payload) as response:
                response.raise_for_status()
                res = await response.json()
                if res.get('result'):
                    user.bitrix_lead_id = res['result']
                    await sync_to_async(user.save)()
    except Exception as e:
        print(e)
        
    await event.message.answer("Спасибо за обращение в нашу компанию, ваша заявка будет передана в ближайшее время.", attachments=[get_back_menu_kb()])
    await context.set_state(ConditionerSG.main)
    


async def send_missing_model_to_bitrix(user: User):
    text_to_manager = f'''<b>Новая заявка: Компания - Модель снята с производства</b>
Название компании: {user.company_name}
ФИО: {user.fio}
Номер телефона: {user.phone_number}
Электронная почта: {user.email}
Адрес и название объекта: {user.data.get('object_info', 'Не указано')}

Дата покупки: {user.data.get('missing_date', 'Не указано')}
Указанная модель: {user.data.get('missing_model', 'Не указано')}
Штрихкод: {user.data.get('missing_barcode', 'Не указано')}
Код ошибки: {user.data.get('missing_error', 'Не указано')}
'''
    
    payload = {
        "fields": {
            "TITLE": f"Запрос (модели нет в списке) - {user.company_name}",
            "NAME": user.fio.split()[0] if user.fio else "",
            "COMPANY_TITLE": user.company_name,
            "PHONE":[{"VALUE": user.phone_number, "VALUE_TYPE": "WORK"}],
            "EMAIL":[{"VALUE": user.email, "VALUE_TYPE": "WORK"}],
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
            url = config.BITRIX24_WEBHOOK_URL + "crm.lead.add.json"
            async with session.post(url, json=payload) as response:
                res = await response.json()
                if res.get('result'):
                    user.bitrix_lead_id = res['result']
                    await sync_to_async(user.save)()
    except Exception as e:
        print(f"Error Missing Model Bitrix: {e}")

@router.message_callback(F.callback.payload == 'not_found_model')
async def model_missing_start(event: MessageCallback, context: MemoryContext):
    await context.set_state(CompanySG.missing_date) 
    await event.message.answer("Укажите дату покупки оборудования или номер счета:", attachments=[get_skip_or_menu_kb()])

@router.message_created(F.message.body, CompanySG.missing_date)
async def process_missing_date(event: MessageCreated, context: MemoryContext, user: User):
    user.data['missing_date'] = event.message.body.text or "Пропущено"
    await sync_to_async(user.save)()
    await context.set_state(CompanySG.missing_model)
    await event.message.answer("Какую модель вы искали?", attachments=[get_skip_or_menu_kb()])

@router.message_created(F.message.body, CompanySG.missing_model)
async def process_missing_model(event: MessageCreated, context: MemoryContext, user: User):
    user.data['missing_model'] = event.message.body.text or "Пропущено"
    await sync_to_async(user.save)()
    await context.set_state(CompanySG.missing_barcode)
    await event.message.answer("Пришлите номер или фотографию штрихкода:", attachments=[get_skip_or_menu_kb()])

@router.message_created(F.message.body, CompanySG.missing_barcode)
async def process_missing_barcode(event: MessageCreated, context: MemoryContext, user: User):
    user.data['missing_barcode'] = event.message.body.text or "Прикреплено фото"
    await sync_to_async(user.save)()
    await context.set_state(CompanySG.missing_error)
    await event.message.answer("Какой код ошибки высвечивается на дисплее? (Можете прислать фото):", attachments=[get_skip_or_menu_kb()])

@router.message_created(F.message.body, CompanySG.missing_error)
async def process_missing_error(event: MessageCreated, context: MemoryContext, user: User):
    user.data['missing_error'] = event.message.body.text or "Прикреплено фото"
    await sync_to_async(user.save)()
    
    await send_missing_model_to_bitrix(user)
    
    await event.message.answer(
        "Ваш запрос принят. Менеджер сервиса ответит вам в ближайшее время.",
        attachments=[get_back_menu_kb()]
    )
    await context.set_state(ConditionerSG.main)

@router.message_callback(F.callback.payload == 'skip_missing_step')
async def skip_missing_step_handler(event: MessageCallback, context: MemoryContext, user: User):
    current_state = await context.get_state()
    
    if current_state == CompanySG.missing_date:
        user.data['missing_date'] = "Пропущено"
        await sync_to_async(user.save)()
        await context.set_state(CompanySG.missing_model)
        await event.message.answer("Какую модель вы искали?", attachments=[get_skip_or_menu_kb()])
        
    elif current_state == CompanySG.missing_model:
        user.data['missing_model'] = "Пропущено"
        await sync_to_async(user.save)()
        await context.set_state(CompanySG.missing_barcode)
        await event.message.answer("Пришлите номер или фотографию штрихкода:", attachments=[get_skip_or_menu_kb()])
        
    elif current_state == CompanySG.missing_barcode:
        user.data['missing_barcode'] = "Пропущено"
        await sync_to_async(user.save)()
        await context.set_state(CompanySG.missing_error)
        await event.message.answer("Какой код ошибки высвечивается на дисплее? (Можете прислать фото):", attachments=[get_skip_or_menu_kb()])
        
    elif current_state == CompanySG.missing_error:
        user.data['missing_error'] = "Пропущено"
        await sync_to_async(user.save)()
        await send_missing_model_to_bitrix(user)
        await event.message.answer(
            "Ваш запрос принят. Менеджер сервиса ответит вам в ближайшее время.",
            attachments=[get_back_menu_kb()]
        )
        await context.set_state(ConditionerSG.main)
