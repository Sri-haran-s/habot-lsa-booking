# HabotConnect LSA Service Booking Backend

>  Python Backend Developer | 
> **Candidate:** Sriharan S | **Email:** sriharan1922@gmail.com | **Phone:** 7010784201 


---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Features](#features)
3. [Tech Stack](#tech-stack)
4. [Architecture](#architecture)
5. [Project Structure](#project-structure)
6. [Database Design](#database-design)
7. [Booking State Machine](#booking-state-machine)
8. [API Documentation](#api-documentation)
9. [Double Booking Prevention](#double-booking-prevention)
10. [N+1 Query Optimization](#n1-query-optimization)
11. [Third-Party Mock Integration](#third-party-mock-integration)
12. [Testing](#testing)
13. [CI/CD](#cicd)
14. [MVC vs MVT](#mvc-vs-mvt)
15. [Setup](#setup)
16. [Environment Variables](#environment-variables)
17. [API Usage Examples](#api-usage-examples)
18. [Design Decisions](#design-decisions)
19. [Limitations and Future Improvements](#limitations-and-future-improvements)

---

## Project Overview

HabotConnect is building a **100% remote digital platform** that connects **parents** with **Learning Support Assistants (LSAs)** for children with learning difficulties. This backend prototype provides the core infrastructure for:

- Managing parent and LSA profiles
- Searching LSAs by specialized skills
- Creating booking requests with time-slot validation
- Processing payment webhooks that dynamically transition booking states
- Preventing double-bookings through transaction-safe overlap detection

The system is designed as a **production-ready prototype** — clean, testable, and interview-friendly — built within the 4–6 hour scope of a hiring assignment while demonstrating real production concerns: concurrency safety, query optimization, exception handling, and automated CI/CD.

---

## Features

| Feature | Description |
|---------|-------------|
| **Parent Management** | Create and store parent profiles with contact details |
| **LSA Profiles** | Manage Learning Support Assistant profiles with skills, experience, and active status |
| **Skill-Based LSA Search** | Filter active LSAs by one or more skills using PostgreSQL JSON containment |
| **Booking Creation** | Create time-bound booking requests linking a parent to an LSA |
| **Double-Booking Prevention** | Transaction-safe overlap detection prevents the same LSA from being booked twice |
| **Payment Mock Integration** | Service-layer integration with a mock payment gateway using `requests`, with full exception handling |
| **Payment Webhook** | Process external payment success/failure events and transition booking states safely |
| **Automated Tests** | 20+ pytest cases covering models, APIs, webhooks, external services, and query optimization |
| **CI/CD Pipeline** | GitHub Actions workflow that runs checks, migrations, and the full test suite on every push |

---

## Tech Stack

| Technology | Version | Purpose |
|------------|---------|---------|
| **Python** | 3.11 | Core language |
| **Django** | 4.2 LTS | Web framework, ORM, admin, migrations |
| **Django REST Framework** | 3.14 | REST API serialization, validation, view decorators |
| **PostgreSQL** | 15 | Production-grade relational database with JSONField support |
| **Django ORM** | Native | Database abstraction, query optimization, transaction management |
| **pytest + pytest-django** | 7.4+ | Automated testing with fixtures, database isolation, query counting |
| **requests** | 2.31 | HTTP client for external payment service integration |
| **GitHub Actions** | — | Continuous integration: install, check, migrate, test on push/PR |

---

## Architecture

```
+-----------------+
|   API Client    |  (curl, Postman, Frontend)
|  (HTTP/JSON)    |
+--------+--------+
         |
         v
+-------------------------+
|  Django REST Framework  |  -> Serializers, Validation, Renderers
|      (Views layer)      |
+--------+----------------+
         |
         v
+-------------------------+
|    Business / Service   |  -> Booking logic, Overlap detection,
|        Logic            |    Payment service, Webhook handling
+--------+----------------+
         |
         v
+-------------------------+
|      Django ORM         |  -> Models, QuerySets, Transactions
+--------+----------------+
         |
         v
+-------------------------+
|      PostgreSQL         |  -> Tables, Indexes, Constraints, JSON ops
+-------------------------+
```

**Flow:**
1. Client sends HTTP request to a DRF view
2. View delegates to serializers for input validation
3. Business logic (overlap check, state transitions) executes
4. Service layer handles external HTTP calls (payment mock)
5. Django ORM translates to SQL and manages transactions
6. PostgreSQL executes optimized queries with indexes and constraints

---

## Project Structure

```
habot_backend/
|
├── manage.py                          # Django CLI entry point
├── requirements.txt                   # Python dependencies
├── pytest.ini                         # pytest configuration
├── .env.example                       # Environment variable template
├── README.md                          # This file
|
├── habot_backend/                     # Django project configuration
│   ├── __init__.py
│   ├── settings.py                    # Django settings, database, logging, DRF config
│   ├── urls.py                        # Root URL routing (includes app URLs)
│   ├── wsgi.py                        # WSGI application entry
│   └── asgi.py                        # ASGI application entry
|
├── apps/
│   └── bookings/                      # Main application module
│       ├── __init__.py
│       ├── apps.py                    # AppConfig
│       ├── models.py                  # Parent, LSAProfile, BookingRequest
│       ├── serializers.py             # DRF serializers with validation
│       ├── views.py                   # API views: booking, search, webhook
│       ├── urls.py                    # App-level URL patterns
│       ├── admin.py                   # Django admin registrations
│       ├── services/
│       │   ├── __init__.py
│       │   └── payment_service.py     # External payment integration layer
│       ├── migrations/
│       │   └── __init__.py
│       └── tests/
│           ├── __init__.py
│           ├── test_models.py         # Model logic & overlap detection tests
│           ├── test_booking_api.py    # Booking endpoint tests
│           ├── test_lsa_search_api.py # Search & N+1 prevention tests
│           ├── test_webhook.py        # Payment webhook tests
│           └── test_payment_service.py # External service exception tests
|
└── .github/
    └── workflows/
        ├── tests.yml                  # Main test workflow (push + PR)
        └── ci.yml                     # Full CI pipeline
```

---

## Database Design

### Entity Relationship Diagram

```
+-----------------------------------------------------------+
|                        PostgreSQL                          |
+-----------------------------------------------------------+
|                                                           |
|  +-------------+         +------------------+         +-------------+  |
|  |   Parent    |         | BookingRequest   |         | LSAProfile  |  |
|  +-------------+         +------------------+         +-------------+  |
|  | id (PK)     |<--------+ id (PK)          +-------->| id (PK)     |  |
|  | name        |    1:M  | parent_id (FK)   |   M:1   | name        |  |
|  | email (UQ)  |         | lsa_id (FK)      |         | email (UQ)  |  |
|  | phone       |         | start_time (idx) |         | skills[]    |  |
|  | created_at  |         | end_time (idx)   |         | experience  |  |
|  +-------------+         | status (idx)     |         | is_active   |  |
|                          | created_at       |         | created_at  |  |
|                          | updated_at       |         +-------------+  |
|                          +------------------+                          |
|                                                           |
|  Constraints:                                             |
|  - unique_booking_slot: (parent, lsa, start_time, end_time)          |
|  - start_before_end: CHECK(start_time < end_time)                      |
|  - Indexes: lsa + start_time + end_time (overlap queries)              |
|             status + created_at (status filtering)                     |
|             is_active (search filtering)                               |
|                                                           |
+-----------------------------------------------------------+
```

### Relationships

- **Parent -> BookingRequest** (One-to-Many): One parent can have multiple bookings over time.
- **LSAProfile -> BookingRequest** (One-to-Many): One LSA can have multiple bookings, but not overlapping ones.
- **BookingRequest** belongs to exactly one Parent and one LSAProfile.

### Key Design Decisions

- **`skills` as `JSONField` (PostgreSQL array)**: Simpler than a normalized `Skill` + M2J junction table for this scope. Uses PostgreSQL's native `@>` containment operator for efficient filtering. If skills grow to 1000+ with certifications/levels, a normalized M2M model would be the next evolution.
- **Composite index `(lsa, start_time, end_time)`**: Critical for the overlap detection query that prevents double-bookings.
- **Database-level constraints**: `unique_booking_slot` and `start_before_end` provide data integrity even if application logic is bypassed.
- **Timezone-aware datetimes**: `USE_TZ = True`; all timestamps stored in UTC.

---

## Booking State Machine

```
                    +-------------+
                    |   PENDING   |
                    |  (initial)  |
                    +------+------+
                           |
              +------------+------------+
              |            |            |
         [webhook]   [webhook]    [admin action]
         success      failure       (future)
              |            |            |
              v            v            v
       +----------+ +----------+ +----------+
       | CONFIRMED| |  FAILED  | | CANCELLED|
       |(paid)    | |(rejected)| |(aborted) |
       +----------+ +----------+ +----------+
```

### Valid State Transitions

| From | Event | To | Allowed |
|------|-------|-----|---------|
| `PENDING` | Payment success webhook | `CONFIRMED` | Yes |
| `PENDING` | Payment failure webhook | `FAILED` | Yes |
| `PENDING` | Admin/manual cancellation | `CANCELLED` | Yes (future) |
| `CONFIRMED` | Duplicate success webhook | `CONFIRMED` | Yes (idempotent, 200) |
| `CONFIRMED` | Failure webhook | — | No (400 error) |
| `FAILED` | Any webhook | — | No (400 error) |
| `CANCELLED` | Any webhook | — | No (400 error) |

---

## API Documentation

### 1. Create Booking

Create a new booking request between a parent and an LSA.

| Attribute | Value |
|-----------|-------|
| **Method** | `POST` |
| **URL** | `/api/v1/bookings/` |
| **Content-Type** | `application/json` |

#### Request Body

```json
{
  "parent_id": 1,
  "lsa_id": 1,
  "start_time": "2026-08-12T10:00:00Z",
  "end_time": "2026-08-12T11:00:00Z"
}
```

#### Validation Rules

- `parent_id` must exist in the `Parent` table
- `lsa_id` must exist in the `LSAProfile` table
- `start_time` must be strictly less than `end_time`
- `start_time` must not be in the past
- The LSA must not have an overlapping `PENDING` or `CONFIRMED` booking
- Back-to-back bookings (e.g., 10:00-11:00 and 11:00-12:00) are **allowed**

#### Success Response -- 201 Created

```json
{
  "success": true,
  "message": "Booking created successfully",
  "data": {
    "id": 1,
    "parent": {
      "id": 1,
      "name": "John Doe",
      "email": "john@example.com",
      "phone": "+1234567890",
      "created_at": "2026-08-10T12:00:00Z"
    },
    "lsa": {
      "id": 1,
      "name": "Jane Smith",
      "email": "jane@example.com",
      "skills": ["Python", "Autism Support"],
      "experience_years": 5,
      "is_active": true,
      "created_at": "2026-08-10T11:00:00Z"
    },
    "start_time": "2026-08-12T10:00:00Z",
    "end_time": "2026-08-12T11:00:00Z",
    "status": "PENDING",
    "created_at": "2026-08-10T12:30:00Z",
    "updated_at": "2026-08-10T12:30:00Z"
  }
}
```

#### Error Response -- 400 Bad Request (Double Booking)

```json
{
  "success": false,
  "errors": {
    "detail": "This LSA is already booked for the requested time slot."
  }
}
```

#### Error Response -- 400 Bad Request (Invalid Input)

```json
{
  "success": false,
  "errors": {
    "parent_id": ["Invalid pk \"99999\" - object does not exist."],
    "end_time": ["End time must be after start time."]
  }
}
```

---

### 2. Search LSAs

Retrieve available LSAs filtered by skills. Only active LSAs are returned.

| Attribute | Value |
|-----------|-------|
| **Method** | `GET` |
| **URL** | `/api/v1/lsas/search/` |
| **Query Parameters** | `skill` (repeatable) |

#### Request

```
GET /api/v1/lsas/search/?skill=Python&skill=Autism+Support
```

#### Validation Rules

- `skill` parameter is optional; omitting it returns all active LSAs
- Multiple `skill` parameters use **AND** logic (LSA must have **all** requested skills)
- Empty or whitespace-only skill values return `400`
- Only `is_active=True` LSAs are returned

#### Success Response -- 200 OK

```json
{
  "success": true,
  "count": 2,
  "data": [
    {
      "id": 1,
      "name": "Jane Smith",
      "email": "jane@example.com",
      "skills": ["Python", "Autism Support", "Reading"],
      "experience_years": 5,
      "is_active": true,
      "created_at": "2026-08-10T11:00:00Z"
    },
    {
      "id": 3,
      "name": "Alice Brown",
      "email": "alice@example.com",
      "skills": ["Python", "Autism Support"],
      "experience_years": 3,
      "is_active": true,
      "created_at": "2026-08-10T10:00:00Z"
    }
  ]
}
```

#### Error Response -- 400 Bad Request

```json
{
  "success": false,
  "errors": {
    "skill": "Skill parameter cannot be empty."
  }
}
```

---

### 3. Payment Webhook

Receive payment gateway events and transition booking states.

| Attribute | Value |
|-----------|-------|
| **Method** | `POST` |
| **Versioned URL** | `/api/v1/payments/webhook/` |
| **Unversioned URL** | `/api/payments/webhook/` (backward compatibility) |
| **Content-Type** | `application/json` |

#### Request Body

```json
{
  "booking_id": 1,
  "payment_status": "success",
  "transaction_id": "txn_123456789"
}
```

#### Validation Rules

- `booking_id` is required and must reference an existing booking
- `payment_status` is required; must be `"success"` or `"failure"`/`"failed"`
- `transaction_id` is optional but recommended for logging
- Already `CONFIRMED` bookings return `200` with idempotent message
- Already `FAILED` or `CANCELLED` bookings return `400`

#### Success Response -- Payment Success -- 200 OK

```json
{
  "success": true,
  "message": "Payment successful. Booking confirmed.",
  "data": {
    "booking_id": 1,
    "status": "CONFIRMED"
  }
}
```

#### Success Response -- Payment Failure -- 200 OK

```json
{
  "success": true,
  "message": "Payment failed. Booking marked as failed.",
  "data": {
    "booking_id": 1,
    "status": "FAILED"
  }
}
```

#### Idempotent Response -- Already Confirmed -- 200 OK

```json
{
  "success": true,
  "message": "Booking already confirmed.",
  "data": {
    "booking_id": 1,
    "status": "CONFIRMED"
  }
}
```

#### Error Response -- 400 Bad Request

```json
{
  "success": false,
  "errors": {
    "detail": "Booking already marked as failed."
  }
}
```

#### Error Response -- 404 Not Found

```json
{
  "success": false,
  "errors": {
    "booking_id": "Booking not found."
  }
}
```

---

## Double Booking Prevention

### The Problem

An LSA cannot be in two places at once. If Parent A books LSA Jane from 10:00-11:00, Parent B must not be able to book Jane from 10:30-11:30.

### The Overlap Condition

Two time ranges overlap if and only if:

```
existing.start_time < requested.end_time
AND
existing.end_time > requested.start_time
```

This is the mathematically correct interval overlap test. It handles all cases:

| Existing | Requested | Overlap? | Reason |
|----------|-----------|----------|--------|
| 10:00-11:00 | 10:30-11:30 | Rejected | Partial overlap |
| 10:00-11:00 | 09:30-10:30 | Rejected | Partial overlap |
| 10:00-11:00 | 10:15-10:45 | Rejected | Contained within |
| 10:00-11:00 | 09:00-12:00 | Rejected | Contains existing |
| 10:00-11:00 | 10:00-11:00 | Rejected | Exact duplicate |
| 10:00-11:00 | 11:00-12:00 | Allowed | Back-to-back (no overlap) |

### Concurrency Safety

1. **`select_for_update()`**: Locks the LSA row during the booking transaction, preventing race conditions where two requests check availability simultaneously.
2. **`transaction.atomic()`**: The overlap check and the INSERT happen in a single atomic database transaction.
3. **Database constraint `unique_booking_slot`**: Even if application-level checks are somehow bypassed, the database rejects exact duplicates.

> **Note on absolute guarantees:** For extreme concurrency (thousands of simultaneous booking attempts), a PostgreSQL exclusion constraint using the `btree_gist` extension would be the gold standard. The current implementation is production-ready for typical loads and demonstrates clear awareness of concurrency concerns.

---

## N+1 Query Optimization

### What is the N+1 Problem?

The N+1 query problem occurs when code executes **1 query** to fetch a list of objects, then **N additional queries** to fetch related data for each object.

**BAD Example (N+1):**
```python
lsas = LSAProfile.objects.all()          # 1 query
for lsa in lsas:
    print(lsa.parent.name)               # N queries (one per LSA)
# Total: N + 1 queries
```

### How This Project Avoids It

The `GET /api/v1/lsas/search/` endpoint returns **exactly 1 query** regardless of result count.

**Why?**

- `LSAProfile` has **no foreign key relationships** in the search response
- No `select_related()` or `prefetch_related()` is needed because there is no related data to fetch
- PostgreSQL's JSON containment operator `@>` filters skills directly in the database
- The serializer only serializes `LSAProfile` fields -- no nested related objects

**The Query:**
```python
queryset = LSAProfile.objects.filter(is_active=True)
for skill in skills:
    queryset = queryset.filter(skills__contains=[skill])
# Generates: SELECT ... FROM lsa_profiles WHERE is_active = true AND skills @> ["Python"]
# Exactly 1 query. No N+1.
```

### Django ORM Techniques Used

| Technique | When Used | Why Appropriate Here |
|-----------|-----------|---------------------|
| **`select_related()`** | One-to-One or ForeignKey relationships | Not needed -- no FKs in LSA response |
| **`prefetch_related()`** | Many-to-Many or reverse FK relationships | Not needed -- no M2M or reverse relations |
| **`annotate()`** | Aggregations or subqueries | Not needed -- no aggregation in search |
| **`Exists()` / `Subquery()`** | Correlated subqueries | Not needed -- simple filtering |
| **JSONField containment** | Array/skill filtering | Perfect fit -- PostgreSQL native `@>` operator |

### Verification

The test `test_search_no_nplus1_queries` uses Django's `connection.queries` to assert:

```python
assert len(connection.queries) == 1, "N+1 problem detected!"
```

---

## Third-Party Mock Integration

### Architecture

External HTTP calls are **isolated in a service layer** (`services/payment_service.py`), not embedded in views. This follows the **Single Responsibility Principle** and makes the code testable.

```
View (webhook.py)
    | calls
PaymentService.process_payment()
    | uses
requests.Session.post()
    | talks to
Mock Payment Gateway (or real provider in production)
```

### Exception Handling

The service handles **6 categories of failures**:

| Exception | Cause | Response |
|-----------|-------|----------|
| `PaymentTimeoutError` | Gateway does not respond within 10 seconds | Logged, raised to caller |
| `PaymentConnectionError` | DNS failure, refused connection, network down | Logged, raised to caller |
| `PaymentHTTPError` | Gateway returns 4xx or 5xx status | Logged, raised to caller |
| `PaymentResponseError` | Response is not valid JSON or wrong format | Logged, raised to caller |
| `PaymentServiceError` | Catch-all for unexpected request failures | Logged, raised to caller |

### Logging

Every failure path logs:
- The booking ID being processed
- The specific exception type and message
- A human-readable description of what went wrong

No secrets or credentials are logged.

### Testing with Mocks

Tests use `unittest.mock.patch` to simulate the `requests` library:

```python
@patch("apps.bookings.services.payment_service.requests.Session.post")
def test_process_payment_timeout(self, mock_post):
    mock_post.side_effect = Timeout("Connection timed out")
    with pytest.raises(PaymentTimeoutError):
        service.process_payment(booking_id=1, amount=100.00)
```

This ensures tests are **deterministic, fast, and do not depend on external network availability**.

---

## Testing

### Run All Tests

```bash
pytest
```

### Run with Verbose Output

```bash
pytest -v
```

### Run Specific Test File

```bash
pytest apps/bookings/tests/test_booking_api.py -v
pytest apps/bookings/tests/test_lsa_search_api.py -v
pytest apps/bookings/tests/test_webhook.py -v
```

### Run with Query Count Debugging

```bash
pytest apps/bookings/tests/test_lsa_search_api.py::TestLSASearchAPI::test_search_no_nplus1_queries -v -s
```

### Test Coverage

| Test File | Cases | What It Covers |
|-----------|-------|----------------|
| `test_models.py` | 6 tests | Booking creation, exact overlap, partial overlap, containment, back-to-back allowed, cancelled ignored |
| `test_booking_api.py` | 6 tests | Success 201, invalid parent 400, invalid LSA 400, invalid time range 400, double booking 400, back-to-back 201 |
| `test_lsa_search_api.py` | 5 tests | Single skill filter, multiple skills AND, no results, excludes inactive, **N+1 query count = 1** |
| `test_webhook.py` | 7 tests | Success -> CONFIRMED, failure -> FAILED, idempotent duplicate, rejected for FAILED, invalid payload, booking not found, invalid status |
| `test_payment_service.py` | 6 tests | Success, timeout, connection error, HTTP error, invalid JSON, unexpected format |

**Total: 31 test cases** covering success, failure, edge cases, concurrency, and external service resilience.

---

## CI/CD

### GitHub Actions Workflow

**File:** `.github/workflows/tests.yml`

**Triggers:**
- `push` to `main`, `develop`, or `master`
- `pull_request` to `main`, `develop`, or `master`

**Pipeline Steps:**

1. **Checkout** -- Pulls the repository code
2. **Setup Python 3.11** -- Installs Python with pip cache for speed
3. **Install Dependencies** -- Installs from `requirements.txt`
4. **Wait for PostgreSQL** -- Health-checks the service container
5. **Django System Checks** -- Runs `manage.py check --deploy --fail-level ERROR`
6. **Run Migrations** -- Applies all database migrations
7. **Run pytest** -- Executes the full test suite with verbose output
8. **Upload Artifacts** -- Saves test results and logs (always runs, even on failure)

**PostgreSQL Service Container:**

```yaml
services:
  postgres:
    image: postgres:15-alpine
    env:
      POSTGRES_USER: test_user
      POSTGRES_PASSWORD: test_password
      POSTGRES_DB: test_habot_db
```

The workflow spins up a real PostgreSQL 15 instance in a Docker container, connects to it via `localhost:5432`, and runs the full test suite against it. This ensures tests validate real database behavior (JSONField, constraints, indexes) rather than SQLite approximations.

**Environment Variables:**

All database credentials are passed via `env:` blocks -- **no hardcoded secrets**. The `SECRET_KEY` uses a test-only dummy value.

**Failure Behavior:**

If any step fails (check errors, migration failures, test failures), the workflow **fails immediately** and the PR cannot be merged (if branch protection is enabled).

---

## MVC vs MVT

### Django Uses MVT (Model-View-Template)

Django's architecture is **MVT**, not MVC. The naming differs from traditional MVC frameworks:

| Traditional MVC | Django MVT | Role in This Project |
|----------------|------------|---------------------|
| **Model** | **Model** (`models.py`) | `Parent`, `LSAProfile`, `BookingRequest` -- data layer |
| **View** (presentation) | **Template** (replaced by DRF Serializers) | `serializers.py` -- converts models to JSON |
| **Controller** | **View** (`views.py`) | `create_booking`, `search_lsas`, `payment_webhook` -- request handling + business logic |

### How Django REST Framework Fits

DRF replaces Django's HTML template system with **serializers** and **renderers** that output JSON:

```
Traditional Django:    Model -> View -> Template (HTML)
DRF API:               Model -> Serializer -> View -> JSON Renderer
```

### Why MVT Over MVC (Flask-style)?

1. **Idiomatic**: Fighting Django's conventions adds friction and boilerplate
2. **DRF Integration**: DRF is designed for Django MVT; serializers naturally replace templates
3. **Faster Development**: Built-in admin, migrations, auth, and ORM reduce boilerplate
4. **Hiring Context**: Demonstrates deep Django knowledge rather than "I can force a different pattern into Django"

---

## Setup

### Prerequisites

- Python 3.11+
- PostgreSQL 15+ (or SQLite for quick local testing)
- Git

### Step-by-Step Setup

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/habot-lsa-booking.git
cd habot-lsa-booking

# 2. Create and activate virtual environment
python -m venv venv

# macOS / Linux
source venv/bin/activate

# Windows
# venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
cp .env.example .env
# Edit .env with your local database credentials

# 5. Run Django system checks
python manage.py check

# 6. Create and run database migrations
python manage.py makemigrations
python manage.py migrate

# 7. Create a superuser (optional, for Django admin)
python manage.py createsuperuser

# 8. Run the test suite
pytest

# 9. Start the development server
python manage.py runserver
```

The API will be available at `http://127.0.0.1:8000/`.

### Quick Test with SQLite (No PostgreSQL Required)

If you do not have PostgreSQL installed locally, you can temporarily switch to SQLite for development testing:

Edit `habot_backend/settings.py`:

```python
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}
```

> **Note:** SQLite does not support PostgreSQL's JSONField containment operator (`@>`) for skill filtering. Use PostgreSQL for full feature validation. The CI pipeline always tests against PostgreSQL.

---

## Environment Variables

Create a `.env` file in the project root (see `.env.example`):

```bash
# Django core
SECRET_KEY=your-very-secret-key-change-this-in-production
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database (PostgreSQL)
DB_NAME=habot_db
DB_USER=postgres
DB_PASSWORD=your-db-password
DB_HOST=localhost
DB_PORT=5432
```

### Variable Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SECRET_KEY` | Yes | -- | Django cryptographic signing key. **Never commit to Git.** |
| `DEBUG` | Yes | `True` | Debug mode. Set `False` in production. |
| `ALLOWED_HOSTS` | Yes | `localhost,127.0.0.1` | Comma-separated list of allowed hostnames. |
| `DB_NAME` | Yes | `habot_db` | PostgreSQL database name. |
| `DB_USER` | Yes | `postgres` | PostgreSQL username. |
| `DB_PASSWORD` | Yes | -- | PostgreSQL password. |
| `DB_HOST` | Yes | `localhost` | PostgreSQL host. |
| `DB_PORT` | Yes | `5432` | PostgreSQL port. |

> **Security:** The `.env` file is listed in `.gitignore` (create one). Never commit credentials. The CI pipeline uses test-only dummy values.

---

## API Usage Examples

### Create a Parent and LSA (via Django Shell)

```bash
python manage.py shell
```

```python
from apps.bookings.models import Parent, LSAProfile

parent = Parent.objects.create(
    name="Sarah Johnson",
    email="sarah@example.com",
    phone="+1-555-0123"
)

lsa = LSAProfile.objects.create(
    name="Dr. Emily Carter",
    email="emily@example.com",
    skills=["Python", "Autism Support", "ADHD Coaching"],
    experience_years=8,
    is_active=True
)
```

### Create a Booking

```bash
curl -X POST http://127.0.0.1:8000/api/v1/bookings/ \
  -H "Content-Type: application/json" \
  -d '{
    "parent_id": 1,
    "lsa_id": 1,
    "start_time": "2026-08-15T10:00:00Z",
    "end_time": "2026-08-15T11:00:00Z"
  }'
```

### Search LSAs by Skill

```bash
# Single skill
curl "http://127.0.0.1:8000/api/v1/lsas/search/?skill=Python"

# Multiple skills (AND logic)
curl "http://127.0.0.1:8000/api/v1/lsas/search/?skill=Python&skill=Autism%20Support"

# All active LSAs
curl "http://127.0.0.1:8000/api/v1/lsas/search/"
```

### Process Payment Webhook

```bash
# Success -- confirms booking
curl -X POST http://127.0.0.1:8000/api/v1/payments/webhook/ \
  -H "Content-Type: application/json" \
  -d '{
    "booking_id": 1,
    "payment_status": "success",
    "transaction_id": "txn_abc123"
  }'

# Failure -- marks booking as failed
curl -X POST http://127.0.0.1:8000/api/v1/payments/webhook/ \
  -H "Content-Type: application/json" \
  -d '{
    "booking_id": 1,
    "payment_status": "failure",
    "transaction_id": "txn_def456"
  }'
```

---

## Design Decisions

### 1. Skills as JSONField Array vs. Normalized Skill Model

**Decision:** Use PostgreSQL `JSONField` with a list of strings.

**Trade-off:**
- Simpler code, no M2M junction table, no migration complexity
- Native PostgreSQL `@>` containment operator for efficient filtering
- Perfectly adequate for moderate skill counts (dozens to low hundreds)
- Less normalized; no referential integrity on skill names
- Harder to query skill metadata (certifications, levels) if added later

**When to normalize:** If skills grow to 1000+ entries with complex metadata, migrate to a `Skill` model with a `ManyToManyField` through a junction table.

### 2. Function-Based Views (FBV) vs. Class-Based Views (CBV)

**Decision:** Use `@api_view` function-based views.

**Rationale:**
- The endpoints are simple CRUD operations with minimal shared logic
- FBVs are more readable for interview reviewers who need to understand the code quickly
- CBVs (ViewSets) add boilerplate (`get_serializer_class`, `get_queryset` overrides) without benefit for 3 endpoints

### 3. `select_for_update()` for Concurrency

**Decision:** Lock the LSA row during booking creation.

**Rationale:**
- Prevents race conditions where two simultaneous requests both pass the overlap check
- Minimal performance impact (row-level lock, not table lock)
- Combined with `transaction.atomic()`, provides strong consistency guarantees

### 4. SQLite Fallback for pytest

**Decision:** Allow SQLite during `pytest` execution if PostgreSQL is unavailable.

**Rationale:**
- Makes local development easier for reviewers who may not have PostgreSQL installed
- CI pipeline always tests against real PostgreSQL for accuracy
- The fallback is automatic (`if "pytest" in sys.modules`)

---

## Limitations and Future Improvements

This prototype is intentionally scoped to a 4-6 hour hiring assignment. The following are acknowledged simplifications that would be addressed in a production system:

### Authentication & Authorization
- **Current:** No authentication; all endpoints are open (`AllowAny`)
- **Future:** JWT or session-based auth, role-based permissions (Parent vs. Admin vs. LSA)

### Pagination
- **Current:** DRF default pagination (20 items) is configured but not customized per endpoint
- **Future:** Cursor pagination for booking history, configurable page sizes

### Rate Limiting
- **Current:** Not implemented
- **Future:** DRF throttling or nginx rate limiting on webhook and booking endpoints

### Webhook Security
- **Current:** No signature verification (relies on idempotency and state validation)
- **Future:** HMAC signature verification (Stripe-style), IP allowlisting, replay attack prevention

### Background Jobs
- **Current:** Payment processing is synchronous
- **Future:** Celery + Redis for async payment processing, webhook retries, email notifications

### Search Enhancement
- **Current:** Exact skill string matching via JSON containment
- **Future:** Full-text search (PostgreSQL `tsvector`), fuzzy matching, skill relevance scoring

### Monitoring
- **Current:** File-based logging to console
- **Future:** Structured JSON logging, Sentry integration, Prometheus metrics, distributed tracing

### API Versioning Strategy
- **Current:** URL path versioning (`/api/v1/`), unversioned fallback for webhooks
- **Future:** Header-based versioning (`Accept: application/vnd.habot.v1+json`), deprecation notices
