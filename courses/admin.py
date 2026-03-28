from django.contrib import admin
from .models import Course, CourseStep, Question, Enrollment, StepCompletion, Order, Program, Person, Company, User, Space, TrainingProgram, Message, LearningModule, ModuleStep, QuizQuestion, Signer, Contract, ModuleProgress, StepProgress, QuizAttempt
from django.utils.html import format_html, mark_safe
from django.contrib.auth.admin import UserAdmin


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
    list_display = ['pk', 'person', 'date', 'amount', 'signer', 'payer_company', 'payer_is_person', 'contract', 'space']
    search_fields = ['person__last_name', 'person__snils']
    list_filter = ['space', 'payer_is_person']
    inlines = [ProgramInline]

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
    list_display  = ['pk', 'last_name', 'first_name', 'middle_name', 'gender',
                     'snils', 'code', 'position', 'workplace', 'account_status']
    search_fields = ['last_name', 'snils', 'pk']
    list_filter   = ['city']
    readonly_fields = ['pk', 'user']
    fieldsets = (
        ('Учётная запись', {
            'fields': ('pk', 'user', 'code'),
            'description': 'Логин = ID слушателя, Пароль = код доступа (6 цифр). '
                           'При создании код генерируется автоматически если не задан.'
        }),
        ('ФИО', {
            'fields': ('last_name', 'first_name', 'middle_name',
                       'last_name_en', 'first_name_en')
        }),
        ('Личные данные', {
            'fields': ('snils', 'dob', 'city', 'phone', 'email', 'gender', 'address', 'passport')
        }),
        ('Образование', {
            'fields': ('edu_level',)
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


@admin.register(Space)
class SpaceAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'get_full_name', 'role', 'get_space', 'is_active']
    list_filter = ['role', 'space']

    fieldsets = UserAdmin.fieldsets + (
        ('Роль и пространство', {
            'fields': ('role', 'space'),
        }),
    )

    def get_space(self, obj):
        return obj.space.name if obj.space else '—'
    get_space.short_description = 'Пространство'


@admin.register(TrainingProgram)
class TrainingProgramAdmin(admin.ModelAdmin):
    list_display = ['pk', 'code', 'title_short', 'category', 'direction', 'status', 'new_price', 'period_hours']
    list_filter = ['status', 'category', 'direction']
    search_fields = ['code', 'title', 'category']

    def title_short(self, obj):
        return obj.title[:100] + ('...' if len(obj.title) > 100 else '')
    title_short.short_description = 'Программа'


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['person', 'author', 'text_short', 'created_at', 'is_read']
    list_filter = ['is_read', 'created_at']
    search_fields = ['text', 'person__last_name']

    def text_short(self, obj):
        return obj.text[:80]
    text_short.short_description = 'Текст'


class ModuleStepInline(admin.TabularInline):
    model = ModuleStep
    extra = 0
    fields = ['order', 'type', 'title', 'url', 'is_active']
    ordering = ['order']


class QuizQuestionInline(admin.StackedInline):
    model = QuizQuestion
    extra = 0
    fields = ['order', 'type', 'text', 'points', 'answers', 'correct', 'terms', 'explanation']
    ordering = ['order']


@admin.register(LearningModule)
class LearningModuleAdmin(admin.ModelAdmin):
    list_display = ['program', 'title', 'order', 'steps_count', 'is_active']
    list_filter = ['is_active', 'program']
    search_fields = ['title', 'program__title', 'program__code']
    inlines = [ModuleStepInline]

    def steps_count(self, obj):
        return obj.steps.count()
    steps_count.short_description = 'Этапов'


@admin.register(ModuleStep)
class ModuleStepAdmin(admin.ModelAdmin):
    list_display = ['module', 'order', 'type', 'title', 'is_active']
    list_filter = ['type', 'is_active']
    search_fields = ['title']
    inlines = [QuizQuestionInline]


@admin.register(QuizQuestion)
class QuizQuestionAdmin(admin.ModelAdmin):
    list_display = ['step', 'order', 'type', 'text_short', 'points']
    list_filter = ['type']
    search_fields = ['text']

    def text_short(self, obj):
        return obj.text[:80]
    text_short.short_description = 'Текст'


@admin.register(Signer)
class SignerAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'position', 'space', 'is_active']
    list_filter = ['space', 'is_active']
    search_fields = ['full_name', 'position']


@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    list_display = ['number', 'date', 'payer', 'our_organization', 'amount', 'is_active']
    list_filter = ['our_organization', 'is_active']
    search_fields = ['number', 'payer__short_name']


@admin.register(ModuleProgress)
class ModuleProgressAdmin(admin.ModelAdmin):
    list_display = ['person', 'module', 'is_completed', 'started_at', 'completed_at']
    list_filter = ['is_completed']
    search_fields = ['person__last_name', 'module__title']


@admin.register(StepProgress)
class StepProgressAdmin(admin.ModelAdmin):
    list_display = ['module_progress', 'step', 'status', 'score', 'completed_at']
    list_filter = ['status']


@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = ['step_progress', 'is_completed', 'score', 'current_question_index']
    list_filter = ['is_completed']