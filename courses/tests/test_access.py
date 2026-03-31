import json
from django.test import TestCase, Client
from courses.models import MenuPermission, LearningModule, ModuleStep, QuizQuestion, TrainingProgram
from courses.tests.helpers import BaseTestCase, create_menu_permissions, create_test_program, create_test_module


class MenuAccessTest(BaseTestCase):
    """Проверка доступа к разделам по ролям через MenuPermission."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        create_menu_permissions()

    # ── Неаутентифицированный пользователь ──

    def test_anonymous_redirect_to_login(self):
        """Неавторизованный пользователь перенаправляется на логин."""
        client = Client()
        urls = ['/dashboard/', '/programs/', '/persons/', '/modules/', '/learning/']
        for url in urls:
            resp = client.get(url)
            self.assertIn(resp.status_code, [301, 302], f'{url} не редиректит анонима')

    # ── Суперадмин — доступ ко всему ──

    def test_superadmin_access_all(self):
        """Суперадмин может открыть любой раздел."""
        client = self.get_client('superadmin')
        urls = ['/dashboard/', '/programs/', '/persons/', '/modules/', '/learning/',
                '/contracts/', '/settings/menu/']
        for url in urls:
            resp = client.get(url)
            self.assertNotEqual(resp.status_code, 403, f'Суперадмин не может открыть {url}')

    # ── Слушатель — ограниченный доступ ──

    def test_student_can_access_dashboard(self):
        """Слушатель может открыть дашборд."""
        client = self.get_client('student')
        resp = client.get('/dashboard/')
        self.assertEqual(resp.status_code, 200)

    def test_student_can_access_learning(self):
        """Слушатель может открыть раздел Обучение."""
        client = self.get_client('student')
        resp = client.get('/learning/')
        self.assertEqual(resp.status_code, 200)

    def test_student_cannot_access_programs(self):
        """Слушатель НЕ может открыть Программы."""
        client = self.get_client('student')
        resp = client.get('/programs/')
        self.assertEqual(resp.status_code, 403)

    def test_student_cannot_access_persons(self):
        """Слушатель НЕ может открыть Физические лица."""
        client = self.get_client('student')
        resp = client.get('/persons/')
        self.assertEqual(resp.status_code, 403)

    def test_student_cannot_access_modules(self):
        """Слушатель НЕ может открыть Модули."""
        client = self.get_client('student')
        resp = client.get('/modules/')
        self.assertEqual(resp.status_code, 403)

    def test_student_cannot_access_contracts(self):
        """Слушатель НЕ может открыть Договоры."""
        client = self.get_client('student')
        resp = client.get('/contracts/')
        self.assertEqual(resp.status_code, 403)

    def test_student_cannot_access_settings(self):
        """Слушатель НЕ может открыть Настройки меню."""
        client = self.get_client('student')
        resp = client.get('/settings/menu/')
        self.assertEqual(resp.status_code, 403)

    # ── Преподаватель ──

    def test_teacher_can_access_programs(self):
        """Преподаватель может открыть Программы."""
        client = self.get_client('teacher')
        resp = client.get('/programs/')
        self.assertEqual(resp.status_code, 200)

    def test_teacher_can_access_modules(self):
        """Преподаватель может открыть Модули."""
        client = self.get_client('teacher')
        resp = client.get('/modules/')
        self.assertEqual(resp.status_code, 200)

    def test_teacher_cannot_access_contracts(self):
        """Преподаватель НЕ может открыть Договоры."""
        client = self.get_client('teacher')
        resp = client.get('/contracts/')
        self.assertEqual(resp.status_code, 403)

    def test_teacher_cannot_access_learning(self):
        """Преподаватель НЕ может открыть Обучение."""
        client = self.get_client('teacher')
        resp = client.get('/learning/')
        self.assertEqual(resp.status_code, 403)

    # ── Администратор ──

    def test_admin_can_access_contracts(self):
        """Администратор может открыть Договоры."""
        client = self.get_client('admin')
        resp = client.get('/contracts/')
        self.assertEqual(resp.status_code, 200)

    def test_admin_cannot_access_settings(self):
        """Администратор НЕ может открыть Настройки меню."""
        client = self.get_client('admin')
        resp = client.get('/settings/menu/')
        self.assertEqual(resp.status_code, 403)

    # ── Динамическое изменение прав ──

    def test_dynamic_permission_change(self):
        """Изменение MenuPermission сразу влияет на доступ."""
        client = self.get_client('student')

        # Сначала запрещено
        resp = client.get('/programs/')
        self.assertEqual(resp.status_code, 403)

        # Открываем доступ
        MenuPermission.objects.update_or_create(
            menu_item='programs', role='student',
            defaults={'is_visible': True}
        )
        resp = client.get('/programs/')
        self.assertEqual(resp.status_code, 200)

        # Закрываем обратно
        MenuPermission.objects.filter(
            menu_item='programs', role='student'
        ).update(is_visible=False)
        resp = client.get('/programs/')
        self.assertEqual(resp.status_code, 403)


class APIAccessTest(BaseTestCase):
    """Проверка что API-эндпоинты тоже защищены по ролям."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        create_menu_permissions()

    def test_student_cannot_call_programs_api(self):
        """Слушатель не может вызвать API сохранения программы."""
        client = self.get_client('student')
        resp = client.post(
            '/programs/1/save/',
            data=json.dumps({'title': 'test'}),
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 403)

    def test_student_cannot_call_persons_api(self):
        """Слушатель не может вызвать API сообщений слушателя."""
        client = self.get_client('student')
        resp = client.get(f'/api/messages/{self.person_student.pk}/')
        self.assertEqual(resp.status_code, 403)

    def test_api_returns_json_for_ajax(self):
        """API возвращает JSON при запрете доступа для AJAX-запроса."""
        client = self.get_client('student')
        resp = client.get(
            f'/api/messages/{self.person_student.pk}/',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(resp.status_code, 403)
        data = json.loads(resp.content)
        self.assertIn('error', data)

    def test_api_returns_html_403_for_browser(self):
        """Обычный браузерный запрос к защищённой странице — HTML 403."""
        client = self.get_client('student')
        resp = client.get('/programs/')
        self.assertEqual(resp.status_code, 403)
        self.assertIn('text/html', resp['Content-Type'])


class ModuleAccessTest(BaseTestCase):
    """Проверка что слушатель может проходить модули через learning, но не управлять ими."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        create_menu_permissions()
        cls.program = create_test_program()
        cls.module = create_test_module(program=cls.program)
        cls.step = ModuleStep.objects.create(
            module=cls.module, title='Тест', type='quiz', order=1,
        )
        cls.question = QuizQuestion.objects.create(
            step=cls.step, text='Вопрос?', type='single',
            answers=['Да', 'Нет'], correct=[0], order=1,
        )

    # ── Слушатель: прохождение модуля — доступно ──

    def test_student_can_preview_module(self):
        """Слушатель может открыть прохождение модуля."""
        client = self.get_client('student')
        resp = client.get(f'/modules/{self.module.pk}/preview/')
        self.assertEqual(resp.status_code, 200)

    def test_student_can_get_module_steps(self):
        """Слушатель может загрузить этапы модуля (API)."""
        client = self.get_client('student')
        resp = client.get(f'/api/modules/{self.module.pk}/steps/')
        self.assertEqual(resp.status_code, 200)

    def test_student_can_get_step_questions(self):
        """Слушатель может загрузить вопросы теста (API)."""
        client = self.get_client('student')
        resp = client.get(f'/api/steps/{self.step.pk}/questions/')
        self.assertEqual(resp.status_code, 200)

    def test_student_can_open_quiz_preview(self):
        """Слушатель может открыть страницу тестирования."""
        client = self.get_client('student')
        resp = client.get(f'/modules/step/{self.step.pk}/quiz/preview/')
        self.assertEqual(resp.status_code, 200)

    # ── Слушатель: управление модулями — запрещено ──

    def test_student_cannot_access_module_list(self):
        """Слушатель НЕ может открыть список модулей."""
        client = self.get_client('student')
        resp = client.get('/modules/')
        self.assertEqual(resp.status_code, 403)

    def test_student_cannot_edit_module(self):
        """Слушатель НЕ может открыть конструктор модуля."""
        client = self.get_client('student')
        resp = client.get(f'/modules/{self.module.pk}/edit/')
        self.assertEqual(resp.status_code, 403)

    # ── Преподаватель: управление и просмотр — доступно ──

    def test_teacher_can_preview_module(self):
        """Преподаватель может открыть прохождение модуля."""
        client = self.get_client('teacher')
        resp = client.get(f'/modules/{self.module.pk}/preview/')
        self.assertEqual(resp.status_code, 200)

    def test_teacher_can_get_module_steps(self):
        """Преподаватель может загрузить этапы модуля."""
        client = self.get_client('teacher')
        resp = client.get(f'/api/modules/{self.module.pk}/steps/')
        self.assertEqual(resp.status_code, 200)
