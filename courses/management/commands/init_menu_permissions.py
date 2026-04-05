from django.core.management.base import BaseCommand
from courses.models import MenuPermission


class Command(BaseCommand):
    help = 'Создать начальные настройки меню по ролям'

    def handle(self, *args, **options):
        defaults = {
            'dashboard':     {'student': True,  'teacher': True,  'admin': True,  'superadmin': True},
            'learning':      {'student': True,  'teacher': False, 'admin': False, 'superadmin': True},
            'schedule':      {'student': True,  'teacher': True,  'admin': True,  'superadmin': True},
            'results':       {'student': True,  'teacher': True,  'admin': True,  'superadmin': True},
            'library':       {'student': True,  'teacher': True,  'admin': True,  'superadmin': True},
            'programs':      {'student': False, 'teacher': True,  'admin': True,  'superadmin': True},
            'modules':       {'student': False, 'teacher': True,  'admin': True,  'superadmin': True},
            'persons':       {'student': False, 'teacher': False, 'admin': True,  'superadmin': True},
            'students':      {'student': False, 'teacher': True,  'admin': True,  'superadmin': True},
            'companies':     {'student': False, 'teacher': False, 'admin': True,  'superadmin': True},
            'organizations': {'student': False, 'teacher': False, 'admin': True,  'superadmin': True},
            'contracts':     {'student': False, 'teacher': False, 'admin': True,  'superadmin': True},
            'orders':        {'student': False, 'teacher': False, 'admin': True,  'superadmin': True},
            'progress':      {'student': False, 'teacher': True,  'admin': True,  'superadmin': True},
            'groups':        {'student': False, 'teacher': True,  'admin': True,  'superadmin': True},
        }

        created = 0
        for menu_item, roles in defaults.items():
            for role, visible in roles.items():
                _, is_new = MenuPermission.objects.get_or_create(
                    menu_item=menu_item,
                    role=role,
                    defaults={'is_visible': visible}
                )
                if is_new:
                    created += 1

        self.stdout.write(self.style.SUCCESS(f'Создано: {created}'))
