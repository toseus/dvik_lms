import json
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import Course, CourseStep, Question, Enrollment, StepCompletion, Order, Program, Person, Company, OrganizationAssignment, PersonOrganization, TrainingProgram, Message, LearningModule, ModuleStep, QuizQuestion, Signer, Contract, Space, ModuleProgress, StepProgress, QuizAttempt
from django.contrib.auth import authenticate, login, logout
from django.db import IntegrityError
from django.contrib import messages


# ─────────────────────────────────────────────
# Список курсов
# ─────────────────────────────────────────────
@login_required
def course_list(request):
    courses = Course.objects.filter(is_active=True).prefetch_related('steps')
    return render(request, 'courses/list.html', {'courses': courses})


# ─────────────────────────────────────────────
# Страница обучения (learn) — прохождение курса
# ─────────────────────────────────────────────
@login_required
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
# Карточка слушателя (card.html — extends base.html)
# ─────────────────────────────────────────────
@login_required
def student_card(request, pk):
    person = get_object_or_404(
        Person.objects.select_related('user').prefetch_related(
            'orders__programs',
            'enrollments__course',
            'enrollments__completed_steps',
        ),
        pk=pk
    )

    # JSON для заявок
    orders_data = []
    for o in person.orders.all():
        orders_data.append({
            'id': o.pk,
            'date': o.date.isoformat() if o.date else '',
            'amount': str(o.amount),
            'payer': o.payer,
            'partner': o.partner,
            'author': o.author,
        })

    # JSON для программ (подготовок)
    progs_data = []
    for o in person.orders.all():
        for p in o.programs.all():
            progs_data.append({
                'order_id': o.pk,
                'cat': p.category,
                'tp': p.prog_type,
                'code': p.code,
                'fr': p.date_start.isoformat() if p.date_start else '',
                'to': p.date_end.isoformat() if p.date_end else '',
                'disc': p.discount,
                'amt': str(p.amount),
                'cert': p.cert_number,
                'reg': p.reg_number,
                'grade': p.grade,
                'iss': p.issue_status,
                'notes': p.notes,
            })

    import json
    current_user_name = request.user.get_full_name() or request.user.username

    return render(request, 'persons/detail.html', {
        'person': person,
        'orders_json': json.dumps(orders_data, ensure_ascii=False),
        'progs_json': json.dumps(progs_data, ensure_ascii=False),
        'current_user_name': current_user_name,
    })


# ─────────────────────────────────────────────
# AJAX: сохранение данных карточки
# ─────────────────────────────────────────────
@login_required
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
        'snils', 'dob', 'city', 'position', 'workplace', 'notes',
        'phone', 'email',
    ]
    for field in allowed:
        if field in data:
            setattr(person, field, data[field])
    person.save()
    return JsonResponse({'ok': True})


# ─────────────────────────────────────────────
# Добавление слушателя по СНИЛС (поддержка JSON и form-data)
# ─────────────────────────────────────────────
@login_required
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
        return redirect('home')

    error = None
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect(request.GET.get('next', 'home'))
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
def home_view(request):
    ctx = _user_context(request.user)

    # Данные для разделов «Слушатели» и «Физические лица» (для admin/superadmin)
    if request.user.role in ('admin', 'superadmin'):
        ctx['persons_count'] = Person.objects.count()
        ctx['students_count'] = Person.objects.filter(user__isnull=False).count()

    return render(request, 'dashboard/home.html', ctx)


@login_required
def learn_view(request):
    ctx = _user_context(request.user)
    return render(request, 'courses/learn.html', ctx)


@login_required
def quest_view(request):
    ctx = _user_context(request.user)
    return render(request, 'courses/test.html', ctx)


@login_required
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
def program_catalog(request):
    """Справочник программ обучения."""
    q = request.GET.get('q', '').strip()
    cat = request.GET.get('cat', '').strip()
    dept = request.GET.get('dept', '').strip()
    programs = TrainingProgram.objects.filter(status='В работе')

    if cat:
        programs = programs.filter(category=cat)
    if dept:
        programs = programs.filter(department=dept)

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
        'sort': sort,
        'dir': direction,
    })


# ─────────────────────────────────────────────
# API для личного кабинета
# ─────────────────────────────────────────────

@login_required
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
def api_schedule(request):
    """API для расписания"""
    # Пока возвращаем пустой список
    return JsonResponse({'schedule': []})


@login_required
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
def api_library(request):
    """API для библиотеки"""
    # Пока возвращаем пустой список
    return JsonResponse({'items': []})


@login_required
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
def module_edit(request, pk):
    module = get_object_or_404(
        LearningModule.objects.select_related('program').prefetch_related('steps__questions'),
        pk=pk
    )
    return render(request, 'modules/edit.html', {'module': module})


@login_required
@require_POST
def module_delete(request, pk):
    module = get_object_or_404(LearningModule, pk=pk)
    module.delete()
    return redirect('module_list')


