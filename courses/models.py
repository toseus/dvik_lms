from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings


class Space(models.Model):
    """Пространство (организация / площадка)."""
    name = models.CharField(max_length=200, verbose_name='Название')
    slug = models.SlugField(max_length=200, unique=True, verbose_name='Slug')
    description = models.TextField(blank=True, verbose_name='Описание')
    is_active = models.BooleanField(default=True, verbose_name='Активно')

    class Meta:
        verbose_name = 'Пространство'
        verbose_name_plural = 'Пространства'
        ordering = ['name']

    def __str__(self):
        return self.name


class User(AbstractUser):
    class Role(models.TextChoices):
        STUDENT = 'student', 'Слушатель'
        TEACHER = 'teacher', 'Преподаватель'
        ADMIN = 'admin', 'Администратор'
        SUPERADMIN = 'superadmin', 'Суперадмин'

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.STUDENT,
        verbose_name='Роль'
    )

    space = models.ForeignKey(
        'Space',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users',
        verbose_name='Пространство'
    )

    class Meta:  # ← Здесь был неправильный отступ
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return f'{self.get_full_name()} ({self.get_role_display()})'


class Person(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='person',
        verbose_name='Учётная запись'
    )

    snils = models.CharField(max_length=14, blank=True, default='', verbose_name='СНИЛС')
    last_name = models.CharField(max_length=100, verbose_name='Фамилия')
    first_name = models.CharField(max_length=100, verbose_name='Имя')
    middle_name = models.CharField(max_length=100, blank=True, verbose_name='Отчество')
    last_name_en = models.CharField(max_length=100, blank=True, verbose_name='Фамилия (англ)')
    first_name_en = models.CharField(max_length=100, blank=True, verbose_name='Имя (англ)')
    dob = models.DateField(null=True, blank=True, verbose_name='Дата рождения')
    city = models.CharField(max_length=100, blank=True, verbose_name='Город')
    position = models.CharField(max_length=200, blank=True, verbose_name='Должность')
    workplace = models.CharField(max_length=200, blank=True, verbose_name='Место работы')
    gender = models.CharField(max_length=1, blank=True, choices=[('М', 'Мужской'), ('Ж', 'Женский')], verbose_name='Пол')
    address = models.TextField(blank=True, verbose_name='Адрес')
    edu_level = models.CharField(max_length=100, blank=True, verbose_name='Уровень образования')
    passport = models.TextField(blank=True, verbose_name='Паспортные данные')
    phone = models.CharField(max_length=20, blank=True, verbose_name='Телефон')
    email = models.EmailField(blank=True, verbose_name='Email')
    notes = models.TextField(blank=True, verbose_name='Примечания')

    # Должность АИС
    ais_position = models.CharField(max_length=200, blank=True, default='', verbose_name='Должность АИС диплом')

    # Образование — документ
    edu_document = models.CharField(max_length=300, blank=True, default='', verbose_name='Документ об образовании')
    edu_reg_number = models.CharField(max_length=100, blank=True, default='', verbose_name='Рег. номер документа об образовании')
    edu_year = models.IntegerField(null=True, blank=True, verbose_name='Год выдачи документа об образовании')

    # ИТФ
    is_itf = models.BooleanField(default=False, verbose_name='Слушатель ИТФ')
    itf_specialty = models.CharField(max_length=200, blank=True, default='', verbose_name='Специальность ИТФ')
    itf_course = models.IntegerField(null=True, blank=True, verbose_name='Курс ИТФ')

    # Код для входа — 6 цифр, вводится вручную при создании
    code = models.CharField(max_length=20, blank=True, verbose_name='Код доступа', help_text='Используется как пароль для входа в систему')

    # Кто создал запись
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_persons',
        verbose_name='Кто создал'
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')

    class Meta:
        verbose_name = 'Физическое лицо'
        verbose_name_plural = 'Физические лица'
        ordering = ['last_name', 'first_name']

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.snils:
            dup = Person.objects.filter(snils=self.snils).exclude(pk=self.pk).exists()
            if dup:
                raise ValidationError({'snils': 'Физическое лицо с таким СНИЛС уже существует'})

    def __str__(self):
        return f'{self.last_name} {self.first_name} {self.middle_name}'.strip()

    @property
    def fio(self):
        return str(self)

    @property
    def has_account(self):
        return self.user is not None

    def create_user_account(self):
        """
        Создать учётную запись:
          логин   = str(self.pk)  — ID слушателя
          пароль  = self.code     — 6-значный код
        """
        if self.user:
            return self.user  # уже существует

        if not self.code:
            raise ValueError('Для создания аккаунта необходимо заполнить код доступа')

        user = User.objects.create_user(
            username=str(self.pk),
            password=self.code,
            first_name=self.first_name,
            last_name=self.last_name,
            email=self.email,
            role='student',
        )
        self.user = user
        self.save(update_fields=['user'])
        return user

    def update_user_account(self):
        """Обновить пароль если код изменился"""
        if self.user and self.code:
            self.user.set_password(self.code)
            self.user.first_name = self.first_name
            self.user.last_name = self.last_name
            self.user.email = self.email
            self.user.save()


class Company(models.Model):
    """Юридическое лицо."""
    short_name = models.CharField(max_length=200, verbose_name='Короткое название')
    full_name = models.CharField(max_length=500, verbose_name='Полное название')
    inn = models.CharField(max_length=12, unique=True, verbose_name='ИНН')
    kpp = models.CharField(max_length=9, blank=True, verbose_name='КПП')
    ogrn = models.CharField(max_length=15, blank=True, verbose_name='ОГРН')
    legal_address = models.TextField(blank=True, verbose_name='Юридический адрес')
    postal_address = models.TextField(blank=True, verbose_name='Почтовый адрес')
    phone = models.CharField(max_length=50, blank=True, verbose_name='Телефон')
    email = models.EmailField(blank=True, verbose_name='Email')
    website = models.URLField(blank=True, verbose_name='Сайт')
    bank_name = models.CharField(max_length=200, blank=True, verbose_name='Банк')
    bik = models.CharField(max_length=9, blank=True, verbose_name='БИК')
    corr_account = models.CharField(max_length=20, blank=True, verbose_name='Корр. счёт')
    settlement_account = models.CharField(max_length=20, blank=True, verbose_name='Расч. счёт')
    director = models.CharField(max_length=200, blank=True, verbose_name='Руководитель')
    notes = models.TextField(blank=True, verbose_name='Примечания')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Юридическое лицо'
        verbose_name_plural = 'Юридические лица'
        ordering = ['short_name']

    def __str__(self):
        return self.short_name


class Course(models.Model):
    """Учебный курс / программа обучения."""
    short_name = models.CharField(max_length=30, verbose_name='Сокращение')
    title = models.CharField(max_length=300, verbose_name='Название')
    author = models.CharField(max_length=200, blank=True, verbose_name='Автор / кафедра')
    description = models.TextField(blank=True, verbose_name='Описание')

    cover_color = models.CharField(max_length=7, default='#0f62ae', verbose_name='Цвет обложки')
    cover_emoji = models.CharField(max_length=10, default='📘', verbose_name='Эмодзи обложки')
    cover_bg = models.CharField(max_length=200, blank=True, verbose_name='CSS-градиент обложки')

    # Время на тест (минуты)
    test_time_minutes = models.PositiveIntegerField(default=20, verbose_name='Время на тест (мин)')

    is_active = models.BooleanField(default=True, verbose_name='Активен')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Курс'
        verbose_name_plural = 'Курсы'
        ordering = ['title']

    def __str__(self):
        return f'{self.short_name} — {self.title}'

    @property
    def steps_count(self):
        return self.steps.count()


