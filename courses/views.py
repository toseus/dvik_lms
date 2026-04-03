import json
import os
from django.conf import settings
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import Course, CourseStep, Question, Enrollment, StepCompletion, Order, Program, Person, Company, OrganizationAssignment, PersonOrganization, TrainingProgram, Message, LearningModule, ModuleStep, QuizQuestion, Signer, Contract, Space, ModuleProgress, StepProgress, QuizAttempt, ModuleResult, ProgramDocument, ProgramDocumentTemplate, Department, WorkRole, PersonDocument, SeaService, ProgramTemplate, ModuleAssignment, QuizAnswerRecord, MenuPermission
from django.contrib.auth import authenticate, login, logout
from django.db import IntegrityError
from django.contrib import messages
from courses.decorators import menu_access_required, menu_access_any


# ─────────────────────────────────────────────
# Список курсов
# ─────────────────────────────────────────────
@login_required
@menu_access_required('learning')
def course_list(request):
    courses = Course.objects.filter(is_active=True).prefetch_related('steps')
    return render(request, 'courses/list.html', {'courses': courses})


# ─────────────────────────────────────────────
# Страница обучения (learn) — прохождение курса
# ─────────────────────────────────────────────
@login_required
@menu_access_required('learning')
def learn_view(request, pk):
    """Страница прохождения курса — шаги, прогресс, загрузки."""
    course = get_object_or_404(Course, pk=pk)
    steps = list(course.steps.order_by('order'))

    # Зачисление и прогресс
    enrollment = None
    completed_step_ids = set()
    graded_step_ids = set()

    if hasattr(request.user, 'person'):
        enrollment = Enrollment.objects.filter(
            person=request.user.person, course=course
        ).first()
        if enrollment:
            for sc in enrollment.completed_steps.select_related('step').all():
                completed_step_ids.add(sc.step_id)
                if sc.graded_by_id is not None:
                    graded_step_ids.add(sc.step_id)

    # Формируем JSON курса для JS
    steps_data = []
    for idx, step in enumerate(steps):
        steps_data.append({
            'id': step.pk,
            'idx': idx,
            'type': step.type,
            'title': step.title,
            'role': step.role,
            'url': step.url,
            'date': step.date.strftime('%d.%m.%Y') if step.date else None,
        })

    course_json = {
        'id': course.pk,
        'short': course.short_name,
        'title': course.title,
        'author': course.author,
        'description': course.description,
        'assignedDate': enrollment.assigned_date.strftime('%d.%m.%Y') if enrollment else '',
        'coverColor': course.cover_color,
        'coverBg': course.cover_bg or f'linear-gradient(135deg,{course.cover_color} 0%,#08305a 100%)',
        'steps': steps_data,
    }

    return render(request, 'courses/learn.html', {
        'course': course,
        'course_json': json.dumps(course_json, ensure_ascii=False),
        'completed_ids_json': json.dumps(list(completed_step_ids)),
        'graded_ids_json': json.dumps(list(graded_step_ids)),
    })


# ─────────────────────────────────────────────
# Страница тестирования (quest)
# ─────────────────────────────────────────────
@login_required
@menu_access_required('learning')
def quest_view(request, step_pk):
    """Страница тестирования — вопросы из БД."""
    step = get_object_or_404(CourseStep, pk=step_pk, type='test')
    course = step.course
    questions = list(step.questions.order_by('order'))

    questions_json = []
    for q in questions:
        qdata = {
            'text': q.text,
            'type': q.type,
            'points': q.points,
            'weight': q.weight,
            'image': q.image_url or None,
            'caption': q.caption or None,
            'description': q.description or None,
            'instruction': q.instruction,
            'answers': q.answers,
            'correct': q.correct,
        }
        if q.type == 'match' and q.terms:
            qdata['terms'] = q.terms
        questions_json.append(qdata)

    return render(request, 'courses/test.html', {
        'course': course,
        'step': step,
        'questions_json': json.dumps(questions_json, ensure_ascii=False),
        'test_time': course.test_time_minutes,
    })


# ─────────────────────────────────────────────
# API: отметить шаг как пройденный
# ─────────────────────────────────────────────
@login_required
@menu_access_required('learning')
@require_POST
def step_complete(request, pk):
    step = get_object_or_404(CourseStep, pk=pk)

    if not hasattr(request.user, 'person'):
        return JsonResponse({'error': 'Нет привязки к слушателю'}, status=400)

    enrollment = Enrollment.objects.filter(
        person=request.user.person, course=step.course
    ).first()
    if not enrollment:
        return JsonResponse({'error': 'Нет зачисления на курс'}, status=400)

    obj, created = StepCompletion.objects.get_or_create(
        enrollment=enrollment, step=step
    )

    return JsonResponse({
        'ok': True,
        'created': created,
        'progress': enrollment.progress_percent,
    })


# ─────────────────────────────────────────────
# API: загрузка файла для шага upload
# ─────────────────────────────────────────────
@login_required
@menu_access_required('learning')
@require_POST
def step_upload(request, pk):
    step = get_object_or_404(CourseStep, pk=pk)

    if not hasattr(request.user, 'person'):
        return JsonResponse({'error': 'Нет привязки к слушателю'}, status=400)

    enrollment = Enrollment.objects.filter(
        person=request.user.person, course=step.course
    ).first()
    if not enrollment:
        return JsonResponse({'error': 'Нет зачисления'}, status=400)

    f = request.FILES.get('file')
    if not f:
        return JsonResponse({'error': 'Нет файла'}, status=400)

    obj, created = StepCompletion.objects.get_or_create(
        enrollment=enrollment, step=step
    )
    obj.uploaded_file = f
    obj.save()

    return JsonResponse({
        'ok': True,
        'filename': f.name,
        'size': f.size,
    })


# ─────────────────────────────────────────────
# API: сохранить результат теста
# ─────────────────────────────────────────────
@login_required
@menu_access_required('learning')
@require_POST
def quest_result(request, step_pk):
    step = get_object_or_404(CourseStep, pk=step_pk, type='test')

    if not hasattr(request.user, 'person'):
        return JsonResponse({'error': 'Нет привязки к слушателю'}, status=400)

    enrollment = Enrollment.objects.filter(
        person=request.user.person, course=step.course
    ).first()
    if not enrollment:
        return JsonResponse({'error': 'Нет зачисления'}, status=400)

    try:
        data = json.loads(request.body)
    except (ValueError, KeyError):
        return JsonResponse({'error': 'bad json'}, status=400)

    score = data.get('score', 0)

    obj, created = StepCompletion.objects.get_or_create(
        enrollment=enrollment, step=step
    )
    obj.test_score = score
    obj.save()

    return JsonResponse({
        'ok': True,
        'progress': enrollment.progress_percent,
    })


# ─────────────────────────────────────────────
# API: данные курсов для личного кабинета
# ─────────────────────────────────────────────
@login_required
@menu_access_required('learning')
def api_my_courses(request):
    if not hasattr(request.user, 'person'):
        return JsonResponse({'courses': []})

    enrollments = Enrollment.objects.filter(
        person=request.user.person, is_active=True
    ).select_related('course').prefetch_related(
        'course__steps', 'completed_steps'
    )

    courses = []
    for enr in enrollments:
        course = enr.course
        total = course.steps.count()
        done = enr.completed_steps.count()
        courses.append({
            'id': course.pk,
            'short': course.short_name,
            'title': course.title,
            'author': course.author,
            'description': course.description,
            'coverColor': course.cover_color,
            'coverEmoji': course.cover_emoji,
            'coverBg': course.cover_bg or f'linear-gradient(135deg,{course.cover_color} 0%,#08305a 100%)',
            'assignedDate': enr.assigned_date.strftime('%d.%m.%Y'),
            'progress': enr.progress_percent,
            'totalSteps': total,
            'doneSteps': done,
            'url': f'/courses/{course.pk}/learn/',
        })

    return JsonResponse({'courses': courses})

# ─────────────────────────────────────────────
# Список физических лиц
# ─────────────────────────────────────────────
@login_required
@menu_access_required('persons')
def person_list(request):
    q = request.GET.get('q', '').strip()
    sort = request.GET.get('sort', 'id')
    direction = request.GET.get('dir', 'desc')

    allowed_sorts = {
        'id': 'pk',
        'last_name': 'last_name',
        'snils': 'snils',
        'position': 'position',
        'workplace': 'workplace',
    }
    order_field = allowed_sorts.get(sort, 'last_name')
    if direction == 'desc':
        order_field = '-' + order_field

    persons = Person.objects.select_related('user').order_by(order_field)
    if q:
        from django.db.models import Q
        persons = persons.filter(
            Q(last_name__icontains=q)   |
            Q(first_name__icontains=q)  |
            Q(middle_name__icontains=q) |
            Q(snils__icontains=q)       |
            Q(workplace__icontains=q)
        )
    from django.core.paginator import Paginator
    paginator = Paginator(persons, 50)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    return render(request, 'persons/list.html', {
        'persons': page_obj,
        'q': q,
        'total_count': paginator.count,
        'sort': sort,
        'sort_dir': direction,
    })


# ─────────────────────────────────────────────
# Список слушателей (у кого есть user)
# ─────────────────────────────────────────────
@login_required
@menu_access_required('students')
def student_list(request):
    """Список слушателей (у кого есть аккаунт)"""
    q = request.GET.get('q', '').strip()
    sort = request.GET.get('sort', 'id')
    direction = request.GET.get('dir', 'desc')

    allowed_sorts = {
        'id': 'pk',
        'last_name': 'last_name',
        'snils': 'snils',
        'position': 'position',
        'workplace': 'workplace',
    }
    order_field = allowed_sorts.get(sort, 'last_name')
    if direction == 'desc':
        order_field = '-' + order_field

    persons = Person.objects.filter(user__isnull=False).select_related('user').order_by(order_field)

    pos = request.GET.get('pos', '').strip()
    if pos:
        persons = persons.filter(position=pos)

    if q:
        from django.db.models import Q
        persons = persons.filter(
            Q(last_name__icontains=q) |
            Q(first_name__icontains=q) |
            Q(middle_name__icontains=q) |
            Q(snils__icontains=q)
        )

    # AJAX-ответ для обновления таблицы
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.GET.get('json') == '1':
        from django.core.paginator import Paginator
        paginator = Paginator(persons, 50)
        page_number = request.GET.get('page', 1)
        page_obj = paginator.get_page(page_number)
        persons_data = []
        for p in page_obj:
            persons_data.append({
                'id': p.id,
                'snils': p.snils,
                'last_name': p.last_name,
                'first_name': p.first_name,
                'middle_name': p.middle_name,
                'dob': p.dob.isoformat() if p.dob else None,
                'position': p.position,
                'workplace': p.workplace,
                'username': p.user.username if p.user else None,
            })
        return JsonResponse({'persons': persons_data})

    from django.core.paginator import Paginator
    paginator = Paginator(persons, 50)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    return render(request, 'persons/students.html', {
        'persons': page_obj,
        'q': q,
        'total_count': paginator.count,
        'sort': sort,
        'sort_dir': direction,
        'current_pos': pos,
    })

