"# Clinic-Appointment-Service" 

Used technologies:
django
Django REST Framework

How to run project:
1) Create .env in root directory and populate data from .env.sample
2) run: docker-compose up --build
3) Create own branch and start developing

.env Example (free to use it to development):
POSTGRES_DB=clinic_db
POSTGRES_USER=clinic_user
POSTGRES_PASSWORD=clinic_vector_password
POSTGRES_HOST=db
POSTGRES_PORT=5432
SECRET_KEY=@2qdi3!tvck7%!dhse^4k$9r+%ub@cr(55_%=d43y)f0g56c&7
CELERY_BROKER_URL=redis://redis:6379
CELERY_RESULT_BACKEND=redis://redis:6379
