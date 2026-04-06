from typing import Any

from django.db import models
from solo.models import SingletonModel


class Settings(SingletonModel):
    manager_id = models.BigIntegerField('Телеграм ID менеджера', null=True, blank=True)
    act = models.FileField('Акт о неисправности', upload_to='web/media/acts', null=True, blank=True)
    file_id = models.CharField(null=True, blank=True)

    def __str__(self):
        return 'Настройки'

    class Meta:
        verbose_name = 'Настройки'
        verbose_name_plural = 'Настройки'


class User(models.Model):
    id = models.BigIntegerField('Идентификатор Телеграм', primary_key=True, blank=False)

    username = models.CharField('Юзернейм', max_length=64, null=True, blank=True)
    first_name = models.CharField('Имя', null=True, blank=True)
    last_name = models.CharField('Фамилия', null=True, blank=True)

    company_name = models.CharField('Название компании', null=True, blank=True)
    company_address = models.CharField('Адрес компании', null=True, blank=True)
    fio = models.CharField('ФИО', null=True, blank=True)
    phone_number = models.CharField('Номер телефона для связи', null=True, blank=True)
    email = models.CharField('Адрес электронной почты', null=True, blank=True)

    created_at = models.DateTimeField('Дата регистрации', auto_now_add=True, blank=True)
    
    bitrix_lead_id = models.IntegerField(blank=True, null=True)

    data = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f'id{self.id} | @{self.username or "-"} {self.first_name or "-"} {self.last_name or "-"}'

    class Meta:
        verbose_name = 'Телеграм пользователь'
        verbose_name_plural = 'Телеграм пользователи'


class ErrorCode(models.Model):
    code = models.CharField('Код ошибки')
    manual = models.FileField('Мануал по починке', upload_to='web/media/manuals', blank=True, null=True)
    file_id = models.CharField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.pk:
            old_manual = type(self).objects.get(pk=self.pk).manual

            if old_manual != self.manual:
                self.file_id = None

        super().save(*args, **kwargs)

    def __str__(self):
        return self.code


class GreeErrorCode(ErrorCode):
    model = models.ForeignKey('GreeModel', on_delete=models.CASCADE, related_name='error_codes')

    class Meta:
        verbose_name = 'Ошибка Gree'
        verbose_name_plural = 'Ошибки Gree'


class KitanoErrorCode(ErrorCode):
    model = models.ForeignKey('KitanoModel', on_delete=models.CASCADE, related_name='error_codes')

    class Meta:
        verbose_name = 'Ошибка Kitano'
        verbose_name_plural = 'Ошибки Kitano'


class RoverErrorCode(ErrorCode):
    model = models.ForeignKey('RoverModel', on_delete=models.CASCADE, related_name='error_codes')

    class Meta:
        verbose_name = 'Ошибка Rover'
        verbose_name_plural = 'Ошибки Rover'


class ActualModel(models.Model):
    types = {
        'byt': 'Бытовые',
        'prom': 'Промышленные',
        'mult': 'Мультизональное оборудование'
    }

    model = models.CharField('Модель кондиционера')
    type = models.CharField('Тип кондиционера', choices=types, default='byt')
    
    manual_user = models.FileField('Инструкция пользователя', upload_to='web/media/manuals/user', null=True, blank=True, editable=False)
    manual_install = models.FileField('Инструкция по монтажу', upload_to='web/media/manuals/install', null=True, blank=True, editable=False)

    def __str__(self):
        return self.model



class GreeModel(ActualModel):
    class Meta:
        verbose_name = 'Модель Gree'
        verbose_name_plural = 'Модели Gree'


class KitanoModel(ActualModel):
    class Meta:
        verbose_name = 'Модель Kitano'
        verbose_name_plural = 'Модели Kitano'


class RoverModel(ActualModel):
    class Meta:
        verbose_name = 'Модель Rover'
        verbose_name_plural = 'Модели Rover'


