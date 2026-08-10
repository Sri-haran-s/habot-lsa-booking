# HabotConnect LSA Service Booking Backend
## Python Backend Developer Hiring Project
### Presentation Script & Slide Content

---

## SLIDE 1: Title Slide

**Title:** LSA Service Booking Backend  
**Subtitle:** Python Backend Developer Hiring Project  
**Candidate:** Sri Haran  
**Contact:** sriharan@email.com | github.com/sriharan | linkedin.com/in/sriharan

**Suggested Layout:**
- Large title centered
- Subtitle below
- Contact info at bottom
- HabotConnect logo (if available) or simple geometric design

**What to say:**
"Good morning/afternoon. I'm Sri Haran, and this is my backend prototype for the HabotConnect LSA Service Booking platform. Over the next 10 minutes, I'll walk you through the architecture, design decisions, and implementation of a production-ready Django backend that connects parents with Learning Support Assistants."

**Possible questions:**
- Q: "Why did you choose Django over Flask?"
- A: "Django's built-in ORM, admin panel, and migration system reduce boilerplate significantly. For a 4-6 hour prototype, this let me focus on business logic rather than infrastructure. Django REST Framework also provides excellent serialization and validation out of the box."

---

## SLIDE 2: Problem Statement & Objective

**Bullet points:**
- HabotConnect connects parents with Learning Support Assistants (LSAs)
- Children with learning difficulties need specialized, scheduled support
- The platform requires reliable booking, search, and payment infrastructure
- **Objective:** Build a production-ready backend prototype with clean architecture

**Suggested diagram:**
- Simple flow: Parent -> Platform -> LSA -> Scheduled Session

**What to say:**
"The core challenge is managing time-sensitive bookings between two parties. Parents need to find qualified LSAs by skill, book specific time slots, and have those bookings confirmed through a payment flow. The system must prevent double-bookings, handle payment webhooks safely, and remain performant as the user base grows."

**Possible questions:**
- Q: "What was the hardest requirement to implement?"
- A: "The double-booking prevention with concurrency safety. It's easy to check for overlaps in Python, but handling race conditions where two parents book the same LSA simultaneously requires database-level locking with select_for_update() inside atomic transactions."

---

## SLIDE 3: Requirements Implemented

**Bullet points:**
- Database schema: Parent, LSA_Profile, Booking_Request
- REST APIs: Booking creation, LSA search, Payment webhook
- Double-booking prevention with transaction safety
- N+1 query optimization in LSA search
- Mock payment integration with 6 exception types
- Payment webhook with idempotency & state transitions
- 31 automated pytest cases (models, APIs, webhooks, services)
- GitHub Actions CI with PostgreSQL service container

**Suggested diagram:**
- Checklist graphic with all items checked

**What to say:**
"I implemented all required features from the hiring document. The database has three core entities with proper relationships and constraints. The API layer provides three endpoints with comprehensive validation. The payment service handles timeouts, connection errors, HTTP errors, and invalid responses. And the entire test suite runs automatically in CI on every push."

**Possible questions:**
- Q: "Did you implement anything beyond the requirements?"
- A: "I added webhook idempotency handling, which wasn't explicitly required but is critical for production payment systems. I also added database-level constraints beyond application validation, and implemented proper logging throughout the service layer."

---

## SLIDE 4: System Architecture

**Bullet points:**
- Django MVT adapted for REST APIs
- DRF Serializers replace HTML templates with JSON
- Service layer isolates external HTTP calls
- PostgreSQL with JSONField for skill arrays
- Layered architecture: Client -> DRF -> Business Logic -> ORM -> Database

**Suggested diagram:**
```
Client (curl/Postman/Frontend)
    |
    v
Django REST Framework (Views + Serializers)
    |
    v
Business Logic + Service Layer
    |
    v
Django ORM (Models + QuerySets)
    |
    v
PostgreSQL 15 (Indexes + Constraints)
```

