from typing import Any, Awaitable, Callable, Dict
from maxapi.filters.middleware import BaseMiddleware
from maxapi.types import UpdateUnion
from asgiref.sync import sync_to_async
from web.panel.models import User

class AuthMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[UpdateUnion, Dict[str, Any]], Awaitable[Any]],
        event_object: UpdateUnion,
        data: Dict[str, Any],
    ) -> Any:
        
        max_user = getattr(event_object, 'user', None) or getattr(event_object, 'from_user', None)
        if not max_user and hasattr(event_object, 'message'):
            max_user = getattr(event_object.message, 'from_user', None)
            
        if max_user:
            fio = f"{max_user.first_name or ''} {max_user.last_name or ''}".strip()
            
            user, _ = await sync_to_async(User.objects.get_or_create)(
                id=max_user.user_id,
                defaults={
                    'username': max_user.username or "",
                    'fio': fio
                }
            )
            data['user'] = user
            
        return await handler(event_object, data)
