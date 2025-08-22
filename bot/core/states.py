from aiogram.fsm.state import StatesGroup, State


class MainSG(StatesGroup):
    main = State()


class DealerSG(StatesGroup):
    main = State()
    company_name_input = State()
    company_address_input = State()
    fio_input = State()
    phone_number_input = State()
    site_url_input = State()


class ConditionerSG(StatesGroup):
    main = State()
    company = State()
    person = State()


class CompanySG(StatesGroup):
    zapros = State()
    cond_error_code = State()
    cond_model = State()
    cond_type = State()
    by_myself = State()
    choosing_myself = State()
    object_name = State()
    object_address = State()
    email_input = State()
    fio_input = State()
    phone_input = State()
    address_input = State()
    main = State()


class ComplaintSG(StatesGroup):
    yes_dealer = State()
    no_dealer = State()
    main = State()


class NoDealerSG(StatesGroup):
    message = State()
    main = State()


class YesDealerSG(StatesGroup):
    error_code1 = State()
    diagnostic_results = State()
    what_do = State()
    diagnostic = State()
    error_code = State()
    barcode = State()
    date = State()
    yes = State()
    no = State()
    main = State()


class QuestionSG(StatesGroup):
    question_text = State() 
    answ_text = State()
    
    
class ManagerReplySG(StatesGroup):
    text_input = State()
