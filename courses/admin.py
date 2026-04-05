from django.contrib import admin
from .models import Course, CourseStep, Question, Enrollment, StepCompletion, Order, Program, Person, Company, User, Space, TrainingProgram, Message, LearningModule, ModuleStep, QuizQuestion, Signer, Contract, ModuleProgress, StepProgress, QuizAttempt, ModuleResult, ProgramDocument, ProgramDocumentTemplate, Reference, ProgramPlan, Department, WorkRole, PersonWorkRole, PersonDocument, SeaService, ProgramTemplate, ModuleAssignment, MenuPermission, QuizAnswerRecord, RoleIPRestriction, AllowedIP, TrainingGroup
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
    list_display = ['pk', 'person', 'date', 'payer_type', 'payer_company', 'author_person', 'notes_short']
    search_fields = ['person__last_name', 'notes', 'pk']
    list_filter = ['payer_type', 'date']
    raw_id_fields = ['person', 'payer_company', 'author_person', 'signer_person', 'signed_by_manager']
    inlines = [ProgramInline]

    def notes_short(self, obj):
        return (obj.notes or '')[:50]
    notes_short.short_description = 'Примечание'

@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    list_display = [
        'pk', 'order', 'person', 'training_program', 'date_start', 'date_end',
        'amount', 'discount_percent', 'cert_number', 'reg_number',
        'learning_status', 'is_draft',
    ]
    list_filter = ['is_draft', 'is_active', 'learning_status', 'exam_passed']
    search_fields = [
        'cert_number', 'reg_number', 'person__last_name',
        'code', 'pk',
    ]
    raw_id_fields = [
        'order', 'person', 'training_program', 'payer_company',
        'created_by_person', 'print_manager', 'issue_manager', 'eva_access_manager',
    ]
    fieldsets = (
        ('Основное', {'fields': (
            'order', 'person', 'training_program', 'payer_company',
            'code', 'category', 'prog_type',
            'date_start', 'date_end', 'is_active', 'is_draft',
        )}),
        ('Финансы', {'fields': (
            'amount', 'discount', 'discount_percent', 'bonus', 'contract_cost', 'cost_net',
            'payment_date', 'payment_manager',
        ), 'classes': ('collapse',)}),
        ('Документы', {'fields': (
            'cert_number', 'reg_number', 'cert_number_org', 'cert_number_endorsement',
            'blank_id', 'issue_type', 'issue_status', 'issue_date', 'issued_date', 'expire_date',
            'print_date', 'scrap_confirm',
        ), 'classes': ('collapse',)}),
        ('Оценки', {'fields': (
            'eval_entrance', 'entrance_result', 'grade', 'exam_result', 'exam_passed',
            'learning_quality', 'upd_exam_id',
        ), 'classes': ('collapse',)}),
        ('Статусы', {'fields': (
            'learning_status', 'registration_status', 'learning_here',
            'step_progress', 'step_result', 'service_quantity',
        ), 'classes': ('collapse',)}),
        ('Ответственные', {'fields': (
            'created_by_person', 'print_manager', 'issue_manager', 'eva_access_manager',
        ), 'classes': ('collapse',)}),
        ('ФРДО', {'fields': (
            'frdo_confirmed', 'frdo_type', 'frdo_status_date',
        ), 'classes': ('collapse',)}),
        ('Служебное', {'fields': (
            'notes', 'report_date', 'first_report_date', 'eva_access_date',
            'group_id_legacy', 'department_id_legacy', 'original_training_id',
            'created_at_legacy', 'old_discount_percent', 'old_bonus',
        ), 'classes': ('collapse',)}),
    )

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
class PersonWorkRoleInline(admin.TabularInline):
    model = PersonWorkRole
    extra = 1
    autocomplete_fields = ['role']


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
    inlines = [PersonWorkRoleInline]
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


class ProgramDocumentInline(admin.TabularInline):
    model = ProgramDocument
    extra = 0
    fields = ['title', 'file', 'created_at', 'uploaded_by']
    readonly_fields = ['created_at']


@admin.register(TrainingProgram)
class TrainingProgramAdmin(admin.ModelAdmin):
    list_display = ['pk', 'code', 'title_short', 'category', 'direction', 'status', 'new_price', 'period_hours']
    list_filter = ['status', 'category', 'direction']
    search_fields = ['code', 'title', 'category']
    inlines = [ProgramDocumentInline]

    def title_short(self, obj):
        return obj.title[:100] + ('...' if len(obj.title) > 100 else '')
    title_short.short_description = 'Программа'


