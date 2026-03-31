import json
from courses.models import LearningModule, ModuleStep, QuizQuestion
from courses.tests.helpers import (
    BaseTestCase, create_menu_permissions,
    create_test_program, create_test_module,
)


class ModuleListTest(BaseTestCase):

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        create_menu_permissions()
        cls.program = create_test_program()
        cls.module = create_test_module(program=cls.program)

    def test_module_list_loads(self):
        """Список модулей открывается."""
        client = self.get_client('admin')
        resp = client.get('/modules/')
        self.assertEqual(resp.status_code, 200)

    def test_module_edit_loads(self):
        """Конструктор модуля открывается."""
        client = self.get_client('admin')
        resp = client.get(f'/modules/{self.module.pk}/edit/')
        self.assertEqual(resp.status_code, 200)

    def test_module_preview_loads(self):
        """Прохождение модуля открывается."""
        client = self.get_client('admin')
        resp = client.get(f'/modules/{self.module.pk}/preview/')
        self.assertEqual(resp.status_code, 200)


class QuizAPITest(BaseTestCase):
    """Тесты API тестирования."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        create_menu_permissions()
        cls.program = create_test_program()
        cls.module = create_test_module(program=cls.program)

        # Этап — тест
        cls.step = ModuleStep.objects.create(
            module=cls.module,
            title='Промежуточный тест',
            type='quiz',
            order=1,
        )

        # Вопрос
        cls.question = QuizQuestion.objects.create(
            step=cls.step,
            text='Столица России?',
            type='single',
            answers=['Москва', 'Петербург', 'Новосибирск'],
            correct=[0],
            order=1,
        )

    def test_load_questions(self):
        """API загрузки вопросов теста."""
        client = self.get_client('admin')
        resp = client.get(f'/api/steps/{self.step.pk}/questions/')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertTrue(len(data.get('questions', data)) > 0)

    def test_quiz_preview_loads(self):
        """Страница тестирования открывается."""
        client = self.get_client('admin')
        resp = client.get(f'/modules/step/{self.step.pk}/quiz/preview/')
        self.assertEqual(resp.status_code, 200)

    def test_save_single_answer(self):
        """API сохранения одного ответа на вопрос."""
        # Нужен пользователь с привязанной Person (get_current_person)
        client = self.get_client('teacher')
        resp = client.post(
            f'/api/quiz/{self.step.pk}/save-answer/',
            data=json.dumps({
                'question_id': self.question.pk,
                'answer': [0],
                'is_correct': True,
                'score': 1,
            }),
            content_type='application/json'
        )
        self.assertIn(resp.status_code, [200, 201])
