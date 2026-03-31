import json
from courses.models import ModuleAssignment, QuizAnswerRecord, ModuleResult
from courses.tests.helpers import (
    BaseTestCase, create_menu_permissions, create_full_module,
)


class FullLearningFlowTest(BaseTestCase):
    """
    Сквозной тест: полный цикл обучения.
    Админ назначает модуль -> слушатель видит -> проходит этапы -> результат в БД.
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        create_menu_permissions()
        cls.data = create_full_module()

    def test_full_learning_cycle(self):
        """Полный цикл: назначение -> ЛК -> прохождение -> результат."""
        admin_client = self.get_client('admin')
        student_client = self.get_client('student')
        module = self.data['module']
        step_quiz = self.data['step_quiz']
        step_final = self.data['step_final']
        questions = self.data['questions']

        # === ШАГ 1. Админ назначает модуль ===
        resp = admin_client.post(
            f'/api/persons/{self.person_student.pk}/assign-modules/',
            data=json.dumps({'module_ids': [module.pk]}),
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(
            ModuleAssignment.objects.filter(
                person=self.person_student, module=module
            ).exists()
        )

        # === ШАГ 2. Слушатель видит модуль в ЛК ===
        resp = student_client.get('/learning/')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, module.title)

        # === ШАГ 3. Слушатель открывает модуль ===
        resp = student_client.get(f'/modules/{module.pk}/preview/')
        self.assertEqual(resp.status_code, 200)

        # === ШАГ 4. Слушатель видит этапы ===
        resp = student_client.get(f'/api/modules/{module.pk}/steps/')
        self.assertEqual(resp.status_code, 200)
        steps = json.loads(resp.content).get('steps', [])
        self.assertEqual(len(steps), 4)

        # === ШАГ 5. Слушатель проходит промежуточный тест ===
        correct_answers = [[0], [0, 1, 3], [0, 1, 2]]
        for q, correct in zip(questions, correct_answers):
            student_client.post(
                f'/api/quiz/{step_quiz.pk}/save-answer/',
                data=json.dumps({
                    'question_id': q.pk,
                    'answer': correct,
                    'is_correct': True,
                    'score': 1,
                }),
                content_type='application/json'
            )

        quiz_answers = QuizAnswerRecord.objects.filter(
            person=self.person_student, step=step_quiz,
        )
        self.assertEqual(quiz_answers.count(), 3)

        # === ШАГ 6. Слушатель загружает вопросы итоговой ===
        resp = student_client.get(f'/api/final-exam/{step_final.pk}/questions/')
        self.assertEqual(resp.status_code, 200)
        exam_questions = json.loads(resp.content).get('questions', [])
        self.assertGreater(len(exam_questions), 0)

        # === ШАГ 7. Слушатель сдаёт итоговую ===
        resp = student_client.post(
            f'/api/final-exam/{step_final.pk}/submit/',
            data=json.dumps({
                'score': 100,
                'quiz_scores': {},
                'details': [],
            }),
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 200)
        result_data = json.loads(resp.content)
        self.assertTrue(result_data.get('passed'))

        # === ШАГ 8. Результат записан в БД ===
        result = ModuleResult.objects.filter(
            person=self.person_student, module=module,
        ).first()
        self.assertIsNotNone(result, 'ModuleResult не создан после итоговой')
        self.assertTrue(result.final_exam_passed)
        self.assertEqual(result.final_exam_score, 100)