# ─────────────────────────────────────────────
# Карточка слушателя (4-колоночный layout)
# ─────────────────────────────────────────────
@login_required
@menu_access_required('students')
def student_card(request, pk):
    person = get_object_or_404(
        Person.objects.select_related('user').prefetch_related(
            'orders__programs__training_program',
            'messages__author',
            'documents',
            'sea_services',
        ),
        pk=pk
    )

    # Заявки с программами
    orders_data = []
    for o in person.orders.all():
        programs_in_order = []
        for p in o.programs.all():
            tp = p.training_program
            if tp:
                display_name = f'{tp.pk} | {tp.code or tp.title or ""}'
            elif p.code:
                display_name = p.code
            else:
                display_name = '\u2014'
            # Статус модулей
            ma_qs = ModuleAssignment.objects.filter(program_line=p, is_active=True)
            module_status = None
            if ma_qs.exists():
                ma_total = ma_qs.count()
                ma_completed = 0
                for ma in ma_qs.select_related('module'):
                    mp = ModuleProgress.objects.filter(person=person, module=ma.module).first()
                    if mp and mp.is_completed:
                        ma_completed += 1
                module_status = {'total': ma_total, 'completed': ma_completed}

            programs_in_order.append({
                'id': p.pk,
                'catId': tp.pk if tp else p.pk,
                'name': display_name,
                'sub': p.category or '\u0411\u0426',
                'price': float(p.amount) if p.amount else 0,
                'dateFrom': p.date_start.isoformat() if p.date_start else '',
                'dateTo': p.date_end.isoformat() if p.date_end else '',
                'disc': 0,
                'dt': '',
                'docNum': p.cert_number or '',
                'regNum': p.reg_number or '',
                'issuedDate': p.issued_date.isoformat() if p.issued_date else '',
                'grade': p.grade or '',
                'paymentDate': p.payment_date.isoformat() if p.payment_date else '',
                'moduleStatus': module_status,
                'manualGrade': p.grade or '',
            })
        payer_name = o.payer or ''
        if not payer_name and o.payer_company:
            payer_name = str(o.payer_company)
        if not payer_name and o.payer_is_person:
            payer_name = f'{person.last_name} {person.first_name[:1]}.{person.middle_name[:1]}.' if person.middle_name else f'{person.last_name} {person.first_name[:1]}.'
        total = sum(float(p.amount) for p in o.programs.all())
        orders_data.append({
            'id': o.pk,
            'num': str(o.pk).zfill(5),
            'date': o.date.isoformat() if o.date else '',
            'payer': payer_name or '\u2014',
            'payerType': o.payer_type or '',
            'author': o.author or '\u2014',
            'bonus': 0,
            'status': 'draft',
            'paid': False,
            'debt': 0,
            'programs': programs_in_order,
        })

    # Документы слушателя
    person_docs = []
    for doc in person.documents.all():
        person_docs.append({
            'id': doc.pk,
            'date': doc.created_at.strftime('%Y-%m-%d') if doc.created_at else '',
            'name': doc.title,
            'author': str(doc.uploaded_by) if doc.uploaded_by else '\u2014',
            'archived': doc.is_archived,
            'fileUrl': doc.file.url if doc.file else None,
        })

    # Ценз
    cenz_data = []
    for ss in person.sea_services.all():
        cenz_data.append({
            'id': ss.pk,
            'dateFrom': ss.date_from.isoformat() if ss.date_from else '',
            'dateTo': ss.date_to.isoformat() if ss.date_to else '',
            'vessel': ss.vessel_name or '',
            'tonnage': ss.tonnage or 0,
            'power': ss.power or 0,
        })

    # Комментарии
    def _author_display(user_obj):
        if not user_obj:
            return '\u2014'
        name = user_obj.get_full_name().strip()
        if not name and hasattr(user_obj, 'person'):
            try:
                p = user_obj.person
                name = f'{p.last_name} {p.first_name[:1]}.'.strip()
            except Exception:
                pass
        return name or user_obj.username

    msgs_data = []
    for msg in person.messages.all():
        is_own = msg.author == request.user
        author_name = _author_display(msg.author)
        ini_parts = author_name.replace('.', ' ').split()[:2]
        ini = ''.join(w[0] for w in ini_parts if w) if ini_parts else '?'
        msgs_data.append({
            'id': msg.pk,
            'who': author_name,
            'ini': ini,
            'c': 0 if is_own else (hash(author_name) % 4),
            'text': msg.text,
            'time': msg.created_at.strftime('%H:%M') if msg.created_at else '',
            'own': is_own,
            'pinned': msg.is_pinned,
            'cs': msg.case_status or '',
        })

    # Справочник программ для модалки
    all_programs = TrainingProgram.objects.filter(
        status__in=['\u0412 \u0440\u0430\u0431\u043E\u0442\u0435', '\u0412 \u0440\u0430\u0431\u043E\u0442\u0435 \u0412\u041F\u041E']
    ).exclude(title='(\u0431\u0435\u0437 \u043D\u0430\u0437\u0432\u0430\u043D\u0438\u044F)').values('pk', 'code', 'title', 'period_hours', 'new_price', 'price', 'category')[:500]
    programs_catalog = [{
        'id': p['pk'],
        'code': p['code'] or '',
        'name': p['title'] or '',
        'h': p['period_hours'] or 0,
        'p': float(p['new_price'] or p['price'] or 0),
        'cat': p['category'] or '',
    } for p in all_programs]

    # Категории программ
    program_categories = list(
        TrainingProgram.objects.filter(
            status__in=['\u0412 \u0440\u0430\u0431\u043E\u0442\u0435', '\u0412 \u0440\u0430\u0431\u043E\u0442\u0435 \u0412\u041F\u041E']
        ).exclude(category__isnull=True).exclude(category='')
        .values_list('category', flat=True).distinct().order_by('category')
    )

    # Шаблоны наборов программ
    templates = ProgramTemplate.objects.filter(is_active=True).prefetch_related('programs')
    templates_data = [{
        'id': t.pk,
        'name': t.name,
        'programs': list(t.programs.values_list('pk', flat=True)),
        'count': t.programs.count(),
    } for t in templates]

    # Справочники для select'ов
    ais_positions = [
        '\u041A\u0430\u043F\u0438\u0442\u0430\u043D', '\u0421\u0442\u0430\u0440\u0448\u0438\u0439 \u043F\u043E\u043C\u043E\u0449\u043D\u0438\u043A', '\u0412\u0442\u043E\u0440\u043E\u0439 \u043F\u043E\u043C\u043E\u0449\u043D\u0438\u043A', '\u0422\u0440\u0435\u0442\u0438\u0439 \u043F\u043E\u043C\u043E\u0449\u043D\u0438\u043A',
        '\u0421\u0442\u0430\u0440\u0448\u0438\u0439 \u043C\u0435\u0445\u0430\u043D\u0438\u043A', '\u0412\u0442\u043E\u0440\u043E\u0439 \u043C\u0435\u0445\u0430\u043D\u0438\u043A', '\u0422\u0440\u0435\u0442\u0438\u0439 \u043C\u0435\u0445\u0430\u043D\u0438\u043A',
        '\u042D\u043B\u0435\u043A\u0442\u0440\u043E\u043C\u0435\u0445\u0430\u043D\u0438\u043A', '\u0411\u043E\u0446\u043C\u0430\u043D', '\u041C\u0430\u0442\u0440\u043E\u0441',
    ]
    itf_specialties = [
        '\u0421\u0443\u0434\u043E\u0432\u043E\u0436\u0434\u0435\u043D\u0438\u0435',
        '\u042D\u043A\u0441\u043F\u043B\u0443\u0430\u0442\u0430\u0446\u0438\u044F \u0441\u0443\u0434\u043E\u0432\u044B\u0445 \u044D\u043D\u0435\u0440\u0433\u0435\u0442\u0438\u0447\u0435\u0441\u043A\u0438\u0445 \u0443\u0441\u0442\u0430\u043D\u043E\u0432\u043E\u043A',
        '\u042D\u043A\u0441\u043F\u043B\u0443\u0430\u0442\u0430\u0446\u0438\u044F \u0441\u0443\u0434\u043E\u0432\u043E\u0433\u043E \u044D\u043B\u0435\u043A\u0442\u0440\u043E\u043E\u0431\u043E\u0440\u0443\u0434\u043E\u0432\u0430\u043D\u0438\u044F \u0438 \u0441\u0440\u0435\u0434\u0441\u0442\u0432 \u0430\u0432\u0442\u043E\u043C\u0430\u0442\u0438\u043A\u0438',
        '\u042D\u043B\u0435\u043A\u0442\u0440\u043E\u044D\u043D\u0435\u0440\u0433\u0435\u0442\u0438\u043A\u0430 \u0438 \u044D\u043B\u0435\u043A\u0442\u0440\u043E\u0442\u0435\u0445\u043D\u0438\u043A\u0430',
    ]

    def _safe_json(data):
        return json.dumps(data, ensure_ascii=False).replace('</script>', '<\\/script>')

    # Видимость кнопки impersonation
    show_impersonate = MenuPermission.objects.filter(
        menu_item='impersonate_btn', role=getattr(request.user, 'role', ''), is_visible=True
    ).exists()

    context = {
        'person': person,
        'ais_positions': ais_positions,
        'itf_specialties': itf_specialties,
        'show_impersonate_btn': show_impersonate,
        'person_json': _safe_json({'id': person.pk, 'dob': person.dob.isoformat() if person.dob else '', 'gender': person.gender or ''}),
        'orders_json': _safe_json(orders_data),
        'docs_json': _safe_json(person_docs),
        'cenz_json': _safe_json(cenz_data),
        'msgs_json': _safe_json(msgs_data),
        'programs_json': _safe_json(programs_catalog),
        'program_categories_json': _safe_json(program_categories),
        'templates_json': _safe_json(templates_data),
    }
    return render(request, 'persons/detail.html', context)


# ─────────────────────────────────────────────
# AJAX: сохранение данных карточки
# ─────────────────────────────────────────────
@login_required
@menu_access_required('students')
@require_POST
def person_save(request, pk):
    person = get_object_or_404(Person, pk=pk)
    try:
        data = json.loads(request.body)
    except (ValueError, KeyError):
        return JsonResponse({'error': 'bad json'}, status=400)

    allowed = [
        'last_name', 'first_name', 'middle_name',
        'last_name_en', 'first_name_en',
        'snils', 'city', 'position', 'workplace', 'notes',
        'phone', 'email', 'address', 'edu_level', 'gender',
        'ais_position', 'edu_document', 'edu_reg_number',
        'itf_specialty',
    ]
    for field in allowed:
        if field in data:
            setattr(person, field, data[field])
    if 'dob' in data:
        person.dob = data['dob'] or None
    if 'edu_year' in data:
        person.edu_year = int(data['edu_year']) if data['edu_year'] else None
    if 'itf_course' in data:
        person.itf_course = int(data['itf_course']) if data['itf_course'] else None
    if 'is_itf' in data:
        val = data['is_itf']
        person.is_itf = val in (True, 'true', 'True', '1', 'on')
    person.save()
    return JsonResponse({'ok': True})


# ─────────────────────────────────────────────
# Добавление слушателя по СНИЛС (поддержка JSON и form-data)
# ─────────────────────────────────────────────
@login_required
@menu_access_required('students')
@require_POST
def student_add(request):
    """
    POST (JSON):
      { snils, create_account?, person_id? }
    """
    try:
        data = json.loads(request.body)
    except (ValueError, KeyError):
        return JsonResponse({'error': 'bad json'}, status=400)

    snils = data.get('snils', '').strip()
    create_account = data.get('create_account', False)
    person_id = data.get('person_id')

    if not snils and not person_id:
        return JsonResponse({'error': 'СНИЛС или ID обязателен'}, status=400)

    # TODO: фильтрация по Space будет добавлена позже
    current_org = None  # заглушка — пока не используем

    # Если передан person_id, используем его
    if person_id:
        try:
            person = Person.objects.get(pk=person_id)
        except Person.DoesNotExist:
            return JsonResponse({'error': 'Person not found'}, status=404)
    else:
        # Нормализуем СНИЛС — оставляем только цифры
        digits = ''.join(filter(str.isdigit, snils))

        # Ищем по цифрам СНИЛС
        person = None
        for p in Person.objects.filter(snils__isnull=False).select_related('user'):
            p_digits = ''.join(filter(str.isdigit, p.snils))
            if p_digits == digits:
                person = p
                break

        if person is None:
            return JsonResponse({'found': False})

    # Проверяем, есть ли уже связь с организацией
    assignment = OrganizationAssignment.objects.filter(
        company=current_org,
        assigned_for=current_org.short_name
    ).first()

    if not assignment:
        # Создаем назначение организации
        assignment = OrganizationAssignment.objects.create(
            company=current_org,
            org_type='educational',
            assigned_by=request.user,
            assigned_for=current_org.short_name,
            notes='Автоматически создано при добавлении слушателя'
        )

    # Проверяем, есть ли связь PersonOrganization
    person_org, created = PersonOrganization.objects.get_or_create(
        person=person,
        assignment=assignment
    )

    # Если связь уже существовала
    if not created:
        return JsonResponse({
            'found': True,
            'exists': True,  # Флаг, что слушатель уже в организации
            'id': person.pk,
            'fio': person.fio,
            'dob': person.dob.isoformat() if person.dob else '',
            'position': person.position,
            'workplace': person.workplace,
            'has_account': person.has_account,
            'url': f'/persons/{person.pk}/',
        })

    # Если просят создать аккаунт и его ещё нет
    if create_account and not person.has_account:
        try:
            person.create_user_account()
            person.refresh_from_db()
        except ValueError as e:
            return JsonResponse({
                'found': True,
                'exists': False,
                'id': person.pk,
                'fio': person.fio,
                'dob': person.dob.isoformat() if person.dob else '',
                'position': person.position,
                'workplace': person.workplace,
                'has_account': False,
                'error': str(e)
            })

    return JsonResponse({
        'found': True,
        'exists': False,
        'id': person.pk,
        'fio': person.fio,
        'dob': person.dob.isoformat() if person.dob else '',
        'position': person.position,
        'workplace': person.workplace,
        'has_account': person.has_account,
        'url': f'/persons/{person.pk}/',
    })

@login_required
@menu_access_required('students')
def order_list(request):
    """Список всех заявок."""
    q = request.GET.get('q', '').strip()
    orders = Order.objects.select_related('person').prefetch_related('programs').all()
    if q:
        from django.db.models import Q
        orders = orders.filter(
            Q(person__last_name__icontains=q) |
            Q(person__snils__icontains=q) |
            Q(pk__icontains=q)
        )
    return render(request, 'orders/list.html', {'orders': orders, 'q': q})


@login_required
@menu_access_required('students')
def api_person_orders(request, person_pk):
    """JSON: заявки и программы конкретного слушателя."""
    person = get_object_or_404(Person, pk=person_pk)
    orders = person.orders.prefetch_related('programs').all()

    orders_data = []
    for order in orders:
        progs = []
        for prog in order.programs.all():
            progs.append({
                'id': prog.pk,
                'category': prog.category,
                'type': prog.prog_type,
                'code': prog.code,
                'dateStart': prog.date_start.isoformat() if prog.date_start else '',
                'dateEnd': prog.date_end.isoformat() if prog.date_end else '',
                'discount': prog.discount,
                'amount': str(prog.amount),
                'certNumber': prog.cert_number,
                'regNumber': prog.reg_number,
                'grade': prog.grade,
                'issueStatus': prog.issue_status,
                'issueStatusDisplay': prog.get_issue_status_display(),
                'notes': prog.notes,
            })
        orders_data.append({
            'id': order.pk,
            'date': order.date.isoformat() if order.date else '',
            'amount': str(order.amount),
            'payer': order.payer,
            'partner': order.partner,
            'author': order.author,
            'programs': progs,
        })

    return JsonResponse({'orders': orders_data})

@login_required
@menu_access_required('companies')
def company_list(request):
    q = request.GET.get('q', '').strip()
    companies = Company.objects.all()
    if q:
        from django.db.models import Q
        companies = companies.filter(
            Q(short_name__icontains=q) |
            Q(full_name__icontains=q) |
            Q(inn__icontains=q)
        )
    return render(request, 'companies/list.html', {
        'companies': companies,
        'q': q,
    })

# ─────────────────────────────────────────────
# Вспомогательные функции
# ─────────────────────────────────────────────
ROLE_LABELS = {
    'student':    'Слушатель',
    'teacher':    'Преподаватель',
    'admin':      'Администратор',
    'superadmin': 'Суперадминистратор',
}


