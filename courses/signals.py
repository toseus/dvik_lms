"""
courses/signals.py
"""
import random

from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Person, ProgramDocumentTemplate


@receiver(post_save, sender=Person)
def auto_create_user(sender, instance, created, **kwargs):
    if not created:
        return
    if instance.user_id:
        return
    if not instance.code:
        instance.code = f'{random.randint(0, 999999):06d}'
        Person.objects.filter(pk=instance.pk).update(code=instance.code)
    instance.create_user_account()


@receiver(post_save, sender=ProgramDocumentTemplate)
def create_template_documents(sender, instance, created, **kwargs):
    """При создании нового шаблона — добавить документ во все активные программы."""
    if created and instance.is_active:
        from courses.models import TrainingProgram, ProgramDocument
        programs = TrainingProgram.objects.filter(status='\u0412 \u0440\u0430\u0431\u043e\u0442\u0435')
        docs = []
        for prog in programs:
            if not ProgramDocument.objects.filter(program=prog, template=instance).exists():
                docs.append(ProgramDocument(program=prog, template=instance, title=instance.title))
        if docs:
            ProgramDocument.objects.bulk_create(docs)
