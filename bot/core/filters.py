from aiogram.enums import ChatType
from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery


class ChatTypeFilter(BaseFilter):
    def __init__(self, chat_type: ChatType | list[ChatType]):
        self.chat_type = chat_type

    async def __call__(self, telegram_entity: Message | CallbackQuery) -> bool:
        if isinstance(self.chat_type, str):
            return telegram_entity.chat.type == self.chat_type

        return telegram_entity.chat.type in self.chat_type