def _user_context(user):
    """Стандартный контекст для шаблонов с данными пользователя."""
    full_name = user.get_full_name() or user.username
    parts = full_name.split()
    initials = ''.join(p[0] for p in parts)[:2].upper() if parts else 'U'
    role = getattr(user, 'role', 'student')

    # Получаем курсы слушателя из БД
    course_ids = []
    enrollments_data = []
    if hasattr(user, 'person') and user.person:
        enrollments = Enrollment.objects.filter(
            person=user.person, is_active=True
        ).select_related('course').prefetch_related(
            'course__steps', 'completed_steps'
        )
        for enr in enrollments:
            course = enr.course
            course_ids.append(course.pk)
            total = course.steps.count()
            done = enr.completed_steps.count()
            enrollments_data.append({
                'id': course.pk,
                'short': course.short_name,
                'title': course.title,
                'author': course.author,
                'description': course.description,
                'coverColor': course.cover_color,
                'coverEmoji': course.cover_emoji,
                'coverBg': course.cover_bg or f'linear-gradient(135deg,{course.cover_color} 0%,#08305a 100%)',
                'assignedDate': enr.assigned_date.strftime('%d.%m.%Y'),
                'progress': enr.progress_percent,
                'totalSteps': total,
                'doneSteps': done,
            })

    return {
        'user_display_name': full_name,
        'user_initials':     initials,
        'user_role_display': ROLE_LABELS.get(role, role),
        'course_ids_json':   json.dumps(course_ids),
        'enrollments_json':  json.dumps(enrollments_data, ensure_ascii=False),
    }


# ─────────────────────────────────────────────
# Вход / Выход
# ─────────────────────────────────────────────
def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    error = None
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect(request.GET.get('next', 'dashboard'))
        else:
            error = 'Неверный логин или пароль'

    return render(request, 'auth/login.html', {'error': error})


@require_POST
def logout_view(request):
    logout(request)
    return redirect('login')


# ─────────────────────────────────────────────
# Личный кабинет
# ─────────────────────────────────────────────
@login_required
@menu_access_required('dashboard')
def dashboard(request):
    from .utils import get_current_person
    context = {
        'greeting': _get_greeting(),
    }

    role = getattr(request.user, 'role', 'student')
    person = get_current_person(request)

    if role == 'student' and person:
        context.update(_dashboard_student(person))
    elif role in ('admin', 'superadmin', 'teacher'):
        context.update(_dashboard_admin(request.user))

    return render(request, 'dashboard/dashboard.html', context)


def _get_greeting():
    """Возвращает приветствие по времени суток (Asia/Vladivostok)."""
    from datetime import datetime
    from zoneinfo import ZoneInfo
    tz = ZoneInfo('Asia/Vladivostok')
    hour = datetime.now(tz).hour
    if hour < 6:
        return 'Доброй ночи'
    elif hour < 12:
        return 'Доброе утро'
    elif hour < 18:
        return 'Добрый день'
    else:
        return 'Добрый вечер'


def _dashboard_student(person):
    """Статистика обучения для слушателя."""
    # Завершённые (реальные, не preview)
    completed_ids = set(
        ModuleResult.objects.filter(
            person=person, final_exam_passed=True, is_preview=False,
        ).values_list('module_id', flat=True)
    )
    completed_count = len(completed_ids)

    # Незавершённые назначения
    assignments = ModuleAssignment.objects.filter(
        person=person, is_active=True
    ).select_related('module', 'module__program').exclude(
        module_id__in=completed_ids
    )

    active_count = assignments.count()

    modules_data = []
    in_progress_count = 0

    for a in assignments:
        m = a.module
        progress = ModuleProgress.objects.filter(person=person, module=m).first()
        total_steps = m.steps.filter(is_active=True).count()
        current_step = 0
        if progress and progress.current_step:
            current_step = m.steps.filter(order__lte=progress.current_step.order).count()

        progress_percent = round(current_step / total_steps * 100) if total_steps > 0 else 0
        if progress_percent > 0:
            in_progress_count += 1

        modules_data.append({
            'id': m.pk,
            'title': m.title,
            'program_title': m.program.title if m.program else '',
            'program_code': m.program.code if m.program else '',
            'cover_image': m.cover_image or '',
            'total_steps': total_steps,
            'is_completed': False,
            'progress_percent': progress_percent,
        })

    # Модуль для «Продолжить» — первый незавершённый
    continue_module = None
    for md in modules_data:
        if not md['is_completed']:
            continue_module = md
            break

    return {
        'learning_total': active_count + completed_count,
        'learning_active': active_count,
        'learning_completed': completed_count,
        'learning_in_progress': in_progress_count,
        'learning_not_started': active_count - in_progress_count,
        'learning_modules': modules_data[:5],
        'continue_module': continue_module,
        'show_student_panel': True,
    }


def _dashboard_admin(user):
    """Сводная статистика для админов и преподавателей."""
    total_assignments = ModuleAssignment.objects.filter(is_active=True).count()
    total_students = ModuleAssignment.objects.filter(
        is_active=True
    ).values('person').distinct().count()
    total_completed = ModuleResult.objects.filter(
        final_exam_passed=True, is_preview=False
    ).count()

    return {
        'admin_total_assignments': total_assignments,
        'admin_total_students': total_students,
        'admin_total_completed': total_completed,
        'show_admin_panel': True,
    }


@login_required
@menu_access_required('dashboard')
def home_view(request):
    ctx = _user_context(request.user)

    # Данные для разделов «Слушатели» и «Физические лица» (для admin/superadmin)
    if request.user.role in ('admin', 'superadmin'):
        ctx['persons_count'] = Person.objects.count()
        ctx['students_count'] = Person.objects.filter(user__isnull=False).count()

    return render(request, 'dashboard/home.html', ctx)


@login_required
@menu_access_required('learning')
def learn_view(request):
    ctx = _user_context(request.user)
    return render(request, 'courses/learn.html', ctx)


@login_required
@menu_access_required('learning')
def quest_view(request):
    ctx = _user_context(request.user)
    return render(request, 'courses/test.html', ctx)


@login_required
@menu_access_required('organizations')
def organization_list(request):
    """Список назначенных организаций с фильтрацией"""
    q = request.GET.get('q', '').strip()
    org_type = request.GET.get('type', '').strip()

    # Получаем все назначения с связанными компаниями
    assignments = OrganizationAssignment.objects.select_related('company', 'assigned_by').all()

    if q:
        from django.db.models import Q
        assignments = assignments.filter(
            Q(company__short_name__icontains=q) |
            Q(company__full_name__icontains=q) |
            Q(company__inn__icontains=q) |
            Q(assigned_for__icontains=q)
        )

    if org_type:
        assignments = assignments.filter(org_type=org_type)

    return render(request, 'organizations/list.html', {
        'assignments': assignments,
        'q': q,
        'current_type': org_type,
    })


@login_required
@menu_access_required('organizations')
@require_POST
def organization_assign(request):
    """Назначить существующую компанию с типом"""
    try:
        data = json.loads(request.body)
    except (ValueError, KeyError):
        return JsonResponse({'error': 'Неверный формат данных'}, status=400)

    inn = data.get('inn', '').strip()
    org_type = data.get('org_type', '').strip()
    notes = data.get('notes', '').strip()

    # TODO: фильтрация по Space будет добавлена позже

    if not inn:
        return JsonResponse({'error': 'Введите ИНН'}, status=400)

    if not org_type:
        return JsonResponse({'error': 'Выберите тип организации'}, status=400)

    # Ищем компанию по ИНН
    try:
        company = Company.objects.get(inn=inn)
    except Company.DoesNotExist:
        return JsonResponse({
            'error': f'Компания с ИНН {inn} не найдена в справочнике'
        }, status=404)

    # Создаём назначение с автоматическим заполнением assigned_for из текущей организации
    try:
        assignment = OrganizationAssignment.objects.create(
            company=company,
            org_type=org_type,
            assigned_by=request.user,
            assigned_for=request.user.get_full_name() or request.user.username,  # TODO: заменить на Space
            notes=notes
        )

        # Добавляем связь с текущим пользователем, если у него есть Person
        if hasattr(request.user, 'person') and request.user.person:
            from .models import PersonOrganization
            PersonOrganization.objects.get_or_create(
                person=request.user.person,
                assignment=assignment
            )

        return JsonResponse({
            'success': True,
            'id': assignment.id,
            'company': {
                'short_name': company.short_name,
                'full_name': company.full_name,
                'inn': company.inn,
            },
            'org_type': assignment.get_org_type_display(),
            'assigned_for': assignment.assigned_for,
            'created_at': assignment.created_at.strftime('%d.%m.%Y %H:%M'),
        })

    except IntegrityError:
        return JsonResponse({'error': 'Ошибка при создании назначения'}, status=400)

@login_required
@menu_access_required('organizations')
@require_POST
def organization_search_by_inn(request):
    """API для поиска компании по ИНН"""
    try:
        data = json.loads(request.body)
    except (ValueError, KeyError):
        return JsonResponse({'error': 'Неверный формат данных'}, status=400)

    inn = data.get('inn', '').strip()
    if not inn:
        return JsonResponse({'error': 'Введите ИНН'}, status=400)

    try:
        company = Company.objects.get(inn=inn)
        return JsonResponse({
            'found': True,
            'id': company.id,
            'short_name': company.short_name,
            'full_name': company.full_name,
            'inn': company.inn,
        })
    except Company.DoesNotExist:
        return JsonResponse({
            'found': False,
            'message': f'Компания с ИНН {inn} не найдена в справочнике'
        })


@login_required
@menu_access_required('organizations')
@require_POST
def organization_delete(request, pk):
    """Удалить назначение организации"""
    assignment = get_object_or_404(OrganizationAssignment, pk=pk)

    # Проверяем права (можно добавить свою логику)
    if assignment.assigned_by != request.user and request.user.role not in ['admin', 'superadmin']:
        return JsonResponse({'error': 'Нет прав для удаления'}, status=403)

    assignment.delete()
    return JsonResponse({'success': True})


@login_required
@menu_access_required('organizations')
def organization_create(request):
    """Создание новой организации"""
    if request.method == 'POST':
        try:
            company = Company.objects.create(
                short_name=request.POST.get('short_name', '').strip(),
                full_name=request.POST.get('full_name', '').strip(),
                inn=request.POST.get('inn', '').strip(),
                kpp=request.POST.get('kpp', '').strip(),
                ogrn=request.POST.get('ogrn', '').strip(),
                legal_address=request.POST.get('legal_address', '').strip(),
                postal_address=request.POST.get('postal_address', '').strip(),
                phone=request.POST.get('phone', '').strip(),
                email=request.POST.get('email', '').strip(),
                website=request.POST.get('website', '').strip(),
                bank_name=request.POST.get('bank_name', '').strip(),
                bik=request.POST.get('bik', '').strip(),
                corr_account=request.POST.get('corr_account', '').strip(),
                settlement_account=request.POST.get('settlement_account', '').strip(),
                director=request.POST.get('director', '').strip(),
                notes=request.POST.get('notes', '').strip(),
            )
            messages.success(request, f'Организация "{company.short_name}" успешно создана')
            return redirect('company_list')
        except Exception as e:
            messages.error(request, f'Ошибка при создании: {str(e)}')

    return render(request, 'companies/create.html', {
        'title': 'Создание юридического лица'
    })


@login_required
@menu_access_required('organizations')
def organization_edit(request, pk):
    """Редактирование организации"""
    company = get_object_or_404(Company, pk=pk)

    if request.method == 'POST':
        try:
            company.short_name = request.POST.get('short_name', '').strip()
            company.full_name = request.POST.get('full_name', '').strip()
            company.inn = request.POST.get('inn', '').strip()
            company.kpp = request.POST.get('kpp', '').strip()
            company.ogrn = request.POST.get('ogrn', '').strip()
            company.legal_address = request.POST.get('legal_address', '').strip()
            company.postal_address = request.POST.get('postal_address', '').strip()
            company.phone = request.POST.get('phone', '').strip()
            company.email = request.POST.get('email', '').strip()
            company.website = request.POST.get('website', '').strip()
            company.bank_name = request.POST.get('bank_name', '').strip()
            company.bik = request.POST.get('bik', '').strip()
            company.corr_account = request.POST.get('corr_account', '').strip()
            company.settlement_account = request.POST.get('settlement_account', '').strip()
            company.director = request.POST.get('director', '').strip()
            company.notes = request.POST.get('notes', '').strip()
            company.save()

            messages.success(request, f'Организация "{company.short_name}" успешно обновлена')
            return redirect('organization_list')

        except Exception as e:
            messages.error(request, f'Ошибка при обновлении: {str(e)}')

    return render(request, 'companies/create.html', {
        'company': company,
        'title': f'Редактирование: {company.short_name}'
    })


@login_required
@menu_access_required('organizations')
def organization_detail(request, pk):
    """Просмотр детальной информации об организации"""
    company = get_object_or_404(Company, pk=pk)

    # Получаем назначения этой организации
    assignments = OrganizationAssignment.objects.filter(
        company=company
    ).select_related('assigned_by').order_by('-created_at')

    return render(request, 'companies/detail.html', {
        'company': company,
        'assignments': assignments,
    })


@login_required
@menu_access_required('persons')
def person_create(request):
    """Создание нового физического лица"""
    if request.method == 'POST':
        try:
            # Генерируем код доступа если не указан
            code = request.POST.get('code', '').strip()
            if not code:
                import random
                code = ''.join([str(random.randint(0, 9)) for _ in range(6)])

            person = Person.objects.create(
                snils=request.POST.get('snils', '').strip(),
                last_name=request.POST.get('last_name', '').strip(),
                first_name=request.POST.get('first_name', '').strip(),
                middle_name=request.POST.get('middle_name', '').strip(),
                last_name_en=request.POST.get('last_name_en', '').strip(),
                first_name_en=request.POST.get('first_name_en', '').strip(),
                dob=request.POST.get('dob') or None,
                city=request.POST.get('city', '').strip(),
                position=request.POST.get('position', '').strip(),
                workplace=request.POST.get('workplace', '').strip(),
                phone=request.POST.get('phone', '').strip(),
                email=request.POST.get('email', '').strip(),
                notes=request.POST.get('notes', '').strip(),
                code=code,
                created_by=request.user,
            )

            # TODO: автоматическое назначение Space будет добавлено позже

            # Если отмечен чекбокс "создать аккаунт"
            if request.POST.get('create_account') == 'on':
                try:
                    person.create_user_account()
                    messages.success(request, f'Физическое лицо "{person.fio}" успешно создано с аккаунтом')
                except Exception as e:
                    messages.warning(request, f'Физическое лицо создано, но аккаунт не создан: {str(e)}')
            else:
                messages.success(request, f'Физическое лицо "{person.fio}" успешно создано')

            # Если есть параметр next, возвращаемся на страницу слушателей
            next_url = request.GET.get('next')
            if next_url:
                return redirect(next_url)

            return redirect('person_list')

        except Exception as e:
            messages.error(request, f'Ошибка при создании: {str(e)}')

    # Передаем next параметр в шаблон
    next_url = request.GET.get('next')
    return render(request, 'persons/create.html', {
        'title': 'Создание физического лица',
        'next': next_url,
    })

