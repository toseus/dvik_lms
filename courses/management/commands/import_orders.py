import csv
from datetime import datetime
from django.core.management.base import BaseCommand
from courses.models import Order, Person, Company


class Command(BaseCommand):
    help = 'Импорт заявок из CSV (Access export таблицы set)'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str)
        parser.add_argument('--dry-run', action='store_true', help='Только подсчёт')
        parser.add_argument('--limit', type=int, default=0, help='Ограничить количество записей')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        limit = options['limit']

        existing_persons = set(Person.objects.values_list('pk', flat=True))
        existing_companies = set(Company.objects.values_list('pk', flat=True))
        existing_orders = set(Order.objects.values_list('pk', flat=True))

        self.stdout.write(f'Persons: {len(existing_persons)}, Companies: {len(existing_companies)}, Orders: {len(existing_orders)}')

        created = 0
        skipped = 0
        errors = 0
        batch = []
        BATCH_SIZE = 2000

        with open(options['csv_file'], 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            for row in reader:
                if limit and created >= limit:
                    break

                try:
                    id_set = int(row.get('idSet', '').strip())
                except (ValueError, TypeError):
                    skipped += 1
                    continue

                if id_set in existing_orders:
                    skipped += 1
                    continue

                # Дата
                in_dt = row.get('inDt', '').strip().strip('"')
                order_date = None
                if in_dt:
                    try:
                        dt_part = in_dt.split(' ')[0]
                        order_date = datetime.strptime(dt_part, '%d.%m.%Y').date()
                    except (ValueError, IndexError):
                        pass

                if not order_date:
                    set_dt = row.get('setDt', '').strip().strip('"')
                    if set_dt:
                        try:
                            order_date = datetime.strptime(set_dt.split(' ')[0], '%m/%d/%y').date()
                        except (ValueError, IndexError):
                            pass

                # Person (слушатель)
                person_id = self._parse_fk(row.get('idUs', ''), existing_persons)

                # Компания
                company_id = self._parse_fk(row.get('idCom', ''), existing_companies)

                # Автор (Person)
                author_id = self._parse_fk(row.get('idAuthor', ''), existing_persons)

                # Подписант (Person)
                signer_id = self._parse_fk(row.get('agrSign', ''), existing_persons)

                # Менеджер подтверждения
                manager_id = self._parse_fk(row.get('stuSignedMng', ''), existing_persons)

                # Тип плательщика
                u_lfl = row.get('uLfL', '').strip().strip('"')
                payer_type = ''
                if u_lfl in ('ФЛ', 'ф', 'Ф'):
                    payer_type = 'fl'
                elif u_lfl in ('ЮЛ',):
                    payer_type = 'ul'

                notes = row.get('setRem', '').strip().strip('"')
                stu_signed = row.get('stuSigned', '').strip().strip('"')

                if not dry_run:
                    batch.append(Order(
                        pk=id_set,
                        person_id=person_id,
                        date=order_date,
                        payer_company_id=company_id,
                        author_person_id=author_id,
                        signer_person_id=signer_id,
                        signed_by_manager_id=manager_id,
                        payer_type=payer_type,
                        notes=notes,
                        student_signed_date=stu_signed,
                        created_at_legacy=in_dt,
                    ))
                    if len(batch) >= BATCH_SIZE:
                        try:
                            Order.objects.bulk_create(batch, ignore_conflicts=True)
                        except Exception as e:
                            errors += len(batch)
                            if errors <= 10:
                                self.stderr.write(f'Batch error: {e}')
                        created += len(batch)
                        if created % 10000 == 0:
                            self.stdout.write(f'  ...{created}')
                        batch = []
                else:
                    created += 1

            # Остаток
            if batch and not dry_run:
                try:
                    Order.objects.bulk_create(batch, ignore_conflicts=True)
                except Exception as e:
                    errors += len(batch)
                    self.stderr.write(f'Final batch error: {e}')
                created += len(batch)

        action = 'Будет создано' if dry_run else 'Создано'
        self.stdout.write(self.style.SUCCESS(
            f'{action}: {created}, пропущено: {skipped}, ошибок: {errors}'
        ))

    def _parse_fk(self, value, valid_set):
        value = (value or '').strip()
        if not value:
            return None
        try:
            pk = int(value)
            return pk if pk in valid_set else None
        except (ValueError, TypeError):
            return None
