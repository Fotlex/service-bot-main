import aiohttp
from asgiref.sync import sync_to_async

from maxapi import F, Router
from maxapi.types import MessageCreated, MessageCallback
from maxapi.context import MemoryContext

from web.panel.models import AllText, User
from maxbot.states import DealerStates
from config import config

from maxbot.keyboards.inline import (
    get_main_keyboard, 
    get_dealer_brands_keyboard, 
    get_back_to_menu_keyboard
)

router = Router()

@router.message_callback(F.callback.payload == "want_dealer")
async def want_dealer_handler(event: MessageCallback, context: MemoryContext):
    await context.clear()
    
    text = await sync_to_async(AllText.objects.first)()
    text_content = text.dealer_brand_question if text else "Выберите бренд:"

    await event.message.edit(
        text=text_content, 
        attachments=[get_dealer_brands_keyboard()]
    )

@router.message_callback(F.callback.payload.startswith("dealer_brand_"))
async def choose_brand(event: MessageCallback, context: MemoryContext, user: User):
    brand = event.callback.payload.split("_")[-1].upper()
    
    user.data['conditioner_type'] = brand
    await sync_to_async(user.save)(update_fields=['data'])
    
    await context.set_state(DealerStates.company_name)
    await event.message.edit(
        text='Укажите название компании', 
        attachments=[get_back_to_menu_keyboard()]
    )

@router.message_created(F.message.body, DealerStates.company_name)
async def process_company_name(event: MessageCreated, context: MemoryContext, user: User):
    user.data['company_name'] = event.message.body.text
    await sync_to_async(user.save)(update_fields=['data'])
    
    await context.set_state(DealerStates.address)
    await event.message.answer(
        text='Укажите адрес компании', 
        attachments=[get_back_to_menu_keyboard()]
    )

@router.message_created(F.message.body, DealerStates.address)
async def process_company_address(event: MessageCreated, context: MemoryContext, user: User):
    user.data['company_address'] = event.message.body.text
    await sync_to_async(user.save)(update_fields=['data'])
    
    await context.set_state(DealerStates.fio)
    await event.message.answer(
        text='Укажите ФИО', 
        attachments=[get_back_to_menu_keyboard()]
    )

@router.message_created(F.message.body, DealerStates.fio)
async def process_fio(event: MessageCreated, context: MemoryContext, user: User):
    user.data['fio'] = event.message.body.text
    await sync_to_async(user.save)(update_fields=['data'])
    
    await context.set_state(DealerStates.phone)
    await event.message.answer(
        text='Укажите номер телефона', 
        attachments=[get_back_to_menu_keyboard()]
    )

@router.message_created(F.message.body, DealerStates.phone)
async def process_phone(event: MessageCreated, context: MemoryContext, user: User):
    input_text = event.message.body.text or ""
    digits = list(filter(str.isdigit, input_text))
    
    if len(digits) != 11:
        await event.message.answer(
            text='Пожалуйста, укажите валидный номер телефона (11 цифр).', 
            attachments=[get_back_to_menu_keyboard()]
        )
        return

    user.data['phone_number'] = input_text
    await sync_to_async(user.save)(update_fields=['data'])
    
    await context.set_state(DealerStates.site)
    await event.message.answer(
        text='Укажите ссылку на сайт (если нет, то укажите прочерк "-")', 
        attachments=[get_back_to_menu_keyboard()]
    )

@router.message_created(F.message.body, DealerStates.site)
async def process_site_and_finish(event: MessageCreated, context: MemoryContext, user: User):
    user.data['site'] = event.message.body.text
    await sync_to_async(user.save)(update_fields=['data'])
    
    await send_to_bitrix(user)
    await context.clear()
    
    text = await sync_to_async(AllText.objects.first)()
    manager_contact = text.dealer_manager_contact if text else "Заявка успешно отправлена! Менеджер свяжется с вами."
    main_page_text = text.main_page if text else "Главное меню"
    
    await event.message.answer(text=manager_contact)
    await event.message.answer(text=main_page_text, attachments=[get_main_keyboard(text)])

@router.message_callback(F.callback.payload == "back_to_main")
@router.message_callback(F.callback.payload == "main_menu")
async def back_to_main_handler(event: MessageCallback, context: MemoryContext):
    await context.clear()
    text = await sync_to_async(AllText.objects.first)()
    main_page_text = text.main_page if text else "Главное меню"
    
    await event.message.edit(text=main_page_text, attachments=[get_main_keyboard(text)])


async def send_to_bitrix(user: User):
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
            "UF_CRM_1760933453": "Дилер"
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
