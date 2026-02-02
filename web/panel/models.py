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