@login_required
@menu_access_required('students')
@require_POST
def check_student_organization(request):
    """Проверка, относится ли слушатель к текущей организации пользователя"""
    try:
        data = json.loads(request.body)
    except (ValueError, KeyError):
        return JsonResponse({'error': 'bad json'}, status=400)

    person_id = data.get('person_id')
    if not person_id:
        return JsonResponse({'error': 'person_id required'}, status=400)

    try:
        person = Person.objects.get(pk=person_id)
    except Person.DoesNotExist:
        return JsonResponse({'error': 'Person not found'}, status=404)

    # TODO: проверка принадлежности к Space будет добавлена позже
    return JsonResponse({'belongs_to_current_org': True})



# ─────────────────────────────────────────────
# Справочник программ обучения
# ─────────────────────────────────────────────

@login_required
@menu_access_required('programs')
def program_catalog(request):
    """Справочник программ обучения."""
    q = request.GET.get('q', '').strip()
    cat = request.GET.get('cat', '').strip()
    dept = request.GET.get('dept', '').strip()
    from django.db.models import Count, Q as DQ
    programs = TrainingProgram.objects.filter(status='В работе').annotate(
        docs_total=Count('documents'),
        docs_uploaded=Count('documents', filter=DQ(documents__file__gt=''))
    )

    if cat:
        programs = programs.filter(category=cat)
    if dept:
        try:
            dept_id = int(dept)
            programs = programs.filter(department_ref_id=dept_id)
        except (ValueError, TypeError):
            programs = programs.filter(department=dept)

    departments_list = Department.objects.filter(is_active=True)

    if q:
        from django.db.models import Q
        programs = programs.filter(
            Q(code__icontains=q) |
            Q(title__icontains=q) |
            Q(category__icontains=q) |
            Q(direction__icontains=q)
        )

    sort = request.GET.get('sort', 'code')
    direction = request.GET.get('dir', 'asc')
    allowed_sorts = {
        'id': 'pk', 'code': 'code', 'title': 'title',
        'category': 'category', 'direction': 'direction',
        'department': 'department', 'price': 'new_price',
        'hours': 'period_hours', 'prog_group': 'prog_group',
    }
    order_field = allowed_sorts.get(sort, 'code')
    if direction == 'desc':
        order_field = '-' + order_field
    programs = programs.order_by(order_field)

    from django.core.paginator import Paginator
    paginator = Paginator(programs, 50)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    return render(request, 'programs/catalog.html', {
        'programs': page_obj,
        'q': q,
        'total_count': paginator.count,
        'current_cat': cat,
        'current_dept': dept,
        'departments_list': departments_list,
        'sort': sort,
        'dir': direction,
    })


# ─────────────────────────────────────────────
# API для личного кабинета
# ─────────────────────────────────────────────

@login_required
@menu_access_required('persons')
def api_persons_list(request):
    """API для списка физических лиц"""
    persons = Person.objects.select_related('user').all().order_by('last_name', 'first_name')

    data = {
        'persons': [{
            'id': p.id,
            'snils': p.snils,
            'last_name': p.last_name,
            'first_name': p.first_name,
            'middle_name': p.middle_name,
            'dob': p.dob.isoformat() if p.dob else None,
            'position': p.position,
            'workplace': p.workplace,
            'fio': str(p),
            'notes': p.notes,
        } for p in persons]
    }
    return JsonResponse(data)


@login_required
@menu_access_required('learning')
def api_schedule(request):
    """API для расписания"""
    # Пока возвращаем пустой список
    return JsonResponse({'schedule': []})


@login_required
@menu_access_required('learning')
def api_results(request):
    """API для результатов тестов"""
    results = []

    if hasattr(request.user, 'person'):
        # Получаем пройденные тесты
        completions = StepCompletion.objects.filter(
            enrollment__person=request.user.person,
            test_score__isnull=False
        ).select_related('step__course')

        for sc in completions:
            results.append({
                'name': sc.step.title,
                'course': sc.step.course.short_name,
                'pct': sc.test_score,
                'date': sc.completed_at.strftime('%d.%m.%Y'),
            })

    return JsonResponse({'results': results})


@login_required
@menu_access_required('learning')
def api_library(request):
    """API для библиотеки"""
    # Пока возвращаем пустой список
    return JsonResponse({'items': []})


@login_required
@menu_access_required('learning')
def api_practice_items(request):
    """API для практических занятий"""
    items = []

    if hasattr(request.user, 'person') and request.user.role in ['teacher', 'superadmin']:
        practice_steps = CourseStep.objects.filter(
            type__in=['practice', 'upload']
        ).select_related('course').order_by('course__short_name', 'order')

        for step in practice_steps:
            items.append({
                'course': {
                    'id': step.course.id,
                    'short': step.course.short_name,
                    'title': step.course.title,
                },
                'step': {
                    'id': step.id,
                    'title': step.title,
                    'type': step.type,
                    'date': step.date.strftime('%d.%m.%Y') if step.date else None,
                },
                'stepIdx': step.order,
            })

    return JsonResponse({'items': items})


@login_required
@menu_access_required('learning')
def api_course_students(request, course_id):
    """API для получения слушателей курса"""
    course = get_object_or_404(Course, pk=course_id)
    students = []

    enrollments = Enrollment.objects.filter(
        course=course,
        is_active=True
    ).select_related('person__user')

    for enr in enrollments:
        if enr.person.user:
            students.append({
                'login': enr.person.user.username,
                'name': str(enr.person),
                'id': enr.person.id,
            })

    return JsonResponse({'students': students})


@login_required
@menu_access_required('learning')
def api_all_students(request):
    """API для всех слушателей"""
    students = Person.objects.filter(
        user__isnull=False
    ).select_related('user').order_by('last_name', 'first_name')

    data = {
        'students': [{
            'id': p.id,
            'login': p.user.username,
            'name': str(p),
            'snils': p.snils,
            'position': p.position,
            'workplace': p.workplace,
        } for p in students]
    }
    return JsonResponse(data)


# ─────────────────────────────────────────────
# Сообщения (чат по слушателю)
# ─────────────────────────────────────────────

@login_required
@menu_access_required('students')
def api_messages(request, person_pk):
    """GET — список сообщений по слушателю."""
    messages_qs = Message.objects.filter(person_id=person_pk).select_related('author').order_by('created_at')

    # Помечаем как прочитанные (если читает не автор)
    messages_qs.filter(is_read=False).exclude(author=request.user).update(is_read=True)

    data = []
    for msg in messages_qs:
        data.append({
            'id': msg.pk,
            'text': msg.text,
            'author_id': msg.author_id,
            'author_name': msg.author.get_full_name() or msg.author.username if msg.author else 'Система',
            'is_mine': msg.author_id == request.user.pk,
            'created_at': msg.created_at.strftime('%d.%m.%Y %H:%M'),
            'date': msg.created_at.strftime('%d.%m.%Y'),
            'time': msg.created_at.strftime('%H:%M'),
            'is_read': msg.is_read,
        })
    return JsonResponse({'messages': data})


@login_required
@menu_access_required('students')
@require_POST
def api_message_send(request, person_pk):
    """POST — отправить сообщение."""
    try:
        data = json.loads(request.body)
    except (ValueError, KeyError):
        return JsonResponse({'error': 'bad json'}, status=400)

    text = data.get('text', '').strip()
    if not text:
        return JsonResponse({'error': 'Пустое сообщение'}, status=400)

    person = get_object_or_404(Person, pk=person_pk)
    msg = Message.objects.create(
        person=person,
        author=request.user,
        text=text,
    )
    return JsonResponse({
        'ok': True,
        'message': {
            'id': msg.pk,
            'text': msg.text,
            'author_name': request.user.get_full_name() or request.user.username,
            'is_mine': True,
            'created_at': msg.created_at.strftime('%d.%m.%Y %H:%M'),
            'date': msg.created_at.strftime('%d.%m.%Y'),
            'time': msg.created_at.strftime('%H:%M'),
        }
    })


# ─────────────────────────────────────────────
# Модули обучения (ELS)
# ─────────────────────────────────────────────

@login_required
@menu_access_required('modules')
def module_list(request):
    from django.db.models import Count, Q as DQ
    q = request.GET.get('q', '').strip()
    modules = LearningModule.objects.select_related('program').annotate(
        total_steps=Count('steps', filter=DQ(steps__is_active=True)),
        material_count=Count('steps', filter=DQ(steps__type='material', steps__is_active=True)),
        slide_count=Count('steps', filter=DQ(steps__type='slide', steps__is_active=True)),
        quiz_count=Count('steps', filter=DQ(steps__type='quiz', steps__is_active=True)),
        practice_count=Count('steps', filter=DQ(steps__type='practice', steps__is_active=True)),
        upload_count=Count('steps', filter=DQ(steps__type='upload', steps__is_active=True)),
        final_exam_count=Count('steps', filter=DQ(steps__type='final_exam', steps__is_active=True)),
    ).order_by('program__code', 'order')

    if q:
        modules = modules.filter(
            DQ(title__icontains=q) |
            DQ(program__code__icontains=q) |
            DQ(program__title__icontains=q)
        )

    from django.core.paginator import Paginator
    paginator = Paginator(modules, 50)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    programs = TrainingProgram.objects.filter(status='В работе').order_by('code')

    return render(request, 'modules/list.html', {
        'modules': page_obj,
        'q': q,
        'total_count': paginator.count,
        'programs': programs,
    })


@login_required
@menu_access_required('modules')
@require_POST
def module_create(request):
    program_id = request.POST.get('program_id')
    title = request.POST.get('title', '').strip()
    if not program_id or not title:
        return redirect('module_list')

    program = get_object_or_404(TrainingProgram, pk=program_id)
    from django.db.models import Max
    max_order = program.modules.aggregate(Max('order'))['order__max'] or 0
    module = LearningModule.objects.create(
        program=program,
        title=title,
        order=max_order + 1,
    )
    return redirect('module_edit', pk=module.pk)


@login_required
@menu_access_required('modules')
def module_edit(request, pk):
    module = get_object_or_404(
        LearningModule.objects.select_related('program').prefetch_related('steps__questions'),
        pk=pk
    )
    return render(request, 'modules/edit.html', {'module': module})


@login_required
@menu_access_required('modules')
@require_POST
def module_delete(request, pk):
    module = get_object_or_404(LearningModule, pk=pk)
    module.delete()
    return redirect('module_list')


@login_required
@menu_access_any('learning', 'modules')
def api_module_steps(request, pk):
    module = get_object_or_404(LearningModule, pk=pk)
    steps = module.steps.filter(is_active=True).order_by('order')
    data = []
    for s in steps:
        data.append({
            'id': s.pk,
            'order': s.order,
            'type': s.type,
            'type_display': s.get_type_display(),
            'title': s.title,
            'description': s.description,
            'url': s.url,
            'time_limit_minutes': s.time_limit_minutes,
            'pass_score': s.pass_score,
            'exam_config': s.exam_config,
            'questions_count': s.questions.count() if s.type in ('quiz', 'slide') else 0,
            'slide_content': s.slide_content,
            'is_active': s.is_active,
        })
    response = JsonResponse({'steps': data}, json_dumps_params={'ensure_ascii': False})
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return response


@login_required
@menu_access_required('modules')
@require_POST
def api_module_steps_save(request, pk):
    module = get_object_or_404(LearningModule, pk=pk)
    try:
        data = json.loads(request.body)
    except ValueError:
        return JsonResponse({'error': 'bad json'}, status=400)

    # Обновить заголовок, описание и обложку модуля
    updated_fields = []
    if 'module_title' in data:
        module.title = data['module_title']
        updated_fields.append('title')
    if 'module_description' in data:
        module.description = data['module_description']
        updated_fields.append('description')
    if 'cover_image' in data:
        module.cover_image = data['cover_image']
        updated_fields.append('cover_image')
    if updated_fields:
        module.save(update_fields=updated_fields)

    steps_data = data.get('steps', [])
    existing_ids = set(module.steps.filter(is_active=True).values_list('pk', flat=True))
    incoming_ids = set()

    for i, step_data in enumerate(steps_data):
        step_id = step_data.get('id')
        defaults = {
            'order': i,
            'type': step_data.get('type', 'material'),
            'title': step_data.get('title', ''),
            'description': step_data.get('description', ''),
            'url': step_data.get('url', ''),
            'time_limit_minutes': step_data.get('time_limit_minutes') or None,
            'pass_score': step_data.get('pass_score') or None,
            'exam_config': step_data.get('exam_config'),
            'slide_content': step_data.get('slide_content', ''),
            'is_active': step_data.get('is_active', True),
        }

        if step_id and step_id in existing_ids:
            ModuleStep.objects.filter(pk=step_id, module=module).update(**defaults)
            incoming_ids.add(step_id)
        else:
            new_step = ModuleStep.objects.create(module=module, **defaults)
            incoming_ids.add(new_step.pk)

    to_delete = existing_ids - incoming_ids
    if to_delete:
        # Не удалять шаги, у которых есть вопросы — деактивировать
        for del_id in to_delete:
            has_questions = QuizQuestion.objects.filter(step_id=del_id).exists()
            if has_questions:
                ModuleStep.objects.filter(pk=del_id).update(is_active=False)
            else:
                ModuleStep.objects.filter(pk=del_id).delete()

    return JsonResponse({'ok': True})


