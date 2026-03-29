import csv
from datetime import datetime
from django.core.management.base import BaseCommand
from courses.models import TrainingProgram


class Command(BaseCommand):
    help = 'Обновление полей программ из CSV (Access export)'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str)
        parser.add_argument('--dry-run', action='store_true', help='Только показать что будет обновлено')

    def handle(self, *args, **options):
        FIELD_MAP = {
            'prog': 'code',
            'program': 'title',
            'programEng': 'title_eng',
            'price': 'price',
            'newprice': 'new_price',
            'newpricedt': 'new_price_date',
            'oldprice': 'old_price',
            'iddep': 'id_dep',
            'idorg': 'id_org',
            'dir': 'direction',
            'cat': 'category',
            'arcDt': 'archive_date',
            'idBlank': 'id_blank',
            'sign': 'id_sign',
            'periodHour': 'period_hours',
            'periodDay': 'period_days',
            'periodWeek': 'period_weeks',
            'bonusRate': 'bonus_rate',
            'progRem': 'notes',
            'dpo': 'dpo',
            'colorGr': 'color_gr',
            'limit': 'group_limit',
            'quontRequired': 'quant_required',
            'signingHead': 'signing_head',
            'signingHeadEng': 'signing_head_eng',
            'status': 'status',
            'blankType': 'blank_type',
            'contractFirst': 'contract_first',
            'sertText1': 'sert_text1',
            'sertText2': 'sert_text2',
            'userAdmin': 'user_admin',
            'instructor': 'instructor',
            'idSign': 'id_sign',
            'sertText1Eng': 'sert_text1_eng',
            'sertText2Eng': 'sert_text2_eng',
            'sertText3': 'sert_text3',
            'sertText3Eng': 'sert_text3_eng',
            'auto_contract': 'auto_contract',
            'umkd': 'umkd',
            'ais_sert': 'ais_sert',
            'ais_rank': 'ais_rank',
            'sub_prog': 'sub_prog',
            'sub_prog_eng': 'sub_prog_eng',
            'edu_level': 'edu_level',
            'rem_stu': 'rem_stu',
            'stat_type': 'stat_type',
            'inspection_sts': 'inspection_sts',
            'old_programm': 'old_programm',
            'main_title': 'main_title',
            'msun': 'msun',
            'blank_reg_type': 'blank_reg_type',
            'online_sts': 'online_sts',
            'sert_text4': 'sert_text4',
            'sert_text4_eng': 'sert_text4_eng',
            'sfera_prof': 'sfera_prof',
            'group_prof': 'group_prof',
            'tr_form': 'training_form',
            'ais_uid_doc_type': 'ais_uid_doc_type',
            'tr_form_FAMRT': 'tr_form_famrt',
            'frdo_po_prof': 'frdo_po_prof',
            'frdo_po_type_edu': 'frdo_po_type_edu',
            'qual_rank_po': 'qual_rank_po',
            'prog_group': 'prog_group',
            'prog_public': 'is_published',
            'frdo_prog_type': 'frdo_prog_type',
            'frdo_doc_type': 'frdo_doc_type',
            'dvik157': 'dvik157',
            'vmc157': 'vmc157',
            'eva_default': 'eva_default',
            'permit_doc_gov': 'permit_doc_gov',
            'examiner_default': 'examiner_default',
            'edu_doc_frdo': 'edu_doc_frdo',
            'edt': 'edit_date',
        }

        DATE_FIELDS = {'new_price_date', 'archive_date'}
        DATETIME_FIELDS = {'edit_date'}
        INT_FIELDS = {
            'id_dep', 'id_org', 'id_blank', 'id_sign', 'period_hours',
            'period_days', 'period_weeks', 'bonus_rate', 'group_limit',
            'quant_required', 'contract_first', 'user_admin', 'instructor',
            'ais_sert', 'ais_rank', 'permit_doc_gov', 'examiner_default',
        }
        FLOAT_FIELDS = {'price', 'new_price', 'old_price', 'msun'}
        BOOL_FIELDS = {'is_published', 'dvik157', 'vmc157'}

        dry_run = options['dry_run']

        with open(options['csv_file'], 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            updated = 0
            skipped = 0
            not_found = 0

            for row in reader:
                idpro = row.get('idpro', '').strip()
                if not idpro:
                    skipped += 1
                    continue

                try:
                    program = TrainingProgram.objects.get(pk=int(idpro))
                except (TrainingProgram.DoesNotExist, ValueError):
                    not_found += 1
                    continue

                changed = False
                for csv_col, model_field in FIELD_MAP.items():
                    csv_val = row.get(csv_col, '').strip()
                    if not csv_val:
                        continue

                    try:
                        TrainingProgram._meta.get_field(model_field)
                    except Exception:
                        continue

                    if model_field in DATE_FIELDS:
                        try:
                            parsed = datetime.strptime(csv_val.split(' ')[0], '%m/%d/%y').date()
                            csv_val = parsed
                        except (ValueError, IndexError):
                            continue
                    elif model_field in DATETIME_FIELDS:
                        try:
                            parsed = datetime.strptime(csv_val, '%m/%d/%y %H:%M:%S')
                            csv_val = parsed
                        except ValueError:
                            try:
                                parsed = datetime.strptime(csv_val.split(' ')[0], '%m/%d/%y')
                                csv_val = parsed
                            except ValueError:
                                continue
                    elif model_field in INT_FIELDS:
                        try:
                            csv_val = int(float(csv_val))
                        except (ValueError, TypeError):
                            continue
                    elif model_field in FLOAT_FIELDS:
                        try:
                            csv_val = float(csv_val)
                        except (ValueError, TypeError):
                            continue
                    elif model_field in BOOL_FIELDS:
                        csv_val = csv_val.lower() in ('да', 'yes', '1', 'true', 'опубликована')

                    setattr(program, model_field, csv_val)
                    changed = True

                if changed and not dry_run:
                    program.save()
                    updated += 1
                elif changed:
                    updated += 1

        action = 'Будет обновлено' if dry_run else 'Обновлено'
        self.stdout.write(self.style.SUCCESS(
            f'{action}: {updated}, пропущено: {skipped}, не найдено: {not_found}'
        ))
