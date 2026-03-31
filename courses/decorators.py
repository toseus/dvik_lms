from functools import wraps
from django.http import JsonResponse
from django.shortcuts import redirect, render


def _get_visible_menu(request):
    """Получить set разрешённых menu_key для текущего пользователя. Кэшируется на request."""
    if hasattr(request, '_visible_menu'):
        return request._visible_menu

    role = getattr(request.user, 'role', 'student')
    if role == 'superadmin':
        request._visible_menu = None  # None = доступ ко всему
        return None

    from courses.models import MenuPermission
    request._visible_menu = set(
        MenuPermission.objects.filter(role=role, is_visible=True)
        .values_list('menu_item', flat=True)
    )
    return request._visible_menu


def _forbidden_response(request):
    """Ответ 403 — JSON для API, HTML-страница для обычных запросов."""
    if request.path.startswith('/api/') or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'error': 'Доступ запрещён'}, status=403)
    return render(request, 'errors/403_menu.html', status=403)


def menu_access_required(menu_key):
    """
    Декоратор для view-функций.
    Проверяет что у текущего пользователя (по его роли) разрешён доступ
    к разделу menu_key в таблице MenuPermission.
    Суперадмин проходит всегда без проверки.
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')

            visible = _get_visible_menu(request)
            if visible is None:  # superadmin
                return view_func(request, *args, **kwargs)

            if menu_key not in visible:
                return _forbidden_response(request)

            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def menu_access_any(*menu_keys):
    """Доступ если хотя бы один из указанных ключей разрешён."""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')

            visible = _get_visible_menu(request)
            if visible is None:  # superadmin
                return view_func(request, *args, **kwargs)

            if not visible.intersection(menu_keys):
                return _forbidden_response(request)

            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator
