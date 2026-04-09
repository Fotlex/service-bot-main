import aiohttp
import base64
import io
from asgiref.sync import sync_to_async
from maxapi import Router, F
from maxapi.types import MessageCreated, MessageCallback, InputMedia
from maxapi.context import MemoryContext

from maxbot.states import ComplaintSG, YesDealerSG, NoDealerSG, MainSG, ConditionerSG, ManagerReplySG, QuestionSG
from maxbot.keyboards.inline import (
    get_complaint_main_kb, get_yes_dealer_main_kb, get_back_menu_kb, get_skip_barcode_kb, 
    get_yes_no_diagnostic_kb, get_manager_reply_kb, get_user_reply_kb, get_confirm_data_kb
)
from config import config
from web.panel.models import Settings, User

router = Router()

@router.message_callback(F.callback.payload == 'complaint_main')
async def complaint_main(event: MessageCallback, context: MemoryContext):
    await context.set_state(ComplaintSG.main)
    await event.message.answer("Вы являетесь нашим дилером?", attachments=[get_complaint_main_kb()])

@router.message_callback(F.callback.payload == 'yes_dealer_main')
async def yes_dealer_main(event: MessageCallback, context: MemoryContext):
    await context.set_state(YesDealerSG.main)
    await event.message.answer("У вас есть возможность заполнить и отправить акт о неисправности?", attachments=[get_yes_dealer_main_kb()])

@router.message_callback(F.callback.payload == 'no_dealer_main')
async def no_dealer_main(event: MessageCallback, context: MemoryContext):
    await context.set_state(NoDealerSG.main)
    await event.message.answer("Укажите марку и модель кондиционера", attachments=[get_back_menu_kb()])

@router.message_callback(F.callback.payload == 'yes_dealer_yes')
async def yes_dealer_yes(event: MessageCallback, context: MemoryContext):
    await context.set_state(YesDealerSG.yes)
    settings = await sync_to_async(Settings.get_solo)()
    attachments =[InputMedia(path=settings.act.path)] if settings.act else[]
    await event.message.answer("Заполните акт и отправьте его сюда", attachments=attachments)

@router.message_callback(F.callback.payload == 'yes_dealer_no')
async def yes_dealer_no(event: MessageCallback, context: MemoryContext):
    await context.set_state(YesDealerSG.no)
    await event.message.answer("Укажите марку и модель кондиционера")

@router.message_created(F.message.body, YesDealerSG.yes)
async def on_act(event: MessageCreated, context: MemoryContext, user: User):
    settings = await sync_to_async(Settings.get_solo)()
    manager_id = settings.max_id
    
    text = f'''<b>Новая заявка: монтажная компания, дилер, акт</b>
Название компании: {user.company_name}
Адрес компании: {user.company_address}
ФИО: {user.fio}
Номер телефона: {user.phone_number}
Электронная почта: {user.email}
Адрес и название объекта: {user.data.get('object_info', 'Не указано')}'''

    if manager_id and manager_id != -1:
        await event.bot.send_message(
            chat_id=manager_id,
            text=text,
            attachments=[get_manager_reply_kb(user.id)]
        )

    file_for_bitrix = None
    if event.message.body.attachments:
        att = event.message.body.attachments[0]
        if hasattr(att, 'payload') and hasattr(att.payload, 'url'):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(att.payload.url) as resp:
                        if resp.status == 200:
                            content = await resp.read()
                            encoded_content = base64.b64encode(content).decode('utf-8')
                            file_for_bitrix = ["act.pdf", encoded_content]
            except Exception as e:
                print(f"MAX File error: {e}")

    bitrix_payload = {
        "fields": {
            "TITLE": "Заявка из MAX: Дилер, Акт о неисправности",
            "NAME": user.fio,
            "COMMENTS": text,
            "OPENED": "Y",
            "STATUS_ID": "NEW",
            "UF_CRM_1755788093": str(user.id),
        },
        "params": {"REGISTER_SONET_EVENT": "Y"}
    }
    if file_for_bitrix:
        bitrix_payload["fields"]["UF_CRM_1755617658"] = {"fileData": file_for_bitrix}

    try:
        async with aiohttp.ClientSession() as session:
            url = config.BITRIX24_WEBHOOK_URL + "crm.lead.add.json"
            async with session.post(url, json=bitrix_payload) as response:
                res = await response.json()
                if res.get('result'):
                    user.bitrix_lead_id = res['result']
                    await sync_to_async(user.save)()
    except Exception as e:
        print(f"Bitrix Error: {e}")

    await event.message.answer("Ваш запрос в работе. Менеджер сервиса ответит вам в ближайшее время.")
    await context.set_state(ConditionerSG.main)

@router.message_created(F.message.body.text, YesDealerSG.no)
async def brand_input(event: MessageCreated, context: MemoryContext):
    await context.update_data(brand=event.message.body.text)
    await context.set_state(YesDealerSG.barcode)
    await event.message.answer("Если есть возможость пришлите номер штрихкода, фотографию штрихкода.", attachments=[get_skip_barcode_kb()])

@router.message_callback(F.callback.payload == 'skip_barcode', YesDealerSG.barcode)
async def skip_barcode(event: MessageCallback, context: MemoryContext):
    await context.update_data(barcode="Пропущено")
    await context.set_state(YesDealerSG.date)
    await event.message.answer("Укажите дату покупки оборудования или номер счета")

@router.message_created(F.message.body, YesDealerSG.barcode)
async def barcode_input(event: MessageCreated, context: MemoryContext):
    await context.update_data(barcode=event.message.body.text or "Фото")
    await context.set_state(YesDealerSG.date)
    await event.message.answer("Укажите дату покупки оборудования или номер счета")

@router.message_created(F.message.body.text, YesDealerSG.date)
async def date_input(event: MessageCreated, context: MemoryContext):
    await context.update_data(date=event.message.body.text)
    await context.set_state(YesDealerSG.diagnostic)
    await event.message.answer("Вы проводили первичную диагностику?", attachments=[get_yes_no_diagnostic_kb()])

@router.message_callback(F.callback.payload == 'diagnostic_yes')
async def diag_yes(event: MessageCallback, context: MemoryContext):
    await context.set_state(YesDealerSG.what_do)
    await event.message.answer("Что вы делали?")

@router.message_callback(F.callback.payload == 'diagnostic_no')
async def diag_no(event: MessageCallback, context: MemoryContext):
    await context.set_state(YesDealerSG.error_code)
    await event.message.answer("Какой код ошибки высвечивается на дисплее кондиционера. Если есть возможность, пришлите фотографию.")

@router.message_created(F.message.body.text, YesDealerSG.what_do)
async def what_do_input(event: MessageCreated, context: MemoryContext):
    await context.update_data(what_do=event.message.body.text)
    await context.set_state(YesDealerSG.diagnostic_results)
    await event.message.answer("Какие результаты диагностики?")

@router.message_created(F.message.body.text, YesDealerSG.diagnostic_results)
async def diag_res_input(event: MessageCreated, context: MemoryContext):
    await context.update_data(diagnostic_results=event.message.body.text)
    await context.set_state(YesDealerSG.error_code1)
    await event.message.answer("Какой код ошибки высвечивается на дисплее кондиционера. Если есть возможность, пришлите фотографию.")

@router.message_created(F.message.body, YesDealerSG.error_code)
@router.message_created(F.message.body, YesDealerSG.error_code1)
async def error_code_input(event: MessageCreated, context: MemoryContext, user: User):
    err_code = event.message.body.text or "Фото"
    await context.update_data(error_code=err_code)
    
    await context.set_state(YesDealerSG.confirm_data)
    await event.message.answer("Вы указали все запрашиваемые данные?", attachments=[get_confirm_data_kb()])

@router.message_callback(F.callback.payload == 'confirm_data_no')
async def confirm_data_no(event: MessageCallback, context: MemoryContext):
    await context.set_state(YesDealerSG.waiting_additional_data)
    await event.message.answer("Пожалуйста, укажите все запрашиваемые данные. Если вы заполнили не все данные, мы не сможем с вами связаться.")

@router.message_created(F.message.body, YesDealerSG.waiting_additional_data)
async def additional_data_input(event: MessageCreated, context: MemoryContext, user: User):
    additional = event.message.body.text or "Фото/Файл"
    await context.update_data(additional_data=additional)
    await finalize_dealer_complaint(event, context, user)

@router.message_callback(F.callback.payload == 'confirm_data_yes')
async def confirm_data_yes(event: MessageCallback, context: MemoryContext, user: User):
    await finalize_dealer_complaint(event, context, user)

