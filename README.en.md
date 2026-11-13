# University Course Selection System (Python + SQLite)

[中文](README.md) | **English**

A complete course selection management system: administrators schedule and manage courses, teachers view student rosters and enter grades, and students enroll in or drop courses and view their timetables — plus a role-isolated AI assistant. Its feature set matches the reference project (Vue 3 + Spring Boot 3 + MySQL 8) item for item, with the stack rebuilt on **Python + FastAPI + SQLite**.

No npm, no Node, no MySQL — and it runs completely offline.

---

## Quick Start

```bash
pip install -r requirements.txt
python scripts/init_db.py        # Create the database + load demo data (idempotent, safe to re-run)
python run.py                    # http://localhost:8000
```

Open <http://localhost:8000>. The API documentation is available at <http://localhost:8000/docs>.

### Demo Accounts

| Role | Username | Password | Notes |
|---|---|---|---|
| Administrator | `admin` | `123456` | Full management capabilities |
| Teacher | `tea001` ~ `tea010` | `123456` | My courses, student rosters, grade entry |
| Student | `stu001` ~ `stu050` | `123456` | Course enrollment, withdrawal, timetable, grades |

> Passwords are for local demonstrations only (override with `DEFAULT_PASSWORD`). Be sure to change them for production deployments.

---

## Features

### Administrator

| Module | Capabilities |
|---|---|
| Course Management | Pagination with keyword/semester/status filters; create, edit, and delete courses; open/close enrollment. Course code is unique per semester; capacity cannot fall below current enrollment; deletion is rejected when enrollment records exist. |
| Schedule Management | Maintain multiple class sessions per course (day of week / period / weeks / location); **teacher time-conflict** validation (rejected when courses share a semester, day, and overlapping period ranges). |
| Student Management | Pagination + major filter; create, update, and delete students. Creating a student **automatically provisions a login account** (username = student ID, password `123456`); renaming a student syncs the account name. Deletion is rejected when enrollment records exist. |
| Teacher Management | Same as student management, with username = employee ID. Deletion is rejected when courses exist. |
| Account Management | Pagination (including linked student/teacher profile data); change login username, reset password, enable/disable, and delete accounts. You cannot disable or delete yourself. |
| Enrollment Records | Filter by student/course/status/semester; **enroll on behalf of a student**; soft withdrawal (history retained); hard delete (capacity returned accordingly). |
| Statistics & Reports | Top-N popular courses (including fill rate), enrollment distribution by major, and teacher workload. |

### Students

Course center (with Available Courses / My Courses tabs), enrollment, withdrawal, my timetable (weekly grid), grade lookup, and **reverse conflict lookup** (lists which courses are blocked by current enrollments).

### Teachers

My courses, student rosters, and inline entry/edit of grades (0–100; withdrawn students do not appear in rosters).

### AI Assistant (All Three Roles)

The built-in knowledge base is **filtered by role**: a student asking "how do I add a course" won't receive admin-side answers, and a teacher asking "how do I drop a course" gets "No match". Suggested questions also differ by role. Optionally, any Anthropic-protocol-compatible LLM can be connected as a fallback.