class CourseStep(models.Model):
    """Шаг (этап) внутри курса."""

    class StepType(models.TextChoices):
        ONLINE = 'online', 'Онлайн-лекция'
        PDF = 'pdf', 'PDF-материал'
        PRACTICE = 'practice', 'Практическое занятие'
        UPLOAD = 'upload', 'Загрузка работы'
        TEST = 'test', 'Тестирование'

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='steps', verbose_name='Курс')
    order = models.PositiveIntegerField(default=0, verbose_name='Порядок')
    type = models.CharField(max_length=10, choices=StepType.choices, default=StepType.ONLINE, verbose_name='Тип')
    title = models.CharField(max_length=300, verbose_name='Название')
    role = models.CharField(max_length=100, blank=True, verbose_name='Роль / тип занятия')
    url = models.URLField(max_length=500, blank=True, verbose_name='Ссылка')
    date = models.DateField(null=True, blank=True, verbose_name='Дата проведения')

    class Meta:
        verbose_name = 'Шаг курса'
        verbose_name_plural = 'Шаги курсов'
        ordering = ['course', 'order']

    def __str__(self):
        return f'{self.course.short_name} → {self.order}. {self.title}'


class Question(models.Model):
    """Вопрос для тестирования (привязан к шагу типа test)."""

    class QType(models.TextChoices):
        SINGLE = 'single', 'Один ответ'
        MULTI = 'multi', 'Несколько ответов'
        ORDER = 'order', 'Последовательность'
        MATCH = 'match', 'Сопоставление'

    step = models.ForeignKey(CourseStep, on_delete=models.CASCADE, related_name='questions', verbose_name='Шаг (тест)')
    order = models.PositiveIntegerField(default=0, verbose_name='Порядок')
    text = models.TextField(verbose_name='Текст вопроса')
    type = models.CharField(max_length=10, choices=QType.choices, default=QType.SINGLE, verbose_name='Тип')
    points = models.PositiveIntegerField(default=2, verbose_name='Баллы')
    weight = models.PositiveIntegerField(default=1, verbose_name='Вес')
    image_url = models.URLField(max_length=500, blank=True, verbose_name='URL изображения')
    caption = models.CharField(max_length=300, blank=True, verbose_name='Подпись к рисунку')
    description = models.TextField(blank=True, verbose_name='Описание / подсказка')
    instruction = models.TextField(default='Выберите <strong>один правильный ответ</strong>.', verbose_name='Инструкция')
    # JSON-поля для гибкости
    answers = models.JSONField(verbose_name='Варианты ответов', help_text='Массив строк: ["ответ 1","ответ 2",...]')
    correct = models.JSONField(verbose_name='Правильные ответы', help_text='Массив индексов правильных ответов: [0,2]')
    terms = models.JSONField(blank=True, null=True, verbose_name='Понятия (для match)', help_text='Массив строк для сопоставления')

    class Meta:
        verbose_name = 'Вопрос'
        verbose_name_plural = 'Вопросы'
        ordering = ['step', 'order']

    def __str__(self):
        return f'Q{self.order}: {self.text[:60]}'


class Enrollment(models.Model):
    """Зачисление слушателя на курс."""
    person = models.ForeignKey('Person', on_delete=models.CASCADE, related_name='enrollments', verbose_name='Слушатель')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='enrollments', verbose_name='Курс')
    assigned_date = models.DateField(auto_now_add=True, verbose_name='Дата назначения')
    is_active = models.BooleanField(default=True, verbose_name='Активно')

    class Meta:
        verbose_name = 'Зачисление'
        verbose_name_plural = 'Зачисления'
        unique_together = ['person', 'course']
        ordering = ['-assigned_date']

    def __str__(self):
        return f'{self.person} → {self.course.short_name}'

    @property
    def progress_percent(self):
        total = self.course.steps.count()
        if total == 0:
            return 0
        done = self.completed_steps.count()
        return round(done / total * 100)


class StepCompletion(models.Model):
    """Отметка о прохождении шага слушателем."""
    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE, related_name='completed_steps',
                                   verbose_name='Зачисление')
    step = models.ForeignKey(CourseStep, on_delete=models.CASCADE, related_name='completions', verbose_name='Шаг')
    completed_at = models.DateTimeField(auto_now_add=True)
    # Для практики — кто зачёл
    graded_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, verbose_name='Проставил зачёт')
    # Для загрузки файлов
    uploaded_file = models.FileField(upload_to='uploads/steps/', blank=True, verbose_name='Загруженный файл')
    # Для тестов — результат
    test_score = models.PositiveIntegerField(null=True, blank=True, verbose_name='Результат теста (%)')

    class Meta:
        verbose_name = 'Прохождение шага'
        verbose_name_plural = 'Прохождения шагов'
        unique_together = ['enrollment', 'step']

    def __str__(self):
        return f'{self.enrollment.person} ✓ {self.step.title}'


class Signer(models.Model):
    """Подписант — сотрудник организации, подписывающий документы."""
    full_name = models.CharField(max_length=300, verbose_name='ФИО')
    position = models.CharField(max_length=300, verbose_name='Должность')
    space = models.ForeignKey('Space', on_delete=models.CASCADE, related_name='signers', verbose_name='Пространство')
    is_active = models.BooleanField(default=True, verbose_name='Активен')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Подписант'
        verbose_name_plural = 'Подписанты'
        ordering = ['full_name']

    def __str__(self):
        return f'{self.full_name} ({self.position})'


class Contract(models.Model):
    """Договор с плательщиком."""
    number = models.CharField(max_length=100, verbose_name='Номер договора')
    date = models.DateField(verbose_name='Дата договора')
    payer = models.ForeignKey('Company', on_delete=models.CASCADE, related_name='contracts', verbose_name='Плательщик')
    our_organization = models.ForeignKey('Space', on_delete=models.CASCADE, related_name='contracts', verbose_name='Наша организация')
    amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, verbose_name='Сумма')
    notes = models.TextField(blank=True, verbose_name='Примечания')
    is_active = models.BooleanField(default=True, verbose_name='Действующий')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Договор'
        verbose_name_plural = 'Договоры'
        ordering = ['-date']

    def __str__(self):
        return f'Договор №{self.number} от {self.date} — {self.payer.short_name}'


