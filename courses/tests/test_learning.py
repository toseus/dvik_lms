import json
from courses.models import ModuleAssignment
from courses.tests.helpers import (
    BaseTestCase, create_menu_permissions,
    create_full_module, assign_module_to_person,
)


class StudentLearningPageTest(BaseTestCase):
    """Тесты страницы «Обучение» для слушателя."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        create_menu_permissions()
        cls.data = create_full_module()

    def test_learning_page_empty(self):
        """Страница Обучение открывается, когда нет назначений — пустая."""
        client = self.get_client('student')
        resp = client.get('/learning/')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Пока нет назначенных модулей')

    def test_learning_page_with_module(self):
        """После назначения модуля — он появляется на странице Обучение."""
        assign_module_to_person(
            self.person_student, self.data['module'],
            assigned_by=self.admin_user,
        )
        client = self.get_client('student')
        resp = client.get('/learning/')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, self.data['module'].title)

    def test_learning_page_hides_inactive_assignment(self):
        """Деактивированное назначение не показывается в Обучении."""
        assignment = assign_module_to_person(
            self.person_student, self.data['module'],
            assigned_by=self.admin_user,
        )
        assignment.is_active = False
        assignment.save()

        client = self.get_client('student')
        resp = client.get('/learning/')
        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, self.data['module'].title)


class StudentModulePreviewTest(BaseTestCase):
    """Тесты прохождения модуля слушателем."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        create_menu_permissions()
        cls.data = create_full_module()
        assign_module_to_person(
            cls.person_student, cls.data['module'],
            assigned_by=cls.admin_user,
        )

    def test_student_can_open_module_preview(self):
        """Слушатель может открыть прохождение модуля."""
        client = self.get_client('student')
        resp = client.get(f'/modules/{self.data["module"].pk}/preview/')
        self.assertEqual(resp.status_code, 200)

    def test_student_sees_steps(self):
        """API этапов возвращает 4 этапа для слушателя."""
        client = self.get_client('student')
        resp = client.get(f'/api/modules/{self.data["module"].pk}/steps/')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        steps = data.get('steps', [])
        self.assertEqual(len(steps), 4)

    def test_steps_have_correct_types(self):
        """Этапы возвращаются с правильными типами."""
        client = self.get_client('student')
        resp = client.get(f'/api/modules/{self.data["module"].pk}/steps/')
        data = json.loads(resp.content)
        types = [s.get('type') for s in data.get('steps', [])]
        self.assertIn('material', types)
        self.assertIn('slide', types)
        self.assertIn('quiz', types)
        self.assertIn('final_exam', types)
