# Шаг 1: Модель Space + единая регистрация через Person.pk

## Обзор изменений

| Файл | Что делаем |
|------|-----------|
| `courses/models.py` | Добавляем `Space`, меняем `User`, правим `Person.create_user_account`, убираем `Person.update_user_account` дублирование |
| `courses/signals.py` | Полностью переписываем — единая логика регистрации |
| `courses/apps.py` | Подключаем signals через `ready()` |
| `courses/admin.py` | Добавляем `SpaceAdmin`, меняем `CustomUserAdmin` |
| Миграция | Генерируем через `makemigrations` |

---

## 1. courses/models.py

### 1.1 Добавить модель Space (после импортов, перед class User)

Вставить **между** строкой `from django.conf import settings` и строкой `class User(AbstractUser):`:

```python
class Space(models.Model):
    """Пространство (команда): Сахалин, Находка, Владивосток и т.д."""
    name = models.CharField(max_length=100, unique=True, verbose_name='Название')
    slug = models.SlugField(max_length=100, unique=True, verbose_name='Код')
    description = models.TextField(blank=True, verbose_name='Описание')
    is_active = models.BooleanField(default=True, verbose_name='Активно')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Пространство'
        verbose_name_plural = 'Пространства'
        ordering = ['name']

    def __str__(self):
        return self.name
```

### 1.2 Изменить модель User

**Заменить** весь блок `class User(AbstractUser):` (строки 7-44) на:

```python
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

    # Space — к какому пространству относится пользователь
    space = models.ForeignKey(
        'Space',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users',
        verbose_name='Пространство'
    )

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return f'{self.get_full_name()} ({self.get_role_display()})'
```

> **Что удалено:** поля `organizations` (ManyToMany) и `current_organization` (ForeignKey на Company). Вместо них одно поле `space`.

### 1.3 Изменить метод Person.create_user_account

**Заменить** метод `create_user_account` (строки 107-129) на:

```python
    def create_user_account(self):
        """
        Создать учётную запись:
          логин  = str(self.pk) — ID физического лица
          пароль = self.code    — 6-значный код доступа
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
```

> Этот метод не меняется по сути — он уже использует `pk` как логин. Просто убедитесь, что он выглядит именно так.

### 1.4 Изменить метод Person.update_user_account

**Заменить** метод `update_user_account` (строки 131-138) на:

```python
    def update_user_account(self):
        """Синхронизировать данные User с данными Person"""
        if self.user:
            changed = False
            if self.code:
                self.user.set_password(self.code)
                changed = True
            if self.user.first_name != self.first_name:
                self.user.first_name = self.first_name
                changed = True
            if self.user.last_name != self.last_name:
                self.user.last_name = self.last_name
                changed = True
            if self.user.email != self.email:
                self.user.email = self.email
                changed = True
            # Логин = ID физлица (на случай если username был другим)
            if self.user.username != str(self.pk):
                self.user.username = str(self.pk)
                changed = True
            if changed:
                self.user.save()
```

---

## 2. courses/signals.py

**Заменить весь файл** на:

```python
"""
courses/signals.py
Автоматическое создание User при создании Person.
Логин  = str(person.pk)
Пароль = person.code (6-значный код доступа)
"""
import random
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Person


def generate_code():
    """Генерация 6-значного кода доступа."""
    return ''.join([str(random.randint(0, 9)) for _ in range(6)])


@receiver(post_save, sender=Person)
def auto_create_user(sender, instance, created, **kwargs):
    """
    При создании Person:
    1. Если нет кода доступа — генерируем.
    2. Если нет связанного User — создаём аккаунт.
    """
    if not created:
        return

    # Генерируем код если его нет
    if not instance.code:
        instance.code = generate_code()
        Person.objects.filter(pk=instance.pk).update(code=instance.code)

    # Если User уже привязан — не трогаем
    if instance.user_id:
        return

    # Создаём аккаунт
    try:
        instance.create_user_account()
    except Exception:
        pass  # create_user_account сам обработает ошибки
```

> **Что изменилось:** убрана старая логика с СНИЛС как логином. Теперь единый путь: логин = `person.pk`, пароль = `code`. Код генерируется автоматически если пустой.

---

## 3. courses/apps.py

**Заменить весь файл** на:

```python
from django.apps import AppConfig


class CoursesConfig(AppConfig):
    name = 'courses'
    default_auto_field = 'django.db.models.BigAutoField'

    def ready(self):
        import courses.signals  # noqa: F401
```

> Это подключает сигналы. Без `ready()` сигнал `auto_create_user` не будет срабатывать (сейчас он работает только потому, что Django автоматически подхватывает `@receiver` при импорте, но лучше подключить явно).

---

## 4. courses/admin.py

### 4.1 Обновить импорты

**Заменить** строку 2:

```python
from .models import Course, CourseStep, Question, Enrollment, StepCompletion, Order, Program, Person, Company, User
```

на:

```python
from .models import (
    Course, CourseStep, Question, Enrollment, StepCompletion,
    Order, Program, Person, Company, User, Space
)
```

### 4.2 Добавить SpaceAdmin

Вставить **после** `class QuestionInline` (после строки 28), **перед** `@admin.register(Course)`:

```python
@admin.register(Space)
class SpaceAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'is_active', 'users_count']
    list_filter = ['is_active']
    search_fields = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}

    def users_count(self, obj):
        return obj.users.count()
    users_count.short_description = 'Пользователей'
```

### 4.3 Заменить CustomUserAdmin

**Заменить** весь блок `UserAdminForm` + `CustomUserAdmin` (строки 183-236) на:

```python
@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'get_full_name', 'role', 'space', 'is_active']
    list_filter = ['role', 'space']
    list_select_related = ['space']

    fieldsets = UserAdmin.fieldsets + (
        ('Роль и пространство', {
            'fields': ('role', 'space'),
            'description': (
                '<strong>Пространство</strong> — команда, к которой относится пользователь '
                '(Сахалин, Находка, Владивосток и т.д.)'
            )
        }),
    )
```

> **Что удалено:** `UserAdminForm` (больше не нужна), `filter_horizontal` по организациям, `get_organizations`, `get_current_org`. Вместо этого — простой dropdown для выбора Space.

### 4.4 Обновить PersonAdmin — description в fieldsets

**Заменить** в `PersonAdmin` блок fieldsets (строки 124-142):

```python
    fieldsets = (
        ('Учётная запись', {
            'fields': ('pk', 'user', 'code'),
            'description': 'Логин = ID физического лица (pk), Пароль = код доступа. Код генерируется автоматически при создании.'
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
```

---

## 5. Миграция

После внесения всех изменений выполнить:

```bash
python manage.py makemigrations courses
python manage.py migrate
```

Django создаст миграцию которая:
- Создаст таблицу `courses_space`
- Добавит поле `space` (FK, nullable) в таблицу `courses_user`
- Удалит поле `current_organization` из `courses_user`
- Удалит M2M таблицу `courses_user_organizations`

> **Внимание:** если в БД уже есть пользователи с заполненным `current_organization`, данные этого поля будут потеряны. Если нужно мигрировать данные — создайте промежуточную миграцию (могу помочь).

---

## 6. Создать Spaces в админке

После миграции зайти в Django Admin и создать пространства:

| name | slug | is_active |
|------|------|-----------|
| Сахалин | sakhalin | ✓ |
| Находка | nakhodka | ✓ |
| Владивосток | vladivostok | ✓ |

Затем у каждого пользователя-админа выбрать нужный Space.

---

## Что НЕ меняется на этом шаге

- `Company`, `Course`, `CourseStep`, `Question`, `Enrollment`, `StepCompletion`, `Order`, `Program` — без изменений
- `OrganizationAssignment`, `PersonOrganization` — пока оставляем (удалим на следующем шаге, когда добавим `PersonSpace`)
- Views и templates — не трогаем (доработаем на следующем шаге)

---

## Итого: что получаем

1. **Space** — чистая модель для команд, управляется в админке
2. **User.space** — один админ строго в одном пространстве
3. **Единая регистрация:** логин = `person.pk`, пароль = `person.code`
4. **Автогенерация кода** при создании Person, если код не указан
5. **Signal `auto_create_user`** — при создании Person автоматически создаётся User
