from django.urls import path
from . import views

urlpatterns = [
    # Пользователи
    path('', views.login_view, name='login'),  # Только один раз!
    path('logout/', views.logout_view, name='logout'),
    path('home/', views.home_view, name='home'),

    # Курсы
    path('courses/', views.course_list, name='course_list'),
    path('courses/<int:pk>/learn/', views.learn_view, name='learn_view'),
    path('courses/quest/<int:step_pk>/', views.quest_view, name='quest_view'),
    path('courses/step/<int:pk>/complete/', views.step_complete, name='step_complete'),
    path('courses/step/<int:pk>/upload/', views.step_upload, name='step_upload'),
    path('courses/quest/<int:step_pk>/result/', views.quest_result, name='quest_result'),
    path('courses/api/my-courses/', views.api_my_courses, name='api_my_courses'),

    # Студенты/Персоны
    path('persons/', views.person_list, name='person_list'),
    path('persons/<int:pk>/', views.student_card, name='student_card'),
    path('persons/<int:pk>/save/', views.person_save, name='person_save'),
    path('persons/students/', views.student_list, name='student_list'),
    path('persons/students/add/', views.student_add, name='student_add'),
    path('persons/companies/', views.company_list, name='company_list'),
    path('persons/create/', views.person_create, name='person_create'),
    path('persons/check-organization/', views.check_student_organization, name='check_student_organization'),

    # Программы обучения
    path('programs/', views.program_catalog, name='program_catalog'),

    # Модули обучения
    path('modules/', views.module_list, name='module_list'),
    path('modules/create/', views.module_create, name='module_create'),
    path('modules/<int:pk>/edit/', views.module_edit, name='module_edit'),
    path('modules/<int:pk>/delete/', views.module_delete, name='module_delete'),
    path('modules/<int:pk>/preview/', views.module_preview, name='module_preview'),
    path('modules/step/<int:pk>/slides/', views.module_slides, name='module_slides'),
    path('modules/step/<int:step_pk>/quiz/preview/', views.module_quiz_preview, name='module_quiz_preview'),

    # API конструктора модулей
    path('api/modules/<int:pk>/steps/', views.api_module_steps, name='api_module_steps'),
    path('api/modules/<int:pk>/steps/save/', views.api_module_steps_save, name='api_module_steps_save'),
    path('api/steps/<int:pk>/questions/', views.api_step_questions, name='api_step_questions'),
    path('api/steps/<int:pk>/questions/save/', views.api_step_questions_save, name='api_step_questions_save'),
    path('api/steps/<int:pk>/questions/import/', views.api_import_questions, name='api_import_questions'),

    # Заказы
    path('orders/api/person/<int:person_pk>/', views.api_person_orders, name='api_person_orders'),

    # Договоры
    path('contracts/', views.contract_list, name='contract_list'),
    path('contracts/create/', views.contract_create, name='contract_create'),

    # API для заявок
    path('api/signers/', views.api_signers, name='api_signers'),
    path('api/payers/<int:person_pk>/', views.api_payers, name='api_payers'),
    path('api/contracts/by-payer/<int:company_pk>/', views.api_contracts_by_payer, name='api_contracts_by_payer'),
    path('api/orders/create/', views.api_order_create, name='api_order_create'),

    # Сообщения
    path('api/messages/<int:person_pk>/', views.api_messages, name='api_messages'),
    path('api/messages/<int:person_pk>/send/', views.api_message_send, name='api_message_send'),

    # Организации (новые)
    path('organizations/', views.organization_list, name='organization_list'),
    path('organizations/create/', views.organization_create, name='organization_create'),
    path('organizations/<int:pk>/', views.organization_detail, name='organization_detail'),
    path('organizations/<int:pk>/edit/', views.organization_edit, name='organization_edit'),
    path('organizations/search/', views.organization_search_by_inn, name='organization_search'),
    path('organizations/assign/', views.organization_assign, name='organization_assign'),
    path('organizations/<int:pk>/delete/', views.organization_delete, name='organization_delete'),

    # API для личного кабинета (добавить эти строки)
    path('persons/api/list/', views.api_persons_list, name='api_persons_list'),
    path('courses/api/schedule/', views.api_schedule, name='api_schedule'),
    path('courses/api/results/', views.api_results, name='api_results'),
    path('courses/api/library/', views.api_library, name='api_library'),
    path('courses/api/practice-items/', views.api_practice_items, name='api_practice_items'),
    path('courses/api/course/<int:course_id>/students/', views.api_course_students, name='api_course_students'),
    path('courses/api/students/', views.api_all_students, name='api_all_students'),

    # API прогресса модулей
    path('api/progress/module/<int:module_pk>/', views.api_module_progress, name='api_module_progress'),
    path('api/progress/step/<int:step_pk>/complete/', views.api_step_complete, name='api_step_progress_complete'),
    path('api/progress/quiz/<int:step_pk>/save/', views.api_quiz_save_progress, name='api_quiz_save_progress'),
    path('api/progress/quiz/<int:step_pk>/complete/', views.api_quiz_complete, name='api_quiz_complete'),
]