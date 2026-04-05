from django.core.management.base import BaseCommand
from courses.models import Program, TrainingGroup


class Command(BaseCommand):
    help = 'Привязывает подготовки (Program) к группам по group_id_legacy'

    def handle(self, *args, **options):
        # Маппинг legacy_id → pk
        group_map = dict(TrainingGroup.objects.values_list('legacy_id', 'pk'))
        self.stdout.write(f'Групп в базе: {len(group_map)}')

        programs = Program.objects.filter(
            group_id_legacy__isnull=False,
            group__isnull=True
        )
        total = programs.count()
        self.stdout.write(f'Подготовок для привязки: {total}')

        updated = 0
        for p in programs.iterator(chunk_size=5000):
            gid = p.group_id_legacy
            if gid in group_map:
                p.group_id = group_map[gid]
                p.save(update_fields=['group'])
                updated += 1

        self.stdout.write(self.style.SUCCESS(f'Привязано: {updated}'))