class Order(models.Model):
    """Заявка слушателя"""
    person = models.ForeignKey(Person, on_delete=models.CASCADE, null=True, blank=True, related_name='orders', verbose_name='Слушатель')
    date = models.DateField(null=True, blank=True, verbose_name='Дата заявки')
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Сумма')
    payer = models.CharField(max_length=200, blank=True, verbose_name='Плательщик')
    partner = models.CharField(max_length=100, blank=True, verbose_name='Сетевой партнёр')
    author = models.CharField(max_length=200, blank=True, verbose_name='Автор')
    # Связи
    signer = models.ForeignKey('Signer', on_delete=models.SET_NULL, null=True, blank=True, related_name='orders', verbose_name='Подписант')
    payer_company = models.ForeignKey('Company', on_delete=models.SET_NULL, null=True, blank=True, related_name='paid_orders', verbose_name='Плательщик (организация)')
    payer_is_person = models.BooleanField(default=False, verbose_name='Плательщик — сам слушатель')
    contract = models.ForeignKey('Contract', on_delete=models.SET_NULL, null=True, blank=True, related_name='orders', verbose_name='Договор')
    space = models.ForeignKey('Space', on_delete=models.SET_NULL, null=True, blank=True, related_name='orders', verbose_name='Организация')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_orders', verbose_name='Кто создал')
    created_at = models.DateTimeField(auto_now_add=True)
    # Поля из Access
    payer_type = models.CharField(max_length=20, blank=True, default='', choices=[('', '\u2014'), ('fl', '\u0424\u041B'), ('ul', '\u042E\u041B')], verbose_name='Тип плательщика')
    notes = models.TextField(blank=True, default='', verbose_name='Примечание')
    author_person = models.ForeignKey('Person', null=True, blank=True, on_delete=models.SET_NULL, related_name='authored_orders', verbose_name='Автор (физлицо)')
    signer_person = models.ForeignKey('Person', null=True, blank=True, on_delete=models.SET_NULL, related_name='signed_orders', verbose_name='Подписант (физлицо)')
    student_signed_date = models.CharField(max_length=40, blank=True, default='', verbose_name='Дата подписания слушателем')
    signed_by_manager = models.ForeignKey('Person', null=True, blank=True, on_delete=models.SET_NULL, related_name='confirmed_orders', verbose_name='Менеджер подтверждения')
    created_at_legacy = models.CharField(max_length=40, blank=True, default='', verbose_name='Дата создания (Access)')

    class Meta:
        verbose_name = 'Заявка'
        verbose_name_plural = 'Заявки'
        ordering = ['-date']

    def __str__(self):
        return f'Заявка №{self.pk} — {self.person} от {self.date}'


class Program(models.Model):
    """Подготовка (строка в заявке)"""

    class IssueStatus(models.TextChoices):
        TO_ISSUE = 'da', 'На выдачу'
        NO_ISSUE = 'ne', 'Не выдавать'
        CANCELLED = 'otm', 'Отменён'

    # === Основные связи ===
    order = models.ForeignKey(Order, on_delete=models.CASCADE, null=True, blank=True, related_name='programs', verbose_name='Заявка')
    person = models.ForeignKey('Person', null=True, blank=True, on_delete=models.SET_NULL,
        related_name='trainings', verbose_name='Слушатель')
    training_program = models.ForeignKey('TrainingProgram', null=True, blank=True, on_delete=models.SET_NULL,
        related_name='trainings', verbose_name='Программа обучения')
    payer_company = models.ForeignKey('Company', null=True, blank=True, on_delete=models.SET_NULL,
        related_name='trainings', verbose_name='Плательщик')
    group_id_legacy = models.IntegerField(null=True, blank=True, verbose_name='ID группы (Access)')
    department_id_legacy = models.IntegerField(null=True, blank=True, verbose_name='ID подразделения (Access)')

    # === Основные поля ===
    category = models.CharField(max_length=50, blank=True, verbose_name='Категория')
    prog_type = models.CharField(max_length=50, blank=True, verbose_name='Тип')
    code = models.CharField(max_length=200, blank=True, default='', verbose_name='Код/название программы')
    date_start = models.DateField(null=True, blank=True, verbose_name='Дата начала')
    date_end = models.DateField(null=True, blank=True, verbose_name='Дата окончания')
    discount = models.CharField(max_length=50, blank=True, verbose_name='Скидка')
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='К оплате')
    cert_number = models.CharField(max_length=100, blank=True, verbose_name='№ сертификата')
    reg_number = models.CharField(max_length=100, blank=True, verbose_name='Рег. номер')
    grade = models.CharField(max_length=50, blank=True, verbose_name='Оценка')
    issue_status = models.CharField(max_length=3, choices=IssueStatus.choices, default=IssueStatus.NO_ISSUE,
                                    verbose_name='Статус выдачи')
    notes = models.TextField(blank=True, verbose_name='Примечания')

    # === Даты ===
    created_at_legacy = models.DateTimeField(null=True, blank=True, verbose_name='Дата создания (Access)')
    payment_date = models.DateField(null=True, blank=True, verbose_name='Дата оплаты')
    issue_date = models.DateField(null=True, blank=True, verbose_name='Дата выдачи документа')
    expire_date = models.DateField(null=True, blank=True, verbose_name='Срок действия')
    report_date = models.DateField(null=True, blank=True, verbose_name='Дата явки')
    print_date = models.DateField(null=True, blank=True, verbose_name='Дата печати')
    issued_date = models.DateField(null=True, blank=True, verbose_name='Дата фактической выдачи')
    first_report_date = models.DateField(null=True, blank=True, verbose_name='Дата первой явки')
    frdo_status_date = models.DateField(null=True, blank=True, verbose_name='Дата статуса ФРДО')
    eva_access_date = models.DateField(null=True, blank=True, verbose_name='Дата доступа EVA')

    # === Финансы ===
    discount_percent = models.FloatField(default=0, verbose_name='Скидка %')
    old_discount_percent = models.FloatField(null=True, blank=True, verbose_name='Старая скидка %')
    bonus = models.FloatField(default=0, verbose_name='Бонус')
    old_bonus = models.FloatField(null=True, blank=True, verbose_name='Старый бонус')
    contract_cost = models.FloatField(null=True, blank=True, verbose_name='Стоимость по договору')
    cost_net = models.FloatField(null=True, blank=True, verbose_name='Чистая стоимость')

    # === Документы ===
    cert_number_org = models.CharField(max_length=255, blank=True, default='', verbose_name='№ серт. организации')
    cert_number_endorsement = models.CharField(max_length=255, blank=True, default='', verbose_name='№ серт. андорсмент')
    blank_id = models.CharField(max_length=255, blank=True, default='', verbose_name='ID бланка')
    issue_type = models.CharField(max_length=255, blank=True, default='', verbose_name='Тип выдачи')
    scrap_confirm = models.CharField(max_length=255, blank=True, default='', verbose_name='Подтверждение списания')

    # === Оценки ===
    eval_entrance = models.CharField(max_length=255, blank=True, default='', verbose_name='Входная оценка')
    entrance_result = models.IntegerField(null=True, blank=True, verbose_name='Результат входного контроля')
    exam_result = models.IntegerField(null=True, blank=True, verbose_name='Результат экзамена')
    exam_passed = models.BooleanField(default=False, verbose_name='Экзамен сдан')
    upd_exam_id = models.CharField(max_length=255, blank=True, default='', verbose_name='ID обновлённого экзамена')
    learning_quality = models.IntegerField(null=True, blank=True, verbose_name='Качество обучения')

    # === Статусы ===
    is_active = models.BooleanField(default=True, verbose_name='Активна')
    is_draft = models.BooleanField(default=False, verbose_name='Черновик')
    learning_status = models.CharField(max_length=255, blank=True, default='', verbose_name='Статус обучения')
    registration_status = models.CharField(max_length=255, blank=True, default='', verbose_name='Статус регистрации')
    learning_here = models.CharField(max_length=255, blank=True, default='', verbose_name='Обучается здесь')
    step_progress = models.IntegerField(null=True, blank=True, verbose_name='Прогресс этапов')
    step_result = models.IntegerField(null=True, blank=True, verbose_name='Результат этапов')
    service_quantity = models.IntegerField(null=True, blank=True, verbose_name='Кол-во услуг')

    # === Ответственные ===
    created_by_person = models.ForeignKey('Person', null=True, blank=True, on_delete=models.SET_NULL,
        related_name='created_trainings', verbose_name='Создал (Person)')
    payment_manager = models.CharField(max_length=255, blank=True, default='', verbose_name='Менеджер оплаты')
    print_manager = models.ForeignKey('Person', null=True, blank=True, on_delete=models.SET_NULL,
        related_name='printed_trainings', verbose_name='Менеджер печати')
    issue_manager = models.ForeignKey('Person', null=True, blank=True, on_delete=models.SET_NULL,
        related_name='issued_trainings', verbose_name='Менеджер выдачи')
    eva_access_manager = models.ForeignKey('Person', null=True, blank=True, on_delete=models.SET_NULL,
        related_name='eva_trainings', verbose_name='Менеджер EVA')

    # === ФРДО ===
    frdo_confirmed = models.BooleanField(default=False, verbose_name='ФРДО подтверждено')
    frdo_type = models.CharField(max_length=255, blank=True, default='', verbose_name='Тип ФРДО')

    # === Прочее ===
    original_training_id = models.IntegerField(null=True, blank=True, verbose_name='ID оригинальной подготовки')

    class Meta:
        verbose_name = 'Подготовка'
        verbose_name_plural = 'Подготовки'
        ordering = ['date_start']

    def __str__(self):
        return f'{self.code} ({self.date_start} — {self.date_end})'