async def finalize_dealer_complaint(event, context: MemoryContext, user: User):
    data = await context.get_data()
    
    settings = await sync_to_async(Settings.get_solo)()
    manager_id = settings.max_id

    brand = data.get('brand', 'Не указано')
    what_do = data.get('what_do', 'Не указано')
    diagnostic_results = data.get('diagnostic_results', 'Не указано')
    error_code = data.get('error_code', 'Не указано')
    additional_data = data.get('additional_data', '')

    text = f'''<b>Новая заявка: монтажная компания, дилер, без акта</b>
Марка и модель кондиционера: {brand}
Что делали: {what_do}
Результаты диагностики: {diagnostic_results}
Код ошибки: {error_code}'''

    if additional_data:
        text += f"\nДополнительная информация: {additional_data}"

    if manager_id and manager_id != -1:
        try:
            await event.bot.send_message(
                chat_id=manager_id,
                text=text,
                attachments=[get_manager_reply_kb(user.id)]
            )
        except Exception as e:
            print(f"Ошибка отправки сообщения менеджеру {manager_id}: {e}")
    
    bitrix_payload = {
        "fields": {
            "TITLE": f"Заявка из MAX (Без акта): {user.company_name or user.fio or 'Дилер'}",
            "NAME": user.fio or "Не указано",
            "COMPANY_TITLE": user.company_name or "",
            "PHONE": [{"VALUE": user.phone_number or "", "VALUE_TYPE": "WORK"}],
            "COMMENTS": text,
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
                res = await response.json()
                if res.get('result'):
                    user.bitrix_lead_id = res['result']
                    await sync_to_async(user.save)()
    except Exception as e:
        print(f"Ошибка Bitrix24 (Без акта): {e}")

    await event.message.answer("Ваш запрос в работе. Менеджер сервиса ответит вам в ближайшее время.")
    await context.set_state(ConditionerSG.main)
    
    
@router.message_created(F.message.body.text, NoDealerSG.main)
async def no_dealer_brand(event: MessageCreated, context: MemoryContext):
    await context.update_data(conditioner_brand=event.message.body.text)
    await context.set_state(NoDealerSG.message)
    await event.message.answer("Отправьте ваш запрос техническому специалисту")

@router.message_created(F.message.body.text, NoDealerSG.message)
async def no_dealer_message(event: MessageCreated, context: MemoryContext, user: User):
    data = await context.get_data()
    conditioner_brand = data.get('conditioner_brand')
    settings = await sync_to_async(Settings.get_solo)()
    
    text = f'''<b>Новая заявка: монтажная компания, не дилер</b>
Марка: {conditioner_brand}
Обращение: {event.message.body.text}'''

    if settings.max_id and settings.max_id != -1:
        await event.bot.send_message(
            chat_id=settings.max_id,
            text=text,
            attachments=[get_manager_reply_kb(user.id, is_final=True)]
        )
    
    await event.message.answer("Ваш запрос в работе. Менеджер сервиса ответит вам в ближайшее время.")
    await context.set_state(ConditionerSG.main)

@router.message_callback(F.callback.payload.startswith('answer_user:'))
async def ask_manager_for_reply(event: MessageCallback, context: MemoryContext):
    parts = event.callback.payload.split(':')
    user_id = int(parts[1])
    is_final_reply = parts[2] == "1"
    
    await context.set_state(ManagerReplySG.text_input)
    await context.update_data(user_id_to_reply=user_id, is_final_reply=is_final_reply)
    await event.message.answer("Введите ответ для пользователя:")

@router.message_created(F.message.body.text, ManagerReplySG.text_input)
async def handle_manager_reply(event: MessageCreated, context: MemoryContext):
    data = await context.get_data()
    original_user_id = data.get('user_id_to_reply')
    is_final_reply = data.get('is_final_reply', False)
    manager_reply_text = event.message.body.text
    
    await event.bot.send_message(
        chat_id=original_user_id,
        text=f"Ответ от менеджера:\n\n{manager_reply_text}",
        attachments=[get_user_reply_kb(is_final=is_final_reply)]
    )
    
    user = await sync_to_async(User.objects.get)(id=original_user_id)
    if user.bitrix_lead_id:
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{config.BITRIX24_WEBHOOK_URL}crm.timeline.comment.add" 
                await session.post(url, json={
                    "fields": {
                        "ENTITY_ID": user.bitrix_lead_id,
                        "ENTITY_TYPE": "lead",
                        "COMMENT": f"Ответ менеджера: {manager_reply_text}"
                    }
                })
        except Exception as e:
            print(f"Error comment bitrix: {e}")

    await event.message.answer("Ответ отправлен пользователю и сохранен в Лиде.")
    await context.clear()
    
@router.message_callback(F.callback.payload == "reply_ask_more")
async def process_ask_more(event: MessageCallback, context: MemoryContext):
    await context.set_state(QuestionSG.question_text)
    await event.message.answer("Пожалуйста, напишите ваш вопрос в сообщении ниже.")

@router.message_callback(F.callback.payload == "reply_understood")
async def process_understood(event: MessageCallback, context: MemoryContext, user: User):
    if user.bitrix_lead_id:
        user.bitrix_lead_id = None
        await sync_to_async(user.save)()
    await event.message.answer("Рад был помочь! Если возникнут новые вопросы, обращайтесь.", attachments=[get_back_menu_kb()])
    await context.set_state(ConditionerSG.main)

@router.message_created(F.message.body.text, QuestionSG.question_text)
async def on_user_question(event: MessageCreated, context: MemoryContext, user: User):
    settings = await sync_to_async(Settings.get_solo)()
    question = event.message.body.text
    
    if settings.max_id and settings.max_id != -1:
        await event.bot.send_message(
            chat_id=settings.max_id,
            text=f"Новый вопрос от пользователя (ID:{user.id})\n\nВопрос: {question}",
            attachments=[get_manager_reply_kb(user.id)]
        )
    await event.message.answer("Ваш вопрос передан менеджеру. Ожидайте ответа.", attachments=[get_back_menu_kb()])
    await context.set_state(ConditionerSG.main)