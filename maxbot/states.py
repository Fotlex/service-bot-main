from maxapi.context import State, StatesGroup

class MainSG(StatesGroup):
    main = State()

class ConditionerSG(StatesGroup):
    main = State()
    person = State()

class ComplaintSG(StatesGroup):
    main = State()

class YesDealerSG(StatesGroup):
    main = State()
    yes = State()
    no = State()
    barcode = State()
    date = State()
    diagnostic = State()
    error_code = State()
    what_do = State()
    diagnostic_results = State()
    error_code1 = State()

class NoDealerSG(StatesGroup):
    main = State()
    message = State()

class CompanySG(StatesGroup):
    main = State()
    address_input = State()
    fio_input = State()
    phone_input = State()
    email_input = State()
    object_name = State()
    choosing_myself = State()
    by_myself = State()
    cond_type = State()
    model = State()
    error_code = State()
    ask_for_more_errors = State()
    
    # --- НОВЫЕ СОСТОЯНИЯ ДЛЯ ОТСУТСТВУЮЩЕЙ МОДЕЛИ ---
    missing_date = State()
    missing_model = State()
    missing_barcode = State()
    missing_error = State()
    
class FinalConsumerSG(StatesGroup):
    choice = State()

class ManagerReplySG(StatesGroup):
    text_input = State()

class QuestionSG(StatesGroup):
    question_text = State()

class ManualsSG(StatesGroup):
    brand = State()
    type = State()
    model = State()
    missing_date = State()
    missing_model = State()
    
class DealerStates(StatesGroup):
    company_name = State()
    address = State()
    fio = State()
    phone = State()
    site = State()