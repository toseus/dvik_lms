import csv
from django.core.management.base import BaseCommand
from courses.models import ProgramPlan, TrainingProgram


class Command(BaseCommand):
    help = 'Импорт учебного плана из CSV'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str)

    def handle(self, *args, **options):
        with open(options['csv_file'], 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            created = 0
            skipped = 0
            for row in reader:
                prog_id = row.get('id_prog', '').strip()
                if not prog_id:
                    skipped += 1
                    continue
                try:
                    program = TrainingProgram.objects.get(pk=int(prog_id))
                except (TrainingProgram.DoesNotExist, ValueError):
                    skipped += 1
                    continue

                hours_self = row.get('hour2', '0').strip()
                try:
                    hours_self = float(hours_self) if hours_self else 0
                except ValueError:
                    hours_self = 0

                days = row.get('trday', '').strip()
                try:
                    days = int(days) if days else None
                except ValueError:
                    days = None

                sort_order_val = row.get('idindtr', '').strip()
                try:
                    sort_order = int(sort_order_val) if sort_order_val else 0
                except ValueError:
                    sort_order = 0

                ProgramPlan.objects.create(
                    program=program,
                    title=row.get('trProg', '').strip(),
                    hours=int(row.get('hour', 0) or 0),
                    hours_self=hours_self,
                    control_form=row.get('trRem', '').strip(),
                    days=days,
                    sort_order=sort_order,
                )
                created += 1

            self.stdout.write(self.style.SUCCESS(
                f'Импорт завершён: создано {created}, пропущено {skipped}'
            ))
