from django.test import TestCase, Client
from courses.models import (
    Space, User, Person, MenuPermission,
    TrainingProgram, LearningModule, ModuleStep, QuizQuestion,
    Order, Program, ModuleAssignment,
)


class BaseTestCase(TestCase):
    """Базовый класс с созданием пользователей всех ролей."""

    @classmethod
    def setUpTestData(cls):
        cls.space = Space.objects.create(
            name='Тестовое', slug='test', is_active=True
        )

        # Пользователи 4 ролей
        cls.superadmin_user = User.objects.create_user(
            username='superadmin1', password='test123456',
            role='superadmin', space=cls.space
        )
        cls.admin_user = User.objects.create_user(
            username='admin1', password='test123456',
            role='admin', space=cls.space
        )
        cls.teacher_user = User.objects.create_user(
            username='teacher1', password='test123456',
            role='teacher', space=cls.space
        )
        cls.student_user = User.objects.create_user(
            username='student1', password='test123456',
            role='student', space=cls.space
        )

        # Person для слушателя (user уже задан — signal не создаст дубль)
        cls.person_student = Person.objects.create(
            last_name='Иванов',
            first_name='Иван',
            middle_name='Иванович',
            user=cls.student_user,
            code='123456',
        )

        # Person для преподавателя
        cls.person_teacher = Person.objects.create(
            last_name='Петров',
            first_name='Пётр',
            middle_name='Петрович',
            user=cls.teacher_user,
            code='654321',
        )

    def get_client(self, role):
        """Возвращает залогиненный Client для указанной роли."""
        user_map = {
            'superadmin': self.superadmin_user,
            'admin': self.admin_user,
            'teacher': self.teacher_user,
            'student': self.student_user,
        }
        client = Client()
        user = user_map[role]
        client.login(username=user.username, password='test123456')
        return client


def create_menu_permissions(defaults=None):
    """
    Создаёт записи MenuPermission.
    defaults — dict {menu_key: {role: bool}}.
    """
    if defaults is None:
        defaults = {
            'dashboard':      {'student': True,  'teacher': True,  'admin': True,  'superadmin': True},
            'programs':       {'student': False, 'teacher': True,  'admin': True,  'superadmin': True},
            'modules':        {'student': False, 'teacher': True,  'admin': True,  'superadmin': True},
            'persons':        {'student': False, 'teacher': True,  'admin': True,  'superadmin': True},
            'students':       {'student': False, 'teacher': True,  'admin': True,  'superadmin': True},
            'contracts':      {'student': False, 'teacher': False, 'admin': True,  'superadmin': True},
            'learning':       {'student': True,  'teacher': False, 'admin': False, 'superadmin': True},
            'orders':         {'student': False, 'teacher': False, 'admin': True,  'superadmin': True},
            'menu_settings':  {'student': False, 'teacher': False, 'admin': False, 'superadmin': True},
            'companies':      {'student': False, 'teacher': False, 'admin': True,  'superadmin': True},
            'organizations':  {'student': False, 'teacher': False, 'admin': True,  'superadmin': True},
            'impersonate_btn': {'student': False, 'teacher': False, 'admin': False, 'superadmin': True},
        }

    for menu_item, roles in defaults.items():
        for role, visible in roles.items():
            MenuPermission.objects.update_or_create(
                menu_item=menu_item,
                role=role,
                defaults={'is_visible': visible}
            )


def create_test_program(**kwargs):
    """Создаёт тестовую программу обучения."""
    defaults = {
        'title': 'Тестовая программа',
        'code': 'ТП-001',
        'status': 'В работе',
        'period_hours': 72,
        'new_price': 15000,
    }
    defaults.update(kwargs)
    return TrainingProgram.objects.create(**defaults)


def create_test_module(program=None, **kwargs):
    """Создаёт тестовый модуль обучения."""
    if program is None:
        program = create_test_program()
    defaults = {
        'title': 'Тестовый модуль',
        'program': program,
        'is_active': True,
    }
    defaults.update(kwargs)
    return LearningModule.objects.create(**defaults)


def create_full_module(program=None):
    """
    Создаёт модуль с 4 этапами: material, slide, quiz (3 вопроса), final_exam.
    Возвращает dict со всеми объектами.
    """
    if program is None:
        program = create_test_program(title='Программа для тестов', code='TEST-FULL')

    module = LearningModule.objects.create(
        title='Полный тестовый модуль',
        program=program,
        is_active=True,
    )

    step_online = ModuleStep.objects.create(
        module=module, title='Введение', type='material',
        order=1, url='https://example.com/intro', is_active=True,
    )

    step_slide = ModuleStep.objects.create(
        module=module, title='Теория', type='slide',
        order=2, is_active=True,
    )

    step_quiz = ModuleStep.objects.create(
        module=module, title='Промежуточный тест', type='quiz',
        order=3, pass_score=60, is_active=True,
    )

    q1 = QuizQuestion.objects.create(
        step=step_quiz, text='Столица России?', type='single',
        answers=['Москва', 'Петербург', 'Новосибирск'],
        correct=[0], order=1,
    )
    q2 = QuizQuestion.objects.create(
        step=step_quiz, text='Выберите моря:', type='multi',
        answers=['Чёрное', 'Каспийское', 'Уральское', 'Белое'],
        correct=[0, 1, 3], order=2,
    )
    q3 = QuizQuestion.objects.create(
        step=step_quiz, text='Расположите по порядку:', type='order',
        answers=['Первый', 'Второй', 'Третий'],
        correct=[0, 1, 2], order=3,
    )

    step_final = ModuleStep.objects.create(
        module=module, title='Итоговая аттестация', type='final_exam',
        order=4, pass_score=70, is_active=True,
        exam_config={str(step_quiz.pk): 2},
    )

    return {
        'program': program,
        'module': module,
        'step_online': step_online,
        'step_slide': step_slide,
        'step_quiz': step_quiz,
        'step_final': step_final,
        'questions': [q1, q2, q3],
    }


def assign_module_to_person(person, module, order=None, program_line=None, assigned_by=None):
    """Назначает модуль слушателю."""
    assignment, created = ModuleAssignment.objects.get_or_create(
        person=person,
        module=module,
        program_line=program_line,
        defaults={
            'order': order,
            'assigned_by': assigned_by,
            'is_active': True,
        }
    )
    return assignment
