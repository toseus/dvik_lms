# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

DVIK LMS (ДВИК) — a Russian-language distance learning management system built with **Django 6.0.3** on **Python 3.14**, using **MySQL** as the database backend. Single-app Django project with the `courses` app containing all models, views, and templates.

## Common Commands

```bash
# Run development server
python manage.py runserver

# Database migrations
python manage.py makemigrations
python manage.py migrate

# Create admin user
python manage.py createsuperuser

# Run tests
python manage.py test

# Import persons from legacy CSV
python manage.py shell < import_persons.py
```

## Architecture

### Custom User Model

`AUTH_USER_MODEL = 'courses.User'` — extends `AbstractUser` with roles (STUDENT, TEACHER, ADMIN, SUPERADMIN) and FK to `Space`.

### Key Model Relationships

```
Space ←── User ←── Person ←── Enrollment ←── StepCompletion ──→ CourseStep ←── Course
                      │                                               │
                      └── Order ←── Program                      Question
                      └── PersonOrganization ←── OrganizationAssignment ←── Company
```

- **Person** has a OneToOne to **User**; auto-account creation happens via a `post_save` signal in `signals.py` (username=person.pk, password=auto-generated 6-digit code)
- **Enrollment** links Person to Course; **StepCompletion** tracks per-step progress
- **CourseStep** types: ONLINE, PDF, PRACTICE, UPLOAD, TEST
- **Question** types: SINGLE, MULTI, ORDER, MATCH — uses JSON fields for `answers`, `correct`, `terms`

### Views

All views are function-based in `courses/views.py`. Two categories:
- **Template views** — return `render()` with HTML templates
- **API views** — return `JsonResponse` (prefixed with `api_` in URL names, under `/courses/api/` and `/persons/api/`)

### Templates

Located in `courses/templates/` with subdirectories: `auth/`, `base/`, `courses/`, `dashboard/`, `persons/`, `companies/`, `organizations/`, `orders/`. Base layouts: `base.html` (main) and `base_lms.html` (learning interface).

### URL Structure

Root includes `courses.urls`. Key prefixes: `/courses/`, `/persons/`, `/organizations/`, `/orders/`. Login is at `/`.

## Configuration Notes

- Locale: Russian (`ru`), timezone `Asia/Vladivostok`
- Custom cookie names: `sessionid_lms`, `csrftoken_lms`
- PDF generation via WeasyPrint (for certificates)
- Static files served from `courses/static/` (css, js, images)
- Media uploads at `/media/`

## Active TODOs

Space-based filtering is not yet implemented across views (marked TODO in `views.py`). Space assignment and membership checks are pending.
