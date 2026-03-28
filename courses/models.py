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
    person = models.ForeignKey(Person, on_delete=models.CASCADE, related_name='orders', verbose_name='Слушатель')
    date = models.DateField(verbose_name='Дата заявки')
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Сумма')
    payer = models.CharField(max_length=200, blank=True, verbose_name='Плательщик')
    partner = models.CharField(max_length=100, blank=True, verbose_name='Сетевой партнёр')
    author = models.CharField(max_length=200, blank=True, verbose_name='Автор')
    # Новые поля
    signer = models.ForeignKey('Signer', on_delete=models.SET_NULL, null=True, blank=True, related_name='orders', verbose_name='Подписант')
    payer_company = models.ForeignKey('Company', on_delete=models.SET_NULL, null=True, blank=True, related_name='paid_orders', verbose_name='Плательщик (организация)')
    payer_is_person = models.BooleanField(default=False, verbose_name='Плательщик — сам слушатель')
    contract = models.ForeignKey('Contract', on_delete=models.SET_NULL, null=True, blank=True, related_name='orders', verbose_name='Договор')
    space = models.ForeignKey('Space', on_delete=models.SET_NULL, null=True, blank=True, related_name='orders', verbose_name='Организация')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_orders', verbose_name='Кто создал')
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


class TrainingProgram(models.Model):
    """Программа обучения (справочник)."""
    code = models.CharField(max_length=100, blank=True, verbose_name='Сокращение')
    title = models.TextField(verbose_name='Название программы')
    title_eng = models.TextField(blank=True, verbose_name='Название (англ)')
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='Стоимость')
    new_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='Стоимость текущая')
    department = models.CharField(max_length=100, blank=True, verbose_name='Подразделение')
    category = models.CharField(max_length=100, blank=True, verbose_name='Категория')
    direction = models.CharField(max_length=200, blank=True, verbose_name='Направление')
    status = models.CharField(max_length=50, blank=True, verbose_name='Статус')
    period_hours = models.PositiveIntegerField(null=True, blank=True, verbose_name='Часов')
    period_days = models.PositiveIntegerField(null=True, blank=True, verbose_name='Дней')
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
    image_url = models.URLField(max_length=500, blank=True, verbose_name='URL изображения')
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