class OrganizationAssignment(models.Model):
    """Назначение организации с указанием её роли (образовательная, заказчик, партнер)"""

    ORGANIZATION_TYPES = [
        ('educational', 'Образовательная организация'),
        ('customer', 'Заказчик'),
        ('partner', 'Партнер'),
    ]

    # Связь с существующей моделью Company
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='assignments',
        verbose_name='Юридическое лицо'
    )

    # Тип организации для нашей системы
    org_type = models.CharField(
        max_length=20,
        choices=ORGANIZATION_TYPES,
        verbose_name='Тип организации'
    )

    # Кто назначил (пользователь)
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='organization_assignments',
        verbose_name='Кто назначил'
    )

    # Для кого назначена (краткое название пользователя)
    assigned_for = models.CharField(
        max_length=200,
        verbose_name='Для кого (краткое название)'
    )

    # Дополнительные поля
    notes = models.TextField(blank=True, verbose_name='Примечания')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата назначения')

    class Meta:
        verbose_name = 'Назначение организации'
        verbose_name_plural = 'Назначения организаций'
        ordering = ['-created_at']
        # Убираем unique_together - теперь можно создавать сколько угодно назначений
        # для одной компании с разными assigned_by и assigned_for

    def __str__(self):
        return f'{self.company.short_name} ({self.get_org_type_display()}) для {self.assigned_for}'


class PersonOrganization(models.Model):
    """Связь физического лица с назначением организации"""
    person = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        related_name='org_assignments',
        verbose_name='Физическое лицо'
    )
    assignment = models.ForeignKey(
        OrganizationAssignment,
        on_delete=models.CASCADE,
        related_name='person_assignments',
        verbose_name='Назначение организации'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата добавления')

    class Meta:
        verbose_name = 'Связь с организацией'
        verbose_name_plural = 'Связи с организациями'
        unique_together = ['person', 'assignment']
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.person.fio} → {self.assignment}'


