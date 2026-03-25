import json
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import Course, CourseStep, Question, Enrollment, StepCompletion, Order, Program, Person, Company, OrganizationAssignment, PersonOrganization
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
    persons = Person.objects.select_related('user').order_by('last_name', 'first_name')
    if q:
        from django.db.models import Q
        persons = persons.filter(
            Q(last_name__icontains=q)   |
            Q(first_name__icontains=q)  |
            Q(middle_name__icontains=q) |
            Q(snils__icontains=q)       |
            Q(workplace__icontains=q)
        )
    return render(request, 'persons/list.html', {
        'persons': persons,
        'q': q,
    })


# ─────────────────────────────────────────────
# Список слушателей (у кого есть user)
# ─────────────────────────────────────────────
@login_required
def student_list(request):
    """Список слушателей, видимых для текущей организации пользователя"""
    q = request.GET.get('q', '').strip()

    # Получаем текущую организацию пользователя
    current_org = request.user.current_organization
    if not current_org:
        persons = Person.objects.none()
    else:
        assignment = OrganizationAssignment.objects.filter(
            company=current_org,
            assigned_for=current_org.short_name
        ).first()

        if assignment:
            persons = Person.objects.filter(
                org_assignments__assignment=assignment,
                user__isnull=False
            ).select_related('user').distinct()
        else:
            persons = Person.objects.none()

    if q and persons.exists():
        from django.db.models import Q
        persons = persons.filter(
            Q(last_name__icontains=q) |
            Q(first_name__icontains=q) |
            Q(middle_name__icontains=q) |
            Q(snils__icontains=q)
        )

    # Если запрос AJAX или есть параметр json, возвращаем JSON
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.GET.get('json') == '1':
        persons_data = []
        for p in persons:
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

    return render(request, 'persons/students.html', {
        'persons': persons,
        'q': q,
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
    return render(request, 'persons/detail.html', {
        'person': person,
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

    # Проверяем, есть ли у пользователя текущая организация
    if not request.user.current_organization:
        return JsonResponse({
            'error': 'У вас не выбрана текущая организация. Сначала выберите её в профиле.'
        }, status=400)

    current_org = request.user.current_organization

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

    # Проверяем, есть ли у пользователя текущая организация
    if not request.user.current_organization:
        return JsonResponse({
            'error': 'У вас не выбрана текущая организация. Сначала выберите её в профиле.'
        }, status=400)

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
            assigned_for=request.user.current_organization.short_name,
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

            # ─── АВТОМАТИЧЕСКОЕ НАЗНАЧЕНИЕ ОРГАНИЗАЦИИ ───
            current_org = request.user.current_organization
            if current_org:
                # Находим или создаем назначение организации для текущего пользователя
                assignment = OrganizationAssignment.objects.filter(
                    company=current_org,
                    assigned_for=current_org.short_name
                ).first()

                if not assignment:
                    assignment = OrganizationAssignment.objects.create(
                        company=current_org,
                        org_type='educational',
                        assigned_by=request.user,
                        assigned_for=current_org.short_name,
                        notes='Автоматически создано при создании физического лица'
                    )

                # Создаем связь физического лица с организацией
                PersonOrganization.objects.get_or_create(
                    person=person,
                    assignment=assignment
                )
            # ─────────────────────────────────────────────

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

    # Получаем текущую организацию пользователя
    current_org = request.user.current_organization
    if not current_org:
        return JsonResponse({'belongs_to_current_org': False})

    # Проверяем, есть ли связь с организацией
    belongs = PersonOrganization.objects.filter(
        person=person,
        assignment__company=current_org
    ).exists()

    return JsonResponse({'belongs_to_current_org': belongs})



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


