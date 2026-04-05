from django.core.management.base import BaseCommand
from courses.models import RoleIPRestriction


class Command(BaseCommand):
    help = 'Создаёт записи RoleIPRestriction для всех ролей (если не существуют)'

    def handle(self, *args, **options):
        roles_config = [
            ('student', False),     # Слушатели — без ограничений
            ('teacher', True),      # Преподаватели — только разрешённые IP
            ('admin', True),        # Администраторы — только разрешённые IP
            ('superadmin', True),   # Суперадмины — только разрешённые IP
        ]

        created_count = 0
        for role, ip_check in roles_config:
            obj, created = RoleIPRestriction.objects.get_or_create(
                role=role,
                defaults={'ip_check_enabled': ip_check}
            )
            if created:
                created_count += 1
                self.stdout.write(f'  Создано: {obj}')
            else:
                self.stdout.write(f'  Уже есть: {obj}')

        self.stdout.write(self.style.SUCCESS(
            f'\nГотово. Создано {created_count} новых записей.'
        ))