@login_required
@menu_access_any('learning', 'modules')
def api_step_questions(request, pk):
    step = get_object_or_404(ModuleStep, pk=pk)
    questions = step.questions.order_by('order')
    data = []
    for q in questions:
        data.append({
            'id': q.pk,
            'order': q.order,
            'type': q.type,
            'text': q.text,
            'points': q.points,
            'image_url': q.image_url,
            'explanation': q.explanation,
            'answers': q.answers,
            'correct': q.correct,
            'terms': q.terms,
        })
    return JsonResponse({'questions': data, 'step_title': step.title}, json_dumps_params={'ensure_ascii': False})


@login_required
@menu_access_required('modules')
@require_POST
def api_step_questions_save(request, pk):
    step = get_object_or_404(ModuleStep, pk=pk)
    try:
        data = json.loads(request.body)
    except ValueError:
        return JsonResponse({'error': 'bad json'}, status=400)

    questions_data = data.get('questions', [])
    existing_ids = set(step.questions.values_list('pk', flat=True))
    incoming_ids = set()

    for i, q_data in enumerate(questions_data):
        q_id = q_data.get('id')
        defaults = {
            'order': i,
            'type': q_data.get('type', 'single'),
            'text': q_data.get('text', ''),
            'points': q_data.get('points', 1),
            'image_url': q_data.get('image_url', ''),
            'explanation': q_data.get('explanation', ''),
            'answers': q_data.get('answers', []),
            'correct': q_data.get('correct', []),
            'terms': q_data.get('terms'),
        }

        if q_id and q_id in existing_ids:
            QuizQuestion.objects.filter(pk=q_id, step=step).update(**defaults)
            incoming_ids.add(q_id)
        else:
            new_q = QuizQuestion.objects.create(step=step, **defaults)
            incoming_ids.add(new_q.pk)

    to_delete = existing_ids - incoming_ids
    if to_delete:
        QuizQuestion.objects.filter(pk__in=to_delete).delete()

    return JsonResponse({'ok': True, 'count': len(questions_data)})


# ─────────────────────────────────────────────
# Превью модуля
# ─────────────────────────────────────────────

@login_required
@menu_access_any('learning', 'modules')
def module_preview(request, pk):
    module = get_object_or_404(LearningModule.objects.select_related('program'), pk=pk)
    from django.urls import reverse
    from .utils import is_impersonating
    role = getattr(request.user, 'role', 'student')
    # Слушатель или суперадмин в режиме impersonation → обратно в обучение
    if role == 'student' or is_impersonating(request):
        back_url = reverse('student_learning')
        back_label = 'Назад к обучению'
    else:
        back_url = reverse('module_list')
        back_label = 'Назад к модулям'
    return render(request, 'modules/preview.html', {
        'module': module, 'back_url': back_url, 'back_label': back_label,
    })


@login_required
@menu_access_any('learning', 'modules')
def module_slides(request, pk):
    """Прохождение слайд-презентации внутри одного этапа (pk = ModuleStep.pk)."""
    step = get_object_or_404(ModuleStep.objects.select_related('module__program'), pk=pk)

    # Парсим слайды из slide_content (JSON массив)
    try:
        slides_data = json.loads(step.slide_content) if step.slide_content else []
    except (json.JSONDecodeError, TypeError):
        slides_data = []

    slides_json = json.dumps(slides_data, ensure_ascii=False).replace('</script>', '<\\/script>')
    return render(request, 'modules/slides.html', {
        'step': step,
        'module': step.module,
        'slides_json': slides_json,
        'total_slides': len(slides_data),
    })


@login_required
@menu_access_any('learning', 'modules')
def module_quiz_preview(request, step_pk):
    step = get_object_or_404(ModuleStep.objects.select_related('module__program'), pk=step_pk)
    return render(request, 'modules/quiz.html', {'step': step, 'preview': True})


@login_required
@menu_access_required('modules')
@require_POST
def api_import_questions(request, pk):
    """Импорт вопросов из Excel."""
    step = get_object_or_404(ModuleStep, pk=pk)

    if 'file' not in request.FILES:
        return JsonResponse({'error': 'Файл не выбран'}, status=400)

    import openpyxl
    from django.db.models import Max

    try:
        wb = openpyxl.load_workbook(request.FILES['file'], read_only=True)
        ws = wb.active

        imported = 0
        max_order = step.questions.aggregate(Max('order'))['order__max'] or -1

        for row in ws.iter_rows(min_row=2, values_only=True):
            if not row or not row[0]:
                continue

            q_type = str(row[0]).strip().lower()
            if q_type not in ('single', 'multi', 'order', 'match'):
                continue

            text = str(row[1] or '').strip()
            if not text:
                continue

            points = int(row[2] or 1)

            answers = []
            for i in range(3, 9):
                val = row[i] if i < len(row) else None
                if val and str(val).strip():
                    answers.append(str(val).strip())

            correct_str = str(row[9] or '').strip() if len(row) > 9 else ''
            correct = []
            if correct_str:
                for x in correct_str.split(','):
                    x = x.strip()
                    if x.isdigit():
                        correct.append(int(x) - 1)

            terms = None
            if q_type == 'match' and len(row) > 10 and row[10]:
                terms = [t.strip() for t in str(row[10]).split('|') if t.strip()]

            image_url = str(row[11] or '').strip() if len(row) > 11 else ''
            explanation = str(row[12] or '').strip() if len(row) > 12 else ''

            max_order += 1
            QuizQuestion.objects.create(
                step=step, order=max_order, type=q_type, text=text,
                points=points, answers=answers, correct=correct,
                terms=terms, image_url=image_url, explanation=explanation,
            )
            imported += 1

        return JsonResponse({'ok': True, 'imported': imported})

    except Exception as e:
        return JsonResponse({'error': f'Ошибка: {str(e)}'}, status=400)


# ─────────────────────────────────────────────
# Загрузка изображений (обложки, картинки вопросов)
# ─────────────────────────────────────────────

@login_required
@menu_access_required('modules')
@require_POST
def upload_module_cover(request, pk):
    """Загрузка обложки модуля."""
    module = get_object_or_404(LearningModule, pk=pk)
    file = request.FILES.get('cover')
    if not file:
        return JsonResponse({'error': 'Файл не выбран'}, status=400)

    upload_dir = os.path.join(settings.MEDIA_ROOT, 'pics', 'modules')
    os.makedirs(upload_dir, exist_ok=True)

    ext = file.name.rsplit('.', 1)[-1].lower() if '.' in file.name else 'png'
    filename = f'module_{module.pk}.{ext}'
    filepath = os.path.join(upload_dir, filename)

    with open(filepath, 'wb+') as f:
        for chunk in file.chunks():
            f.write(chunk)

    url = f'/media/pics/modules/{filename}'
    module.cover_image = url
    module.save(update_fields=['cover_image'])

    return JsonResponse({'success': True, 'url': url})


@login_required
@menu_access_required('modules')
@require_POST
def upload_question_image(request, step_pk):
    """Загрузка картинки для конкретного вопроса."""
    step = get_object_or_404(ModuleStep, pk=step_pk)
    file = request.FILES.get('image')
    question_order = request.POST.get('question_order')

    if not file or not question_order:
        return JsonResponse({'error': 'Файл и номер вопроса обязательны'}, status=400)

    upload_dir = os.path.join(settings.MEDIA_ROOT, 'pics', 'quiz', f'step_{step.pk}')
    os.makedirs(upload_dir, exist_ok=True)

    filename = f'{question_order}.png'
    filepath = os.path.join(upload_dir, filename)

    with open(filepath, 'wb+') as f:
        for chunk in file.chunks():
            f.write(chunk)

    url = f'/media/pics/quiz/step_{step.pk}/{filename}'

    question = QuizQuestion.objects.filter(step=step, order=int(question_order)).first()
    if question:
        question.image_url = url
        question.save(update_fields=['image_url'])

    return JsonResponse({'success': True, 'url': url, 'question_order': question_order})


@login_required
@menu_access_required('modules')
@require_POST
def upload_question_images_bulk(request, step_pk):
    """Массовая загрузка картинок для вопросов теста."""
    step = get_object_or_404(ModuleStep, pk=step_pk)
    files = request.FILES.getlist('images')

    if not files:
        return JsonResponse({'error': 'Файлы не выбраны'}, status=400)

    upload_dir = os.path.join(settings.MEDIA_ROOT, 'pics', 'quiz', f'step_{step.pk}')
    os.makedirs(upload_dir, exist_ok=True)

    uploaded = []
    for file in files:
        name_without_ext = file.name.rsplit('.', 1)[0]
        try:
            question_order = int(name_without_ext)
        except ValueError:
            continue

        filename = f'{question_order}.png'
        filepath = os.path.join(upload_dir, filename)

        with open(filepath, 'wb+') as f:
            for chunk in file.chunks():
                f.write(chunk)

        url = f'/media/pics/quiz/step_{step.pk}/{filename}'

        question = QuizQuestion.objects.filter(step=step, order=question_order).first()
        if question:
            question.image_url = url
            question.save(update_fields=['image_url'])

        uploaded.append({'order': question_order, 'url': url, 'filename': file.name})

    return JsonResponse({'success': True, 'uploaded': uploaded, 'count': len(uploaded)})


@login_required
@menu_access_required('modules')
def list_question_images(request, step_pk):
    """Список загруженных картинок для теста."""
    step = get_object_or_404(ModuleStep, pk=step_pk)
    upload_dir = os.path.join(settings.MEDIA_ROOT, 'pics', 'quiz', f'step_{step.pk}')

    images = []
    if os.path.exists(upload_dir):
        for fname in sorted(os.listdir(upload_dir)):
            if fname.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg')):
                order_str = fname.rsplit('.', 1)[0]
                try:
                    order = int(order_str)
                except ValueError:
                    continue
                url = f'/media/pics/quiz/step_{step.pk}/{fname}'
                size = os.path.getsize(os.path.join(upload_dir, fname))
                images.append({
                    'order': order,
                    'filename': fname,
                    'url': url,
                    'size_kb': round(size / 1024, 1),
                })

    questions = QuizQuestion.objects.filter(step=step).order_by('order')
    question_orders = [q.order for q in questions]
    image_orders = set(img['order'] for img in images)
    missing = [o for o in question_orders if o not in image_orders]

    return JsonResponse({
        'images': images,
        'missing': missing,
        'total_questions': len(question_orders),
    })


@login_required
@menu_access_required('modules')
@require_POST
def delete_question_image(request, step_pk, question_order):
    """Удалить картинку вопроса."""
    step = get_object_or_404(ModuleStep, pk=step_pk)
    upload_dir = os.path.join(settings.MEDIA_ROOT, 'pics', 'quiz', f'step_{step.pk}')

    for ext in ['png', 'jpg', 'jpeg', 'gif', 'svg']:
        filepath = os.path.join(upload_dir, f'{question_order}.{ext}')
        if os.path.exists(filepath):
            os.remove(filepath)

    question = QuizQuestion.objects.filter(step=step, order=question_order).first()
    if question:
        question.image_url = ''
        question.save(update_fields=['image_url'])

    return JsonResponse({'success': True})


# ─────────────────────────────────────────────
# Договоры
# ─────────────────────────────────────────────

@login_required
@menu_access_required('contracts')
def contract_list(request):
    q = request.GET.get('q', '').strip()
    contracts = Contract.objects.select_related('payer', 'our_organization').all()
    if q:
        from django.db.models import Q
        contracts = contracts.filter(
            Q(number__icontains=q) |
            Q(payer__short_name__icontains=q)
        )
    from django.core.paginator import Paginator
    paginator = Paginator(contracts, 50)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    companies = Company.objects.order_by('short_name')
    spaces = Space.objects.filter(is_active=True)

    return render(request, 'contracts/list.html', {
        'contracts': page_obj,
        'q': q,
        'total_count': paginator.count,
        'companies': companies,
        'spaces': spaces,
    })


@login_required
@menu_access_required('contracts')
@require_POST
def contract_create(request):
    try:
        Contract.objects.create(
            number=request.POST.get('number', '').strip(),
            date=request.POST.get('date'),
            payer_id=request.POST.get('payer_id'),
            our_organization_id=request.POST.get('our_org_id'),
            amount=request.POST.get('amount') or None,
            notes=request.POST.get('notes', '').strip(),
        )
    except Exception:
        pass
    return redirect('contract_list')


@login_required
@menu_access_required('contracts')
def api_signers(request):
    space = request.user.space
    if not space:
        return JsonResponse({'signers': []})
    signers = Signer.objects.filter(space=space, is_active=True).order_by('full_name')
    data = [{'id': s.pk, 'full_name': s.full_name, 'position': s.position} for s in signers]
    return JsonResponse({'signers': data})


@login_required
@menu_access_required('contracts')
def api_payers(request, person_pk):
    person = get_object_or_404(Person, pk=person_pk)
    companies = Company.objects.order_by('short_name').values('id', 'short_name', 'inn')
    payers = [{'id': 'self', 'name': f'{person.fio} (сам слушатель)', 'type': 'person'}]
    for c in companies:
        payers.append({'id': c['id'], 'name': f"{c['short_name']} (ИНН: {c['inn']})", 'type': 'company'})
    return JsonResponse({'payers': payers})


@login_required
@menu_access_required('contracts')
def api_contracts_by_payer(request, company_pk):
    contracts = Contract.objects.filter(payer_id=company_pk, is_active=True).order_by('-date')
    data = [{'id': c.pk, 'number': c.number, 'date': c.date.strftime('%d.%m.%Y'), 'display': f'№{c.number} от {c.date.strftime("%d.%m.%Y")}'} for c in contracts]
    return JsonResponse({'contracts': data})


