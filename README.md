# Clinic Appointment Service

Backend service for managing clinic appointments, built with Django and Django REST Framework.  
The project is containerized with Docker and designed for team-based development.

---
### All your branches creat from branch: develop
---

## Tech Stack

**Backend**
- Django
- Django REST Framework
- django-filter
- drf-spectacular (OpenAPI / Swagger)

**Async & Background Jobs**
- Celery
- django-celery-beat
- Redis

**Database**
- PostgreSQL
- psycopg2

**Infrastructure & Utilities**
- Docker / Docker Compose
- python-dotenv

---

## Project Architecture (High Level)

- `web` — Django application
- `db` — PostgreSQL database
- `redis` — message broker / cache
- `celery` — background task worker

---

## Environment Configuration

### `.env` setup

Create a `.env` file in the project root using `.env.sample` as a reference.

Example (for local development only):

```env
POSTGRES_DB=clinic_db
POSTGRES_USER=clinic_user
POSTGRES_PASSWORD=clinic_vector_password
POSTGRES_HOST=db
POSTGRES_PORT=5432

SECRET_KEY=@2qdi3!tvck7%!dhse^4k$9r+%ub@cr(55_%=d43y)f0g56c&7

CELERY_BROKER_URL=redis://redis:6379
CELERY_RESULT_BACKEND=redis://redis:6379

STRIPE_SECRET_KEY=
STRIPE_SUCCESS_URL=http://127.0.0.1:/api/payment/success/?session_id={CHECKOUT_SESSION_ID}
STRIPE_CANCEL_URL=http://127.0.0.1:/api/payment/cancel/
```
### Authentication (JWT)
To access protected endpoints (like `/api/user/patients/`), you must use a custom authorization header:

- **Header Name**: `Authorize`
- **Header Value**: `Authorize <your_token>`

Example:
`Authorize: Authorize eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`

## How to Run the Project (Docker)

### Prerequisites

Ensure the following tools are installed on your system:

- Docker
- Docker Desktop or Docker Engine
- Docker Compose

---

### Setup & Run

1. Create environment file from template:
```bash
   cp .env.sample .env
```
2. Start Docker (Docker Desktop or system service).

3. Build and run containers:

```bash
  docker-compose up --build
```
4. Open the API in your browser:

 - API Root: http://127.0.0.1:8000

 - Swagger UI: http://127.0.0.1:8000/api/schema/swagger-ui/

5. Stop containers when finished:

```bash
  docker-compose down
```

**Git Workflow (Mandatory)**
This workflow is required for all team members.

1) Create a feature branch from develop:

```bash
  git checkout -b feature/<short-task-name>
```
2) Develop only inside your feature branch.

3) Open a Pull Request into develop.

4) Direct commits to main and develop are strictly forbidden.

### Useful Commands
Django Create a superuser:
```bash
  docker-compose exec web python manage.py createsuperuser
```
Apply migrations manually:
```bash
  docker-compose exec web python manage.py migrate
```
Create new migrations:
```bash
  docker-compose exec web python manage.py makemigrations
```
Open Django shell:
```bash
  docker-compose exec web python manage.py shell
```
**Celery**
Run Celery worker locally (outside Docker, for debugging):
```bash
  celery -A config worker -l INFO
```
View Celery worker logs inside Docker:
```bash
  docker-compose logs -f celery
```
Docker
View running containers:
```bash
  docker-compose ps
```
Rebuild containers:
```bash
  docker-compose up --build
```
Stop and remove containers:
```bash
  docker-compose down
```
Remove containers and volumes (⚠️ this will delete DB data):
```bash
  docker-compose down -v
```
