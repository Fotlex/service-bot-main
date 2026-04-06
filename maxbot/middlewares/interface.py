from typing import Any, Awaitable, Callable, Dict
from maxapi.filters.middleware import BaseMiddleware

from maxbot.utils.db import get_texts 

class TextMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Any, Dict[str, Any]], Awaitable[Any]],
        event: Any,
        data: Dict[str, Any],
    ) -> Any:
        
        texts = await get_texts()
        
        
        data["text"] = texts
        
        return await handler(event, data)