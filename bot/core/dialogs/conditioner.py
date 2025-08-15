from aiogram import Router
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram_dialog import Dialog, DialogManager, Window, StartMode, ShowMode
from aiogram_dialog.widgets.input import TextInput
from aiogram_dialog.widgets.kbd import Button, Row, Next, Back, SwitchTo, ScrollingGroup, Select
from aiogram_dialog.widgets.text import Const, Format
from asgiref.sync import sync_to_async

from bot.core.states import MainSG, ConditionerSG, CompanySG, ComplaintSG
from web.panel.models import GreeModel, KitanoModel, RoverModel, ActualModel, ErrorCode

router = Router()


async def go_to_menu(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    await dialog_manager.start(state=MainSG.main, mode=StartMode.RESET_STACK)


async def go_to_complaint(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    await dialog_manager.start(state=ComplaintSG.main)


async def go_to_conditioner(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    await dialog_manager.start(state=ConditionerSG.main)


async def on_company(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    if dialog_manager.middleware_data['user'].email:
        await dialog_manager.start(state=CompanySG.object_name)
        return

    await dialog_manager.start(state=CompanySG.main)


main_window = Window(
    Const(text='Кем вы являетесь?'),
    Button(Const(text='Климатическая компания/монтажная организация'), id='company', on_click=on_company),
    Row(
        Back(text=Const('Конечный потребитель')),
        Back(text=Const('Частное лицо')),
    ),
    Button(Const(text='Назад в меню'), id='menu', on_click=go_to_menu),
    state=ConditionerSG.main
)

person_window = Window(
    Const(
        'Если у вас не работает кондиционер, просим вас обратиться в компанию у которой вы приобретали оборудование.\n\nВсего наилучшего!'
    ),
    Next(text=Const('Назад')),
    Button(Const(text='Назад в меню'), id='menu', on_click=go_to_menu),
    state=ConditionerSG.person
)

dialog = Dialog(
    person_window,
    main_window,
)

router.include_router(dialog)


async def on_text_input_success(message: Message, widget: TextInput, dialog_manager: DialogManager, text: str):
    user = dialog_manager.middleware_data['user']

    match widget.widget_id:
        case 'company_name':
            user.company_name = text
        case 'company_address':
            user.company_address = text
        case 'fio':
            user.fio = text
        case 'phone_number':
            user.phone_number = text
        case 'email':
            user.email = text
        case _:
            user.data[widget.widget_id] = text

    await user.asave()
    await dialog_manager.next()


async def on_text_input_error(message: Message, widget: TextInput, dialog_manager: DialogManager, text: str):
    await message.answer(text='Укажите валидные данные')


def validate_phone(input_text: str) -> str:
    if len(list(filter(str.isdigit, input_text))) != 11:
        raise ValueError("Номер должен содержать 11 цифр!")
    return input_text


def get_input_window(text: str, id: str, state: CompanySG, type_factory=str):
    return Window(
        Const(text=text),
        Back(text=Const('Назад'), when=lambda *_: id not in ['company_name', 'object_name']),
        Button(text=Const('Назад в меню'), id='menu', on_click=go_to_menu),
        TextInput(on_success=on_text_input_success, on_error=on_text_input_error, id=id, type_factory=type_factory),
        state=state
    )


async def on_do_myself(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    user = dialog_manager.middleware_data['user']
    user.data['conditioner'] = button.widget_id
    await user.asave()
    await dialog_manager.next()


async def on_do_type(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    user = dialog_manager.middleware_data['user']
    user.data['c_type'] = button.widget_id
    await user.asave()
    await dialog_manager.next()


async def models_buttons_getter(dialog_manager: DialogManager, *args, **kwargs):
    user = dialog_manager.middleware_data['user']

    if user.data['conditioner'] == 'GREE':
        model = GreeModel
    elif user.data['conditioner'] == 'KITANO':
        model = KitanoModel
    elif user.data['conditioner'] == 'ROVER':
        model = RoverModel

    data = {'buttons': [{'text': m.model, 'id': m.id} async for m in model.objects.filter(type=user.data['c_type'])]}
    return data


async def models_error_codes_getter(dialog_manager: DialogManager, *args, **kwargs):
    user = dialog_manager.middleware_data['user']

    if user.data['conditioner'] == 'GREE':
        model = await GreeModel.objects.aget(id=user.data['model_id'])
    elif user.data['conditioner'] == 'KITANO':
        model = await KitanoModel.objects.aget(id=user.data['model_id'])
    elif user.data['conditioner'] == 'ROVER':
        model = await RoverModel.objects.aget(id=user.data['model_id'])

    data = {'buttons': [{'text': c.code, 'id': c.id} async for c in model.error_codes.all()]}
    return data


async def on_model_choose(callback: CallbackQuery, select: Select, dialog_manager: DialogManager, item_id):
    user = dialog_manager.middleware_data['user']
    user.data['model_id'] = item_id
    await user.asave()

    await dialog_manager.next()


async def on_err_code_choose(callback: CallbackQuery, select: Select, dialog_manager: DialogManager, item_id):
    user = dialog_manager.middleware_data['user']

    if user.data['conditioner'] == 'GREE':
        model = await GreeModel.objects.aget(id=user.data['model_id'])
    elif user.data['conditioner'] == 'KITANO':
        model = await KitanoModel.objects.aget(id=user.data['model_id'])
    elif user.data['conditioner'] == 'ROVER':
        model = await RoverModel.objects.aget(id=user.data['model_id'])

    err_code: ErrorCode = await model.error_codes.aget(id=item_id)

    await callback.message.answer_document(
        document=FSInputFile(path=err_code.manual.path)
    )

    await callback.message.answer(text='Спасибо за обращение в нашу компанию!')

    await dialog_manager.show(ShowMode.SEND)


company_dialog = Dialog(
    get_input_window(text='Укажите название компании', id='company_name', state=CompanySG.main),
    get_input_window(text='Укажите адрес компании', id='company_address', state=CompanySG.address_input),
    get_input_window(text='Укажите ваше ФИО', id='fio', state=CompanySG.fio_input),
    get_input_window(
        text='Укажите номер телефона для связи', id='phone_number', state=CompanySG.phone_input,
        type_factory=validate_phone
    ),
    get_input_window(text='Укажите адрес электронной почты', id='email', state=CompanySG.email_input),
    get_input_window(text='Укажите название объекта', id='object_name', state=CompanySG.object_name),
    get_input_window(text='Укажите адрес объекта', id='object_address', state=CompanySG.object_address),
    Window(
        Const(text='Выберите'),
        Button(text=Const('Отправить запрос по рекламации в сервисный центр'), id='complaint',
               on_click=go_to_complaint),
        SwitchTo(text=Const('Справимся сами. Нужны коды ошибок.'), id='sami', state=CompanySG.by_myself),
        Button(text=Const('Назад в меню'), id='menu', on_click=go_to_menu),
        state=CompanySG.choosing_myself
    ),
    Window(
        Const(text='Выберите бренд кондиционера'),
        Row(
            Button(text=Const('GREE'), id='GREE', on_click=on_do_myself),
            Button(text=Const('KITANO'), id='KITANO', on_click=on_do_myself),
            Button(text=Const('ROVER'), id='ROVER', on_click=on_do_myself),
        ),
        Back(text=Const('Назад'), id='back'),
        Button(text=Const('Назад в меню'), id='menu', on_click=go_to_menu),
        state=CompanySG.by_myself
    ),
    Window(
        Const(text='Выберите тип кондиционера'),
        Button(text=Const('Бытовые'), id='byt', on_click=on_do_type),
        Button(text=Const('Полупромышленные'), id='prom', on_click=on_do_type),
        Button(text=Const('Мультизональное оборудование'), id='mult', on_click=on_do_type),
        Back(text=Const('Назад'), id='back'),
        Button(text=Const('Назад в меню'), id='menu', on_click=go_to_menu),
        state=CompanySG.cond_type
    ),
    Window(
        Const(text='Выберите модель кондиционера'),
        ScrollingGroup(
            Select(
                Format(text='{item[text]}'),
                items='buttons',
                on_click=on_model_choose,
                item_id_getter=lambda x: x['id'],
                id='s_buttons'
            ),
            id='scroll',
            width=5, height=5, hide_on_single_page=True
        ),
        Back(text=Const('Назад'), id='back'),
        Button(text=Const('Назад в меню'), id='menu', on_click=go_to_menu),
        state=CompanySG.cond_model,
        getter=models_buttons_getter
    ),
    Window(
        Const(text='Выберите код ошибки'),
        ScrollingGroup(
            Select(
                Format(text='{item[text]}'),
                items='buttons',
                on_click=on_err_code_choose,
                item_id_getter=lambda x: x['id'],
                id='s_buttons'
            ),
            id='scroll',
            width=5, height=5, hide_on_single_page=True
        ),
        SwitchTo(text=Const('Нет нужной ошибки'), state=CompanySG.zapros, id='zapros'),
        Back(text=Const('Назад'), id='back'),
        Button(text=Const('Назад в меню'), id='menu', on_click=go_to_menu),
        state=CompanySG.cond_error_code,
        getter=models_error_codes_getter
    ),
    Window(
        Const('Отправить запрос по рекламации в сервисный центр'),
        Button(text=Const('Назад в меню'), id='menu', on_click=go_to_menu),
        state=CompanySG.zapros
    )
)

router.include_router(company_dialog)
