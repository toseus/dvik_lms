"""
students/signals.py
Автоматически создаёт User (role=student) при создании Person со СНИЛС.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Person


@receiver(post_save, sender=Person)
def auto_create_user(sender, instance, created, **kwargs):
    """
    При создании новой записи Person:
    - если у неё есть СНИЛС и нет связанного user — создаём User.
    Логин  = цифры СНИЛС (11 символов, без пробелов/тире).
    Пароль = первые 6 цифр СНИЛС.
    Роль   = 'student'.
    """
    if not created:
        return
    if instance.user_id:          # уже привязан — не трогаем
        return
    if not instance.snils:        # нет СНИЛС — пропускаем
        return

    # Извлекаем только цифры
    digits = ''.join(filter(str.isdigit, instance.snils))
    if len(digits) < 6:
        return

    login = digits          # полный СНИЛС без разделителей (11 цифр)
    password = digits[:6]      # первые 6 цифр — временный пароль

    try:
        from users.models import User as LmsUser
    except ImportError:
        from django.contrib.auth import get_user_model
        LmsUser = get_user_model()

    # Если такой логин уже существует — привязываем к нему
    user, was_created = LmsUser.objects.get_or_create(
        username=login,
        defaults={
            'role': 'student',
            'first_name': instance.first_name or '',
            'last_name':  instance.last_name  or '',
        }
    )
    if was_created:
        user.set_password(password)
        user.save()

    # Связываем без повторного сигнала
    Person.objects.filter(pk=instance.pk).update(user=user)
    instance.user = user