**What to say:**
"I used Django's native MVT pattern, where DRF serializers act as the presentation layer instead of HTML templates. This is idiomatic Django and reduces boilerplate. The service layer isolates payment gateway integration, making it testable and resilient. PostgreSQL handles the data layer with composite indexes for overlap queries and JSONField for skill arrays."

**Possible questions:**
- Q: "Why MVT instead of MVC?"
- A: "Django's 'View' is equivalent to MVC's 'Controller.' DRF serializers naturally replace templates for JSON APIs. Fighting Django's conventions adds friction without benefit. This demonstrates deep framework knowledge rather than forcing an unfamiliar pattern."

---

## SLIDE 5: Database Design

**Bullet points:**
- **Parent:** id, name, email (unique), phone, created_at
- **LSA_Profile:** id, name, email (unique), skills (JSON array), experience, is_active
- **Booking_Request:** id, parent (FK), lsa (FK), start_time, end_time, status, timestamps
- Constraints: unique_booking_slot, start_before_end (CHECK)
- Indexes: composite (lsa, start_time, end_time), status + created_at

**Suggested diagram:**
- ER diagram showing 1:M relationships
- Highlight the composite index on Booking_Request

**What to say:**
"The schema is intentionally simple but production-minded. I used PostgreSQL's JSONField for skills rather than a normalized Skill model. This is a trade-off: less normalized but avoids M2M join complexity and uses PostgreSQL's native containment operator for efficient filtering. For 1000+ skills with metadata, I would migrate to a proper M2M model. The composite index on (lsa, start_time, end_time) is critical for the overlap detection query."

**Possible questions:**
- Q: "Why JSONField for skills instead of a separate table?"
- A: "For this prototype scope, JSONField is the right trade-off. It simplifies the schema, avoids migration complexity, and PostgreSQL's @> operator filters efficiently. If skills grew to thousands with certifications and levels, I would normalize to a Skill model with a ManyToManyField through a junction table."

---

## SLIDE 6: API Design

**Bullet points:**
- `POST /api/v1/bookings/` — Create booking with validation
- `GET /api/v1/lsas/search/?skill=Python` — Filter active LSAs by skills
- `POST /api/v1/payments/webhook/` — Process payment events
- `POST /api/payments/webhook/` — Unversioned backward compatibility
- All endpoints return structured JSON: `{success, message, data}`
- Proper HTTP status codes: 201, 200, 400, 404, 500

**Suggested diagram:**
- Three endpoint cards with method, URL, and status codes

**What to say:**
"All three endpoints follow REST conventions with consistent response structures. The booking endpoint validates parent and LSA existence, time ranges, and prevents overlaps. The search endpoint filters by skills using AND logic and only returns active LSAs. The webhook supports both versioned and unversioned paths for backward compatibility, and handles idempotency for duplicate events."

**Possible questions:**
- Q: "Why did you support both /api/v1/ and /api/ for webhooks?"
- A: "The hiring document mentioned /api/payments/webhook/ specifically. I implemented the versioned endpoint as the primary route but preserved the unversioned path for backward compatibility. This shows awareness of API evolution and client migration concerns."

---

## SLIDE 7: Booking Validation & Double-Booking Prevention

**Bullet points:**
- Overlap condition: `existing.start < requested.end AND existing.end > requested.start`
- Handles: partial overlaps, containment, exact duplicates
- Allows: back-to-back bookings (10:00-11:00 and 11:00-12:00)
- `select_for_update()` locks LSA row during transaction
- `transaction.atomic()` ensures check + insert are atomic
- Database constraint `unique_booking_slot` as final defense

**Suggested diagram:**
- Timeline showing allowed vs. rejected overlaps
- Lock icon on the transaction block

**What to say:**
"The overlap condition is the mathematically correct interval overlap test. It catches partial overlaps, complete containment, and exact duplicates while correctly allowing back-to-back bookings. For concurrency, I use select_for_update() to lock the LSA row, preventing two simultaneous requests from both passing the availability check. The database's unique constraint is the final safety net."

