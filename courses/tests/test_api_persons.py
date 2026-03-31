import json
from courses.tests.helpers import BaseTestCase, create_menu_permissions


class PersonCardTest(BaseTestCase):
    """Тесты карточки слушателя и её API."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        create_menu_permissions()

    def test_person_card_loads(self):
        """Карточка слушателя открывается для администратора."""
        client = self.get_client('admin')
        resp = client.get(f'/persons/{self.person_student.pk}/')
        self.assertEqual(resp.status_code, 200)

    def test_person_save(self):
        """Сохранение данных слушателя через API."""
        client = self.get_client('admin')
        resp = client.post(
            f'/persons/{self.person_student.pk}/save/',
            data=json.dumps({
                'last_name': 'Иванов',
                'first_name': 'Иван',
                'phone': '+79001234567',
            }),
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertTrue(data.get('ok') or data.get('success'))

    def test_person_list_loads(self):
        """Список физических лиц открывается."""
        client = self.get_client('admin')
        resp = client.get('/persons/')
        self.assertEqual(resp.status_code, 200)


class MessageTest(BaseTestCase):
    """Тесты системы сообщений."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        create_menu_permissions()

    def test_load_messages(self):
        """Загрузка списка сообщений."""
        client = self.get_client('admin')
        resp = client.get(f'/api/messages/{self.person_student.pk}/')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertIn('messages', data)

    def test_send_message(self):
        """Отправка сообщения через API карточки слушателя."""
        client = self.get_client('admin')
        resp = client.post(
            f'/api/messages/{self.person_student.pk}/send/',
            data=json.dumps({'text': 'Тестовое сообщение'}),
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 200)

    def test_send_message_via_person_api(self):
        """Отправка сообщения через persons API."""
        client = self.get_client('admin')
        resp = client.post(
            f'/api/persons/{self.person_student.pk}/messages/send/',
            data=json.dumps({'text': 'Ещё одно сообщение'}),
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 200)
