import json
from courses.models import TrainingProgram, ProgramDocumentTemplate
from courses.tests.helpers import BaseTestCase, create_menu_permissions, create_test_program


class ProgramCatalogTest(BaseTestCase):

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        create_menu_permissions()
        cls.program = create_test_program()

    def test_catalog_loads(self):
        """Каталог программ открывается."""
        client = self.get_client('admin')
        resp = client.get('/programs/')
        self.assertEqual(resp.status_code, 200)

    def test_catalog_search(self):
        """Поиск по каталогу программ."""
        client = self.get_client('admin')
        resp = client.get('/programs/?q=Тестовая')
        self.assertEqual(resp.status_code, 200)

    def test_program_detail_loads(self):
        """Карточка программы открывается."""
        client = self.get_client('admin')
        resp = client.get(f'/programs/{self.program.pk}/')
        self.assertEqual(resp.status_code, 200)

    def test_program_save(self):
        """Сохранение полей программы через API."""
        client = self.get_client('admin')
        resp = client.post(
            f'/programs/{self.program.pk}/save/',
            data=json.dumps({
                'title': 'Обновлённое название',
                'period_hours': 80,
            }),
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 200)

    def test_create_template_docs(self):
        """Создание документов из шаблонов."""
        tmpl = ProgramDocumentTemplate.objects.create(
            title='Учебный план', is_active=True
        )
        client = self.get_client('admin')
        resp = client.post(
            f'/api/programs/{self.program.pk}/create-template-docs/',
            data=json.dumps({'template_ids': [tmpl.pk]}),
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 200)
