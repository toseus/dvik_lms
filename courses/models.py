from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings



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

    # Связь с организациями (все доступные организации)
    organizations = models.ManyToManyField(
        'Company',
        blank=True,
        related_name='users',
        verbose_name='Организации'
    )

    # Текущая организация (одна из списка organizations)
    current_organization = models.ForeignKey(
        'Company',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='current_users',
        verbose_name='Текущая организация'
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

    snils = models.CharField(max_length=14, unique=True, verbose_name='СНИЛС')
    last_name = models.CharField(max_length=100, verbose_name='Фамилия')
    first_name = models.CharField(max_length=100, verbose_name='Имя')
    middle_name = models.CharField(max_length=100, blank=True, verbose_name='Отчество')
    last_name_en = models.CharField(max_length=100, blank=True, verbose_name='Фамилия (англ)')
    first_name_en = models.CharField(max_length=100, blank=True, verbose_name='Имя (англ)')
    dob = models.DateField(null=True, blank=True, verbose_name='Дата рождения')
    city = models.CharField(max_length=100, blank=True, verbose_name='Город')
    position = models.CharField(max_length=200, blank=True, verbose_name='Должность')
    workplace = models.CharField(max_length=200, blank=True, verbose_name='Место работы')
    phone = models.CharField(max_length=20, blank=True, verbose_name='Телефон')
    email = models.EmailField(blank=True, verbose_name='Email')
    notes = models.TextField(blank=True, verbose_name='Примечания')

    # Код для входа — 6 цифр, вводится вручную при создании
    code = models.CharField(
        max_length=6,
        blank=True,
        verbose_name='Код доступа (6 цифр)',
        help_text='Используется как пароль для входа в систему'
    )

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


class Order(models.Model):
    """Заявка слушателя"""
    person = models.ForeignKey(Person, on_delete=models.CASCADE, related_name='orders', verbose_name='Слушатель')
    date = models.DateField(verbose_name='Дата заявки')
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Сумма')
    payer = models.CharField(max_length=200, blank=True, verbose_name='Плательщик')
    partner = models.CharField(max_length=100, blank=True, verbose_name='Сетевой партнёр')
    author = models.CharField(max_length=200, blank=True, verbose_name='Автор')
    created_at = models.DateTimeField(auto_now_add=True)

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

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='programs', verbose_name='Заявка')
    category = models.CharField(max_length=50, blank=True, verbose_name='Категория')
    prog_type = models.CharField(max_length=50, blank=True, verbose_name='Тип')
    code = models.CharField(max_length=200, verbose_name='Код/название программы')
    date_start = models.DateField(verbose_name='Дата начала')
    date_end = models.DateField(verbose_name='Дата окончания')
    discount = models.CharField(max_length=50, blank=True, verbose_name='Скидка')
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='К оплате')
    cert_number = models.CharField(max_length=100, blank=True, verbose_name='№ сертификата')
    reg_number = models.CharField(max_length=100, blank=True, verbose_name='Рег. номер')
    grade = models.CharField(max_length=50, blank=True, verbose_name='Оценка')
    issue_status = models.CharField(max_length=3, choices=IssueStatus.choices, default=IssueStatus.NO_ISSUE,
                                    verbose_name='Статус выдачи')
    notes = models.TextField(blank=True, verbose_name='Примечания')

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