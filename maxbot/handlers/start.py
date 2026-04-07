from asgiref.sync import sync_to_async
from maxapi.types import MessageCreated, Command, MessageCallback, BotStarted
from maxapi import F, Router
from maxapi.context import MemoryContext
from web.panel.models import AllText
from maxbot.keyboards.inline import get_main_keyboard

router = Router()


@router.bot_started()
async def bot_started(event: BotStarted):
    text = await sync_to_async(AllText.objects.first)()
    main_page_text = text.main_page if text else "Главное меню"
    
    await event.answer(text=main_page_text, attachments=[get_main_keyboard(text)])


@router.message_created(Command('start'))
async def start_handler(event: MessageCreated, context: MemoryContext):
    await context.clear()
    text = await sync_to_async(AllText.objects.first)()
    main_page_text = text.main_page if text else "Главное меню"
    
    await event.message.answer(text=main_page_text, attachments=[get_main_keyboard(text)])

@router.message_callback(F.callback.payload == "back_to_main")
@router.message_callback(F.callback.payload == "main_menu")
async def back_to_main_handler(event: MessageCallback, context: MemoryContext):
    await context.clear()
    text = await sync_to_async(AllText.objects.first)()
    main_page_text = text.main_page if text else "Главное меню"
    
    await event.message.edit(text=main_page_text, attachments=[get_main_keyboard(text)])