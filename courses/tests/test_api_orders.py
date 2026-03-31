import json
from courses.models import Order, Program
from courses.tests.helpers import (
    BaseTestCase, create_menu_permissions, create_test_program,
)


class OrderTest(BaseTestCase):

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        create_menu_permissions()
        cls.program = create_test_program()

    def test_create_order_for_person(self):
        """Создание заявки для слушателя."""
        client = self.get_client('admin')
        resp = client.post(
            f'/api/persons/{self.person_student.pk}/orders/create/',
            data=json.dumps({}),
            content_type='application/json'
        )
        self.assertIn(resp.status_code, [200, 201])

    def test_add_program_to_order(self):
        """Добавление программы в заявку."""
        order = Order.objects.create(
            person=self.person_student,
            date='2026-03-31',
        )
        client = self.get_client('admin')
        resp = client.post(
            f'/api/orders/{order.pk}/add-program/',
            data=json.dumps({
                'training_program_id': self.program.pk,
            }),
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 200)

    def test_remove_program_from_order(self):
        """Удаление программы из заявки."""
        order = Order.objects.create(
            person=self.person_student,
            date='2026-03-31',
        )
        prog = Program.objects.create(
            order=order,
            training_program=self.program,
            person=self.person_student,
        )
        client = self.get_client('admin')
        resp = client.post(
            f'/api/orders/{order.pk}/remove-programs/',
            data=json.dumps({'ids': [prog.pk]}),
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 200)

    def test_order_list_loads(self):
        """Список заявок для слушателя загружается."""
        client = self.get_client('admin')
        resp = client.get(f'/orders/api/person/{self.person_student.pk}/')
        self.assertEqual(resp.status_code, 200)
