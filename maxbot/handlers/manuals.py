import aiohttp
from asgiref.sync import sync_to_async

from maxapi import F, Router
from maxapi.types import MessageCreated, MessageCallback, InputMedia
from maxapi.context import MemoryContext

from web.panel.models import (
    AllText, User, Settings,
    GreeModel, KitanoModel, RoverModel,
    GreeManual, KitanoManual, RoverManual
)
from maxbot.states import ManualsSG
from config import config

from maxbot.keyboards.inline import (
    get_main_keyboard, 
    get_manual_brands_keyboard,
    get_conditioner_types_keyboard,
    get_dynamic_models_keyboard,
    get_manuals_list_keyboard
)

router = Router()

@router.message_callback(F.callback.payload.in_(["action_manuals", "manuals_brand"]))
async def start_manuals_flow(event: MessageCallback, context: MemoryContext):
    await context.set_state(ManualsSG.brand)
    
    text_obj = await sync_to_async(AllText.objects.first)()
    msg_text = text_obj.select_brand if text_obj and text_obj.select_brand else "Выберите бренд оборудования:"
    
    await event.message.edit(
        text=msg_text,
        attachments=[get_manual_brands_keyboard()]
    )

@router.message_callback(F.callback.payload.startswith("man_brand_"))
async def choose_manual_brand(event: MessageCallback, context: MemoryContext, user: User):
    brand = event.callback.payload.split("_")[-1].upper()
    
    user.data['manual_brand'] = brand
    await sync_to_async(user.save)(update_fields=['data'])
    
    await context.set_state(ManualsSG.type)
    
    text_obj = await sync_to_async(AllText.objects.first)()
    msg_text = text_obj.select_type if text_obj and text_obj.select_type else "Выберите тип оборудования:"
    
    await event.message.edit(
        text=msg_text, 
        attachments=[get_conditioner_types_keyboard()]
    )

@router.message_callback(F.callback.payload.startswith("man_type_"))
async def choose_manual_type(event: MessageCallback, context: MemoryContext, user: User):
    c_type = event.callback.payload.split("_")[-1]
    user.data['manual_type'] = c_type
    brand = user.data.get('manual_brand')
    await sync_to_async(user.save)(update_fields=['data'])
    
    models_qs = []
    if brand == 'GREE':
        models_qs = await sync_to_async(list)(GreeModel.objects.filter(type=c_type))
    elif brand == 'KITANO':
        models_qs = await sync_to_async(list)(KitanoModel.objects.filter(type=c_type))
    elif brand == 'ROVER':
        models_qs = await sync_to_async(list)(RoverModel.objects.filter(type=c_type))
        
    await context.set_state(ManualsSG.model)
    
    text_obj = await sync_to_async(AllText.objects.first)()
    msg_text = text_obj.select_series if text_obj and text_obj.select_series else "Выберите серию/модель:"
    
    await event.message.edit(
        text=msg_text,
        attachments=[get_dynamic_models_keyboard(models_qs)]
    )

@router.message_callback(F.callback.payload.startswith("man_model_"))
async def choose_specific_manual(event: MessageCallback, context: MemoryContext, user: User):
    model_id = int(event.callback.payload.split("_")[-1])
    user.data['manual_model_id'] = model_id
    brand = user.data.get('manual_brand')
    await sync_to_async(user.save)(update_fields=['data'])

    manuals_list = []
    model_name = "Неизвестно"
    
    if brand == 'GREE':
        model_instance = await sync_to_async(GreeModel.objects.prefetch_related('manuals').get)(id=model_id)
        manuals_list = await sync_to_async(list)(model_instance.manuals.all())
        model_name = model_instance.model
    elif brand == 'KITANO':
        model_instance = await sync_to_async(KitanoModel.objects.prefetch_related('manuals').get)(id=model_id)
        manuals_list = await sync_to_async(list)(model_instance.manuals.all())
        model_name = model_instance.model
    elif brand == 'ROVER':
        model_instance = await sync_to_async(RoverModel.objects.prefetch_related('manuals').get)(id=model_id)
        manuals_list = await sync_to_async(list)(model_instance.manuals.all())
        model_name = model_instance.model

    msg_text = f"Модель: {model_name}\nВыберите инструкцию для скачивания:" if manuals_list else f"К модели {model_name} инструкции пока не загружены."

    await event.message.edit(
        text=msg_text,
        attachments=[get_manuals_list_keyboard(manuals_list)]
    )

