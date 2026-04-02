"""
Тесты API ручного добавления и сохранения вопросов:
POST /api/steps/<pk>/questions/save/
GET  /api/steps/<pk>/questions/
"""
import json
from courses.models import LearningModule, ModuleStep, QuizQuestion
from courses.tests.helpers import (
    BaseTestCase, create_menu_permissions,
    create_test_program, create_test_module,
)


class QuestionsSaveTest(BaseTestCase):
    """Тесты сохранения вопросов через API."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        create_menu_permissions()
        cls.program = create_test_program()
        cls.module = create_test_module(program=cls.program)
        cls.step = ModuleStep.objects.create(
            module=cls.module, title='Тест', type='quiz', order=1,
        )

    def _save_url(self):
        return f'/api/steps/{self.step.pk}/questions/save/'

    def _load_url(self):
        return f'/api/steps/{self.step.pk}/questions/'

    def _make_question(self, text='Вопрос?', qtype='single', answers=None,
                       correct=None, qid=None):
        return {
            'id': qid,
            'type': qtype,
            'text': text,
            'points': 1,
            'image_url': '',
            'explanation': '',
            'answers': answers or ['Да', 'Нет'],
            'correct': correct or [0],
            'terms': None,
        }

    def _post_questions(self, questions):
        client = self.get_client('admin')
        return client.post(
            self._save_url(),
            data=json.dumps({'questions': questions}),
            content_type='application/json',
        )

    def _load_questions(self):
        client = self.get_client('admin')
        resp = client.get(self._load_url())
        return json.loads(resp.content)['questions']

    # ── Базовое сохранение ──

    def test_save_one_new_question(self):
        """Сохранение одного нового вопроса."""
        resp = self._post_questions([self._make_question('Столица?')])
        data = json.loads(resp.content)
        self.assertTrue(data['ok'])
        self.assertEqual(data['count'], 1)
        self.assertEqual(QuizQuestion.objects.filter(step=self.step).count(), 1)

    def test_save_three_new_questions(self):
        """Сохранение трёх новых вопросов за один запрос."""
        questions = [
            self._make_question('Вопрос 1'),
            self._make_question('Вопрос 2'),
            self._make_question('Вопрос 3'),
        ]
        resp = self._post_questions(questions)
        data = json.loads(resp.content)
        self.assertTrue(data['ok'])
        self.assertEqual(data['count'], 3)
        self.assertEqual(QuizQuestion.objects.filter(step=self.step).count(), 3)

    def test_saved_questions_load_correctly(self):
        """Сохранённые вопросы корректно загружаются через API."""
        self._post_questions([
            self._make_question('Первый'),
            self._make_question('Второй'),
            self._make_question('Третий'),
        ])
        loaded = self._load_questions()
        self.assertEqual(len(loaded), 3)
        texts = [q['text'] for q in loaded]
        self.assertIn('Первый', texts)
        self.assertIn('Второй', texts)
        self.assertIn('Третий', texts)

    def test_loaded_questions_have_ids(self):
        """После сохранения вопросы имеют id (не null)."""
        self._post_questions([self._make_question('Test')])
        loaded = self._load_questions()
        self.assertIsNotNone(loaded[0]['id'])
        self.assertIsInstance(loaded[0]['id'], int)

    # ── Повторное сохранение (ключевой сценарий бага) ──

    def test_resave_with_ids_preserves_questions(self):
        """
        Сохранить 3 вопроса → загрузить → пересохранить с теми же id →
        вопросы не должны пропасть.
        """
        self._post_questions([
            self._make_question('Q1'),
            self._make_question('Q2'),
            self._make_question('Q3'),
        ])
        loaded = self._load_questions()
        self.assertEqual(len(loaded), 3)

        # Пересохраняем с полученными id (как это делает фронтенд)
        resp = self._post_questions(loaded)
        data = json.loads(resp.content)
        self.assertTrue(data['ok'])
        self.assertEqual(data['count'], 3)

        # Проверяем что вопросы на месте
        reloaded = self._load_questions()
        self.assertEqual(len(reloaded), 3)

    def test_add_fourth_question_to_existing_three(self):
        """
        Сохранить 3 → загрузить → добавить 4-й (id=null) → сохранить →
        должно быть 4 вопроса.
        """
        self._post_questions([
            self._make_question('Q1'),
            self._make_question('Q2'),
            self._make_question('Q3'),
        ])
        loaded = self._load_questions()
        self.assertEqual(len(loaded), 3)

        # Добавляем 4-й вопрос (как делает addQuestion() на фронте)
        loaded.append(self._make_question('Q4 новый'))
        resp = self._post_questions(loaded)
        data = json.loads(resp.content)
        self.assertTrue(data['ok'])
        self.assertEqual(data['count'], 4)

        reloaded = self._load_questions()
        self.assertEqual(len(reloaded), 4)

    def test_multiple_rounds_of_adding(self):
        """
        3 раунда: сохранить 1 → добавить ещё 1 → добавить ещё 1.
        Итого 3 вопроса.
        """
        # Раунд 1
        self._post_questions([self._make_question('R1')])
        loaded = self._load_questions()
        self.assertEqual(len(loaded), 1)

        # Раунд 2
        loaded.append(self._make_question('R2'))
        self._post_questions(loaded)
        loaded = self._load_questions()
        self.assertEqual(len(loaded), 2)

        # Раунд 3
        loaded.append(self._make_question('R3'))
        self._post_questions(loaded)
        loaded = self._load_questions()
        self.assertEqual(len(loaded), 3)

    # ── Обновление существующих ──

    def test_update_question_text(self):
        """Изменение текста существующего вопроса."""
        self._post_questions([self._make_question('Старый текст')])
        loaded = self._load_questions()
        loaded[0]['text'] = 'Новый текст'
        self._post_questions(loaded)

        reloaded = self._load_questions()
        self.assertEqual(reloaded[0]['text'], 'Новый текст')

    def test_update_preserves_id(self):
        """При обновлении id вопроса не меняется."""
        self._post_questions([self._make_question('Test')])
        loaded = self._load_questions()
        original_id = loaded[0]['id']

        loaded[0]['text'] = 'Изменённый'
        self._post_questions(loaded)

        reloaded = self._load_questions()
        self.assertEqual(reloaded[0]['id'], original_id)

    # ── Удаление ──

    def test_remove_one_from_three(self):
        """Удаление одного вопроса из трёх (отправка двух)."""
        self._post_questions([
            self._make_question('Q1'),
            self._make_question('Q2'),
            self._make_question('Q3'),
        ])
        loaded = self._load_questions()
        self.assertEqual(len(loaded), 3)

        # Убираем второй
        del loaded[1]
        self._post_questions(loaded)

        reloaded = self._load_questions()
        self.assertEqual(len(reloaded), 2)

    def test_save_empty_deletes_all(self):
        """Отправка пустого списка удаляет все вопросы."""
        self._post_questions([
            self._make_question('Q1'),
            self._make_question('Q2'),
        ])
        self.assertEqual(QuizQuestion.objects.filter(step=self.step).count(), 2)

        self._post_questions([])
        self.assertEqual(QuizQuestion.objects.filter(step=self.step).count(), 0)

    # ── Типы вопросов ──

    def test_save_all_question_types(self):
        """Сохранение всех 4 типов вопросов."""
        questions = [
            self._make_question('Single?', qtype='single',
                                answers=['A', 'B'], correct=[0]),
            self._make_question('Multi?', qtype='multi',
                                answers=['A', 'B', 'C'], correct=[0, 2]),
            self._make_question('Order?', qtype='order',
                                answers=['1', '2', '3'], correct=[0, 1, 2]),
            {
                'id': None, 'type': 'match', 'text': 'Match?', 'points': 2,
                'image_url': '', 'explanation': '',
                'answers': ['Def1', 'Def2'], 'correct': [],
                'terms': ['Term1', 'Term2'],
            },
        ]
        self._post_questions(questions)
        loaded = self._load_questions()
        self.assertEqual(len(loaded), 4)
        types = {q['type'] for q in loaded}
        self.assertEqual(types, {'single', 'multi', 'order', 'match'})

    def test_match_question_terms_preserved(self):
        """Поле terms у вопроса match сохраняется и загружается."""
        self._post_questions([{
            'id': None, 'type': 'match', 'text': 'Сопоставь',
            'points': 1, 'image_url': '', 'explanation': '',
            'answers': ['Определение 1', 'Определение 2'],
            'correct': [],
            'terms': ['Термин 1', 'Термин 2'],
        }])
        loaded = self._load_questions()
        self.assertEqual(loaded[0]['terms'], ['Термин 1', 'Термин 2'])

    # ── Порядок ──

    def test_order_preserved(self):
        """Порядок вопросов сохраняется."""
        self._post_questions([
            self._make_question('Первый'),
            self._make_question('Второй'),
            self._make_question('Третий'),
        ])
        loaded = self._load_questions()
        self.assertEqual(loaded[0]['text'], 'Первый')
        self.assertEqual(loaded[1]['text'], 'Второй')
        self.assertEqual(loaded[2]['text'], 'Третий')

    def test_reorder_questions(self):
        """Изменение порядка вопросов."""
        self._post_questions([
            self._make_question('A'),
            self._make_question('B'),
            self._make_question('C'),
        ])
        loaded = self._load_questions()

        # Меняем порядок: C, A, B
        reordered = [loaded[2], loaded[0], loaded[1]]
        self._post_questions(reordered)

        reloaded = self._load_questions()
        self.assertEqual(reloaded[0]['text'], 'C')
        self.assertEqual(reloaded[1]['text'], 'A')
        self.assertEqual(reloaded[2]['text'], 'B')

    # ── Доступ ──

    def test_student_cannot_save_questions(self):
        """Слушатель не может сохранять вопросы (403)."""
        client = self.get_client('student')
        resp = client.post(
            self._save_url(),
            data=json.dumps({'questions': [self._make_question('Hack')]}),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 403)

    def test_bad_json_returns_400(self):
        """Невалидный JSON → 400."""
        client = self.get_client('admin')
        resp = client.post(
            self._save_url(),
            data='not json',
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 400)


class QuestionsAndModuleSaveTest(BaseTestCase):
    """
    Тесты взаимодействия сохранения модуля (шагов) и вопросов.
    Баг: после сохранения модуля шаги могут пересоздаться,
    и вопросы удалятся каскадно.
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        create_menu_permissions()
        cls.program = create_test_program()
        cls.module = create_test_module(program=cls.program)

    def _save_module_url(self):
        return f'/api/modules/{self.module.pk}/steps/save/'

    def _load_steps_url(self):
        return f'/api/modules/{self.module.pk}/steps/'

    def _save_questions_url(self, step_pk):
        return f'/api/steps/{step_pk}/questions/save/'

    def _load_questions_url(self, step_pk):
        return f'/api/steps/{step_pk}/questions/'

    def _save_module(self, steps_data):
        client = self.get_client('admin')
        return client.post(
            self._save_module_url(),
            data=json.dumps({
                'module_title': self.module.title,
                'module_description': '',
                'cover_image': '',
                'steps': steps_data,
            }),
            content_type='application/json',
        )

    def _load_steps(self):
        client = self.get_client('admin')
        resp = client.get(self._load_steps_url())
        return json.loads(resp.content)['steps']

    def _save_questions(self, step_pk, questions):
        client = self.get_client('admin')
        return client.post(
            self._save_questions_url(step_pk),
            data=json.dumps({'questions': questions}),
            content_type='application/json',
        )

    def _load_questions(self, step_pk):
        client = self.get_client('admin')
        resp = client.get(self._load_questions_url(step_pk))
        return json.loads(resp.content)['questions']

    def _make_q(self, text='Вопрос?', qid=None):
        return {
            'id': qid, 'type': 'single', 'text': text, 'points': 1,
            'image_url': '', 'explanation': '',
            'answers': ['Да', 'Нет'], 'correct': [0], 'terms': None,
        }

    def test_save_module_then_questions(self):
        """Сохранить модуль с quiz-шагом → добавить 3 вопроса → вопросы на месте."""
        # Сохранить модуль с quiz-этапом
        self._save_module([{
            'id': None, 'order': 0, 'type': 'quiz', 'title': 'Тест',
            'description': '', 'url': '', 'slide_content': '',
            'time_limit_minutes': None, 'pass_score': None,
            'exam_config': None, 'is_active': True,
        }])
        steps = self._load_steps()
        self.assertEqual(len(steps), 1)
        step_pk = steps[0]['id']

        # Добавить 3 вопроса
        self._save_questions(step_pk, [
            self._make_q('Q1'), self._make_q('Q2'), self._make_q('Q3'),
        ])
        self.assertEqual(QuizQuestion.objects.filter(step_id=step_pk).count(), 3)

    def test_resave_module_preserves_questions(self):
        """
        КЛЮЧЕВОЙ ТЕСТ: сохранить модуль → добавить вопросы →
        повторно сохранить модуль → вопросы НЕ должны пропасть.
        """
        # 1. Создаём quiz-этап
        self._save_module([{
            'id': None, 'order': 0, 'type': 'quiz', 'title': 'Тест',
            'description': '', 'url': '', 'slide_content': '',
            'time_limit_minutes': None, 'pass_score': None,
            'exam_config': None, 'is_active': True,
        }])
        steps = self._load_steps()
        step_pk = steps[0]['id']

        # 2. Добавляем 3 вопроса
        self._save_questions(step_pk, [
            self._make_q('Q1'), self._make_q('Q2'), self._make_q('Q3'),
        ])
        self.assertEqual(QuizQuestion.objects.filter(step_id=step_pk).count(), 3)

        # 3. Повторно сохраняем модуль (как делает saveAll на фронте)
        #    шаг передаётся с реальным id
        self._save_module([{
            'id': step_pk, 'order': 0, 'type': 'quiz', 'title': 'Тест',
            'description': '', 'url': '', 'slide_content': '',
            'time_limit_minutes': None, 'pass_score': None,
            'exam_config': None, 'is_active': True,
        }])

        # 4. Проверяем: вопросы на месте
        questions = self._load_questions(step_pk)
        self.assertEqual(len(questions), 3)

    def test_add_new_step_preserves_quiz_questions(self):
        """
        Добавить quiz + вопросы → добавить ещё один этап и сохранить модуль →
        вопросы quiz-этапа не должны пропасть.
        """
        # Quiz-этап с вопросами
        self._save_module([{
            'id': None, 'order': 0, 'type': 'quiz', 'title': 'Тест',
            'description': '', 'url': '', 'slide_content': '',
            'time_limit_minutes': None, 'pass_score': None,
            'exam_config': None, 'is_active': True,
        }])
        steps = self._load_steps()
        quiz_pk = steps[0]['id']

        self._save_questions(quiz_pk, [
            self._make_q('Q1'), self._make_q('Q2'), self._make_q('Q3'),
        ])

        # Добавляем новый этап (material) и пересохраняем модуль
        self._save_module([
            {
                'id': quiz_pk, 'order': 0, 'type': 'quiz', 'title': 'Тест',
                'description': '', 'url': '', 'slide_content': '',
                'time_limit_minutes': None, 'pass_score': None,
                'exam_config': None, 'is_active': True,
            },
            {
                'id': None, 'order': 1, 'type': 'material',
                'title': 'Лекция', 'description': '', 'url': '',
                'slide_content': '', 'time_limit_minutes': None,
                'pass_score': None, 'exam_config': None, 'is_active': True,
            },
        ])

        # Вопросы на месте
        questions = self._load_questions(quiz_pk)
        self.assertEqual(len(questions), 3)

    def test_save_module_without_step_id_deletes_questions(self):
        """
        БАГ-СЦЕНАРИЙ: если фронт отправит шаг с id=null (вместо реального id),
        бэкенд создаст новый шаг и удалит старый — вопросы каскадно удалятся.
        """
        # Создаём quiz + вопросы
        self._save_module([{
            'id': None, 'order': 0, 'type': 'quiz', 'title': 'Тест',
            'description': '', 'url': '', 'slide_content': '',
            'time_limit_minutes': None, 'pass_score': None,
            'exam_config': None, 'is_active': True,
        }])
        steps = self._load_steps()
        quiz_pk = steps[0]['id']

        self._save_questions(quiz_pk, [
            self._make_q('Q1'), self._make_q('Q2'), self._make_q('Q3'),
        ])
        self.assertEqual(QuizQuestion.objects.filter(step_id=quiz_pk).count(), 3)

        # Фронт отправляет шаг с id=null (потерял id) — бэкенд пересоздаёт шаг
        self._save_module([{
            'id': None, 'order': 0, 'type': 'quiz', 'title': 'Тест',
            'description': '', 'url': '', 'slide_content': '',
            'time_limit_minutes': None, 'pass_score': None,
            'exam_config': None, 'is_active': True,
        }])

        # Старый шаг удалён — вопросы каскадно удалены
        self.assertEqual(QuizQuestion.objects.filter(step_id=quiz_pk).count(), 0)

        # У нового шага вопросов нет
        new_steps = self._load_steps()
        new_quiz_pk = new_steps[0]['id']
        self.assertNotEqual(new_quiz_pk, quiz_pk)
        self.assertEqual(QuizQuestion.objects.filter(step_id=new_quiz_pk).count(), 0)

    def test_full_cycle_add_questions_incrementally(self):
        """
        Полный цикл: создать модуль → сохранить → добавить вопросы по одному
        (3 раунда через saveQuiz) → каждый раз пересохранить модуль →
        в итоге 3 вопроса.
        """
        # Модуль с quiz-этапом
        self._save_module([{
            'id': None, 'order': 0, 'type': 'quiz', 'title': 'Тест',
            'description': '', 'url': '', 'slide_content': '',
            'time_limit_minutes': None, 'pass_score': None,
            'exam_config': None, 'is_active': True,
        }])
        steps = self._load_steps()
        quiz_pk = steps[0]['id']

        for round_num in range(1, 4):
            # Загружаем текущие вопросы
            current = self._load_questions(quiz_pk)
            # Добавляем ещё один
            current.append(self._make_q(f'Вопрос {round_num}'))
            self._save_questions(quiz_pk, current)

            # Пересохраняем модуль (как saveAll на фронте)
            steps = self._load_steps()
            self._save_module([{
                'id': s['id'], 'order': i, 'type': s['type'],
                'title': s['title'], 'description': s.get('description', ''),
                'url': s.get('url', ''), 'slide_content': s.get('slide_content', ''),
                'time_limit_minutes': s.get('time_limit_minutes'),
                'pass_score': s.get('pass_score'),
                'exam_config': s.get('exam_config'),
                'is_active': s.get('is_active', True),
            } for i, s in enumerate(steps)])

            # Проверяем: вопросы на месте
            qs = self._load_questions(quiz_pk)
            self.assertEqual(
                len(qs), round_num,
                f'Раунд {round_num}: ожидали {round_num} вопросов, получили {len(qs)}',
            )
