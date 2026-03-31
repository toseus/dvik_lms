import json
from courses.models import QuizAnswerRecord, ModuleResult
from courses.tests.helpers import (
    BaseTestCase, create_menu_permissions,
    create_full_module, assign_module_to_person,
)


class QuizFlowTest(BaseTestCase):
    """Полный цикл прохождения промежуточного теста."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        create_menu_permissions()
        cls.data = create_full_module()
        assign_module_to_person(
            cls.person_student, cls.data['module'],
            assigned_by=cls.admin_user,
        )

    def _get_student_client(self):
        return self.get_client('student')

    # ── Загрузка вопросов ──

    def test_load_quiz_questions(self):
        """Слушатель может загрузить вопросы теста."""
        client = self._get_student_client()
        step = self.data['step_quiz']
        resp = client.get(f'/api/steps/{step.pk}/questions/')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        questions = data.get('questions', data)
        self.assertEqual(len(questions), 3)

    # ── Сохранение ответов ──

    def test_save_single_answer(self):
        """Ответ на вопрос сохраняется в БД."""
        client = self._get_student_client()
        step = self.data['step_quiz']
        q = self.data['questions'][0]

        resp = client.post(
            f'/api/quiz/{step.pk}/save-answer/',
            data=json.dumps({
                'question_id': q.pk,
                'answer': [0],
                'is_correct': True,
                'score': 1,
            }),
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 200)

        record = QuizAnswerRecord.objects.filter(
            person=self.person_student, step=step, question=q,
        ).first()
        self.assertIsNotNone(record)
        self.assertTrue(record.is_correct)

    def test_save_wrong_answer(self):
        """Неправильный ответ тоже сохраняется."""
        client = self._get_student_client()
        step = self.data['step_quiz']
        q = self.data['questions'][0]

        resp = client.post(
            f'/api/quiz/{step.pk}/save-answer/',
            data=json.dumps({
                'question_id': q.pk,
                'answer': [2],
                'is_correct': False,
                'score': 0,
            }),
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 200)

        record = QuizAnswerRecord.objects.get(
            person=self.person_student, step=step, question=q,
        )
        self.assertFalse(record.is_correct)
        self.assertEqual(record.score, 0)

    def test_update_answer_overwrites(self):
        """Повторный ответ на тот же вопрос перезаписывается."""
        client = self._get_student_client()
        step = self.data['step_quiz']
        q = self.data['questions'][0]

        # Первый ответ — неправильный
        client.post(
            f'/api/quiz/{step.pk}/save-answer/',
            data=json.dumps({
                'question_id': q.pk, 'answer': [2],
                'is_correct': False, 'score': 0,
            }),
            content_type='application/json'
        )

        # Второй ответ — правильный
        client.post(
            f'/api/quiz/{step.pk}/save-answer/',
            data=json.dumps({
                'question_id': q.pk, 'answer': [0],
                'is_correct': True, 'score': 1,
            }),
            content_type='application/json'
        )

        # Ровно 1 запись (обновлённая)
        count = QuizAnswerRecord.objects.filter(
            person=self.person_student, step=step, question=q,
        ).count()
        self.assertEqual(count, 1)

        record = QuizAnswerRecord.objects.get(
            person=self.person_student, step=step, question=q,
        )
        self.assertTrue(record.is_correct)

    # ── Загрузка сохранённых ответов ──

    def test_load_saved_answers(self):
        """Сохранённые ответы загружаются при повторном входе в тест."""
        client = self._get_student_client()
        step = self.data['step_quiz']
        q = self.data['questions'][0]

        client.post(
            f'/api/quiz/{step.pk}/save-answer/',
            data=json.dumps({
                'question_id': q.pk, 'answer': [0],
                'is_correct': True, 'score': 1,
            }),
            content_type='application/json'
        )

        resp = client.get(f'/api/quiz/{step.pk}/load-answers/')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        answers = data.get('answers', {})
        self.assertIn(str(q.pk), answers)

    # ── Сброс прогресса ──

    def test_reset_quiz_progress(self):
        """Сброс удаляет все ответы теста."""
        client = self._get_student_client()
        step = self.data['step_quiz']

        for q in self.data['questions']:
            client.post(
                f'/api/quiz/{step.pk}/save-answer/',
                data=json.dumps({
                    'question_id': q.pk, 'answer': [0],
                    'is_correct': True, 'score': 1,
                }),
                content_type='application/json'
            )

        count_before = QuizAnswerRecord.objects.filter(
            person=self.person_student, step=step,
        ).count()
        self.assertEqual(count_before, 3)

        resp = client.post(f'/api/quiz/{step.pk}/reset-answers/')
        self.assertEqual(resp.status_code, 200)

        count_after = QuizAnswerRecord.objects.filter(
            person=self.person_student, step=step,
        ).count()
        self.assertEqual(count_after, 0)

    # ── Полный прогон: все 3 вопроса ──

    def test_complete_quiz_all_correct(self):
        """Прохождение всех вопросов теста с правильными ответами."""
        client = self._get_student_client()
        step = self.data['step_quiz']
        questions = self.data['questions']

        correct_answers = [[0], [0, 1, 3], [0, 1, 2]]
        for q, correct in zip(questions, correct_answers):
            client.post(
                f'/api/quiz/{step.pk}/save-answer/',
                data=json.dumps({
                    'question_id': q.pk, 'answer': correct,
                    'is_correct': True, 'score': 1,
                }),
                content_type='application/json'
            )

        records = QuizAnswerRecord.objects.filter(
            person=self.person_student, step=step,
        )
        self.assertEqual(records.count(), 3)
        self.assertTrue(all(r.is_correct for r in records))


class FinalExamFlowTest(BaseTestCase):
    """Тесты итоговой аттестации."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        create_menu_permissions()
        cls.data = create_full_module()
        assign_module_to_person(
            cls.person_student, cls.data['module'],
            assigned_by=cls.admin_user,
        )

    def test_load_final_exam_questions(self):
        """API итоговой возвращает вопросы из промежуточных тестов."""
        client = self.get_client('student')
        step_final = self.data['step_final']
        resp = client.get(f'/api/final-exam/{step_final.pk}/questions/')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        questions = data.get('questions', [])
        # exam_config задаёт 2 вопроса из quiz
        self.assertEqual(len(questions), 2)

    def test_submit_final_exam_passed(self):
        """Сдача итоговой — ModuleResult с passed=True."""
        client = self.get_client('student')
        step_final = self.data['step_final']

        resp = client.post(
            f'/api/final-exam/{step_final.pk}/submit/',
            data=json.dumps({
                'score': 100,
                'quiz_scores': {},
                'details': [],
            }),
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertTrue(data.get('passed'))

        result = ModuleResult.objects.filter(
            person=self.person_student,
            module=self.data['module'],
        ).first()
        self.assertIsNotNone(result)
        self.assertTrue(result.final_exam_passed)
        self.assertEqual(result.final_exam_score, 100)

    def test_submit_final_exam_failed(self):
        """Несдача итоговой — ModuleResult с passed=False."""
        client = self.get_client('student')
        step_final = self.data['step_final']

        resp = client.post(
            f'/api/final-exam/{step_final.pk}/submit/',
            data=json.dumps({
                'score': 30,
                'quiz_scores': {},
                'details': [],
            }),
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertFalse(data.get('passed'))

        result = ModuleResult.objects.filter(
            person=self.person_student,
            module=self.data['module'],
        ).first()
        self.assertIsNotNone(result)
        self.assertFalse(result.final_exam_passed)
