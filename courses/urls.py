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

    # Заказы
    path('orders/api/person/<int:person_pk>/', views.api_person_orders, name='api_person_orders'),

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
]