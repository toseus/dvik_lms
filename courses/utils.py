def get_current_person(request):
    """Возвращает Person для текущего контекста.
    Если суперадмин в режиме impersonation — возвращает слушателя.
    """
    impersonating_id = request.session.get('impersonating_person_id')
    if impersonating_id and getattr(request.user, 'role', '') == 'superadmin':
        from courses.models import Person
        try:
            return Person.objects.get(pk=impersonating_id)
        except Person.DoesNotExist:
            pass
    return getattr(request.user, 'person', None)


def is_impersonating(request):
    return bool(request.session.get('impersonating_person_id')) and getattr(request.user, 'role', '') == 'superadmin'
