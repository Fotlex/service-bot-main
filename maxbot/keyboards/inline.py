from maxapi.types import CallbackButton
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder

def get_back_menu_kb():
    builder = InlineKeyboardBuilder()
    builder.row(CallbackButton(text='Назад в меню', payload='main_menu'))
    return builder.as_markup()

def get_conditioner_main_kb():
    builder = InlineKeyboardBuilder()
    builder.row(CallbackButton(text='Климатическая компания/монтажная организация', payload='role_company'))
    builder.row(CallbackButton(text='Конечный потребитель', payload='role_final_consumer'))
    builder.row(CallbackButton(text='Назад в меню', payload='main_menu'))
    return builder.as_markup()

def get_company_choosing_kb():
    builder = InlineKeyboardBuilder()
    builder.row(CallbackButton(text='Отправить запрос по рекламации в сервисный центр', payload='complaint_main'))
    builder.row(CallbackButton(text='Коды ошибок', payload='company_by_myself'))
    builder.row(CallbackButton(text='Инструкции', payload='manuals_brand'))
    builder.row(CallbackButton(text='Назад в меню', payload='main_menu'))
    return builder.as_markup()

def get_complaint_main_kb():
    builder = InlineKeyboardBuilder()
    builder.row(CallbackButton(text='Да', payload='yes_dealer_main'))
    builder.row(CallbackButton(text='Нет', payload='no_dealer_main'))
    builder.row(CallbackButton(text='Назад в меню', payload='conditioner_main'))
    return builder.as_markup()

def get_yes_dealer_main_kb():
    builder = InlineKeyboardBuilder()
    builder.row(CallbackButton(text='Да', payload='yes_dealer_yes'))
    builder.row(CallbackButton(text='Нет', payload='yes_dealer_no'))
    builder.row(CallbackButton(text='Назад в меню', payload='conditioner_main'))
    return builder.as_markup()

def get_skip_object_kb():
    builder = InlineKeyboardBuilder()
    builder.row(CallbackButton(text='Пропустить', payload='skip_object'))
    builder.row(CallbackButton(text='Назад в меню', payload='main_menu'))
    return builder.as_markup()

def get_skip_barcode_kb():
    builder = InlineKeyboardBuilder()
    builder.row(CallbackButton(text='Пропустить', payload='skip_barcode'))
    return builder.as_markup()

def get_yes_no_diagnostic_kb():
    builder = InlineKeyboardBuilder()
    builder.row(CallbackButton(text='Да', payload='diagnostic_yes'))
    builder.row(CallbackButton(text='Нет', payload='diagnostic_no'))
    return builder.as_markup()

def get_manager_reply_kb(user_id, is_final=False):
    builder = InlineKeyboardBuilder()
    builder.row(CallbackButton(text='Ответить на вопрос', payload=f'answer_user:{user_id}:{"1" if is_final else "0"}'))
    return builder.as_markup()

def get_user_reply_kb(is_final=False):
    builder = InlineKeyboardBuilder()
    builder.row(CallbackButton(text='Понятно', payload='reply_understood'))
    if not is_final:
        builder.row(CallbackButton(text='Задать еще вопрос', payload='reply_ask_more'))
    return builder.as_markup()

def get_brands_kb():
    builder = InlineKeyboardBuilder()
    builder.row(
        CallbackButton(text='GREE', payload='brand_GREE'),
        CallbackButton(text='KITANO', payload='brand_KITANO'),
        CallbackButton(text='ROVER', payload='brand_ROVER')
    )
    builder.row(CallbackButton(text='Назад', payload='company_choosing_myself'))
    builder.row(CallbackButton(text='Назад в меню', payload='main_menu'))
    return builder.as_markup()