class TrainingProgram(models.Model):
    """Программа обучения (справочник)."""
    code = models.CharField(max_length=100, blank=True, verbose_name='Сокращение')
    title = models.TextField(verbose_name='Название программы')
    title_eng = models.TextField(blank=True, verbose_name='Название (англ)')
    price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, verbose_name='Стоимость')
    new_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, verbose_name='Стоимость текущая')
    old_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, verbose_name='Старая стоимость')
    new_price_date = models.DateField(null=True, blank=True, verbose_name='Дата изменения цены')
    department = models.CharField(max_length=100, blank=True, verbose_name='Подразделение')
    category = models.CharField(max_length=100, blank=True, verbose_name='Категория')
    direction = models.CharField(max_length=200, blank=True, verbose_name='Направление')
    status = models.CharField(max_length=50, blank=True, verbose_name='Статус')
    period_hours = models.PositiveIntegerField(null=True, blank=True, verbose_name='Часов')
    period_days = models.PositiveIntegerField(null=True, blank=True, verbose_name='Дней')
    period_weeks = models.PositiveIntegerField(null=True, blank=True, verbose_name='Недель')
    stat_type = models.CharField(max_length=50, blank=True, verbose_name='Тип документа')
    specialty = models.CharField(max_length=200, blank=True, verbose_name='Специальность')
    training_form = models.CharField(max_length=100, blank=True, verbose_name='Форма обучения')
    edu_level = models.CharField(max_length=100, blank=True, verbose_name='Уровень образования')
    prog_group = models.CharField(max_length=200, blank=True, verbose_name='Группа программ')
    is_published = models.BooleanField(default=False, verbose_name='На сайте')
    dvik157 = models.BooleanField(default=False, verbose_name='157 ДВИК')
    vmc157 = models.BooleanField(default=False, verbose_name='157 ВМК')
    contract_type = models.CharField(max_length=100, blank=True, verbose_name='Тип контракта')
    notes = models.TextField(blank=True, verbose_name='Примечания')
    archive_date = models.DateField(null=True, blank=True, verbose_name='Дата архивации')
    edit_date = models.DateTimeField(null=True, blank=True, verbose_name='Дата редактирования')
    # Тексты сертификатов
    sert_text1 = models.TextField(blank=True, verbose_name='Текст сертификата 1')
    sert_text1_eng = models.TextField(blank=True, verbose_name='Текст сертификата 1 (англ)')
    sert_text2 = models.TextField(blank=True, verbose_name='Текст сертификата 2')
    sert_text2_eng = models.TextField(blank=True, verbose_name='Текст сертификата 2 (англ)')
    sert_text3 = models.TextField(blank=True, verbose_name='Текст сертификата 3')
    sert_text3_eng = models.TextField(blank=True, verbose_name='Текст сертификата 3 (англ)')
    sert_text4 = models.CharField(max_length=500, blank=True, verbose_name='Текст сертификата 4')
    sert_text4_eng = models.CharField(max_length=500, blank=True, verbose_name='Текст сертификата 4 (англ)')
    # Подпрограмма и подписание
    sub_prog = models.CharField(max_length=500, blank=True, verbose_name='Подпрограмма')
    sub_prog_eng = models.CharField(max_length=500, blank=True, verbose_name='Подпрограмма (англ)')
    signing_head = models.CharField(max_length=300, blank=True, verbose_name='Подписант')
    signing_head_eng = models.CharField(max_length=300, blank=True, verbose_name='Подписант (англ)')
    # Бланки и ДПО
    blank_type = models.CharField(max_length=255, blank=True, verbose_name='Тип бланка')
    blank_reg_type = models.CharField(max_length=10, blank=True, verbose_name='Тип регистрации бланка')
    dpo = models.CharField(max_length=255, blank=True, verbose_name='ДПО')
    # Идентификаторы
    id_blank = models.PositiveIntegerField(null=True, blank=True, verbose_name='ID бланка')
    id_sign = models.PositiveIntegerField(null=True, blank=True, verbose_name='ID подписанта')
    id_dep = models.PositiveIntegerField(null=True, blank=True, verbose_name='ID подразделения')
    id_org = models.PositiveIntegerField(null=True, blank=True, verbose_name='ID организации')
    # Лимиты
    group_limit = models.PositiveIntegerField(null=True, blank=True, verbose_name='Лимит группы')
    quant_required = models.PositiveIntegerField(null=True, blank=True, verbose_name='Требуемое количество')
    bonus_rate = models.PositiveIntegerField(null=True, blank=True, verbose_name='Бонусная ставка')
    # АИС
    ais_sert = models.PositiveIntegerField(null=True, blank=True, verbose_name='АИС сертификат')
    ais_rank = models.PositiveIntegerField(null=True, blank=True, verbose_name='АИС ранг')
    ais_uid_doc_type = models.CharField(max_length=255, blank=True, verbose_name='АИС тип документа')
    # ФРДО
    frdo_po_prof = models.CharField(max_length=255, blank=True, verbose_name='ФРДО ПО профессия')
    frdo_po_type_edu = models.CharField(max_length=255, blank=True, verbose_name='ФРДО ПО тип образования')
    frdo_prog_type = models.CharField(max_length=255, blank=True, verbose_name='ФРДО тип программы')
    frdo_doc_type = models.CharField(max_length=255, blank=True, verbose_name='ФРДО тип документа')
    edu_doc_frdo = models.CharField(max_length=255, blank=True, verbose_name='Образовательный документ ФРДО')
    qual_rank_po = models.CharField(max_length=255, blank=True, verbose_name='Квалификация/разряд ПО')
    # Прочее
    main_title = models.CharField(max_length=255, blank=True, verbose_name='Основное название')
    old_programm = models.TextField(blank=True, verbose_name='Старая программа')
    inspection_sts = models.CharField(max_length=255, blank=True, verbose_name='Статус инспекции')
    online_sts = models.CharField(max_length=255, blank=True, verbose_name='Статус онлайн')
    auto_contract = models.CharField(max_length=255, blank=True, verbose_name='Авто-контракт')
    umkd = models.CharField(max_length=255, blank=True, verbose_name='УМКД')
    msun = models.FloatField(null=True, blank=True, verbose_name='МСУН')
    sfera_prof = models.CharField(max_length=255, blank=True, verbose_name='Сфера профессии')
    group_prof = models.CharField(max_length=255, blank=True, verbose_name='Группа профессии')
    color_gr = models.CharField(max_length=50, blank=True, verbose_name='Цвет группы')
    contract_first = models.PositiveIntegerField(null=True, blank=True, verbose_name='Первый контракт')
    user_admin = models.PositiveIntegerField(null=True, blank=True, verbose_name='ID админа')
    instructor = models.PositiveIntegerField(null=True, blank=True, verbose_name='ID инструктора')
    rem_stu = models.CharField(max_length=500, blank=True, verbose_name='Примечание для слушателя')
    eva_default = models.CharField(max_length=50, blank=True, verbose_name='Оценка по умолчанию')
    permit_doc_gov = models.PositiveIntegerField(null=True, blank=True, verbose_name='Разрешительный документ')
    examiner_default = models.PositiveIntegerField(null=True, blank=True, verbose_name='Экзаменатор по умолчанию')
    tr_form_famrt = models.CharField(max_length=255, blank=True, verbose_name='Форма обучения ФАМРТ')
    department_ref = models.ForeignKey('Department', null=True, blank=True, on_delete=models.SET_NULL,
        related_name='programs', verbose_name='Подразделение (справочник)')
    signer_person = models.ForeignKey('Person', null=True, blank=True, on_delete=models.SET_NULL,
        related_name='signed_programs', verbose_name='Подписант')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Программа обучения'
        verbose_name_plural = 'Программы обучения'
        ordering = ['code']

    def __str__(self):
        return f'{self.code} — {self.title[:80]}' if self.code else self.title[:80]


class Message(models.Model):
    """Сообщение, привязанное к слушателю (Person)."""
    person = models.ForeignKey(
        'Person',
        on_delete=models.CASCADE,
        related_name='messages',
        verbose_name='Слушатель'
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='sent_messages',
        verbose_name='Автор'
    )
    text = models.TextField(verbose_name='Текст сообщения')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата')
    is_read = models.BooleanField(default=False, verbose_name='Прочитано')
    is_pinned = models.BooleanField(default=False, verbose_name='Закреплено (кейс)')
    case_status = models.CharField(
        max_length=20, blank=True, default='',
        choices=[('', '\u2014'), ('active', '\u0412 \u0440\u0430\u0431\u043E\u0442\u0435'), ('archive', '\u0410\u0440\u0445\u0438\u0432')],
        verbose_name='\u0421\u0442\u0430\u0442\u0443\u0441 \u043A\u0435\u0439\u0441\u0430'
    )

    class Meta:
        verbose_name = 'Сообщение'
        verbose_name_plural = 'Сообщения'
        ordering = ['created_at']

    def __str__(self):
        return f'{self.author} → {self.person}: {self.text[:50]}'


class LearningModule(models.Model):
    """Модуль обучения, привязанный к программе."""
    program = models.ForeignKey('TrainingProgram', on_delete=models.CASCADE, related_name='modules', verbose_name='Программа')
    title = models.CharField(max_length=300, verbose_name='Название модуля')
    order = models.PositiveIntegerField(default=0, verbose_name='Порядок')
    description = models.TextField(blank=True, verbose_name='Описание')
    cover_image = models.CharField(max_length=500, blank=True, default='', verbose_name='Обложка модуля (URL)')
    is_active = models.BooleanField(default=True, verbose_name='Активен')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Модуль обучения'
        verbose_name_plural = 'Модули обучения'
        ordering = ['program', 'order']

    def __str__(self):
        return f'{self.program.code} → {self.title}'