**Possible questions:**
- Q: "Is this 100% race-condition proof?"
- A: "For typical loads, yes. select_for_update() with transaction.atomic() provides strong consistency. For extreme concurrency with thousands of simultaneous bookings, a PostgreSQL exclusion constraint using btree_gist would be the gold standard. I acknowledged this limitation in the README and documented it as a future improvement."

---

## SLIDE 8: N+1 Query Problem & Optimization

**Bullet points:**
- **N+1 Problem:** 1 query for list + N queries for related data
- **Our solution:** LSA search executes exactly 1 query regardless of result count
- **Why:** No foreign keys in LSA response; JSON containment filters in DB
- **Verification:** `test_search_no_nplus1_queries` asserts `len(connection.queries) == 1`
- **ORM techniques:** No select_related/prefetch_related needed — appropriate for this schema

**Suggested diagram:**
- BAD: 1 + N queries diagram
- GOOD: 1 query diagram
- Code snippet showing the optimized query

**What to say:**
"The N+1 problem is a classic performance killer. In our case, the LSA search endpoint naturally avoids it because LSAProfile has no foreign key relationships in the response. The serializer only touches LSA fields, so Django executes exactly one query. I verified this with a test that checks connection.queries and asserts exactly one query was made. I did not blindly add select_related or prefetch_related — I used them only where the relationship actually requires them."

**Possible questions:**
- Q: "What if you needed to include parent data in the LSA response?"
- A: "Then I would use select_related() for ForeignKey relationships or prefetch_related() for ManyToMany. I would also add the corresponding test to verify the query count remained optimized. The key is understanding why each optimization is applied, not applying them everywhere by default."

---

## SLIDE 9: Mock Payment Integration & Webhook

**Bullet points:**
- **Service layer:** `payment_service.py` isolates external HTTP calls from views
- **Exception handling:** Timeout, ConnectionError, HTTPError, Invalid JSON, Unexpected format
- **Webhook flow:** PENDING -> CONFIRMED (success) or FAILED (failure)
- **Idempotency:** Duplicate success webhooks return 200; failed bookings reject new webhooks
- **State validation:** Only PENDING bookings accept payment events
- **Logging:** Every failure path logs booking ID and error type

**Suggested diagram:**
- Flow: Webhook -> Validation -> State Check -> Transaction -> Response
- Exception type icons

**What to say:**
"The payment service is isolated from views for testability and single responsibility. It handles six categories of failures with specific exception types and comprehensive logging. The webhook validates input, checks state transition rules, and uses transaction.atomic() when updating booking status. Idempotency ensures duplicate webhooks don't cause issues — already confirmed bookings gracefully return 200."

**Possible questions:**
- Q: "How would you handle a real payment provider like Stripe?"
- A: "The service layer architecture makes this straightforward. I would replace the mock base URL with Stripe's API endpoint, add signature verification using the webhook secret, and implement exponential backoff for retries. The exception handling and logging structure would remain exactly the same."

---

## SLIDE 10: Automated Testing

**Bullet points:**
- **31 test cases** across 5 test files
- **test_models.py:** 6 tests — overlap logic, validation, edge cases
- **test_booking_api.py:** 6 tests — success, invalid inputs, double-booking, back-to-back
- **test_lsa_search_api.py:** 5 tests — filtering, N+1 query count verification
- **test_webhook.py:** 7 tests — state transitions, idempotency, error cases
- **test_payment_service.py:** 6 tests — timeout, connection, HTTP, JSON errors
- All external HTTP calls mocked — no real network dependencies

**Suggested diagram:**
- Pie chart or bar chart showing test distribution
- Green checkmarks for passing tests

**What to say:**
"I wrote 31 tests covering success paths, failure paths, edge cases, and concurrency scenarios. The booking API tests verify double-booking prevention and back-to-back allowance. The search tests verify the N+1 query count. The webhook tests cover all state transitions and idempotency. Payment service tests use unittest.mock to simulate every failure mode without making real network calls."