def get_cond_type_kb():
    builder = InlineKeyboardBuilder()
    builder.row(CallbackButton(text='Бытовые', payload='type_byt'))
    builder.row(CallbackButton(text='Полупромышленные', payload='type_prom'))
    builder.row(CallbackButton(text='Мультизональное оборудование', payload='type_mult'))
    builder.row(CallbackButton(text='Назад', payload='company_by_myself'))
    builder.row(CallbackButton(text='Назад в меню', payload='main_menu'))
    return builder.as_markup()


def get_skip_or_menu_kb():
    builder = InlineKeyboardBuilder()
    builder.row(CallbackButton(text='Пропустить', payload='skip_missing_step'))
    builder.row(CallbackButton(text='Назад в меню', payload='main_menu'))
    return builder.as_markup()

def get_back_to_menu_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(CallbackButton(text='Назад в меню', payload='main_menu'))
    return builder.as_markup()

def get_dealer_brands_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(
        CallbackButton(text='GREE', payload='dealer_brand_GREE'),
        CallbackButton(text='KITANO', payload='dealer_brand_KITANO'),
        CallbackButton(text='ROVER', payload='dealer_brand_ROVER')
    )
    builder.row(CallbackButton(text='Назад в меню', payload='main_menu'))
    return builder.as_markup()

def get_main_keyboard(text_model=None):
    builder = InlineKeyboardBuilder()
    builder.row(CallbackButton(text='Хочу стать дилером', payload='want_dealer'))
    builder.row(CallbackButton(text='Сервисное обслуживание', payload='conditioner_main'))
    return builder.as_markup()

def get_manual_brands_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(
        CallbackButton(text='GREE', payload='man_brand_GREE'),
        CallbackButton(text='KITANO', payload='man_brand_KITANO'),
        CallbackButton(text='ROVER', payload='man_brand_ROVER')
    )
    builder.row(CallbackButton(text='Назад в меню', payload='main_menu'))
    return builder.as_markup()

def get_conditioner_types_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(CallbackButton(text='Бытовые', payload='man_type_byt'))
    builder.row(CallbackButton(text='Полупромышленные', payload='man_type_prom'))
    builder.row(CallbackButton(text='Мультизональное оборудование', payload='man_type_mult'))
    builder.row(CallbackButton(text='Назад к брендам', payload='manuals_brand'))
    return builder.as_markup()

def get_dynamic_models_keyboard(models_qs):
    builder = InlineKeyboardBuilder()
    chunk_size = 2
    for i in range(0, len(models_qs), chunk_size):
        row_buttons = [
            CallbackButton(text=m.model, payload=f"man_model_{m.id}")
            for m in models_qs[i:i + chunk_size]
        ]
        builder.row(*row_buttons)
    builder.row(CallbackButton(text="Нет нужной модели в списке", payload="not_found_model"))
    builder.row(CallbackButton(text="Назад к брендам", payload="manuals_brand"))
    return builder.as_markup()

def get_manuals_list_keyboard(manuals_list):
    builder = InlineKeyboardBuilder()
    for man in manuals_list:
        btn_text = man.title if getattr(man, 'title', None) else "Скачать инструкцию"
        builder.row(CallbackButton(text=btn_text, payload=f"download_man_{man.id}"))
    
    builder.row(CallbackButton(text="Нет нужной инструкции", payload="not_found_manual"))
    builder.row(CallbackButton(text="Назад в меню", payload="main_menu"))
    return builder.as_markup()


def get_confirm_data_kb():
    builder = InlineKeyboardBuilder()
    builder.row(CallbackButton(text='ДА', payload='confirm_data_yes'))
    builder.row(CallbackButton(text='НЕТ', payload='confirm_data_no'))
    return builder.as_markup()


def get_final_consumer_choice_kb():
    builder = InlineKeyboardBuilder()
    builder.row(CallbackButton(text='Свяжусь сам', payload='fc_contact_myself'))
    builder.row(CallbackButton(text='Оставлю заявку вам', payload='fc_leave_request'))
    builder.row(CallbackButton(text='Назад в меню', payload='main_menu'))
    return builder.as_markup()