class ModuleStep(models.Model):
    """Этап внутри модуля обучения."""
    class StepType(models.TextChoices):
        MATERIAL = 'material', 'Изучение материала'
        PRACTICE = 'practice', 'Практическое занятие'
        UPLOAD = 'upload', 'Загрузка работы'
        QUIZ = 'quiz', 'Промежуточное тестирование'
        FINAL_EXAM = 'final_exam', 'Итоговая аттестация'
        SLIDE = 'slide', 'Слайд (интерактивный)'

    module = models.ForeignKey(LearningModule, on_delete=models.CASCADE, related_name='steps', verbose_name='Модуль')
    order = models.PositiveIntegerField(default=0, verbose_name='Порядок')
    type = models.CharField(max_length=20, choices=StepType.choices, verbose_name='Тип этапа')
    title = models.CharField(max_length=300, verbose_name='Название')
    description = models.TextField(blank=True, verbose_name='Описание')
    url = models.URLField(max_length=500, blank=True, verbose_name='Ссылка на материал')
    exam_config = models.JSONField(null=True, blank=True, verbose_name='Конфигурация итоговой аттестации',
                                    help_text='{"quiz_step_id": кол-во_вопросов}')
    time_limit_minutes = models.PositiveIntegerField(null=True, blank=True, verbose_name='Время на тест (мин)')
    pass_score = models.PositiveIntegerField(null=True, blank=True, verbose_name='Проходной балл (%)')
    slide_content = models.TextField(blank=True, verbose_name='Слайды (JSON)',
        help_text='JSON массив слайдов: [{"title":"...","content":"HTML...","quiz":{"question":"...","options":[...],"correct":0,"feedback":"..."}}]')
    is_active = models.BooleanField(default=True, verbose_name='Активен')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Этап модуля'
        verbose_name_plural = 'Этапы модулей'
        ordering = ['module', 'order']

    def __str__(self):
        return f'{self.module.title} → {self.order}. {self.title}'


class QuizQuestion(models.Model):
    """Вопрос для промежуточного тестирования."""
    class QType(models.TextChoices):
        SINGLE = 'single', 'Один ответ'
        MULTI = 'multi', 'Несколько ответов'
        ORDER = 'order', 'Последовательность'
        MATCH = 'match', 'Сопоставление'

    step = models.ForeignKey(ModuleStep, on_delete=models.CASCADE, related_name='questions', verbose_name='Этап (тест)')
    order = models.PositiveIntegerField(default=0, verbose_name='Порядок')
    text = models.TextField(verbose_name='Текст вопроса')
    type = models.CharField(max_length=10, choices=QType.choices, default=QType.SINGLE, verbose_name='Тип')
    points = models.PositiveIntegerField(default=1, verbose_name='Баллы')
    image_url = models.CharField(max_length=500, blank=True, default='', verbose_name='Ссылка на картинку')
    explanation = models.TextField(blank=True, verbose_name='Пояснение к ответу')
    answers = models.JSONField(verbose_name='Варианты ответов', help_text='["ответ 1","ответ 2",...]')
    correct = models.JSONField(verbose_name='Правильные ответы', help_text='[0,2]')
    terms = models.JSONField(null=True, blank=True, verbose_name='Понятия (для match)')

    class Meta:
        verbose_name = 'Вопрос теста'
        verbose_name_plural = 'Вопросы тестов'
        ordering = ['step', 'order']

    def __str__(self):
        return f'Q{self.order}: {self.text[:60]}'


class ModuleProgress(models.Model):
    """Прогресс слушателя по модулю."""
    person = models.ForeignKey('Person', on_delete=models.CASCADE, related_name='module_progress', verbose_name='Слушатель')
    module = models.ForeignKey('LearningModule', on_delete=models.CASCADE, related_name='progress', verbose_name='Модуль')
    started_at = models.DateTimeField(auto_now_add=True, verbose_name='Начат')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='Завершён')
    is_completed = models.BooleanField(default=False, verbose_name='Завершён')
    current_step = models.ForeignKey('ModuleStep', on_delete=models.SET_NULL, null=True, blank=True,
                                      related_name='+', verbose_name='Текущий этап')

    class Meta:
        verbose_name = 'Прогресс по модулю'
        verbose_name_plural = 'Прогресс по модулям'
        unique_together = ['person', 'module']

    def __str__(self):
        return f'{self.person} → {self.module.title}'


class StepProgress(models.Model):
    """Прогресс по отдельному этапу модуля."""
    class Status(models.TextChoices):
        NOT_STARTED = 'not_started', 'Не начат'
        IN_PROGRESS = 'in_progress', 'В процессе'
        COMPLETED = 'completed', 'Завершён'
        GRADED = 'graded', 'Оценён'

    module_progress = models.ForeignKey('ModuleProgress', on_delete=models.CASCADE,
                                         related_name='step_progress', verbose_name='Прогресс модуля')
    step = models.ForeignKey('ModuleStep', on_delete=models.CASCADE,
                              related_name='progress', verbose_name='Этап')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NOT_STARTED,
                               verbose_name='Статус')
    score = models.PositiveIntegerField(null=True, blank=True, verbose_name='Балл (%)')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='Дата завершения')
    graded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='+', verbose_name='Кто оценил')
    uploaded_file = models.FileField(upload_to='uploads/module_steps/', blank=True, verbose_name='Загруженный файл')

    class Meta:
        verbose_name = 'Прогресс по этапу'
        verbose_name_plural = 'Прогресс по этапам'
        unique_together = ['module_progress', 'step']

    def __str__(self):
        return f'{self.module_progress.person} → {self.step.title} [{self.status}]'


class QuizAttempt(models.Model):
    """Попытка прохождения теста."""
    step_progress = models.ForeignKey('StepProgress', on_delete=models.CASCADE,
                                       related_name='quiz_attempts', verbose_name='Прогресс этапа')
    answers = models.JSONField(default=dict, verbose_name='Ответы',
                                help_text='{"question_id": {"selected": [0,1], "is_correct": true, "points": 2}}')
    current_question_index = models.PositiveIntegerField(default=0, verbose_name='Текущий вопрос')
    score = models.PositiveIntegerField(null=True, blank=True, verbose_name='Балл (%)')
    max_score = models.PositiveIntegerField(null=True, blank=True, verbose_name='Максимальный балл')
    is_completed = models.BooleanField(default=False, verbose_name='Завершена')
    started_at = models.DateTimeField(auto_now_add=True, verbose_name='Начата')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='Завершена (дата)')

    class Meta:
        verbose_name = 'Попытка теста'
        verbose_name_plural = 'Попытки тестов'

    def __str__(self):
        return f'Попытка: {self.step_progress} ({"завершена" if self.is_completed else "в процессе"})'


class ModuleResult(models.Model):
    """Результат прохождения модуля слушателем."""
    person = models.ForeignKey('Person', on_delete=models.CASCADE, related_name='module_results', verbose_name='Слушатель')
    module = models.ForeignKey('LearningModule', on_delete=models.CASCADE, related_name='results', verbose_name='Модуль')
    quiz_scores = models.JSONField(default=dict, verbose_name='Результаты промежуточных аттестаций',
        help_text='{"step_id": 85, "step_id": 92}')
    final_exam_step = models.ForeignKey('ModuleStep', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='+', verbose_name='Этап итоговой аттестации')
    final_exam_score = models.PositiveIntegerField(null=True, blank=True, verbose_name='Балл итоговой (%)')
    final_exam_passed = models.BooleanField(default=False, verbose_name='Итоговая сдана')
    final_exam_details = models.JSONField(default=list, verbose_name='Детали итоговой аттестации',
        help_text='Полный протокол: вопросы, ответы слушателя, правильные ответы')
    program = models.ForeignKey('TrainingProgram', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='module_results', verbose_name='Программа обучения')
    total_steps = models.PositiveIntegerField(default=0, verbose_name='Всего этапов в модуле')
    completed_steps = models.PositiveIntegerField(default=0, verbose_name='Пройдено этапов')
    total_questions = models.PositiveIntegerField(default=0, verbose_name='Всего вопросов в итоговой')
    correct_questions = models.PositiveIntegerField(default=0, verbose_name='Правильных ответов')
    time_spent_seconds = models.PositiveIntegerField(null=True, blank=True, verbose_name='Время прохождения (сек)')
    completed_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата завершения')
    is_preview = models.BooleanField(default=False, verbose_name='Режим проверки')

    class Meta:
        verbose_name = 'Результат прохождения модуля'
        verbose_name_plural = 'Результаты прохождения модулей'
        ordering = ['-completed_at']

    def __str__(self):
        return f'{self.person} \u2192 {self.module.title} ({self.final_exam_score}%)'