class GreeManual(models.Model):
    model = models.ForeignKey(GreeModel, on_delete=models.CASCADE, related_name='manuals', verbose_name="Модель кондиционера")
    title = models.CharField(max_length=255, verbose_name="Название инструкции")
    file = models.FileField(upload_to='manuals/gree/', verbose_name="Файл инструкции")

    class Meta:
        verbose_name = "Инструкция Gree"
        verbose_name_plural = "Инструкции Gree"

    def __str__(self):
        return self.title

class KitanoManual(models.Model):
    model = models.ForeignKey(KitanoModel, on_delete=models.CASCADE, related_name='manuals', verbose_name="Модель кондиционера")
    title = models.CharField(max_length=255, verbose_name="Название инструкции")
    file = models.FileField(upload_to='manuals/kitano/', verbose_name="Файл инструкции")

    class Meta:
        verbose_name = "Инструкция Kitano"
        verbose_name_plural = "Инструкции Kitano"

    def __str__(self):
        return self.title

class RoverManual(models.Model):
    model = models.ForeignKey(RoverModel, on_delete=models.CASCADE, related_name='manuals', verbose_name="Модель кондиционера")
    title = models.CharField(max_length=255, verbose_name="Название инструкции")
    file = models.FileField(upload_to='manuals/rover/', verbose_name="Файл инструкции")

    class Meta:
        verbose_name = "Инструкция Rover"
        verbose_name_plural = "Инструкции Rover"

    def __str__(self):
        return self.title


class Attachments(models.Model):
    types = {
        'photo': 'Фото',
        'video': 'Видео',
        'document': 'Документ'
    }

    type = models.CharField('Тип вложения', choices=types)
    file = models.FileField('Файл', upload_to='web/media/mailing')
    file_id = models.TextField(null=True)
    mailing = models.ForeignKey('Mailing', on_delete=models.SET_NULL, null=True, related_name='attachments')

    class Meta:
        verbose_name = 'Вложение'
        verbose_name_plural = 'Вложения'


class Mailing(models.Model):
    text = models.TextField('Текст', blank=True, null=True)
    datetime = models.DateTimeField('Дата/Время')
    is_ok = models.BooleanField('Статус отправки', default=False)

    class Meta:
        verbose_name = 'Рассылка'
        verbose_name_plural = 'Рассылки'
        
        
