from django.contrib import admin
from web.panel.models import *
from solo.admin import SingletonModelAdmin


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('id', 'username', 'first_name', 'last_name', 'created_at')
    fields = ('id', 'username', 'first_name', 'last_name', 'created_at')

    exclude = ('data',)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


class AttachmentsInline(admin.TabularInline):
    model = Attachments

    exclude = ('file_id',)

    extra = 0


@admin.register(Mailing)
class MailingAdmin(admin.ModelAdmin):
    list_display = ['datetime', 'text', 'is_ok']
    readonly_fields = ['is_ok']
    inlines = [AttachmentsInline]


class GreeInline(admin.TabularInline):
    model = GreeErrorCode
    exclude = ('file_id',)
    extra = 0


class GreeManualInline(admin.TabularInline):
    model = GreeManual
    extra = 1

class KitanoManualInline(admin.TabularInline):
    model = KitanoManual
    extra = 1

class RoverManualInline(admin.TabularInline):
    model = RoverManual
    extra = 1


@admin.register(GreeModel)
class ConditionerAdmin(admin.ModelAdmin):
    inlines = [GreeInline, GreeManualInline]


class KitanoInline(admin.TabularInline):
    model = KitanoErrorCode
    exclude = ('file_id',)
    extra = 0


@admin.register(KitanoModel)
class ConditionerAdmin(admin.ModelAdmin):
    inlines = [KitanoInline, KitanoManualInline]


class RoverInline(admin.TabularInline):
    model = RoverErrorCode
    exclude = ('file_id',)
    extra = 0


@admin.register(RoverModel)
class ConditionerAdmin(admin.ModelAdmin):
    inlines = [RoverInline, RoverManualInline]


@admin.register(Settings)
class SettingsAdmin(SingletonModelAdmin):
    exclude = ('file_id',)
    
    