class ModuleAssignment(models.Model):
    """Назначение модуля слушателю."""
    person = models.ForeignKey('Person', on_delete=models.CASCADE,
        related_name='module_assignments', verbose_name='Слушатель')
    module = models.ForeignKey('LearningModule', on_delete=models.CASCADE,
        related_name='assignments', verbose_name='Модуль')
    program_line = models.ForeignKey('Program', null=True, blank=True, on_delete=models.SET_NULL,
        related_name='module_assignments', verbose_name='Строка заявки (подготовка)')
    order = models.ForeignKey('Order', null=True, blank=True, on_delete=models.SET_NULL,
        related_name='module_assignments', verbose_name='Заявка')
    assigned_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='assigned_modules', verbose_name='Кто выдал')
    assigned_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата выдачи')
    is_active = models.BooleanField(default=True, verbose_name='Активно')
    manual_grade = models.CharField(max_length=50, blank=True, default='', verbose_name='Оценка')

    class Meta:
        unique_together = ['person', 'module', 'program_line']
        ordering = ['-assigned_at']
        verbose_name = 'Назначение модуля'
        verbose_name_plural = 'Назначения модулей'

    def __str__(self):
        return f'{self.person} — {self.module}'


class ArchivedModuleResult(models.Model):
    """Архивный результат прохождения модулей — создаётся при проставлении оценки по позиции."""
    person = models.ForeignKey('Person', on_delete=models.CASCADE,
        related_name='archived_results', verbose_name='Слушатель')
    module = models.ForeignKey('LearningModule', on_delete=models.CASCADE,
        verbose_name='Модуль')
    program_line = models.ForeignKey('Program', null=True, blank=True, on_delete=models.SET_NULL,
        verbose_name='Позиция подготовки')
    training_program = models.ForeignKey('TrainingProgram', null=True, blank=True, on_delete=models.SET_NULL,
        verbose_name='Программа обучения')
    total_steps = models.IntegerField(default=0, verbose_name='Всего этапов')
    completed_steps = models.IntegerField(default=0, verbose_name='Пройдено этапов')
    quiz_avg_score = models.FloatField(null=True, blank=True, verbose_name='Ср. балл промежуточных')
    final_score = models.FloatField(null=True, blank=True, verbose_name='Итоговый балл')
    manual_grade = models.CharField(max_length=50, blank=True, default='', verbose_name='Оценка')
    assigned_at = models.DateTimeField(null=True, blank=True, verbose_name='Дата выдачи')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='Дата завершения')
    archived_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата архивации')
    archived_by = models.ForeignKey('User', null=True, blank=True, on_delete=models.SET_NULL,
        verbose_name='Архивировал')

    class Meta:
        ordering = ['-archived_at']
        verbose_name = 'Архивный результат'
        verbose_name_plural = 'Архивные результаты'

    def __str__(self):
        return f'{self.person} — {self.module} (архив)'


class ProgramDocument(models.Model):
    """Документ, прикреплённый к программе обучения."""
    program = models.ForeignKey('TrainingProgram', on_delete=models.CASCADE, related_name='documents', verbose_name='Программа')
    title = models.CharField(max_length=300, verbose_name='Название документа')
    file = models.FileField(upload_to='programs/docs/%Y/%m/', verbose_name='Файл')
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Кто загрузил')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата внесения')
    notes = models.TextField(blank=True, verbose_name='Примечания')

    class Meta:
        verbose_name = 'Документ программы'
        verbose_name_plural = 'Документы программ'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.title} ({self.program.code})'

    template = models.ForeignKey('ProgramDocumentTemplate', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='documents', verbose_name='Шаблон')

    @property
    def filename(self):
        import os
        return os.path.basename(self.file.name) if self.file else ''

    @property
    def file_size(self):
        try:
            return self.file.size
        except:
            return 0


class ProgramDocumentTemplate(models.Model):
    """Шаблон базового документа — автоматически создаётся во всех программах."""
    title = models.CharField(max_length=300, verbose_name='Название документа')
    sort_order = models.PositiveIntegerField(default=0, verbose_name='Порядок')
    is_active = models.BooleanField(default=True, verbose_name='Активен')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Шаблон документа программы'
        verbose_name_plural = 'Шаблоны документов программ'
        ordering = ['sort_order']

    def __str__(self):
        return self.title


class Reference(models.Model):
    """Общий справочник — значения для выпадающих списков."""
    entry = models.CharField(max_length=500, verbose_name='Пункт справочника')
    usage = models.CharField(max_length=200, verbose_name='Место использования',
        help_text='category, direction, department, status, training_form, edu_level, stat_type, blank_type, dpo')
    sort_order = models.PositiveIntegerField(default=0, verbose_name='Порядок')
    is_active = models.BooleanField(default=True, verbose_name='Активен')

    class Meta:
        verbose_name = 'Пункт справочника'
        verbose_name_plural = 'Справочник'
        ordering = ['usage', 'sort_order', 'entry']
        unique_together = ['entry', 'usage']

    def __str__(self):
        return f'{self.usage}: {self.entry}'


class ProgramPlan(models.Model):
    """Учебный план программы."""
    program = models.ForeignKey(TrainingProgram, on_delete=models.CASCADE, related_name='plan_items', verbose_name='Программа')
    title = models.CharField(max_length=500, verbose_name='Наименование дисциплины/раздела')
    hours = models.IntegerField(default=0, verbose_name='Часов (аудиторных)')
    hours_self = models.FloatField(default=0, verbose_name='Часов (самостоятельных)')
    control_form = models.CharField(max_length=100, blank=True, default='', verbose_name='Форма контроля')
    days = models.IntegerField(null=True, blank=True, verbose_name='Дней')
    sort_order = models.IntegerField(default=0, verbose_name='Порядок')
    notes = models.TextField(blank=True, default='', verbose_name='Примечание')

    class Meta:
        ordering = ['program', 'sort_order']
        verbose_name = 'Учебный план'
        verbose_name_plural = 'Учебный план'

    def __str__(self):
        return f'{self.program.code} — {self.title}'


class Department(models.Model):
    """Подразделение."""
    name = models.CharField(max_length=255, verbose_name='Название подразделения')
    is_active = models.BooleanField(default=True, verbose_name='Активно')
    sort_order = models.IntegerField(default=0, verbose_name='Порядок сортировки')

    class Meta:
        ordering = ['sort_order', 'name']
        verbose_name = 'Подразделение'
        verbose_name_plural = 'Подразделения'

    def __str__(self):
        return self.name


