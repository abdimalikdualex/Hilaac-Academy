# Hilaac Academy

**Baro Xirfado Casri ah, Dhis Mustaqbalkaaga**

A production-ready, mobile-first online language learning platform built with Django. Phase 1 focuses on **English** and **Kiswahili** courses for all proficiency levels.

## MVP Features

### Public
- HD video hero landing page with course search
- Featured courses, statistics, testimonials, FAQ
- WhatsApp support integration
- Light/dark mode, glassmorphism UI, PWA installable

### Student Portal
- Register with email verification
- Login, password reset, password change
- Browse/search courses by language, level, keywords
- Enroll in free or paid courses
- Video lessons with resume playback, speed control, fullscreen
- PDF, audio, reading, vocabulary lesson types
- Quizzes: MCQ, T/F, fill-blank, reading, listening — with timer
- Auto-graded assessments and final exams
- Progress tracking dashboard with activity feed
- Certificates with QR verification and PDF download
- M-Pesa & EVC Plus payments with receipts
- Digital library with search
- In-app + email notifications

### Admin
- Django Admin for full content management
- Analytics dashboard (students, revenue, completions, pending payments)
- Payment verification and audit logs

## Quick Start

```bash
pip install -r requirements/base.txt
copy .env.example .env   # set USE_SQLITE=True for local dev
python manage.py migrate
python manage.py seed_data --demo   # first-time demo courses only (never overwrites your data)
python manage.py runserver
```

Visit **http://localhost:8000**

### Default Accounts

| Role        | Username | Password    |
|-------------|----------|-------------|
| Super Admin | admin    | admin123    |
| Student     | student  | student123  |

### Key URLs

| Page | URL |
|------|-----|
| Landing | `/` |
| Courses | `/courses/` |
| Dashboard | `/accounts/dashboard/` |
| Admin Panel | `/admin/` |
| Admin Analytics | `/admin-dashboard/` |
| Certificate Verify | `/certificates/verify/<id>/` |

## Docker (Production)

```bash
docker-compose up --build
```

## Celery (Background Tasks)

```bash
celery -A hilaac_academy worker -l info
celery -A hilaac_academy beat -l info   # quiz reminders
```

## Environment Variables

See `.env.example` for Cloudinary, M-Pesa, EVC Plus, and email settings.

## Technology Stack

- Python, Django 4.2, DRF
- PostgreSQL / SQLite
- Tailwind CSS, HTMX, Alpine.js
- Celery + Redis
- Cloudinary (optional)
- Docker, Nginx, Gunicorn

## License

Proprietary — Hilaac Academy © 2026