@router.message_callback(F.callback.payload.startswith("download_man_"))
async def send_manual_file(event: MessageCallback, context: MemoryContext, user: User):
    manual_id = int(event.callback.payload.split("_")[-1])
    brand = user.data.get('manual_brand')
    
    manual_obj = None
    try:
        if brand == 'GREE':
            manual_obj = await sync_to_async(GreeManual.objects.get)(id=manual_id)
        elif brand == 'KITANO':
            manual_obj = await sync_to_async(KitanoManual.objects.get)(id=manual_id)
        elif brand == 'ROVER':
            manual_obj = await sync_to_async(RoverManual.objects.get)(id=manual_id)
    except Exception as e:
        print(f"Manual not found: {e}")

    if manual_obj and manual_obj.file:
        file_title = getattr(manual_obj, 'title', 'Инструкция')
        await event.message.answer(
            text=f"Файл: {file_title}",
            attachments=[InputMedia(path=manual_obj.file.path)] 
        )
    else:
        await event.message.answer(text="К сожалению, файл на сервере не найден.")

@router.message_callback(F.callback.payload.in_(["not_found_model", "not_found_manual"]))
async def missing_data_request_date(event: MessageCallback, context: MemoryContext):
    await context.set_state(ManualsSG.missing_date)
    
    text_obj = await sync_to_async(AllText.objects.first)()
    msg_text = text_obj.purchase_date_invoice if text_obj and text_obj.purchase_date_invoice else "Укажите дату покупки оборудования или номер счета:"
    
    await event.message.edit(
        text=msg_text,
        attachments=[get_manual_brands_keyboard()]
    )

@router.message_created(F.message.body, ManualsSG.missing_date)
async def process_missing_date(event: MessageCreated, context: MemoryContext, user: User):
    user.data['purchase_date'] = event.message.body.text
    await sync_to_async(user.save)(update_fields=['data'])
    
    await context.set_state(ManualsSG.missing_model)
    
    text_obj = await sync_to_async(AllText.objects.first)()
    msg_text = text_obj.input_brand_model if text_obj and text_obj.input_brand_model else "Укажите бренд и модель, которую вы искали:"
    
    await event.message.answer(text=msg_text)

@router.message_created(F.message.body, ManualsSG.missing_model)
async def process_missing_model_and_send(event: MessageCreated, context: MemoryContext, user: User):
    model_input = event.message.body.text
    brand = user.data.get('manual_brand', 'Не указано')
    purchase_date = user.data.get('purchase_date', 'Не указано')
    
    await send_manual_request_to_bitrix(user, brand, model_input, purchase_date)
    
    await context.clear()
    
    text_obj = await sync_to_async(AllText.objects.first)()
    msg_in_work = text_obj.request_in_work if text_obj and text_obj.request_in_work else "Ваш запрос принят и передан менеджерам."
    msg_main = text_obj.main_page if text_obj and text_obj.main_page else "Главное меню"
    
    await event.message.answer(text=msg_in_work)
    await event.message.answer(text=msg_main, attachments=[get_main_keyboard(text_obj)])

async def send_manual_request_to_bitrix(user: User, brand: str, model_input: str, purchase_date: str):
    fio = user.fio or "Не указано"
    company = user.company_name or "Не указано"
    phone = user.phone_number or "Не указано"
    
    comment = (
        f"<b>Запрос инструкции (Нет в списке)</b>\n\n"
        f"ФИО: {fio}\n"
        f"Компания: {company}\n"
        f"Телефон: {phone}\n"
        f"Бренд: {brand}\n"
        f"Модель: {model_input}\n"
        f"Дата/Счет: {purchase_date}"
    )

    bitrix_payload = {
        "fields": {
            "TITLE": f"Запрос инструкции: {model_input}",
            "NAME": fio.split()[0] if fio and len(fio.split()) > 0 else "Пользователь",
            "COMPANY_TITLE": company,
            "PHONE": [{"VALUE": phone, "VALUE_TYPE": "WORK"}],
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
                        await sync_to_async(user.save)(update_fields=['bitrix_lead_id'])
    except Exception as e:
        print(f"Ошибка Битрикс (Запрос инструкции): {e}")
