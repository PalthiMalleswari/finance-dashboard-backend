# Finance Dashboard Backend

A role-based finance dashboard API built with **Django 4.2**, **Django REST Framework**, and **PostgreSQL**.

---

## Tech Stack

| Layer          | Technology                          |
|----------------|-------------------------------------|
| Framework      | Django 4.2 + Django REST Framework  |
| Database       | PostgreSQL                          |
| Filtering      | django-filter                       |
| Auth           | Session + Basic (built-in DRF)      |
| Python         | 3.10+                               |

---

## Project Structure

```
finance_project/
├── manage.py
├── requirements.txt
├── README.md
├── finance_project/          ← Project config
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
└── core/                     ← Main application
    ├── models.py             ← User (with roles) + FinancialRecord
    ├── serializers.py        ← Request/response validation
    ├── permissions.py        ← Role-based access control
    ├── views.py              ← API endpoints
    ├── urls.py               ← URL routing
    ├── admin.py              ← Django admin config
    ├── middleware.py          ← Custom error handler
    ├── tests.py              ← 30+ test cases
    └── management/commands/
        └── seed_data.py      ← Demo data seeder
```

---

## Quick Start

### 1. Prerequisites

- Python 3.10+
- PostgreSQL running locally

### 2. Create the database

```bash
psql -U postgres -c "CREATE DATABASE finance_dashboard;"
```

### 3. Set up the project

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate          # Linux / Mac
# venv\Scripts\activate           # Windows

# Install dependencies
pip install -r requirements.txt
```

### 4. Configure database credentials

Edit `finance_project/settings.py` or set environment variables:

```bash
export DB_NAME=finance_dashboard
export DB_USER=postgres
export DB_PASSWORD=your_password
export DB_HOST=localhost
export DB_PORT=5432
```

### 5. Run migrations

```bash
python manage.py makemigrations core
python manage.py migrate
```

### 6. Create a superuser

```bash
python manage.py createsuperuser
```

### 7. Seed demo data

```bash
python manage.py seed_data
```

This creates 3 users and 60 financial records:

| Username       | Password      | Role    |
|----------------|---------------|---------|
| admin_user     | TestPass123!  | Admin   |
| analyst_user   | TestPass123!  | Analyst |
| viewer_user    | TestPass123!  | Viewer  |

### 8. Run the server

```bash
python manage.py runserver
```

The API is available at `http://127.0.0.1:8000/api/`

### 9. Run tests

```bash
python manage.py test core -v 2
```

---

## API Endpoints

### Authentication

Log in via the Django admin at `/admin/` or use the DRF browsable API login at `/api-auth/login/`. All API requests require authentication.

### User Management (Admin only)

| Method | Endpoint             | Description              |
|--------|----------------------|--------------------------|
| GET    | `/api/me/`           | Current user profile     |
| GET    | `/api/users/`        | List all users           |
| POST   | `/api/users/`        | Create a new user        |
| GET    | `/api/users/<id>/`   | Retrieve user details    |
| PATCH  | `/api/users/<id>/`   | Update user / role       |
| DELETE | `/api/users/<id>/`   | Deactivate user          |

### Financial Records

| Method | Endpoint              | Viewer | Analyst | Admin |
|--------|-----------------------|--------|---------|-------|
| GET    | `/api/records/`       | ✅     | ✅      | ✅    |
| POST   | `/api/records/`       | ❌     | ❌      | ✅    |
| GET    | `/api/records/<id>/`  | ✅     | ✅      | ✅    |
| PATCH  | `/api/records/<id>/`  | ❌     | ❌      | ✅    |
| DELETE | `/api/records/<id>/`  | ❌     | ❌      | ✅    |

#### Filtering & Search

```
GET /api/records/?entry_type=expense
GET /api/records/?category=food
GET /api/records/?date__gte=2025-01-01&date__lte=2025-06-30
GET /api/records/?amount__gte=100&amount__lte=5000
GET /api/records/?search=salary
GET /api/records/?ordering=-amount
```

### Dashboard Analytics (Analyst + Admin)

| Method | Endpoint                      | Description                   |
|--------|-------------------------------|-------------------------------|
| GET    | `/api/dashboard/summary/`     | Total income, expenses, net   |
| GET    | `/api/dashboard/categories/`  | Category-wise breakdown       |
| GET    | `/api/dashboard/trends/`      | Monthly income vs expenses    |
| GET    | `/api/dashboard/recent/`      | Last N records (default 10)   |

#### Dashboard Query Parameters

```
GET /api/dashboard/summary/?date_from=2025-01-01&date_to=2025-06-30
GET /api/dashboard/categories/?entry_type=expense
GET /api/dashboard/recent/?limit=5
```

---

## Access Control Matrix

| Area               | Viewer | Analyst | Admin |
|--------------------|--------|---------|-------|
| View records       | ✅     | ✅      | ✅    |
| Create/edit/delete records | ❌ | ❌   | ✅    |
| Dashboard analytics | ❌    | ✅      | ✅    |
| Manage users       | ❌     | ❌      | ✅    |

Access control is implemented via custom DRF permission classes in `core/permissions.py`:

- **IsAdmin** — restricts to Admin role
- **IsAnalystOrAbove** — allows Analyst and Admin
- **RecordPermission** — read for all, write for Admin only
- **IsActiveUser** — blocks deactivated accounts

---

## Error Response Format

All error responses follow a consistent JSON structure:

```json
{
    "error": true,
    "status_code": 400,
    "message": "Human-readable summary of the error",
    "details": {
        "field_name": ["Specific validation error"]
    }
}
```

---

## Data Persistence

PostgreSQL is used as the primary database. The schema is managed by Django's ORM and migration system. To switch to SQLite for local testing, change `DATABASES` in `settings.py`:

```python
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}
```
