"""
courses/signals.py
При создании Person: генерируем code (6 цифр) если пустой, затем создаём User.
Логин = str(person.pk), Пароль = person.code.
"""
import random

from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Person


@receiver(post_save, sender=Person)
def auto_create_user(sender, instance, created, **kwargs):
    if not created:
        return
    if instance.user_id:
        return

    # Генерируем 6-значный код если не задан
    if not instance.code:
        instance.code = f'{random.randint(0, 999999):06d}'
        Person.objects.filter(pk=instance.pk).update(code=instance.code)

    # Создаём учётную запись (логин=pk, пароль=code)
    instance.create_user_account()
