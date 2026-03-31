from django.test import TestCase
from django.db import IntegrityError
from django.core.exceptions import ValidationError
from courses.models import Space, User, Person
from courses.tests.helpers import BaseTestCase


class SpaceModelTest(TestCase):

    def test_create_space(self):
        """Пространство создаётся с корректными полями."""
        space = Space.objects.create(name='Сахалин', slug='sakhalin')
        self.assertEqual(str(space), 'Сахалин')
        self.assertTrue(space.is_active)

    def test_slug_unique(self):
        """Два пространства с одинаковым slug — ошибка."""
        Space.objects.create(name='A', slug='same')
        with self.assertRaises(IntegrityError):
            Space.objects.create(name='B', slug='same')


class UserModelTest(TestCase):

    def test_create_user_with_role(self):
        """User создаётся с указанной ролью."""
        user = User.objects.create_user(
            username='testuser', password='pass123',
            role='teacher'
        )
        self.assertEqual(user.role, 'teacher')

    def test_default_role_is_student(self):
        """По умолчанию роль — student."""
        user = User.objects.create_user(username='defuser', password='pass123')
        self.assertEqual(user.role, 'student')


class PersonModelTest(BaseTestCase):

    def test_person_str(self):
        """__str__ Person содержит фамилию."""
        s = str(self.person_student)
        self.assertIn('Иванов', s)

    def test_snils_optional(self):
        """Person без СНИЛС создаётся без ошибки."""
        p = Person.objects.create(
            last_name='Сидоров', first_name='Сидор',
            code='111111',
        )
        self.assertEqual(p.snils, '')

    def test_has_account_property(self):
        """has_account возвращает True если есть user."""
        self.assertTrue(self.person_student.has_account)

    def test_has_account_false(self):
        """has_account False для Person без user."""
        p = Person(last_name='Без', first_name='Аккаунта')
        p.user = None
        self.assertFalse(p.has_account)


class PersonSignalTest(TestCase):
    """Проверка автосоздания User при создании Person через signal."""

    def test_auto_user_creation(self):
        """При создании Person без user автоматически создаётся User."""
        p = Person.objects.create(
            last_name='Новый', first_name='Человек',
        )
        p.refresh_from_db()
        self.assertIsNotNone(p.user)
        # Логин = str(pk)
        self.assertEqual(p.user.username, str(p.pk))
        # Код сгенерирован (6 цифр)
        self.assertEqual(len(p.code), 6)
        self.assertTrue(p.code.isdigit())
        # Роль — student
        self.assertEqual(p.user.role, 'student')

    def test_signal_does_not_duplicate_user(self):
        """Повторное сохранение Person не создаёт второго User."""
        p = Person.objects.create(
            last_name='Тест', first_name='Повтор',
        )
        p.refresh_from_db()
        user_pk = p.user.pk
        p.last_name = 'Изменённый'
        p.save()
        p.refresh_from_db()
        self.assertEqual(p.user.pk, user_pk)

    def test_signal_skips_if_user_set(self):
        """Если Person создаётся с user — signal не создаёт нового."""
        user = User.objects.create_user(username='existing', password='pass123')
        p = Person.objects.create(
            last_name='С_юзером', first_name='Тест',
            user=user, code='999999',
        )
        self.assertEqual(p.user.pk, user.pk)
        # Других User не создалось
        self.assertEqual(User.objects.filter(username=str(p.pk)).count(), 0)