@login_required
@menu_access_required('contracts')
@require_POST
def api_order_create(request):
    try:
        data = json.loads(request.body)
    except ValueError:
        return JsonResponse({'error': 'bad json'}, status=400)

    person = get_object_or_404(Person, pk=data.get('person_id'))
    payer_type = data.get('payer_type')

    from datetime import date
    order = Order.objects.create(
        person=person,
        date=date.today(),
        signer_id=data.get('signer_id'),
        payer_is_person=(payer_type == 'person'),
        payer_company_id=data.get('payer_company_id') if payer_type == 'company' else None,
        contract_id=data.get('contract_id') or None,
        space=request.user.space,
        created_by=request.user,
    )

    return JsonResponse({
        'ok': True,
        'order_id': order.pk,
        'message': f'Заявка №{order.pk} создана',
    })


# ══════════════════════════════════════════════════
#   API ПРОГРЕССА МОДУЛЕЙ
# ══════════════════════════════════════════════════

@login_required
@menu_access_any('learning', 'modules')
def api_module_progress(request, module_pk):
    """GET — получить прогресс по модулю для текущего пользователя."""
    from .utils import get_current_person
    person = get_current_person(request)
    if not person:
        return JsonResponse({'error': 'no person'}, status=400)

    progress, created = ModuleProgress.objects.get_or_create(
        person=person, module_id=module_pk
    )

    steps_data = {}
    for sp in progress.step_progress.select_related('step').all():
        quiz_attempt_in_progress = sp.quiz_attempts.filter(is_completed=False).first()
        quiz_attempt_done = sp.quiz_attempts.filter(is_completed=True).order_by('-completed_at').first()
        entry = {
            'status': sp.status,
            'score': sp.score,
            'current_question': quiz_attempt_in_progress.current_question_index if quiz_attempt_in_progress else 0,
        }
        if quiz_attempt_done and quiz_attempt_done.max_score:
            earned = quiz_attempt_done.score or 0
            mx = quiz_attempt_done.max_score
            pct = round(earned / mx * 100) if mx else 0
            total_q = quiz_attempt_done.answers.get('total_count', 0) if isinstance(quiz_attempt_done.answers, dict) else 0
            correct_q = quiz_attempt_done.answers.get('correct_count', 0) if isinstance(quiz_attempt_done.answers, dict) else 0
            entry['quiz_score'] = pct
            entry['quiz_correct'] = correct_q
            entry['quiz_total'] = total_q
            entry['quiz_earned'] = earned
            entry['quiz_max'] = mx
        steps_data[sp.step_id] = entry

    return JsonResponse({
        'module_id': module_pk,
        'current_step_id': progress.current_step_id,
        'is_completed': progress.is_completed,
        'steps': steps_data,
    })


@login_required
@menu_access_any('learning', 'modules')
@require_POST
def api_step_complete(request, step_pk):
    """POST — отметить этап как пройденный."""
    from .utils import get_current_person
    person = get_current_person(request)
    if not person:
        return JsonResponse({'error': 'no person'}, status=400)

    step = get_object_or_404(ModuleStep, pk=step_pk)
    progress, _ = ModuleProgress.objects.get_or_create(
        person=person, module=step.module
    )

    sp, _ = StepProgress.objects.get_or_create(
        module_progress=progress, step=step
    )

    from django.utils import timezone
    sp.status = 'completed'
    sp.completed_at = timezone.now()
    sp.save()

    # Обновить current_step на следующий незавершённый
    all_steps = list(step.module.steps.filter(is_active=True).order_by('order'))
    completed_ids = set(progress.step_progress.filter(
        status__in=['completed', 'graded']
    ).values_list('step_id', flat=True))

    next_step = None
    for s in all_steps:
        if s.pk not in completed_ids:
            next_step = s
            break
    progress.current_step = next_step

    # Проверить завершение модуля
    if not next_step or all(s.pk in completed_ids for s in all_steps):
        progress.is_completed = True
        progress.completed_at = timezone.now()

    progress.save()

    return JsonResponse({'ok': True, 'is_module_completed': progress.is_completed})


@login_required
@menu_access_any('learning', 'modules')
@require_POST
def api_quiz_save_progress(request, step_pk):
    """POST — сохранить промежуточный прогресс теста."""
    from .utils import get_current_person
    person = get_current_person(request)
    if not person:
        return JsonResponse({'error': 'no person'}, status=400)

    try:
        data = json.loads(request.body)
    except ValueError:
        return JsonResponse({'error': 'bad json'}, status=400)

    step = get_object_or_404(ModuleStep, pk=step_pk)
    progress, _ = ModuleProgress.objects.get_or_create(
        person=person, module=step.module
    )
    sp, _ = StepProgress.objects.get_or_create(
        module_progress=progress, step=step
    )
    if sp.status == 'not_started':
        sp.status = 'in_progress'
        sp.save()

    attempt, _ = QuizAttempt.objects.get_or_create(
        step_progress=sp, is_completed=False
    )
    attempt.answers = data.get('answers', {})
    attempt.current_question_index = data.get('current_question', 0)
    attempt.save()

    return JsonResponse({'ok': True})


@login_required
@menu_access_any('learning', 'modules')
@require_POST
def api_quiz_complete(request, step_pk):
    """POST — завершить тест, сохранить результат."""
    from .utils import get_current_person
    person = get_current_person(request)
    if not person:
        return JsonResponse({'error': 'no person'}, status=400)

    try:
        data = json.loads(request.body)
    except ValueError:
        return JsonResponse({'error': 'bad json'}, status=400)

    step = get_object_or_404(ModuleStep, pk=step_pk)
    progress, _ = ModuleProgress.objects.get_or_create(
        person=person, module=step.module
    )
    sp, _ = StepProgress.objects.get_or_create(
        module_progress=progress, step=step
    )

    from django.utils import timezone
    score = data.get('score', 0)
    max_score = data.get('max_score', 0)

    sp.status = 'completed'
    sp.score = score
    sp.completed_at = timezone.now()
    sp.save()

    # Удалить незавершённые попытки
    QuizAttempt.objects.filter(step_progress=sp, is_completed=False).delete()

    # Создать завершённую запись
    QuizAttempt.objects.create(
        step_progress=sp,
        answers=data.get('answers', {}),
        score=score,
        max_score=max_score,
        is_completed=True,
        completed_at=timezone.now(),
    )

    # Обновить current_step на следующий незавершённый
    all_steps = list(step.module.steps.filter(is_active=True).order_by('order'))
    completed_ids = set(progress.step_progress.filter(
        status__in=['completed', 'graded']
    ).values_list('step_id', flat=True))

    next_step = None
    for s in all_steps:
        if s.pk not in completed_ids:
            next_step = s
            break
    progress.current_step = next_step

    if not next_step or all(s.pk in completed_ids for s in all_steps):
        progress.is_completed = True
        progress.completed_at = timezone.now()

    progress.save()

    return JsonResponse({'ok': True, 'score': score})


# ══════════════════════════════════════════════════
#   ИТОГОВАЯ АТТЕСТАЦИЯ
# ══════════════════════════════════════════════════

@login_required
@menu_access_any('learning', 'modules')
def api_final_exam_questions(request, step_pk):
    """GET — собрать вопросы для итоговой аттестации из промежуточных тестов."""
    import random

    step = get_object_or_404(ModuleStep, pk=step_pk, type='final_exam')
    exam_config = step.exam_config or {}

    order_questions = []
    match_questions = []
    regular_questions = []

    for quiz_step_id_str, count in exam_config.items():
        qs = list(QuizQuestion.objects.filter(step_id=int(quiz_step_id_str)))
        for q in qs:
            q._source_step_id = int(quiz_step_id_str)
        order_questions.extend([q for q in qs if q.type == 'order'])
        match_questions.extend([q for q in qs if q.type == 'match'])
        regular_questions.extend([q for q in qs if q.type in ('single', 'multi')])

    selected = []

    if order_questions:
        chosen = random.choice(order_questions)
        selected.append(chosen)
        order_questions.remove(chosen)

    if match_questions:
        chosen = random.choice(match_questions)
        selected.append(chosen)
        match_questions.remove(chosen)

    remaining_pool = order_questions + match_questions + regular_questions
    random.shuffle(remaining_pool)

    total_needed = sum(int(v) for v in exam_config.values())
    still_needed = total_needed - len(selected)
    if still_needed > 0:
        selected.extend(remaining_pool[:still_needed])

    random.shuffle(selected)

    data = []
    for q in selected:
        data.append({
            'id': q.pk,
            'order': len(data),
            'type': q.type,
            'text': q.text,
            'points': q.points,
            'image_url': q.image_url,
            'explanation': q.explanation,
            'answers': q.answers,
            'correct': q.correct,
            'terms': q.terms,
            'source_step_id': getattr(q, '_source_step_id', None),
        })

    return JsonResponse({
        'questions': data,
        'total': len(data),
        'pass_score': step.pass_score or 70,
        'time_limit': step.time_limit_minutes,
        'step_title': step.title,
    }, json_dumps_params={'ensure_ascii': False})


@login_required
@menu_access_any('learning', 'modules')
@require_POST
def api_final_exam_submit(request, step_pk):
    """POST — сохранить результат итоговой аттестации."""
    try:
        data = json.loads(request.body)
    except ValueError:
        return JsonResponse({'error': 'bad json'}, status=400)

    step = get_object_or_404(ModuleStep, pk=step_pk, type='final_exam')
    is_preview = data.get('is_preview', False)

    score = data.get('score', 0)
    pass_score = step.pass_score or 70
    passed = score >= pass_score

    from .utils import get_current_person
    from django.utils import timezone
    person = get_current_person(request)
    if not is_preview and person:
        module = step.module
        details = data.get('details', [])
        total_steps = module.steps.filter(is_active=True).count()
        total_questions = len(details) if isinstance(details, list) else 0
        correct_questions = sum(
            1 for a in details if isinstance(a, dict) and a.get('is_correct')
        ) if isinstance(details, list) else 0

        # Создать или обновить ModuleResult (без дублей)
        result, created = ModuleResult.objects.update_or_create(
            person=person,
            module=module,
            is_preview=False,
            defaults={
                'program': module.program,
                'quiz_scores': data.get('quiz_scores', {}),
                'final_exam_step': step,
                'final_exam_score': score,
                'final_exam_passed': passed,
                'final_exam_details': details,
                'total_steps': total_steps,
                'completed_steps': total_steps,
                'total_questions': total_questions,
                'correct_questions': correct_questions,
            },
        )

        # Отметить итоговый шаг как пройденный в StepProgress
        progress, _ = ModuleProgress.objects.get_or_create(
            person=person, module=module
        )
        sp, _ = StepProgress.objects.get_or_create(
            module_progress=progress, step=step
        )
        sp.status = 'completed'
        sp.score = score
        sp.completed_at = timezone.now()
        sp.save()

        # Пометить модуль завершённым при успешной сдаче
        if passed:
            progress.is_completed = True
            progress.completed_at = timezone.now()
            progress.current_step = None
            progress.save(update_fields=['is_completed', 'completed_at', 'current_step'])

    return JsonResponse({
        'ok': True,
        'score': score,
        'passed': passed,
        'pass_score': pass_score,
        'is_preview': is_preview,
    })


# ══════════════════════════════════════════════════
#   КАРТОЧКА ПРОГРАММЫ ОБУЧЕНИЯ
# ══════════════════════════════════════════════════

@login_required
@menu_access_required('programs')
def program_detail(request, pk):
    program = get_object_or_404(
        TrainingProgram.objects.prefetch_related('documents', 'modules'),
        pk=pk
    )
    departments = Department.objects.filter(is_active=True)
    signer_role = WorkRole.objects.filter(code='signer').first()
    if signer_role:
        available_signers = Person.objects.filter(
            work_roles__role=signer_role
        ).order_by('last_name', 'first_name')
    else:
        available_signers = Person.objects.none()
    return render(request, 'programs/detail.html', {
        'program': program,
        'departments': departments,
        'available_signers': available_signers,
    })


@login_required
@menu_access_required('programs')
@require_POST
def program_save(request, pk):
    program = get_object_or_404(TrainingProgram, pk=pk)
    try:
        data = json.loads(request.body)
    except ValueError:
        return JsonResponse({'error': 'bad json'}, status=400)

    text_fields = [
        'code', 'title', 'title_eng', 'department', 'category', 'direction',
        'status', 'stat_type', 'specialty', 'training_form', 'edu_level',
        'prog_group', 'contract_type', 'notes',
        'sert_text1', 'sert_text1_eng', 'sert_text2', 'sert_text2_eng',
        'sert_text3', 'sert_text3_eng', 'sert_text4', 'sert_text4_eng',
        'sub_prog', 'sub_prog_eng', 'signing_head', 'signing_head_eng',
        'blank_type', 'blank_reg_type', 'dpo',
        'main_title', 'old_programm', 'inspection_sts', 'online_sts',
        'auto_contract', 'umkd', 'sfera_prof', 'group_prof', 'color_gr',
        'rem_stu', 'eva_default', 'tr_form_famrt', 'ais_uid_doc_type',
        'frdo_po_prof', 'frdo_po_type_edu', 'frdo_prog_type', 'frdo_doc_type',
        'edu_doc_frdo', 'qual_rank_po',
    ]
    decimal_fields = ['price', 'new_price', 'old_price']
    int_fields = [
        'period_hours', 'period_days', 'period_weeks',
        'id_blank', 'id_sign', 'id_dep', 'id_org',
        'group_limit', 'quant_required', 'bonus_rate',
        'ais_sert', 'ais_rank', 'contract_first', 'user_admin',
        'instructor', 'permit_doc_gov', 'examiner_default',
    ]
    float_fields = ['msun']
    bool_fields = ['is_published', 'dvik157', 'vmc157']
    date_fields = ['archive_date', 'new_price_date']

    for field in text_fields:
        if field in data:
            setattr(program, field, data[field] or '')
    for field in decimal_fields:
        if field in data:
            val = data[field]
            if val:
                from decimal import Decimal, InvalidOperation
                try:
                    val = Decimal(str(val))
                except (InvalidOperation, ValueError):
                    val = None
            else:
                val = None
            setattr(program, field, val)
    for field in int_fields:
        if field in data:
            val = data[field]
            if val is not None and val != '':
                try:
                    val = int(val)
                except (ValueError, TypeError):
                    val = None
            else:
                val = None
            setattr(program, field, val)
    for field in float_fields:
        if field in data:
            val = data[field]
            if val is not None and val != '':
                try:
                    val = float(val)
                except (ValueError, TypeError):
                    val = None
            else:
                val = None
            setattr(program, field, val)
    for field in bool_fields:
        if field in data:
            setattr(program, field, bool(data[field]))
    for field in date_fields:
        if field in data:
            val = data[field]
            setattr(program, field, val if val else None)
    # FK поля
    if 'department_ref' in data:
        val = data['department_ref']
        if val:
            try:
                program.department_ref = Department.objects.get(pk=int(val))
            except (Department.DoesNotExist, ValueError, TypeError):
                program.department_ref = None
        else:
            program.department_ref = None
    if 'signer_person' in data:
        val = data['signer_person']
        if val:
            try:
                program.signer_person = Person.objects.get(pk=int(val))
            except (Person.DoesNotExist, ValueError, TypeError):
                program.signer_person = None
        else:
            program.signer_person = None
    program.save()
    return JsonResponse({'ok': True})