---

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── main.py              # App composition: CORS, exception handling, router registration, static hosting
│   │   ├── config.py            # Configuration (sensitive settings are read from environment variables only)
│   │   ├── db.py                # SQLite connections: WAL + busy_timeout + thread-local connections
│   │   ├── common/              # Unified response envelope, error codes, exception handling
│   │   ├── security/            # JWT, bcrypt, require_role dependency factory
│   │   ├── schemas/             # Pydantic v2 request/response models
│   │   ├── routers/             # Controller layer (thin: request binding and authentication only)
│   │   ├── service/             # Business layer (transaction boundaries live here)
│   │   ├── repository/          # Data access layer (SQL only)
│   │   └── ai/                  # AI assistant: knowledge base + provider registry
│   └── static/                  # Hand-written frontend (HTML + CSS + native ES modules)
├── sql/
│   ├── 01_schema.sql            # Authoritative DDL: 6 tables, 2 views
│   ├── 02_seed_data.sql         # Demo data
│   └── 03_queries.sql           # 17 demo queries + execution-plan comparison + consistency self-checks
├── scripts/
│   ├── init_db.py               # Database bootstrap script (idempotent)
│   ├── run_queries.py           # Runs 03_queries.sql and prints the results
│   ├── sanitize_check.py        # Pre-packaging sanitization gate
│   └── package.py               # Packaging (gate first, then archive)
└── docs/                        # Design notes, test report, demo script, API contract
```

> This package contains **only the source code required to run the system**. Unit test code and integration test screenshots are not included, but the testing process and results are recorded in [`docs/测试报告.md`](docs/测试报告.md).

---

## Architecture: Controller → Service → Repository

**Transaction boundaries exist only in the Service layer.** Repositories are responsible solely for SQL; routers only bind parameters and enforce authentication.

```
HTTP → routers/ (auth + validation) → service/ (business rules + BEGIN IMMEDIATE transactions) → repository/ (SQL) → SQLite
```

### Four Real Extension Points for the Open/Closed Principle

"Open for extension, closed for modification" is not just a slogan — this project has four places where you can genuinely **add without changing**:

**1. AI answer providers** (the core extension point)

`ai/provider.py` defines the `AiAnswerProvider` protocol (`name` / `order` / `is_available` / `try_answer`). `ai/registry.py` maintains an ordered registry, and `AiService` **only orchestrates**: it queries providers in `order` and uses the first one that returns an answer.

```python
# Add a new answer source: write a class + register it. AiService needs zero changes.
class MyProvider:
    name = "My knowledge source"
    order = 5
    def is_available(self) -> bool: ...
    def try_answer(self, question: str, ctx: AiContext) -> AiAnswer | None: ...

registry.register(MyProvider())
```

The test for whether this principle holds is practical: **to add a new answer source, how many existing files need modification? The answer is zero.**

**2. Router registry**: `routers/__init__.py` exposes `ALL_ROUTERS`, and `main.py` registers them in a loop. A new module = one more element in the list.

**3. Declarative role permissions**: the `require_role(*roles)` dependency factory declares permissions on route signatures instead of scattering `if role == ...` checks across services.

```python
@router.post("", dependencies=[Depends(require_role(Role.ADMIN))])
def create_course(...): ...
```

**4. Frontend view registry**: the route table in `static/js/router.js`, the view table in `views/index.js`, and the menu data in `layout.js`. A new page = a new view module + one registry entry.

---

## Implementation Highlights

### Preventing Overselling: One UPDATE, Check the Affected Rows

Rather than "read remaining capacity, then update" (another request can slip in between), the check is embedded in the UPDATE's `WHERE` clause:

```sql
UPDATE course SET enrolled_count = enrolled_count + 1
 WHERE id = ? AND status = 'OPEN' AND enrolled_count < capacity