@login_required
def api_module_steps(request, pk):
    module = get_object_or_404(LearningModule, pk=pk)
    steps = module.steps.order_by('order')
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
    return JsonResponse({'steps': data}, json_dumps_params={'ensure_ascii': False})


@login_required
@require_POST
def api_module_steps_save(request, pk):
    module = get_object_or_404(LearningModule, pk=pk)
    try:
        data = json.loads(request.body)
    except ValueError:
        return JsonResponse({'error': 'bad json'}, status=400)

    steps_data = data.get('steps', [])
    existing_ids = set(module.steps.values_list('pk', flat=True))
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
        ModuleStep.objects.filter(pk__in=to_delete).delete()

    update_fields = []
    if 'module_title' in data:
        module.title = data['module_title']
        update_fields.append('title')
    if 'module_description' in data:
        module.description = data['module_description']
        update_fields.append('description')
    if update_fields:
        module.save(update_fields=update_fields)

    return JsonResponse({'ok': True})


@login_required
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
def module_preview(request, pk):
    module = get_object_or_404(LearningModule.objects.select_related('program'), pk=pk)
    return render(request, 'modules/preview.html', {'module': module})


@login_required
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
def module_quiz_preview(request, step_pk):
    step = get_object_or_404(ModuleStep.objects.select_related('module__program'), pk=step_pk)
    return render(request, 'modules/quiz.html', {'step': step, 'preview': True})


@login_required
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
# Договоры
# ─────────────────────────────────────────────

@login_required
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
def api_signers(request):
    space = request.user.space
    if not space:
        return JsonResponse({'signers': []})
    signers = Signer.objects.filter(space=space, is_active=True).order_by('full_name')
    data = [{'id': s.pk, 'full_name': s.full_name, 'position': s.position} for s in signers]
    return JsonResponse({'signers': data})


@login_required
def api_payers(request, person_pk):
    person = get_object_or_404(Person, pk=person_pk)
    companies = Company.objects.order_by('short_name').values('id', 'short_name', 'inn')
    payers = [{'id': 'self', 'name': f'{person.fio} (сам слушатель)', 'type': 'person'}]
    for c in companies:
        payers.append({'id': c['id'], 'name': f"{c['short_name']} (ИНН: {c['inn']})", 'type': 'company'})
    return JsonResponse({'payers': payers})


@login_required
def api_contracts_by_payer(request, company_pk):
    contracts = Contract.objects.filter(payer_id=company_pk, is_active=True).order_by('-date')
    data = [{'id': c.pk, 'number': c.number, 'date': c.date.strftime('%d.%m.%Y'), 'display': f'№{c.number} от {c.date.strftime("%d.%m.%Y")}'} for c in contracts]
    return JsonResponse({'contracts': data})


@login_required
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
def api_module_progress(request, module_pk):
    """GET — получить прогресс по модулю для текущего пользователя."""
    if not hasattr(request.user, 'person'):
        return JsonResponse({'error': 'no person'}, status=400)

    progress, created = ModuleProgress.objects.get_or_create(
        person=request.user.person, module_id=module_pk
    )

    steps_data = {}
    for sp in progress.step_progress.select_related('step').all():
        quiz_attempt = sp.quiz_attempts.filter(is_completed=False).first()
        steps_data[sp.step_id] = {
            'status': sp.status,
            'score': sp.score,
            'current_question': quiz_attempt.current_question_index if quiz_attempt else 0,
        }

    return JsonResponse({
        'module_id': module_pk,
        'current_step_id': progress.current_step_id,
        'is_completed': progress.is_completed,
        'steps': steps_data,
    })


@login_required
@require_POST
def api_step_complete(request, step_pk):
    """POST — отметить этап как пройденный."""
    if not hasattr(request.user, 'person'):
        return JsonResponse({'error': 'no person'}, status=400)

    step = get_object_or_404(ModuleStep, pk=step_pk)
    progress, _ = ModuleProgress.objects.get_or_create(
        person=request.user.person, module=step.module
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
@require_POST
def api_quiz_save_progress(request, step_pk):
    """POST — сохранить промежуточный прогресс теста."""
    if not hasattr(request.user, 'person'):
        return JsonResponse({'error': 'no person'}, status=400)

    try:
        data = json.loads(request.body)
    except ValueError:
        return JsonResponse({'error': 'bad json'}, status=400)

    step = get_object_or_404(ModuleStep, pk=step_pk)
    progress, _ = ModuleProgress.objects.get_or_create(
        person=request.user.person, module=step.module
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
@require_POST
def api_quiz_complete(request, step_pk):
    """POST — завершить тест, сохранить результат."""
    if not hasattr(request.user, 'person'):
        return JsonResponse({'error': 'no person'}, status=400)

    try:
        data = json.loads(request.body)
    except ValueError:
        return JsonResponse({'error': 'bad json'}, status=400)

    step = get_object_or_404(ModuleStep, pk=step_pk)
    progress, _ = ModuleProgress.objects.get_or_create(
        person=request.user.person, module=step.module
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

    return JsonResponse({'ok': True, 'score': score})
