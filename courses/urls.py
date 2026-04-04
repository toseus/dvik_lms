from django.urls import path
from . import views

urlpatterns = [
    # Пользователи
    path('', views.login_view, name='login'),  # Только один раз!
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
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
    path('programs/<int:pk>/', views.program_detail, name='program_detail'),
    path('programs/<int:pk>/save/', views.program_save, name='program_save'),
    path('programs/<int:pk>/documents/upload/', views.program_document_upload, name='program_document_upload'),
    path('programs/documents/<int:doc_pk>/delete/', views.program_document_delete, name='program_document_delete'),
    path('api/programs/<int:pk>/create-template-docs/', views.create_template_docs, name='create_template_docs'),
    path('api/programs/<int:pk>/available-templates/', views.available_templates, name='available_templates'),

    # Модули обучения
    path('modules/', views.module_list, name='module_list'),
    path('modules/create/', views.module_create, name='module_create'),
    path('modules/<int:pk>/edit/', views.module_edit, name='module_edit'),
    path('modules/<int:pk>/delete/', views.module_delete, name='module_delete'),
    path('modules/<int:pk>/preview/', views.module_preview, name='module_preview'),
    path('modules/step/<int:pk>/slides/', views.module_slides, name='module_slides'),
    path('modules/step/<int:pk>/slides/raw/', views.serve_slide_raw, name='serve_slide_raw'),
    path('modules/step/<int:step_pk>/quiz/preview/', views.module_quiz_preview, name='module_quiz_preview'),

    # API конструктора модулей
    path('api/modules/<int:pk>/steps/', views.api_module_steps, name='api_module_steps'),
    path('api/modules/<int:pk>/steps/save/', views.api_module_steps_save, name='api_module_steps_save'),
    path('api/final-exam/<int:step_pk>/questions/', views.api_final_exam_questions, name='api_final_exam_questions'),
    path('api/final-exam/<int:step_pk>/submit/', views.api_final_exam_submit, name='api_final_exam_submit'),
    path('api/steps/<int:pk>/questions/', views.api_step_questions, name='api_step_questions'),
    path('api/steps/<int:pk>/questions/save/', views.api_step_questions_save, name='api_step_questions_save'),
    path('api/steps/<int:pk>/questions/import/', views.api_import_questions, name='api_import_questions'),
    path('api/steps/<int:step_pk>/upload-slide-file/', views.upload_slide_file, name='upload_slide_file'),

    # Загрузка изображений
    path('api/modules/<int:pk>/upload-cover/', views.upload_module_cover, name='upload_module_cover'),
    path('api/steps/<int:step_pk>/upload-question-image/', views.upload_question_image, name='upload_question_image'),
    path('api/steps/<int:step_pk>/upload-question-images/', views.upload_question_images_bulk, name='upload_question_images_bulk'),
    path('api/steps/<int:step_pk>/question-images/', views.list_question_images, name='list_question_images'),
    path('api/steps/<int:step_pk>/question-images/<int:question_order>/delete/', views.delete_question_image, name='delete_question_image'),

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

    # API карточки слушателя
    path('api/persons/<int:pk>/orders/create/', views.api_person_order_create, name='api_person_order_create'),
    path('api/orders/<int:order_pk>/add-program/', views.api_order_add_program, name='api_order_add_program'),
    path('api/orders/<int:order_pk>/remove-programs/', views.api_order_remove_programs, name='api_order_remove_programs'),
    path('api/persons/<int:pk>/documents/upload/', views.api_person_document_upload, name='api_person_document_upload'),
    path('api/persons/<int:pk>/documents/archive/', views.api_person_documents_archive, name='api_person_documents_archive'),
    path('api/documents/<int:doc_pk>/restore/', views.api_document_restore, name='api_document_restore'),
    path('api/persons/<int:pk>/sea-service/create/', views.api_person_sea_service_create, name='api_person_sea_service_create'),
    path('api/sea-service/<int:pk>/delete/', views.api_sea_service_delete, name='api_sea_service_delete'),
    path('api/persons/<int:pk>/messages/send/', views.api_person_message_send, name='api_person_message_send'),
    path('api/messages/<int:pk>/pin/', views.api_message_pin, name='api_message_pin'),
    path('api/messages/<int:pk>/unpin/', views.api_message_unpin, name='api_message_unpin'),
    path('api/messages/<int:pk>/toggle-case-status/', views.api_toggle_case_status, name='api_toggle_case_status'),
    path('api/program-templates/', views.api_program_templates_list, name='api_program_templates_list'),
    path('api/program-templates/create/', views.api_create_program_template, name='api_create_program_template'),
    path('api/program-templates/<int:pk>/delete/', views.api_delete_program_template, name='api_delete_program_template'),

    # API прогресса модулей
    path('api/progress/module/<int:module_pk>/', views.api_module_progress, name='api_module_progress'),
    path('api/progress/step/<int:step_pk>/complete/', views.api_step_complete, name='api_step_progress_complete'),
    path('api/progress/quiz/<int:step_pk>/save/', views.api_quiz_save_progress, name='api_quiz_save_progress'),
    path('api/progress/quiz/<int:step_pk>/complete/', views.api_quiz_complete, name='api_quiz_complete'),

    # Выдача модулей
    path('api/training-programs/<int:pk>/modules/', views.api_training_program_modules, name='api_training_program_modules'),
    path('api/persons/<int:pk>/assign-modules/', views.api_assign_modules, name='api_assign_modules'),
    path('api/program-lines/<int:pk>/module-status/', views.api_program_line_module_status, name='api_program_line_module_status'),
    path('api/program-lines/<int:pk>/set-grade/', views.api_set_grade, name='api_set_grade'),

    # Прогресс обучения
    path('progress/', views.module_progress_list, name='module_progress_list'),
    path('api/program-lines/<int:program_line_pk>/archive-modules/', views.archive_program_line_modules, name='archive_program_line_modules'),

    # ЛК Обучение
    path('learning/', views.student_learning, name='student_learning'),
    path('results/', views.learning_results, name='learning_results'),

    # Impersonation
    path('api/impersonate/<int:person_pk>/', views.api_impersonate, name='api_impersonate'),
    path('api/stop-impersonation/', views.api_stop_impersonation, name='api_stop_impersonation'),

    # Прогресс тестов (ответы в БД)
    path('api/quiz/<int:step_pk>/save-answer/', views.api_save_single_answer, name='api_save_single_answer'),
    path('api/quiz/<int:step_pk>/load-answers/', views.api_load_saved_answers, name='api_load_saved_answers'),
    path('api/quiz/<int:step_pk>/reset-answers/', views.api_reset_quiz_answers, name='api_reset_quiz_answers'),

    # Настройки меню
    path('settings/menu/', views.menu_settings_view, name='menu_settings'),
    path('api/menu-permissions/update/', views.api_update_menu_permission, name='api_update_menu_permission'),
]