"""
Management command: импорт учебных групп из Excel-файла (gr.xlsx).

Использование:
    python manage.py import_groups gr.xlsx              # импорт
    python manage.py import_groups gr.xlsx --dry-run    # проверка без записи
"""
import pandas as pd
from datetime import datetime
from django.core.management.base import BaseCommand
from courses.models import TrainingGroup, TrainingProgram


class Command(BaseCommand):
    help = 'Импорт учебных групп из Excel-файла (экспорт таблицы gr из Access)'

    def add_arguments(self, parser):
        parser.add_argument('file', type=str, help='Путь к файлу .xlsx')
        parser.add_argument('--dry-run', action='store_true', help='Только проверка без записи в БД')

    def handle(self, *args, **options):
        filepath = options['file']
        dry_run = options['dry_run']

        df = pd.read_excel(filepath)
        self.stdout.write(f'Загружено строк из файла: {len(df)}')

        # Предзагрузка существующих данных
        from courses.models import Department, Company
        tp_ids = set(TrainingProgram.objects.values_list('pk', flat=True))
        dep_ids = set(Department.objects.values_list('pk', flat=True))
        org_ids = set(Company.objects.values_list('pk', flat=True))
        existing_ids = set(TrainingGroup.objects.values_list('legacy_id', flat=True))

        self.stdout.write(f'Программ в БД: {len(tp_ids)}')
        self.stdout.write(f'Групп уже в БД: {len(existing_ids)}')

        to_create = []
        skipped = 0
        errors = 0
        tp_found = 0
        tp_missing = 0

        for _, row in df.iterrows():
            try:
                idgr = int(row['idgr'])
            except (ValueError, TypeError):
                errors += 1
                continue

            if idgr in existing_ids:
                skipped += 1
                continue

            # FK на программу
            idpro = None
            if pd.notna(row.get('idpro')):
                idpro = int(row['idpro'])
                if idpro in tp_ids:
                    tp_found += 1
                else:
                    tp_missing += 1
                    idpro = None

            group = TrainingGroup(
                legacy_id=idgr,
                training_program_id=idpro,
                date_from=self._parse_date(row.get('fmdt')),
                date_to=self._parse_date(row.get('todt')),
                group_number=self._str(row.get('grNo')),
                finish_date=self._parse_date(row.get('finishDt')),
                department_id=self._int(row.get('idDep')) if self._int(row.get('idDep')) in dep_ids else None,
                notes=self._str(row.get('remGr')),
                learning_status=self._str(row.get('lern_sts')) or 'Да',
                student_limit=self._int(row.get('limit')) or 48,
                elog_status=self._int(row.get('elog_sts')),
                program_name=self._str(row.get('prog_name')),
                rank=self._str(row.get('gr_rank')),
                qual_rank=self._str(row.get('gr_qual_rank')),
                qualification=self._str(row.get('qual')),
                qual_task=self._str(row.get('qual_task')),
                issue_date=self._parse_date(row.get('issue_dt')),
                protocol_number=self._str(row.get('protocol_number')),
                organization_id=self._int(row.get('id_org')) if self._int(row.get('id_org')) in org_ids else None,
                in_low_no=self._str(row.get('in_low_no')),
                out_low_no=self._str(row.get('out_low_no')),
            )
            to_create.append(group)

        self.stdout.write('')
        self.stdout.write(f'К импорту: {len(to_create)}')
        self.stdout.write(f'Пропущено (уже в БД): {skipped}')
        self.stdout.write(f'Ошибки парсинга: {errors}')
        self.stdout.write(f'Программы найдены: {tp_found}, не найдены: {tp_missing}')

        if dry_run:
            self.stdout.write(self.style.WARNING('Dry run — запись не производилась'))
            return

        if to_create:
            batch_size = 2000
            for i in range(0, len(to_create), batch_size):
                batch = to_create[i:i + batch_size]
                TrainingGroup.objects.bulk_create(batch, batch_size=batch_size)
                self.stdout.write(f'  Записано {min(i + batch_size, len(to_create))} / {len(to_create)}')

            total = TrainingGroup.objects.count()
            self.stdout.write(self.style.SUCCESS(
                f'\nИмпортировано: {len(to_create)} групп. Всего в БД: {total}'
            ))
        else:
            self.stdout.write('Нечего импортировать')

    def _parse_date(self, val):
        if pd.isna(val):
            return None
        if isinstance(val, datetime):
            return val.date()
        try:
            return pd.Timestamp(val).date()
        except Exception:
            return None

    def _str(self, val):
        if pd.isna(val):
            return ''
        s = str(val).strip()
        # Убрать .0 у числовых значений прочитанных как float
        if s.endswith('.0'):
            try:
                return str(int(float(s)))
            except (ValueError, OverflowError):
                pass
        return s

    def _int(self, val):
        if pd.isna(val):
            return None
        try:
            return int(float(val))
        except (ValueError, TypeError):
            return None
