from web.panel.models import User, AllText

from asgiref.sync import sync_to_async
from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.utils import timezone


@sync_to_async
def create_user(max_id: int):
    try:
        user, _ = User.objects.get_or_create(
            id=max_id,
        )
        return user
    except Exception as e:
        print(f"DB Error: {e}")
        return None
    
    
@sync_to_async
def get_texts():
    obj, _ = AllText.objects.get_or_create(id=1)
    return obj