class WorkRole(models.Model):
    """Рабочая роль (подписант, преподаватель, экзаменатор и т.д.)."""
    name = models.CharField(max_length=100, verbose_name='Название роли')
    code = models.CharField(max_length=50, unique=True, verbose_name='Код роли')
    description = models.TextField(blank=True, default='', verbose_name='Описание')
    is_active = models.BooleanField(default=True, verbose_name='Активна')
    sort_order = models.IntegerField(default=0, verbose_name='Порядок')

    class Meta:
        ordering = ['sort_order', 'name']
        verbose_name = 'Рабочая роль'
        verbose_name_plural = 'Рабочие роли'

    def __str__(self):
        return self.name


class PersonWorkRole(models.Model):
    """Назначение рабочей роли физлицу."""
    person = models.ForeignKey('Person', on_delete=models.CASCADE, related_name='work_roles', verbose_name='Физлицо')
    role = models.ForeignKey(WorkRole, on_delete=models.CASCADE, related_name='persons', verbose_name='Роль')
    assigned_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата назначения')
    notes = models.TextField(blank=True, default='', verbose_name='Примечание')

    class Meta:
        unique_together = ['person', 'role']
        verbose_name = 'Назначение роли'
        verbose_name_plural = 'Назначения ролей'

    def __str__(self):
        return f'{self.person} — {self.role}'


class PersonDocument(models.Model):
    """Документ слушателя (скан, справка, диплом и т.д.)"""
    person = models.ForeignKey(Person, on_delete=models.CASCADE, related_name='documents', verbose_name='Слушатель')
    title = models.CharField(max_length=500, verbose_name='Название документа')
    doc_type = models.CharField(max_length=50, blank=True, default='other', verbose_name='Тип',
        choices=[('spravka', 'Справка'), ('diploma', 'Диплом'), ('other', 'Другое')])
    file = models.FileField(upload_to='person_docs/%Y/%m/', blank=True, verbose_name='Файл')
    rotation = models.IntegerField(default=0, verbose_name='Поворот (градусов)')
    is_archived = models.BooleanField(default=False, verbose_name='В архиве')
    archived_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='archived_docs', verbose_name='Архивировал')
    archived_at = models.DateTimeField(null=True, blank=True, verbose_name='Дата архивирования')
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='uploaded_person_docs', verbose_name='Загрузил')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата загрузки')
    notes = models.TextField(blank=True, default='', verbose_name='Примечание')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Документ слушателя'
        verbose_name_plural = 'Документы слушателей'

    def __str__(self):
        return f'{self.person} — {self.title}'


class SeaService(models.Model):
    """Плавательный ценз"""
    person = models.ForeignKey(Person, on_delete=models.CASCADE, related_name='sea_services', verbose_name='Слушатель')
    vessel_name = models.CharField(max_length=200, verbose_name='Название судна')
    date_from = models.DateField(verbose_name='Дата начала')
    date_to = models.DateField(verbose_name='Дата окончания')
    tonnage = models.IntegerField(default=0, verbose_name='Тоннаж (GT)')
    power = models.IntegerField(default=0, verbose_name='Мощность (кВт)')
    position = models.CharField(max_length=200, blank=True, default='', verbose_name='Должность на судне')
    document = models.ForeignKey(PersonDocument, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='sea_services', verbose_name='Связанный документ')
    notes = models.TextField(blank=True, default='', verbose_name='Примечание')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date_from']
        verbose_name = 'Плавательный ценз'
        verbose_name_plural = 'Плавательный ценз'

    def __str__(self):
        return f'{self.person} — {self.vessel_name} ({self.date_from}–{self.date_to})'


class ProgramTemplate(models.Model):
    """Шаблон набора программ для быстрого добавления в заявку."""
    name = models.CharField(max_length=200, verbose_name='Название шаблона')
    programs = models.ManyToManyField(TrainingProgram, blank=True, related_name='templates', verbose_name='Программы')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, verbose_name='Создал')
    space = models.ForeignKey('Space', null=True, blank=True, on_delete=models.SET_NULL, verbose_name='Пространство')
    created_at = models.DateTimeField(auto_now_add=True)
    sort_order = models.IntegerField(default=0, verbose_name='Порядок')
    is_active = models.BooleanField(default=True, verbose_name='Активен')

    class Meta:
        ordering = ['sort_order', 'name']
        verbose_name = 'Шаблон набора программ'
        verbose_name_plural = 'Шаблоны наборов программ'

    def __str__(self):
        return self.name


class MenuPermission(models.Model):
    """Настройка видимости пунктов меню по ролям."""
    MENU_ITEMS = [
        ('dashboard', 'Дашборд'),
        ('learning', 'Обучение'),
        ('programs', 'Программы'),
        ('organizations', 'Организации'),
        ('contracts', 'Договоры'),
        ('students', 'Слушатели'),
        ('persons', 'Физические лица'),
        ('modules', 'Модули'),
        ('companies', 'Юридические лица'),
        ('menu_settings', 'Настройки меню'),
        ('impersonate_btn', 'Кнопка «Войти как слушатель»'),
        ('results', 'Результаты'),
        ('progress', 'Прогресс'),
    ]

    ROLES = [
        ('student', 'Слушатель'),
        ('teacher', 'Преподаватель'),
        ('admin', 'Администратор'),
        ('superadmin', 'Суперадмин'),
    ]

    menu_item = models.CharField(max_length=50, choices=MENU_ITEMS, verbose_name='Пункт меню')
    role = models.CharField(max_length=20, choices=ROLES, verbose_name='Роль')
    is_visible = models.BooleanField(default=False, verbose_name='Видим')

    class Meta:
        unique_together = ['menu_item', 'role']
        ordering = ['menu_item', 'role']
        verbose_name = 'Настройка меню'
        verbose_name_plural = 'Настройки меню'

    def __str__(self):
        return f'{self.get_menu_item_display()} — {self.get_role_display()} — {"✓" if self.is_visible else "✗"}'


class QuizAnswerRecord(models.Model):
    """Запись ответа слушателя на конкретный вопрос теста."""
    person = models.ForeignKey('Person', on_delete=models.CASCADE,
        related_name='quiz_answers', verbose_name='Слушатель')
    step = models.ForeignKey('ModuleStep', on_delete=models.CASCADE,
        related_name='quiz_answers', verbose_name='Этап (тест)')
    question = models.ForeignKey('QuizQuestion', on_delete=models.CASCADE,
        related_name='answer_records', verbose_name='Вопрос')
    answer = models.JSONField(default=list, verbose_name='Ответ слушателя')
    is_correct = models.BooleanField(default=False, verbose_name='Правильно')
    score = models.FloatField(default=0, verbose_name='Баллы')
    answered_at = models.DateTimeField(auto_now=True, verbose_name='Время ответа')

    class Meta:
        unique_together = ['person', 'step', 'question']
        verbose_name = 'Ответ на вопрос'
        verbose_name_plural = 'Ответы на вопросы'

    def __str__(self):
        return f'{self.person} — Q{self.question.pk} — {"✓" if self.is_correct else "✗"}'