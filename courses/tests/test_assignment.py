import json
from courses.models import ModuleAssignment, Order, Program as ProgramLine
from courses.tests.helpers import (
    BaseTestCase, create_menu_permissions,
    create_full_module, assign_module_to_person,
)


class AssignModuleTest(BaseTestCase):
    """Тесты назначения модулей слушателям."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        create_menu_permissions()
        cls.data = create_full_module()

    # ── Назначение через API ──

    def test_admin_can_assign_module(self):
        """Администратор может назначить модуль слушателю."""
        client = self.get_client('admin')
        resp = client.post(
            f'/api/persons/{self.person_student.pk}/assign-modules/',
            data=json.dumps({
                'module_ids': [self.data['module'].pk],
            }),
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertGreaterEqual(data.get('created', 0), 1)

        self.assertTrue(
            ModuleAssignment.objects.filter(
                person=self.person_student,
                module=self.data['module'],
            ).exists()
        )

    def test_duplicate_assignment_ignored(self):
        """Повторное назначение того же модуля не создаёт дубль."""
        assign_module_to_person(
            self.person_student, self.data['module'],
            assigned_by=self.admin_user,
        )
        client = self.get_client('admin')
        resp = client.post(
            f'/api/persons/{self.person_student.pk}/assign-modules/',
            data=json.dumps({
                'module_ids': [self.data['module'].pk],
            }),
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertEqual(data.get('created', 0), 0)

    def test_student_cannot_assign_modules(self):
        """Слушатель не может назначать модули."""
        client = self.get_client('student')
        resp = client.post(
            f'/api/persons/{self.person_student.pk}/assign-modules/',
            data=json.dumps({'module_ids': [self.data['module'].pk]}),
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 403)

    # ── Список модулей программы ──

    def test_get_program_modules(self):
        """API возвращает список модулей для программы."""
        client = self.get_client('admin')
        resp = client.get(
            f'/api/training-programs/{self.data["program"].pk}/modules/'
        )
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertGreaterEqual(len(data.get('modules', [])), 1)

    # ── Статус модулей для строки заявки ──

    def test_module_status_for_program_line(self):
        """API возвращает статус назначенных модулей."""
        order = Order.objects.create(
            person=self.person_student,
            date='2026-03-31',
        )
        prog_line = ProgramLine.objects.create(
            order=order,
            training_program=self.data['program'],
            person=self.person_student,
        )
        assign_module_to_person(
            self.person_student, self.data['module'],
            order=order, program_line=prog_line,
            assigned_by=self.admin_user,
        )

        client = self.get_client('admin')
        resp = client.get(f'/api/program-lines/{prog_line.pk}/module-status/')
        self.assertEqual(resp.status_code, 200)
