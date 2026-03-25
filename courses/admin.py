from django.contrib import admin
from .models import Course, CourseStep, Question, Enrollment, StepCompletion, Order, Program, Person, Company, User
from django.utils.html import format_html, mark_safe
from django.contrib.auth.admin import UserAdmin
from django import forms


class CourseStepInline(admin.TabularInline):
    model = CourseStep
    extra = 1
    fields = ['order', 'type', 'title', 'role', 'url', 'date']
    ordering = ['order']


class EnrollmentInline(admin.TabularInline):
    model = Enrollment
    extra = 0
    fields = ['person', 'assigned_date', 'is_active']
    readonly_fields = ['assigned_date']
    autocomplete_fields = ['person']


class QuestionInline(admin.StackedInline):
    model = Question
    extra = 0
    fields = ['order', 'type', 'text', 'points', 'weight', 'instruction',
              'answers', 'correct', 'terms', 'image_url', 'caption', 'description']
    ordering = ['order']


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ['short_name', 'title', 'author', 'steps_count', 'test_time_minutes', 'is_active']
    list_filter = ['is_active']
    search_fields = ['short_name', 'title']
    inlines = [CourseStepInline, EnrollmentInline]

    def steps_count(self, obj):
        return obj.steps.count()
    steps_count.short_description = 'Шагов'


@admin.register(CourseStep)
class CourseStepAdmin(admin.ModelAdmin):
    list_display = ['course', 'order', 'type', 'title']
    list_filter = ['course', 'type']
    search_fields = ['title']
    inlines = [QuestionInline]


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['step', 'order', 'type', 'text_short', 'points']
    list_filter = ['type', 'step__course']
    search_fields = ['text']

    def text_short(self, obj):
        return obj.text[:80] + ('...' if len(obj.text) > 80 else '')
    text_short.short_description = 'Текст'


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ['person', 'course', 'assigned_date', 'is_active', 'progress_display']
    list_filter = ['course', 'is_active']
    search_fields = ['person__last_name', 'person__snils']
    autocomplete_fields = ['person', 'course']

    def progress_display(self, obj):
        return f'{obj.progress_percent}%'
    progress_display.short_description = 'Прогресс'


@admin.register(StepCompletion)
class StepCompletionAdmin(admin.ModelAdmin):
    list_display = ['enrollment', 'step', 'completed_at', 'graded_by', 'test_score']
    list_filter = ['step__course', 'step__type']

class ProgramInline(admin.TabularInline):
    model  = Program
    extra  = 0
    fields = ['code', 'category', 'date_start', 'date_end', 'amount', 'issue_status']

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['pk', 'person', 'date', 'amount', 'partner', 'author']
    search_fields = ['person__last_name', 'person__snils']
    inlines      = [ProgramInline]

@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    list_display = ['code', 'order', 'date_start', 'date_end', 'amount', 'issue_status']

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ['inn', 'short_name', 'full_name', 'phone', 'director']
    search_fields = ['short_name', 'full_name', 'inn']
    list_filter = []
    fieldsets = (
        ('Основные данные', {
            'fields': ('short_name', 'full_name', 'inn', 'kpp', 'ogrn')
        }),
        ('Адреса', {
            'fields': ('legal_address', 'postal_address')
        }),
        ('Контакты', {
            'fields': ('phone', 'email', 'website', 'director')
        }),
        ('Банковские реквизиты', {
            'fields': ('bank_name', 'bik', 'corr_account', 'settlement_account'),
            'classes': ('collapse',)
        }),
        ('Примечания', {
            'fields': ('notes',)
        }),
    )
@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    list_display  = ['pk', 'last_name', 'first_name', 'middle_name',
                     'snils', 'code', 'position', 'workplace', 'account_status']
    search_fields = ['last_name', 'snils', 'pk']
    list_filter   = ['city']
    readonly_fields = ['pk', 'user']
    fieldsets = (
        ('Учётная запись', {
            'fields': ('pk', 'user', 'code'),
            'description': 'Логин = ID слушателя, Пароль = код доступа'
        }),
        ('ФИО', {
            'fields': ('last_name', 'first_name', 'middle_name',
                       'last_name_en', 'first_name_en')
        }),
        ('Личные данные', {
            'fields': ('snils', 'dob', 'city', 'phone', 'email')
        }),
        ('Работа', {
            'fields': ('position', 'workplace')
        }),
        ('Примечания', {
            'fields': ('notes',)
        }),
    )
    actions = ['create_accounts', 'update_accounts']

    def account_status(self, obj):
        if obj.has_account:
            return format_html(
                '<span style="color:green">✓ {}</span>',
                obj.user.username
            )
        if not obj.code:
            return mark_safe('<span style="color:orange">⚠ нет кода</span>')
        return mark_safe('<span style="color:#aaa">— нет аккаунта</span>')
    account_status.short_description = 'Аккаунт'

    @admin.action(description='✓ Создать учётные записи')
    def create_accounts(self, request, queryset):
        created, skipped, errors = 0, 0, []
        for person in queryset:
            if person.has_account:
                skipped += 1
                continue
            try:
                person.create_user_account()
                created += 1
            except ValueError as e:
                errors.append(f'{person}: {e}')
        msg = f'Создано: {created}'
        if skipped: msg += f', пропущено (уже есть): {skipped}'
        if errors:  msg += f', ошибки: {"; ".join(errors)}'
        self.message_user(request, msg)

    @admin.action(description='↺ Обновить пароли из кода')
    def update_accounts(self, request, queryset):
        updated = 0
        for person in queryset:
            if person.has_account and person.code:
                person.update_user_account()
                updated += 1
        self.message_user(request, f'Обновлено паролей: {updated}')


class UserAdminForm(forms.ModelForm):
    """Форма для админки с удобным выбором организаций"""

    class Meta:
        model = User
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Все доступные организации (для выбора в organizations)
        all_companies = Company.objects.all()
        self.fields['organizations'].queryset = all_companies

        # Для current_organization показываем все организации
        # (не ограничиваем только выбранными)
        self.fields['current_organization'].queryset = all_companies
        self.fields['current_organization'].required = False

        # Добавляем подсказку
        self.fields['current_organization'].help_text = 'Можно выбрать любую организацию из списка всех организаций'

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    form = UserAdminForm
    list_display = ['username', 'get_full_name', 'role', 'get_organizations', 'get_current_org', 'is_active']
    list_filter = ['role']
    filter_horizontal = ['organizations']

    fieldsets = UserAdmin.fieldsets + (
        ('Роль', {'fields': ('role',)}),
        ('Организации', {
            'fields': ('organizations', 'current_organization'),
            'description': '''
                <strong>Организации</strong> - все организации, к которым имеет доступ пользователь<br>
                <strong>Текущая организация</strong> - организация, выбранная для текущей работы (должна быть из списка выше)
            '''
        }),
    )

    def get_organizations(self, obj):
        """Отображение организаций в списке пользователей"""
        return ", ".join([org.short_name for org in obj.organizations.all()[:3]]) + \
            ("..." if obj.organizations.count() > 3 else "")

    get_organizations.short_description = 'Организации'

    def get_current_org(self, obj):
        """Отображение текущей организации"""
        if obj.current_organization:
            return f"✓ {obj.current_organization.short_name}"
        return "—"

    get_current_org.short_description = 'Текущая'