```

An affected-row count of 0 means the seat was not secured. Combined with `BEGIN IMMEDIATE` + WAL + `busy_timeout=10000`, even concurrent requests cannot oversell. In testing, N threads compete for K seats: the number of successes is exactly K, and `enrolled_count` matches the actual number of enrollment records (see the test report).

### Time Conflicts: Interval Overlap, Checked on Two Dimensions

```sql
A.start_section <= B.end_section AND B.start_section <= A.end_section
AND A.start_week <= B.end_week AND B.start_week <= A.end_week
```

Student conflicts compare **period + week**; teacher scheduling conflicts compare **period only** (only schedules falling within the same week range count as conflicts). This rule is implemented consistently in **three places**: the available-course list, reverse conflict lookup, and enrollment validation — all in SQL.

### Withdrawal Is a Soft Delete

Withdrawal sets `enrollment.status` to `WITHDRAWN` and preserves history. Because of the unique index `uk_student_course`, re-enrolling in the same course must **reuse the existing row** (set it back to `SELECTED` and clear the old grade).

### The Frontend Never Uses innerHTML

No part of the frontend concatenates user data with `innerHTML` — course names and people's names are user input, and the JWT lives in `localStorage`, so a single XSS could exfiltrate the token. All text goes through `textContent`, and nodes are built with `createElement`. Even the `**bold**` markers in AI answers are rendered by constructing `<strong>` nodes segment by segment rather than by string concatenation.

---

## Configuration and Security

**The repository contains no real credentials.** Sensitive settings are read exclusively from environment variables and all have safely public defaults — the system runs fully with nothing configured (the AI assistant degrades to the built-in knowledge base).

```bash
cp .env.example .env    # .env is already ignored by .gitignore
```

| Variable | Default | Description |
|---|---|---|
| `AI_API_KEY` | empty | **If empty, the LLM provider is unavailable**, and the system uses only the built-in knowledge base |
| `AI_BASE_URL` | `https://api.anthropic.com` | Anthropic-protocol-compatible endpoint |
| `AI_MODEL` | `claude-sonnet-5-5` | Model name |
| `JWT_SECRET` | Public demo placeholder | **Must be replaced for production** with a long random string |
| `JWT_EXPIRE_HOURS` | `24` | Token lifetime |
| `DB_PATH` | `data/course_selection.db` | Database location |
| `DEFAULT_SEMESTER` | `2026-2027-1` | Default semester |
| `DEFAULT_PASSWORD` | `123456` | Initial password for newly created accounts |

`scripts/sanitize_check.py` is a mechanical pre-packaging gate: **the file set it scans is exactly the file set `package.py` archives**. It fails immediately on any of four problem classes — `sk-`-prefixed key literals, `api-key` assigned a non-empty value, hard-coded absolute paths, and JWT secret literals. Files such as a local `.env` and `*.db` are already excluded from the archive, so they cannot be misreported as leaks.

---

## Self-Checks and Verification

```bash
python scripts/run_queries.py       # Run demo SQL: 17 queries + execution-plan comparison + consistency self-checks
python scripts/sanitize_check.py    # Pre-packaging sanitization gate
```

`run_queries.py` includes three **consistency self-check queries** that must return empty result sets against clean data:

- whether each course's `enrolled_count` matches the actual number of enrollments,
- whether any orphaned enrollment records exist,
- whether any student has multiple active records for the same course.

The database bootstrap script also runs a capacity-consistency check on every execution.

The tests run during development (266 unit/API cases plus full browser-based integration flows for all three roles) **have code and screenshots that are not included in the package**. The process, results, and defect records are in [`docs/测试报告.md`](docs/测试报告.md); manual verification steps are in [`docs/演示脚本.md`](docs/演示脚本.md).

---

## Documentation

| Document | Contents |
|---|---|
| [`docs/设计说明.md`](docs/设计说明.md) | Requirements, architecture, database design, key algorithms, Open/Closed principle in practice |
| [`docs/测试报告.md`](docs/测试报告.md) | Unit test and browser integration test process, results, and defect records |
| [`docs/演示脚本.md`](docs/演示脚本.md) | Step-by-step script for the defense demonstration |
| [`docs/api-contract.md`](docs/api-contract.md) | All REST endpoints and error codes |

---

## Technical Differences When Migrating from the Reference Project

| Reference Project (MySQL 8) | This Project (SQLite) | Reason |
|---|---|---|
| `FIELD(a, b, c)` | `CASE WHEN` | SQLite has no `FIELD()` |
| `CONCAT(a, b)` | `a \|\| b` | In SQLite, `\|\|` performs string concatenation |
| `DATE_SUB(NOW(), INTERVAL n DAY)` | `datetime('now', '-n days')` | Different function name |
| `EXPLAIN` | `EXPLAIN QUERY PLAN` | Different execution-plan output format |
| `DECIMAL(3,1)` | `NUMERIC` + convert to `float` on read | SQLite has no fixed-point type |
| Default `REPEATABLE READ` transactions | Explicit `BEGIN IMMEDIATE` write transactions | SQLite only has a database-level write lock, so transactions must be upgraded explicitly |
| `spring.datasource` connection pool | Thread-local connections + WAL + `busy_timeout` | The standard-library `sqlite3` has no connection pool |
