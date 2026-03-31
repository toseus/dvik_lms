import csv
from datetime import datetime
from django.core.management.base import BaseCommand
from courses.models import Program, Order, Person, TrainingProgram, Company


class Command(BaseCommand):
    help = 'Импорт подготовок из CSV (Access export таблицы tr)'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str)
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument('--limit', type=int, default=0)
        parser.add_argument('--batch-size', type=int, default=5000)

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        limit = options['limit']
        batch_size = options['batch_size']

        existing_persons = set(Person.objects.values_list('pk', flat=True))
        existing_programs = set(TrainingProgram.objects.values_list('pk', flat=True))
        existing_orders = set(Order.objects.values_list('pk', flat=True))
        existing_companies = set(Company.objects.values_list('pk', flat=True))
        existing_trainings = set(Program.objects.values_list('pk', flat=True))

        self.stdout.write(
            f'Загружено: {len(existing_persons)} persons, '
            f'{len(existing_programs)} programs, '
            f'{len(existing_orders)} orders, '
            f'{len(existing_companies)} companies, '
            f'{len(existing_trainings)} existing trainings'
        )

        created = 0
        skipped = 0
        errors = 0
        batch = []

        with open(options['csv_file'], 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            for row in reader:
                if limit and created >= limit:
                    break

                idtr = _parse_int(row.get('idtr', ''))
                if not idtr:
                    skipped += 1
                    continue

                if idtr in existing_trainings:
                    skipped += 1
                    continue

                try:
                    obj = Program(
                        pk=idtr,
                        order_id=_fk_or_none(row.get('idSet', ''), existing_orders),
                        person_id=_fk_or_none(row.get('idus', ''), existing_persons),
                        training_program_id=_fk_or_none(row.get('idpro', ''), existing_programs),
                        payer_company_id=_fk_or_none(row.get('idCom', ''), existing_companies),
                        group_id_legacy=_parse_int(row.get('idgr', '')),
                        department_id_legacy=_parse_int(row.get('iddep', '')),
                        date_start=_parse_date(row.get('trFm', '')),
                        date_end=_parse_date(row.get('trTo', '')),
                        created_at_legacy=_parse_datetime(row.get('eTrDt', '')),
                        payment_date=_parse_date(row.get('payDt', '')),
                        issue_date=_parse_date(row.get('issueDt', '')),
                        expire_date=_parse_date(row.get('expireDt', '')),
                        report_date=_parse_date(row.get('repDt', '')),
                        print_date=_parse_date(row.get('printDt', '')),
                        issued_date=_parse_date(row.get('issued', '')),
                        first_report_date=_parse_date(row.get('first_rep', '')),
                        frdo_status_date=_parse_date(row.get('frdo_sts_dt', '')),
                        eva_access_date=_parse_date(row.get('eva_access', '')),
                        amount=_parse_float(row.get('Cost', '')) or 0,
                        discount_percent=_parse_float(row.get('per', '')) or 0,
                        old_discount_percent=_parse_float(row.get('oldper', '')),
                        bonus=_parse_float(row.get('bonus', '')) or 0,
                        old_bonus=_parse_float(row.get('old_bonus', '')),
                        contract_cost=_parse_float(row.get('contract_cost', '')),
                        cost_net=_parse_float(row.get('cost_net', '')),
                        cert_number=(row.get('sertNo', '') or '').strip(),
                        reg_number=(row.get('regNo', '') or '').strip(),
                        cert_number_org=(row.get('sert_no_org', '') or '').strip(),
                        cert_number_endorsement=(row.get('sert_no_andors', '') or '').strip(),
                        blank_id=(row.get('blank_id_tr', '') or '').strip(),
                        issue_type=(row.get('issue_type', '') or '').strip(),
                        scrap_confirm=(row.get('scrap_confirm', '') or '').strip(),
                        eval_entrance=(row.get('inEval', '') or '').strip(),
                        grade=(row.get('eval', '') or '').strip(),
                        entrance_result=_parse_int(row.get('inResult', '')),
                        exam_result=_parse_int(row.get('examResult', '')),
                        exam_passed=_parse_bool(row.get('examOk', '')),
                        upd_exam_id=(row.get('updExamID', '') or '').strip(),
                        learning_quality=_parse_int(row.get('lernQ', '')),
                        is_active=_parse_bool(row.get('use', '')),
                        is_draft=_parse_bool(row.get('draft', '')),
                        learning_status=(row.get('lernSts', '') or '').strip(),
                        registration_status=(row.get('regSts', '') or '').strip(),
                        learning_here=(row.get('lernHere', '') or '').strip(),
                        step_progress=_parse_int(row.get('stepProgres', '')),
                        step_result=_parse_int(row.get('stepResult', '')),
                        service_quantity=_parse_int(row.get('servQuont', '')),
                        created_by_person_id=_fk_or_none(row.get('eTrMng', ''), existing_persons),
                        payment_manager=(row.get('payMng', '') or '').strip(),
                        print_manager_id=_fk_or_none(row.get('printMng', ''), existing_persons),
                        issue_manager_id=_fk_or_none(row.get('issueMng', ''), existing_persons),
                        eva_access_manager_id=_fk_or_none(row.get('eva_access_mng', ''), existing_persons),
                        frdo_confirmed=_parse_bool(row.get('frdo_ok', '')),
                        frdo_type=(row.get('frdo_type', '') or '').strip(),
                        original_training_id=_parse_int(row.get('id_tr_orig', '')),
                    )
                    batch.append(obj)
                    existing_trainings.add(idtr)
                    created += 1
                except Exception as e:
                    errors += 1
                    if errors <= 20:
                        self.stderr.write(f'Ошибка idtr={idtr}: {e}')

                if len(batch) >= batch_size and not dry_run:
                    try:
                        Program.objects.bulk_create(batch, ignore_conflicts=True)
                        self.stdout.write(f'  ... записано {created}')
                    except Exception as e:
                        self.stderr.write(f'Batch error: {e}')
                        for obj in batch:
                            try:
                                obj.save()
                            except Exception:
                                errors += 1
                    batch = []

            if batch and not dry_run:
                try:
                    Program.objects.bulk_create(batch, ignore_conflicts=True)
                except Exception as e:
                    self.stderr.write(f'Final batch error: {e}')
                    for obj in batch:
                        try:
                            obj.save()
                        except Exception:
                            errors += 1

        action = 'Будет создано' if dry_run else 'Создано'
        self.stdout.write(self.style.SUCCESS(
            f'{action}: {created}, пропущено: {skipped}, ошибок: {errors}'
        ))


def _parse_date(val):
    if not val or not val.strip():
        return None
    val = val.strip()
    try:
        return datetime.strptime(val.split(' ')[0], '%Y-%m-%d').date()
    except ValueError:
        return None


def _parse_datetime(val):
    if not val or not val.strip():
        return None
    try:
        return datetime.strptime(val.strip(), '%Y-%m-%d')
    except ValueError:
        return None


def _parse_int(val):
    if not val or not val.strip():
        return None
    try:
        return int(float(val.strip()))
    except (ValueError, TypeError):
        return None


def _parse_float(val):
    if not val or not val.strip():
        return None
    try:
        return float(val.strip())
    except (ValueError, TypeError):
        return None


def _parse_bool(val):
    if not val or not val.strip():
        return False
    return val.strip() in ('1', '-1', 'True', 'true')


def _fk_or_none(val, valid_set):
    pk = _parse_int(val)
    if pk and pk in valid_set:
        return pk
    return None
