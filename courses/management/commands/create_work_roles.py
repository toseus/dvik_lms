from django.core.management.base import BaseCommand
from courses.models import WorkRole


class Command(BaseCommand):
    help = 'Создание начальных рабочих ролей'

    def handle(self, *args, **options):
        roles = [
            ('signer', 'Подписант'),
            ('teacher', 'Преподаватель'),
            ('examiner', 'Экзаменатор'),
            ('instructor', 'Инструктор'),
            ('methodist', 'Методист'),
        ]
        created = 0
        for code, name in roles:
            _, is_new = WorkRole.objects.get_or_create(code=code, defaults={'name': name})
            if is_new:
                created += 1
        self.stdout.write(self.style.SUCCESS(f'Создано ролей: {created}'))