@login_required
@menu_access_required('programs')
@require_POST
def program_document_upload(request, pk):
    program = get_object_or_404(TrainingProgram, pk=pk)
    if 'file' not in request.FILES:
        return JsonResponse({'error': 'Файл не выбран'}, status=400)
    title = request.POST.get('title', '').strip() or request.FILES['file'].name
    doc = ProgramDocument.objects.create(
        program=program, title=title, file=request.FILES['file'], uploaded_by=request.user,
    )
    return JsonResponse({
        'ok': True,
        'doc': {'id': doc.pk, 'title': doc.title, 'filename': doc.filename,
                'url': doc.file.url, 'date': doc.created_at.strftime('%d.%m.%Y')},
    })


@login_required
@menu_access_required('programs')
@require_POST
def program_document_delete(request, doc_pk):
    doc = get_object_or_404(ProgramDocument, pk=doc_pk)
    doc.file.delete(save=False)
    doc.delete()
    return JsonResponse({'ok': True})


@login_required
@menu_access_required('programs')
@require_POST
def create_template_docs(request, pk):
    program = get_object_or_404(TrainingProgram, pk=pk)
    try:
        body = json.loads(request.body)
        template_ids = body.get('template_ids', [])
    except (json.JSONDecodeError, ValueError):
        template_ids = []
    if template_ids:
        templates = ProgramDocumentTemplate.objects.filter(pk__in=template_ids, is_active=True)
    else:
        templates = ProgramDocumentTemplate.objects.filter(is_active=True)
    created = 0
    for tmpl in templates:
        if not ProgramDocument.objects.filter(program=program, template=tmpl).exists():
            ProgramDocument.objects.create(
                program=program,
                template=tmpl,
                title=tmpl.title,
                uploaded_by=request.user
            )
            created += 1
    return JsonResponse({'created': created})


@login_required
@menu_access_required('programs')
def available_templates(request, pk):
    program = get_object_or_404(TrainingProgram, pk=pk)
    templates = ProgramDocumentTemplate.objects.filter(is_active=True).order_by('sort_order')
    existing_template_ids = set(
        ProgramDocument.objects.filter(program=program, template__isnull=False)
        .values_list('template_id', flat=True)
    )
    data = []
    for t in templates:
        data.append({
            'id': t.pk,
            'title': t.title,
            'already_exists': t.pk in existing_template_ids
        })
    return JsonResponse({'templates': data})


# ─────────────────────────────────────────────
# API: карточка слушателя
# ─────────────────────────────────────────────

@login_required
@menu_access_required('students')
@require_POST
def api_person_order_create(request, pk):
    """Создать новую заявку для слушателя."""
    person = get_object_or_404(Person, pk=pk)
    from datetime import date
    order = Order.objects.create(
        person=person,
        date=date.today(),
        author=request.user.get_full_name() or request.user.username,
        created_by=request.user,
    )
    return JsonResponse({
        'success': True,
        'order': {
            'id': order.pk,
            'num': str(order.pk).zfill(5),
            'date': order.date.isoformat(),
            'payer': '',
            'author': order.author,
            'bonus': 0,
            'status': 'draft',
            'paid': False,
            'debt': 0,
            'programs': [],
        }
    })


@login_required
@menu_access_required('students')
@require_POST
def api_order_add_program(request, order_pk):
    """Добавить программы в заявку."""
    order = get_object_or_404(Order, pk=order_pk)
    data = json.loads(request.body)
    program_ids = data.get('program_ids', [])
    added = []
    for tp_id in program_ids:
        tp = TrainingProgram.objects.filter(pk=tp_id).first()
        if not tp:
            continue
        from datetime import timedelta
        prog = Program.objects.create(
            order=order,
            training_program=tp,
            code=str(tp.pk),
            category='',
            date_start=order.date,
            date_end=order.date + timedelta(days=14) if order.date else order.date,
            amount=tp.new_price or tp.price or 0,
        )
        display_name = f'{tp.pk} | {tp.code}' if tp.code else f'{tp.pk} | {tp.title or ""}'
        added.append({
            'id': prog.pk,
            'catId': tp.pk,
            'name': display_name,
            'sub': prog.category or '\u0411\u0426',
            'price': float(prog.amount),
            'dateFrom': prog.date_start.isoformat() if prog.date_start else '',
            'dateTo': prog.date_end.isoformat() if prog.date_end else '',
            'disc': 0,
            'dt': '',
            'docNum': '',
            'regNum': '',
            'issuedDate': '',
            'grade': '',
            'paymentDate': '',
        })
    return JsonResponse({'success': True, 'programs': added})


@login_required
@menu_access_required('students')
@require_POST
def api_order_remove_programs(request, order_pk):
    """Удалить программы из заявки по PK."""
    order = get_object_or_404(Order, pk=order_pk)
    data = json.loads(request.body)
    ids = data.get('ids', [])
    order.programs.filter(pk__in=ids).delete()
    return JsonResponse({'success': True})


@login_required
@menu_access_required('students')
@require_POST
def api_person_document_upload(request, pk):
    """Загрузка документа слушателя."""
    person = get_object_or_404(Person, pk=pk)
    file = request.FILES.get('file')
    title = request.POST.get('title', 'Документ')
    doc_type = request.POST.get('doc_type', 'other')
    rotation = int(request.POST.get('rotation', 0))

    doc = PersonDocument.objects.create(
        person=person,
        title=title,
        doc_type=doc_type,
        file=file,
        rotation=rotation,
        uploaded_by=request.user,
    )

    result = {
        'success': True,
        'document': {
            'id': doc.pk,
            'date': doc.created_at.strftime('%Y-%m-%d'),
            'name': doc.title,
            'author': str(request.user),
            'archived': False,
            'fileUrl': doc.file.url if doc.file else None,
        },
    }

    # Если справка и нужно добавить ценз
    vessel = request.POST.get('vessel', '')
    date_from = request.POST.get('date_from', '')
    date_to = request.POST.get('date_to', '')
    if doc_type == 'spravka' and vessel and date_from and date_to:
        from datetime import date as dt_date
        ss = SeaService.objects.create(
            person=person,
            vessel_name=vessel,
            date_from=date_from,
            date_to=date_to,
            tonnage=int(request.POST.get('tonnage', 0) or 0),
            power=int(request.POST.get('power', 0) or 0),
            document=doc,
        )
        result['sea_service'] = {
            'id': ss.pk,
            'dateFrom': ss.date_from.isoformat(),
            'dateTo': ss.date_to.isoformat(),
            'vessel': ss.vessel_name,
            'tonnage': ss.tonnage,
            'power': ss.power,
        }

    return JsonResponse(result)


@login_required
@menu_access_required('students')
@require_POST
def api_person_documents_archive(request, pk):
    """Архивирование документов слушателя."""
    person = get_object_or_404(Person, pk=pk)
    data = json.loads(request.body)
    doc_ids = data.get('doc_ids', [])
    from django.utils import timezone
    PersonDocument.objects.filter(
        person=person, pk__in=doc_ids
    ).update(
        is_archived=True,
        archived_by=request.user,
        archived_at=timezone.now(),
    )
    return JsonResponse({'success': True})


@login_required
@menu_access_required('students')
@require_POST
def api_document_restore(request, doc_pk):
    """Восстановление документа из архива."""
    doc = get_object_or_404(PersonDocument, pk=doc_pk)
    doc.is_archived = False
    doc.archived_by = None
    doc.archived_at = None
    doc.save()
    return JsonResponse({'success': True})


@login_required
@menu_access_required('students')
@require_POST
def api_person_sea_service_create(request, pk):
    """Добавить запись ценза."""
    person = get_object_or_404(Person, pk=pk)
    data = json.loads(request.body)
    ss = SeaService.objects.create(
        person=person,
        vessel_name=data.get('vessel_name', ''),
        date_from=data.get('date_from'),
        date_to=data.get('date_to'),
        tonnage=int(data.get('tonnage', 0) or 0),
        power=int(data.get('power', 0) or 0),
    )
    return JsonResponse({
        'success': True,
        'sea_service': {
            'id': ss.pk,
            'dateFrom': ss.date_from.isoformat(),
            'dateTo': ss.date_to.isoformat(),
            'vessel': ss.vessel_name,
            'tonnage': ss.tonnage,
            'power': ss.power,
        }
    })


@login_required
@menu_access_required('students')
def api_sea_service_delete(request, pk):
    """Удалить запись ценза."""
    if request.method != 'DELETE':
        return JsonResponse({'error': 'method not allowed'}, status=405)
    ss = get_object_or_404(SeaService, pk=pk)
    ss.delete()
    return JsonResponse({'success': True})


@login_required
@menu_access_required('students')
@require_POST
def api_person_message_send(request, pk):
    """Отправка комментария."""
    person = get_object_or_404(Person, pk=pk)
    data = json.loads(request.body)
    text = data.get('text', '').strip()
    if not text:
        return JsonResponse({'error': 'empty text'}, status=400)
    msg = Message.objects.create(
        person=person,
        author=request.user,
        text=text,
    )
    author_name = request.user.get_full_name().strip() or request.user.username
    ini_parts = author_name.replace('.', ' ').split()[:2]
    return JsonResponse({
        'success': True,
        'message': {
            'id': msg.pk,
            'who': author_name,
            'ini': ''.join(w[0] for w in ini_parts if w),
            'c': 0,
            'text': msg.text,
            'time': msg.created_at.strftime('%H:%M'),
            'own': True,
            'pinned': False,
            'cs': '',
        }
    })


@login_required
@menu_access_required('students')
@require_POST
def api_message_pin(request, pk):
    """Закрепить комментарий (создать кейс)."""
    msg = get_object_or_404(Message, pk=pk)
    msg.is_pinned = True
    msg.case_status = 'active'
    msg.save(update_fields=['is_pinned', 'case_status'])
    return JsonResponse({'success': True})


@login_required
@menu_access_required('students')
@require_POST
def api_message_unpin(request, pk):
    """Открепить комментарий (убрать из кейсов)."""
    msg = get_object_or_404(Message, pk=pk)
    msg.is_pinned = False
    msg.case_status = ''
    msg.save(update_fields=['is_pinned', 'case_status'])
    return JsonResponse({'success': True})


@login_required
@menu_access_required('students')
@require_POST
def api_toggle_case_status(request, pk):
    """Переключить статус кейса: В работе <-> Архив."""
    msg = get_object_or_404(Message, pk=pk)
    msg.case_status = 'archive' if msg.case_status == 'active' else 'active'
    msg.save(update_fields=['case_status'])
    return JsonResponse({'success': True, 'status': msg.case_status})


# ─────────────────────────────────────────────
# API: шаблоны наборов программ
# ─────────────────────────────────────────────

@login_required
@menu_access_required('students')
def api_program_templates_list(request):
    """Список шаблонов наборов программ."""
    templates = ProgramTemplate.objects.filter(is_active=True).prefetch_related('programs')
    data = [{
        'id': t.pk,
        'name': t.name,
        'programs': list(t.programs.values_list('pk', flat=True)),
        'count': t.programs.count(),
    } for t in templates]
    return JsonResponse({'templates': data})


@login_required
@menu_access_required('students')
@require_POST
def api_create_program_template(request):
    """Создать шаблон из выбранных программ."""
    body = json.loads(request.body)
    name = body.get('name', '').strip()
    program_ids = body.get('program_ids', [])
    if not name:
        return JsonResponse({'error': '\u0412\u0432\u0435\u0434\u0438\u0442\u0435 \u043D\u0430\u0437\u0432\u0430\u043D\u0438\u0435 \u0448\u0430\u0431\u043B\u043E\u043D\u0430'}, status=400)
    tpl = ProgramTemplate.objects.create(
        name=name,
        created_by=request.user,
        space=getattr(request.user, 'space', None),
    )
    if program_ids:
        tpl.programs.set(program_ids)
    return JsonResponse({
        'success': True,
        'template': {
            'id': tpl.pk,
            'name': tpl.name,
            'programs': program_ids,
            'count': len(program_ids),
        }
    })


@login_required
@menu_access_required('students')
@require_POST
def api_delete_program_template(request, pk):
    """Удалить шаблон."""
    tpl = get_object_or_404(ProgramTemplate, pk=pk)
    tpl.delete()
    return JsonResponse({'success': True})


# ─────────────────────────────────────────────
# Выдача модулей слушателям
# ─────────────────────────────────────────────