**Possible questions:**
- Q: "What is your test coverage percentage?"
- A: "I focused on meaningful test cases rather than chasing a coverage number. Every business requirement has at least one test: overlap detection, state transitions, validation rules, and exception handling. The critical paths — booking creation, webhook processing, and search optimization — have multiple tests each."

---

## SLIDE 11: GitHub Actions / CI Pipeline

**Bullet points:**
- Triggers on push and pull_request to main/develop/master
- **8-step pipeline:** Checkout -> Python setup -> Dependencies -> PostgreSQL wait -> Django checks -> Migrations -> pytest -> Artifacts
- **PostgreSQL 15 service container** for real database testing
- **Environment variables** for all config — no hardcoded secrets
- **Fail-fast:** Workflow fails immediately on any step failure

**Suggested diagram:**
- Pipeline flow diagram with 8 steps
- PostgreSQL container icon

**What to say:**
"The CI pipeline runs on every push and pull request. It spins up a real PostgreSQL 15 container, installs dependencies, runs Django system checks to catch configuration errors, applies migrations, and executes the full pytest suite. Using a real PostgreSQL instance rather than SQLite ensures JSONField operations and database constraints are actually tested. All credentials are passed via environment variables — no secrets in code."

**Possible questions:**
- Q: "Why test against PostgreSQL instead of SQLite?"
- A: "SQLite doesn't support PostgreSQL's JSONField containment operator, which is how we filter skills. Testing against PostgreSQL catches database-specific issues that SQLite would miss. The CI uses a Docker service container, so it's fast and isolated."

---

## SLIDE 12: Technical Decisions, Demo & Conclusion

**Bullet points:**
- **Skills as JSONField:** Right complexity for prototype; PostgreSQL @> operator is efficient
- **Function-based views:** Readable for 3 simple endpoints; CBV adds unnecessary boilerplate
- **select_for_update():** Row-level locking prevents race conditions without table locks
- **SQLite fallback:** Enables local testing without PostgreSQL; CI always uses PostgreSQL
- **Honest limitations:** No auth, no CORS, no rate limiting — documented for future work

**Demo suggestions:**
- Live curl to create a booking
- Show pytest output (31 passed)
- Show GitHub Actions green checkmark

**What to say:**
"Every decision was a trade-off evaluated against the 4-6 hour scope. JSONField for skills avoids M2M complexity while remaining performant. Function-based views keep the code readable. select_for_update() provides strong consistency without over-engineering. I documented all limitations honestly — no auth, no CORS, no rate limiting — because claiming production features that don't exist is worse than acknowledging scope boundaries. This prototype demonstrates production thinking within realistic constraints."

**Possible questions:**
- Q: "What would you implement first if you had 2 more hours?"
- A: "Authentication with JWT tokens and role-based permissions. Right now endpoints are open, which is acceptable for a prototype but the first thing I would add for production. Second would be webhook signature verification for security."
- Q: "How would you scale this to 10,000 bookings per day?"
- A: "First, add database connection pooling with PgBouncer. Second, implement read replicas for search queries. Third, move payment processing to Celery with Redis for async handling. The current architecture supports these changes because the service layer and ORM usage are already clean."

---

## PRESENTATION TIPS

1. **Time allocation:** 1 minute per slide = 12 minutes total
2. **Speak slowly** on architecture and database design slides
3. **Show the code** briefly when discussing double-booking or N+1
4. **Emphasize trade-offs** — interviewers want to see reasoning, not just implementation
5. **Be honest about limitations** — it shows professional maturity
6. **Have the repo open** in case they ask to see specific files
7. **Practice the curl commands** if doing a live demo

## KEY NUMBERS TO REMEMBER

- **31 tests** passing
- **3 API endpoints**
- **3 database entities**
- **4 booking statuses** (PENDING, CONFIRMED, FAILED, CANCELLED)
- **6 exception types** in payment service
- **1 query** for LSA search (N+1 avoided)
- **8 CI pipeline steps**
