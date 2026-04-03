import os
from datetime import datetime
from django.conf import settings as django_settings


def app_version(request):
    version = 'v2.2'
    views_path = os.path.join(os.path.dirname(__file__), 'views.py')
    try:
        mtime = os.path.getmtime(views_path)
        updated = datetime.fromtimestamp(mtime).strftime('%d.%m.%Y %H:%M')
    except OSError:
        updated = '—'
    return {'app_version': version, 'app_last_updated': updated}


def program_filters(request):
    if request.user.is_authenticated:
        from .models import TrainingProgram, Department
        qs = TrainingProgram.objects.filter(status='В работе')
        categories = qs.values_list('category', flat=True).distinct().order_by('category')
        departments_list = Department.objects.filter(is_active=True)
        return {
            'program_categories': [c for c in categories if c],
            'departments_list': departments_list,
        }
    return {}


def student_filters(request):
    if request.user.is_authenticated:
        from .models import Person
        positions = (
            Person.objects
            .filter(user__isnull=False, position__gt='')
            .values_list('position', flat=True)
            .distinct()
            .order_by('position')[:100]
        )
        return {'student_positions': list(positions)}
    return {}


def menu_permissions(request):
    if not request.user.is_authenticated:
        return {'visible_menu': set()}
    from .models import MenuPermission
    role = getattr(request.user, 'role', 'student')
    # Суперадмин видит всё всегда
    if role == 'superadmin':
        return {'visible_menu': set(k for k, _ in MenuPermission.MENU_ITEMS)}
    visible = set(
        MenuPermission.objects.filter(role=role, is_visible=True)
        .values_list('menu_item', flat=True)
    )
    return {'visible_menu': visible}


def impersonation_context(request):
    person_id = request.session.get('impersonating_person_id')
    if person_id and getattr(request.user, 'role', '') == 'superadmin':
        from .models import Person
        try:
            person = Person.objects.get(pk=person_id)
            return {'impersonated_person_name': f'{person.last_name} {person.first_name}'}
        except Person.DoesNotExist:
            pass
    return {}