class AllText(models.Model):
    class Meta:
        verbose_name = 'Тексты бота (Все сообщения)'
        verbose_name_plural = 'Тексты бота (Все сообщения)'

    # ==========================================
    # ГЛАВНОЕ МЕНЮ И СТАРТ
    # ==========================================
    main_page = models.CharField(
        max_length=255, 
        default='Главная страница', 
        verbose_name='Текст после команды старт'
    )
    want_dealer = models.CharField(
        max_length=255, 
        default='Хочу стать дилером', 
        verbose_name='Кнопка: Хочу стать дилером'
    )
    service_request = models.CharField(
        max_length=255, 
        default='Отправить запрос в сервисный центр', 
        verbose_name='Кнопка: Не работает кондиционер'
    )

    # ==========================================
    # ВЕТКА "А": СТАТЬ ДИЛЕРОМ
    # ==========================================
    dealer_brand_question = models.TextField(
        default='1. Стать дилером какого бренда вы хотите?\n(GREE, KITANO, ROVER)', 
        verbose_name='Вопрос: Выбор бренда для дилерства'
    )
    dealer_info_question = models.TextField(
        default='2. Укажите название компании, адрес, ваше ФИО, номер телефона для связи, адрес электронной почты, сайт если есть', 
        verbose_name='Вопрос: Данные будущего дилера'
    )
    dealer_manager_contact = models.TextField(
        default='Менеджер с вами свяжется в ближайшее время', 
        verbose_name='Сообщение: Менеджер свяжется (дилер)'
    )

    # ==========================================
    # ВЕТКА "Б": НЕ РАБОТАЕТ КОНДИЦИОНЕР (ВЫБОР РОЛИ)
    # ==========================================
    role_selection = models.TextField(
        default='Кем вы являетесь?', 
        verbose_name='Вопрос: Выбор роли пользователя'
    )
    role_company_btn = models.CharField(
        max_length=255, 
        default='Климатическая компания/монтажная организация', 
        verbose_name='Кнопка: Климатическая компания'
    )
    role_consumer_btn = models.CharField(
        max_length=255, 
        default='Конечный потребитель', 
        verbose_name='Кнопка: Конечный потребитель'
    )

    # ==========================================
    # РОЛЬ: КОНЕЧНЫЙ ПОТРЕБИТЕЛЬ
    # ==========================================
    consumer_info = models.TextField(
        default='Если у вас не работает кондиционер, вы можете обратиться в компанию у которой вы преобретали оборудование или оставить заявку в нашем сервисе и мы сами свяжемся с компанией у которой вы приобрели оборудование', 
        verbose_name='Сообщение: Инфо для конечного потребителя'
    )
    consumer_contact_myself_btn = models.CharField(
        max_length=255, default='Свяжусь сам', verbose_name='Кнопка: Свяжусь сам'
    )
    consumer_leave_request_btn = models.CharField(
        max_length=255, default='Оставлю заявку вам', verbose_name='Кнопка: Оставлю заявку вам'
    )
    consumer_contact_details = models.TextField(
        default='Укажите ваше ФИО, номер телефона для связи и адрес электронной почты.', 
        verbose_name='Вопрос: Контакты потребителя'
    )
    consumer_barcode_request = models.TextField(
        default='Пожалуйста, приложите фотографию штрихкода с оборудования, которое вышло из строя', 
        verbose_name='Запрос: Фото штрихкода потребителя'
    )
    consumer_final_thanks = models.TextField(
        default='Спасибо за обращение в нашу компанию, ваша заявка будет передана в ближайшее время.', 
        verbose_name='Сообщение: Заявка потребителя принята'
    )

    # ==========================================
    # РОЛЬ: КЛИМАТИЧЕСКАЯ КОМПАНИЯ (АВТОРИЗАЦИЯ/ДАННЫЕ)
    # ==========================================
    company_details_request = models.TextField(
        default='Укажите Название компании, адрес, ваше ФИО, номер телефона для связи и адрес электронной почты.', 
        verbose_name='Вопрос: Данные климатической компании'
    )
    is_our_dealer_question = models.TextField(
        default='Являетесь ли вы нашим дилером?', 
        verbose_name='Вопрос: Являетесь ли нашим дилером?'
    )
    object_address_request = models.TextField(
        default='2. Укажите адрес и название объекта (должна быть возможность пропустить этот вопрос)', 
        verbose_name='Вопрос: Адрес и название объекта'
    )

    # ==========================================
    # МЕНЮ ДЕЙСТВИЙ ДЛЯ КОМПАНИИ
    # ==========================================
    action_claim_btn = models.CharField(
        max_length=255, 
        default='Отправить запрос по рекламации в сервисный центр', 
        verbose_name='Кнопка: Запрос по рекламации'
    )
    action_errors_btn = models.CharField(
        max_length=255, 
        default='Справимся сами. Нужны коды ошибок.', 
        verbose_name='Кнопка: Нужны коды ошибок'
    )
    action_manuals_btn = models.CharField(
        max_length=255, 
        default='Нужны инструкции по оборудованию или по монтажу', 
        verbose_name='Кнопка: Нужны инструкции'
    )

    # ==========================================
    # ОБЩИЕ ВОПРОСЫ ПО ОБОРУДОВАНИЮ (Бренд, серия, модель)
    # ==========================================
    select_brand = models.TextField(
        default='Выберите бренд кондиционера (Gree, Kitano, Rover и тп)', 
        verbose_name='Вопрос: Выбор бренда оборудования'
    )
    select_type = models.TextField(
        default='Выберите тип кондиционера (Бытовые, полупромышленные, мультизональные)', 
        verbose_name='Вопрос: Выбор типа оборудования'
    )
    select_series = models.TextField(
        default='Выберите серию кондиционера', 
        verbose_name='Вопрос: Выбор серии'
    )
    model_not_in_list = models.CharField(
        max_length=255, 
        default='Варианта нет в списке (Модель снята с производства)', 
        verbose_name='Кнопка: Модели нет в списке'
    )
    input_brand_model = models.TextField(
        default='Укажите марку и модель кондиционера.', 
        verbose_name='Запрос: Ввод марки и модели вручную'
    )
    purchase_date_invoice = models.TextField(
        default='Укажите дату покупки оборудования или номер счета', 
        verbose_name='Запрос: Дата покупки / номер счета'
    )


    error_codes_info = models.TextField(
        default='Коды ошибок. Обычные коды ошибок - информация из инструкции. Расширенные коды ошибок - расширенная информация из сервис мануала', 
        verbose_name='Инфо: Сообщение с кодами ошибок'
    )
    error_not_in_list = models.CharField(
        max_length=255, default='В списке нет нужной ошибки', verbose_name='Кнопка: Нужной ошибки нет'
    )
    manual_not_in_list = models.CharField(
        max_length=255, default='В списке нет нужной инструкции', verbose_name='Кнопка: Нужной инструкции нет'
    )
    error_provide_barcode = models.TextField(
        default='Если есть возможность, пришлите штрихкод или фото штрихкода.', 
        verbose_name='Запрос: Пришлите фото штрихкода (для ошибок)'
    )
    redirect_to_claim = models.TextField(
        default='Так как в списке нет нужного варианта, мы предлагаем вам отправить запрос в сервисный центр', 
        verbose_name='Сообщение: Перевод на создание рекламации'
    )

    claim_act_question = models.TextField(
        default='У вас есть возможность заполнить и отправить акт о неисправности?', 
        verbose_name='Вопрос: Наличие акта неисправности'
    )
    claim_send_act = models.TextField(
        default='Заполните акт и отправьте его сюда', 
        verbose_name='Запрос: Отправка акта'
    )
    claim_barcode = models.TextField(
        default='Если есть возможность, пришлите номер штрихкода / фотографию штрихкода.', 
        verbose_name='Запрос: Фото штрихкода (рекламация)'
    )
    claim_diagnostics = models.TextField(
        default='Вы проводили первичную диагностику?', 
        verbose_name='Вопрос: Первичная диагностика'
    )
    claim_diagnostics_results = models.TextField(
        default='Какие результаты диагностики?', 
        verbose_name='Запрос: Результаты диагностики'
    )
    claim_error_code = models.TextField(
        default='Какой код ошибки высвечивается на дисплее кондиционера. Если есть возможность, пришлите фотографию.', 
        verbose_name='Запрос: Код ошибки (рекламация)'
    )
    claim_what_did_you_do = models.TextField(
        default='Что вы делали? Если есть возможность, пришлите видео и фотографии', 
        verbose_name='Запрос: Что вы делали (рекламация)'
    )
    claim_all_data_provided = models.TextField(
        default='Вы указали все запрашиваемые данные?', 
        verbose_name='Вопрос: Все ли данные указаны'
    )
    claim_provide_all_data = models.TextField(
        default='Пожалуйста, укажите все запрашиваемые данные. Если вы заполнили не все данные, мы не сможем с вами связаться.', 
        verbose_name='Сообщение: Укажите все данные'
    )
    claim_tech_question = models.TextField(
        default='Отправьте ваш вопрос техническому специалисту', 
        verbose_name='Запрос: Вопрос тех. специалисту'
    )

    
    request_in_work = models.TextField(
        default='Ваш запрос в работе. Менеджер сервиса ответит вам в ближайшее время.', 
        verbose_name='Сообщение: Запрос в работе'
    )
    more_questions = models.TextField(
        default='У вас еще есть вопросы по этой неисправности?', 
        verbose_name='Вопрос: Есть ли еще вопросы'
    )
    auto_close_ticket = models.TextField(
        default='Если вопросов нет в течении 24 часов, заявка автоматически закрывается', 
        verbose_name='Сообщение: Автозакрытие заявки'
    )
    thanks_for_contacting = models.TextField(
        default='Спасибо за обращение в нашу компанию', 
        verbose_name='Сообщение: Спасибо за обращение'
    )

    
    btn_yes = models.CharField(max_length=50, default='ДА', verbose_name='Кнопка: ДА')
    btn_no = models.CharField(max_length=50, default='НЕТ', verbose_name='Кнопка: НЕТ')

    def __str__(self):
        return "Тексты бота"