@admin.register(ProgramDocument)
class ProgramDocumentAdmin(admin.ModelAdmin):
    list_display = ['title', 'program', 'filename', 'created_at', 'uploaded_by']
    search_fields = ['title', 'program__code', 'program__title']


@admin.register(ProgramDocumentTemplate)
class ProgramDocumentTemplateAdmin(admin.ModelAdmin):
    list_display = ['title', 'sort_order', 'is_active']
    list_editable = ['sort_order', 'is_active']


@admin.register(Reference)
class ReferenceAdmin(admin.ModelAdmin):
    list_display = ['entry', 'usage', 'sort_order', 'is_active']
    list_filter = ['usage', 'is_active']
    search_fields = ['entry', 'usage']
    list_editable = ['sort_order', 'is_active']
    ordering = ['usage', 'sort_order']


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


@admin.register(ModuleResult)
class ModuleResultAdmin(admin.ModelAdmin):
    list_display = ['person', 'module', 'final_exam_score', 'final_exam_passed', 'completed_at', 'is_preview']
    list_filter = ['final_exam_passed', 'is_preview']
    search_fields = ['person__last_name', 'module__title']
    readonly_fields = ['quiz_scores', 'final_exam_details']


@admin.register(ProgramPlan)
class ProgramPlanAdmin(admin.ModelAdmin):
    list_display = ['program', 'title', 'hours', 'hours_self', 'control_form', 'sort_order']
    list_filter = ['program']
    search_fields = ['title']
    ordering = ['program', 'sort_order']


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'sort_order']
    list_editable = ['is_active', 'sort_order']
    search_fields = ['name']


@admin.register(WorkRole)
class WorkRoleAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'is_active', 'sort_order']
    list_editable = ['is_active', 'sort_order']
    search_fields = ['name', 'code']


@admin.register(PersonDocument)
class PersonDocumentAdmin(admin.ModelAdmin):
    list_display = ['person', 'title', 'doc_type', 'is_archived', 'uploaded_by', 'created_at']
    list_filter = ['doc_type', 'is_archived']
    search_fields = ['title', 'person__last_name']


@admin.register(SeaService)
class SeaServiceAdmin(admin.ModelAdmin):
    list_display = ['person', 'vessel_name', 'date_from', 'date_to', 'tonnage', 'power']
    list_filter = ['vessel_name']
    search_fields = ['vessel_name', 'person__last_name']


@admin.register(ProgramTemplate)
class ProgramTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'sort_order', 'created_by']
    list_editable = ['is_active', 'sort_order']
    filter_horizontal = ['programs']
    search_fields = ['name']


@admin.register(ModuleAssignment)
class ModuleAssignmentAdmin(admin.ModelAdmin):
    list_display = ['person', 'module', 'program_line', 'assigned_by', 'assigned_at', 'is_active']
    list_filter = ['is_active', 'assigned_at']
    search_fields = ['person__last_name', 'module__title']
    raw_id_fields = ['person', 'module', 'program_line', 'order', 'assigned_by']


@admin.register(MenuPermission)
class MenuPermissionAdmin(admin.ModelAdmin):
    list_display = ['menu_item', 'role', 'is_visible']
    list_editable = ['is_visible']
    list_filter = ['role', 'is_visible']
    ordering = ['menu_item', 'role']


@admin.register(QuizAnswerRecord)
class QuizAnswerRecordAdmin(admin.ModelAdmin):
    list_display = ['person', 'step', 'question', 'is_correct', 'score', 'answered_at']
    list_filter = ['is_correct', 'step']
    raw_id_fields = ['person', 'step', 'question']


@admin.register(TrainingGroup)
class TrainingGroupAdmin(admin.ModelAdmin):
    list_display = ['legacy_id', 'training_program', 'date_from', 'date_to', 'notes', 'student_limit']
    list_filter = ['learning_status', 'department']
    search_fields = ['training_program__code', 'training_program__title', 'notes', 'group_number']
    raw_id_fields = ['training_program', 'organization']
    readonly_fields = ['legacy_id']


@admin.register(RoleIPRestriction)
class RoleIPRestrictionAdmin(admin.ModelAdmin):
    list_display = ['get_role_display_col', 'ip_check_enabled']
    list_editable = ['ip_check_enabled']
    list_display_links = None

    def get_role_display_col(self, obj):
        return obj.get_role_display()
    get_role_display_col.short_description = 'Роль'

    def has_add_permission(self, request):
        return True

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(AllowedIP)
class AllowedIPAdmin(admin.ModelAdmin):
    list_display = ['ip_address', 'description', 'is_active', 'created_at']
    list_editable = ['is_active']
    list_filter = ['is_active']
    search_fields = ['ip_address', 'description']
    readonly_fields = ['created_at']