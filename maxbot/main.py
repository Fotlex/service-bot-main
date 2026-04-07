import asyncio
import logging

import os
import sys
from pathlib import Path

import django

sys.path.append(str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "web.core.settings")
django.setup()

from maxapi import Bot, Dispatcher
from maxapi.types import BotStarted
from maxbot.keyboards.inline import get_main_keyboard
from web.panel.models import AllText
from maxbot.middlewares.auth import AuthMiddleware
from maxbot.middlewares.interface import TextMiddleware
from handlers import setup_handlers
from config import config

logging.basicConfig(level=logging.INFO)

bot = Bot(token=config.MAX_TOKEN)
dp = Dispatcher()


@dp.bot_started()
async def bot_started(event: BotStarted):
    text = await AllText.objects.afirst()
    main_page_text = text.main_page if text else "Главное меню"
    
    await bot.send_message(chat_id=event.chat_id, text=main_page_text, attachments=[get_main_keyboard(text)])


async def main():
    dp.middleware(AuthMiddleware())
    dp.middleware(TextMiddleware())
    
    setup_handlers(dp)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())