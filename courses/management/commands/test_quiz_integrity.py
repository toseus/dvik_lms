from django.core.management.base import BaseCommand
from courses.models import ModuleStep, QuizQuestion


class Command(BaseCommand):
    help = 'Проверка целостности вопросов тестов'

    def handle(self, *args, **options):
        quiz_steps = ModuleStep.objects.filter(type__in=['quiz', 'final_exam'])
        empty = []
        for step in quiz_steps:
            count = step.questions.count()
            if count == 0:
                empty.append(step)

        orphan_questions = QuizQuestion.objects.filter(step__isnull=True).count()

        self.stdout.write(f'Всего тестовых шагов: {quiz_steps.count()}')
        self.stdout.write(f'Шагов без вопросов: {len(empty)}')
        if empty:
            for s in empty[:10]:
                self.stdout.write(f'  - Step {s.pk}: "{s.title}" (module: {s.module})')
        self.stdout.write(f'Вопросов-сирот: {orphan_questions}')