@login_required
@menu_access_required('students')
def api_training_program_modules(request, pk):
    """GET — список модулей для программы обучения."""
    program = get_object_or_404(TrainingProgram, pk=pk)
    modules = LearningModule.objects.filter(program=program, is_active=True).order_by('order')
    data = [{
        'id': m.pk,
        'title': m.title,
        'order': m.order,
        'cover_image': m.cover_image or '',
        'steps_count': m.steps.count(),
    } for m in modules]
    return JsonResponse({'modules': data, 'program_title': program.title})


@login_required
@menu_access_required('students')
@require_POST
def api_assign_modules(request, pk):
    """POST — назначить модули слушателю."""
    person = get_object_or_404(Person, pk=pk)
    body = json.loads(request.body)
    module_ids = body.get('module_ids', [])
    program_line_id = body.get('program_line_id')
    order_id = body.get('order_id')

    created = 0
    for mid in module_ids:
        try:
            module = LearningModule.objects.get(pk=mid)
        except LearningModule.DoesNotExist:
            continue
        _, is_new = ModuleAssignment.objects.get_or_create(
            person=person,
            module=module,
            program_line_id=program_line_id,
            defaults={
                'order_id': order_id,
                'assigned_by': request.user,
            }
        )
        if is_new:
            created += 1

    return JsonResponse({'success': True, 'created': created})


@login_required
@menu_access_required('students')
def api_program_line_module_status(request, pk):
    """GET — статус модулей для строки заявки."""
    program_line = get_object_or_404(Program, pk=pk)
    assignments = ModuleAssignment.objects.filter(
        program_line=program_line, is_active=True
    ).select_related('module')

    modules_data = []
    for a in assignments:
        progress = ModuleProgress.objects.filter(
            person=program_line.order.person if program_line.order else None, module=a.module
        ).first()
        result = ModuleResult.objects.filter(
            person=program_line.order.person if program_line.order else None,
            module=a.module, is_preview=False
        ).first()
        quiz_avg = None
        if result and result.quiz_scores and isinstance(result.quiz_scores, dict):
            vals = [v for v in result.quiz_scores.values() if isinstance(v, (int, float))]
            quiz_avg = round(sum(vals) / len(vals), 1) if vals else None

        modules_data.append({
            'id': a.module.pk,
            'title': a.module.title,
            'is_completed': progress.is_completed if progress else False,
            'quiz_avg': quiz_avg,
            'final_score': result.final_exam_score if result else None,
            'final_passed': result.final_exam_passed if result else False,
        })

    total = len(modules_data)
    completed = sum(1 for m in modules_data if m['is_completed'])
    return JsonResponse({'total': total, 'completed': completed, 'modules': modules_data})


@login_required
@menu_access_required('students')
@require_POST
def api_set_grade(request, pk):
    """POST — установить оценку для строки заявки."""
    program_line = get_object_or_404(Program, pk=pk)
    body = json.loads(request.body)
    program_line.grade = body.get('grade', '')
    program_line.save(update_fields=['grade'])
    return JsonResponse({'success': True})


# ─────────────────────────────────────────────
# Личный кабинет — Обучение
# ─────────────────────────────────────────────
# Прогресс обучения
# ─────────────────────────────────────────────

@login_required
@menu_access_required('progress')
def module_progress_list(request):
    """Таблица прогресса прохождения модулей слушателями."""
    assignments = ModuleAssignment.objects.filter(
        is_active=True
    ).select_related(
        'person', 'module', 'module__program'
    ).order_by('-assigned_at')

    rows = []
    for a in assignments:
        person = a.person
        module = a.module
        program = module.program

        total_steps = module.steps.filter(is_active=True).count()

        progress = ModuleProgress.objects.filter(
            person=person, module=module
        ).first()

        completed_steps = 0
        if progress:
            completed_steps = StepProgress.objects.filter(
                module_progress=progress, status='completed'
            ).count()

        progress_percent = round(completed_steps / total_steps * 100) if total_steps > 0 else 0

        # Средний балл промежуточных тестов
        quiz_avg = None
        quiz_scores = []
        quiz_steps = module.steps.filter(type='quiz', is_active=True)
        if quiz_steps.exists() and progress:
            for qs in quiz_steps:
                sp = StepProgress.objects.filter(
                    module_progress=progress, step=qs, status='completed'
                ).first()
                if sp and sp.score is not None:
                    quiz_scores.append(sp.score)
            if quiz_scores:
                quiz_avg = round(sum(quiz_scores) / len(quiz_scores), 1)

        quiz_total_percent = round(sum(quiz_scores) / len(quiz_scores), 1) if quiz_scores else None

        # Статус
        has_final = module.steps.filter(type='final_exam', is_active=True).exists()
        non_final_step_ids = module.steps.filter(is_active=True).exclude(type='final_exam').values_list('pk', flat=True)
        non_final_count = len(non_final_step_ids)
        completed_non_final = 0
        if progress:
            completed_non_final = StepProgress.objects.filter(
                module_progress=progress,
                step_id__in=non_final_step_ids,
                status='completed'
            ).count()

        if progress and progress.is_completed:
            status_label = 'Завершил'
            status_color = '#1e7e34'
            status_bg = '#d4edda'
            status_key = 'completed'
        elif has_final and non_final_count > 0 and completed_non_final >= non_final_count:
            status_label = 'Готов к аттестации'
            status_color = '#e65100'
            status_bg = '#fff3e0'
            status_key = 'ready_exam'
        elif completed_steps > 0:
            status_label = 'В процессе'
            status_color = '#1565c0'
            status_bg = '#e3f2fd'
            status_key = 'in_progress'
        else:
            status_label = 'Выдан'
            status_color = '#555'
            status_bg = '#f5f5f5'
            status_key = 'assigned'

        rows.append({
            'person_id': person.pk,
            'person_name': f'{person.last_name} {person.first_name} {person.middle_name or ""}'.strip(),
            'program_code': program.code if program else '',
            'program_title': program.title if program else '',
            'module_title': module.title,
            'module_id': module.pk,
            'total_steps': total_steps,
            'completed_steps': completed_steps,
            'progress_percent': progress_percent,
            'quiz_avg': quiz_avg,
            'quiz_total_percent': quiz_total_percent,
            'status_label': status_label,
            'status_color': status_color,
            'status_bg': status_bg,
            'status_key': status_key,
            'assigned_at': a.assigned_at,
        })

    context = {
        'rows': rows,
        'total_assignments': len(rows),
        'in_progress_count': sum(1 for r in rows if r['status_key'] == 'in_progress'),
        'ready_exam_count': sum(1 for r in rows if r['status_key'] == 'ready_exam'),
        'completed_count': sum(1 for r in rows if r['status_key'] == 'completed'),
    }
    return render(request, 'courses/progress_list.html', context)


# ─────────────────────────────────────────────
# ЛК Обучение
# ─────────────────────────────────────────────

@login_required
@menu_access_required('learning')
def student_learning(request):
    """Личный кабинет — раздел Обучение."""
    from .utils import get_current_person
    person = get_current_person(request)
    if not person:
        return render(request, 'lk/learning.html', {'modules': []})

    # ID модулей, которые реально завершены (не preview)
    completed_module_ids = set(
        ModuleResult.objects.filter(
            person=person,
            final_exam_passed=True,
            is_preview=False,
        ).values_list('module_id', flat=True)
    )

    # Назначения КРОМЕ завершённых
    assignments = ModuleAssignment.objects.filter(
        person=person, is_active=True
    ).select_related('module', 'module__program').exclude(
        module_id__in=completed_module_ids
    ).order_by('-assigned_at')

    modules_data = []
    for a in assignments:
        m = a.module
        progress = ModuleProgress.objects.filter(person=person, module=m).first()
        total_steps = m.steps.count()
        current_step = 0
        if progress and progress.current_step:
            # current_step — FK, считаем порядок
            current_step = m.steps.filter(order__lte=progress.current_step.order).count()

        modules_data.append({
            'id': m.pk,
            'title': m.title,
            'program_title': m.program.title if m.program else '',
            'program_code': m.program.code if m.program else '',
            'cover_image': m.cover_image or '',
            'total_steps': total_steps,
            'current_step': current_step,
            'is_completed': progress.is_completed if progress else False,
            'progress_percent': round(current_step / total_steps * 100) if total_steps > 0 else 0,
            'assigned_at': a.assigned_at,
        })

    return render(request, 'lk/learning.html', {'modules': modules_data})


# ─────────────────────────────────────────────
# Результаты обучения
# ─────────────────────────────────────────────

@login_required
@menu_access_required('results')
def learning_results(request):
    """Раздел Результаты — завершённые модули."""
    from .utils import get_current_person

    person = get_current_person(request)
    role = getattr(request.user, 'role', 'student')

    if role == 'student' and person:
        results = ModuleResult.objects.filter(
            person=person,
            final_exam_passed=True,
            is_preview=False,
        ).select_related(
            'module', 'module__program', 'final_exam_step'
        ).order_by('-completed_at')
    elif role in ('admin', 'superadmin', 'teacher'):
        results = ModuleResult.objects.filter(
            final_exam_passed=True,
            is_preview=False,
        ).select_related(
            'person', 'module', 'module__program', 'final_exam_step'
        ).order_by('-completed_at')[:500]
    else:
        results = ModuleResult.objects.none()

    total_completed = results.count() if not isinstance(results, list) else len(results)
    avg_score = None
    if total_completed > 0:
        scores = [r.final_exam_score for r in results if r.final_exam_score is not None]
        avg_score = round(sum(scores) / len(scores), 1) if scores else None

    context = {
        'results': results,
        'total_completed': total_completed,
        'avg_score': avg_score,
        'is_admin': role in ('admin', 'superadmin', 'teacher'),
    }
    return render(request, 'results/list.html', context)


# ─────────────────────────────────────────────
# Impersonation (суперадмин → слушатель)
# ─────────────────────────────────────────────

@login_required
@menu_access_required('impersonate_btn')
@require_POST
def api_impersonate(request, person_pk):
    """Войти в режим слушателя."""
    if getattr(request.user, 'role', '') != 'superadmin':
        return JsonResponse({'error': 'Только для суперадмина'}, status=403)
    person = get_object_or_404(Person, pk=person_pk)
    request.session['impersonating_person_id'] = person.pk
    request.session['impersonator_user_id'] = request.user.pk
    return JsonResponse({
        'success': True,
        'person_id': person.pk,
        'person_name': f'{person.last_name} {person.first_name}',
    })


@login_required
@menu_access_required('impersonate_btn')
@require_POST
def api_stop_impersonation(request):
    """Выйти из режима слушателя."""
    person_id = request.session.pop('impersonating_person_id', None)
    request.session.pop('impersonator_user_id', None)
    return JsonResponse({'success': True, 'person_id': person_id})


# ─────────────────────────────────────────────
# Прогресс тестов — QuizAnswerRecord
# ─────────────────────────────────────────────

@login_required
@menu_access_any('learning', 'modules')
@require_POST
def api_save_single_answer(request, step_pk):
    """Сохранить ответ на один вопрос."""
    from .utils import get_current_person
    step = get_object_or_404(ModuleStep, pk=step_pk)
    person = get_current_person(request)
    if not person:
        return JsonResponse({'error': 'no person'}, status=400)

    body = json.loads(request.body)
    question_id = body.get('question_id')
    answer = body.get('answer', [])
    is_correct = body.get('is_correct', False)
    score = body.get('score', 0)

    if not question_id:
        return JsonResponse({'error': 'question_id required'}, status=400)

    question = get_object_or_404(QuizQuestion, pk=question_id)

    QuizAnswerRecord.objects.update_or_create(
        person=person, step=step, question=question,
        defaults={'answer': answer, 'is_correct': is_correct, 'score': score}
    )
    return JsonResponse({'success': True})


@login_required
@menu_access_any('learning', 'modules')
def api_load_saved_answers(request, step_pk):
    """Загрузить все сохранённые ответы для теста."""
    from .utils import get_current_person
    step = get_object_or_404(ModuleStep, pk=step_pk)
    person = get_current_person(request)
    if not person:
        return JsonResponse({'answers': {}, 'count': 0})

    records = QuizAnswerRecord.objects.filter(person=person, step=step)
    answers = {}
    for r in records:
        answers[str(r.question_id)] = {
            'answer': r.answer,
            'is_correct': r.is_correct,
            'score': r.score,
        }
    return JsonResponse({'answers': answers, 'count': len(answers)})


@login_required
@menu_access_any('learning', 'modules')
@require_POST
def api_reset_quiz_answers(request, step_pk):
    """Сбросить все ответы для теста."""
    from .utils import get_current_person
    step = get_object_or_404(ModuleStep, pk=step_pk)
    person = get_current_person(request)
    if not person:
        return JsonResponse({'error': 'no person'}, status=400)
    deleted, _ = QuizAnswerRecord.objects.filter(person=person, step=step).delete()
    return JsonResponse({'success': True, 'deleted': deleted})


# ─────────────────────────────────────────────
# Настройки меню — панель суперадмина
# ─────────────────────────────────────────────

@login_required
@menu_access_required('menu_settings')
def menu_settings_view(request):
    """Страница настроек меню (суперадмин)."""
    if getattr(request.user, 'role', '') != 'superadmin':
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden()
    items = MenuPermission.objects.all()
    roles = MenuPermission.ROLES
    menu_items_choices = MenuPermission.MENU_ITEMS
    perms_json = json.dumps({f'{mp.menu_item}__{mp.role}': mp.is_visible for mp in items})
    return render(request, 'settings/menu.html', {
        'menu_items_choices': menu_items_choices,
        'roles': roles,
        'perms_json': perms_json,
    })


@login_required
@menu_access_required('menu_settings')
@require_POST
def api_update_menu_permission(request):
    """Обновить видимость пункта меню."""
    if getattr(request.user, 'role', '') != 'superadmin':
        return JsonResponse({'error': 'Forbidden'}, status=403)
    body = json.loads(request.body)
    menu_item = body.get('menu_item')
    role = body.get('role')
    is_visible = body.get('is_visible', False)
    MenuPermission.objects.update_or_create(
        menu_item=menu_item, role=role,
        defaults={'is_visible': is_visible}
    )
    return JsonResponse({'success': True})
