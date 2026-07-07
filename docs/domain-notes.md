# Plan: Automated Timetable Generator for Ungdomsskole (v1)

## Context

Lise's school currently builds its weekly class timetable (trinn 8-10) entirely by hand in Excel, then manually re-enters the result into a 3rd-party system called Vigilo. This is time-consuming and error-prone: dozens of subjects, co-teaching pairs, split-class sessions, and whole-grade "trinnfag" blocks (valgfag, fremmedspråk) all have to be juggled by hand against hard constraints (no teacher double-booked, limited gym/hall capacity) and soft preferences (e.g. no back-to-back Musikk, Matte before lunch). The user (not Lise herself, but a colleague forwarding requirements on her behalf) wants a web app, in Python, that takes structured school-specific input (subject-hour allocations, teacher assignments, constraints) and automatically generates a valid, near-optimal timetable, since these rules vary from school to school and year to year.

This is a greenfield project — `d:\Kode\Lise` is currently empty.

**Decisions already made with the user:**
- v1 is a full web app with Google login, not a script or Excel macro.
- Input happens through a web UI (forms/tables), not raw Excel upload or config files — though Excel *export* of the result is wanted, to match their existing validate-in-Excel-then-enter-into-Vigilo workflow.
- Backend language: Python.
- The system does full **automatic** timetable generation (a solver), not just manual-entry + validation. The user can hand-adjust the generated result afterward.
- Frontend: React + TypeScript SPA against a Python API.
- Only 2 users (Lise + colleague) for now; Google login is mainly for simple auth, not a multi-tenant permission system. Can run locally or on cheap/simple hosting.
- KRØV/hall exclusivity is **school-wide**, but scoped to activities that actually use the hall — **not** all trinnfag. Valgfag uses the hall and blocks KRØV school-wide while active; fremmedspråk does **not** use the hall and must **not** block KRØV. This is modeled as a `uses_hall` flag on `Activity` (or `Subject`), not derived from `is_trinnfag`.
- Tuesday is a short day (students leave after lunch): periods 1-4 only, and **periods 2 and 3 are still split into half-hours** just like the other days — usable either as two independent half-hour sessions or combined as one 60-minute session.
- "Two periods in a row" (for Mat&Helse/K&H needing consecutive periods, Musikk avoiding them) is **ordinal** — period 3 and period 4 count as consecutive even though lunch sits between them in clock time.

## Technical approach

- **Backend**: Python + FastAPI, SQLAlchemy 2.x + Alembic, **Google OR-Tools CP-SAT** as the solver engine, Authlib for Google OAuth, openpyxl for Excel export.
- **Frontend**: React + TypeScript (Vite), TanStack Query for server state, React Hook Form + Zod for forms, types generated from FastAPI's OpenAPI schema via openapi-typescript.
- **DB**: SQLAlchemy models behind a thin repository layer so the engine is a one-line swap. SQLite for local dev. For hosted use, prefer a free managed Postgres (Neon/Supabase) over SQLite on Render/Fly — their free tiers typically have ephemeral disks that silently wipe a SQLite file on redeploy unless a persistent volume is explicitly attached.
- **Deployment shape**: single deployable — FastAPI serves the built React static bundle — avoids CORS/two-service complexity for a 2-user app.
- **Auth**: Authlib Google OAuth (authorization-code flow), verify `id_token`, check email against a small allow-list, issue a signed HttpOnly session cookie. No hosted auth provider (Auth0/Clerk) needed at this scale.
- **Build order**: data model/CRUD → solver hard constraints → soft constraints/optimization → solve API/persistence → Excel export → auth → frontend UI polish. Backend/solver correctness is front-loaded since it's the highest-risk, highest-value part; UI is deliberately last, validated against Excel export first.

## Solver design (OR-Tools CP-SAT)

**Why CP-SAT**: this is a classic NP-hard school-timetabling CSP with both hard constraints and weighted soft preferences. CP-SAT is a native, actively maintained, free Python API that handles satisfiability and weighted multi-objective optimization in one model. Problem size (~9 classes × ~15 subjects × a handful of weekly sessions ≈ a few hundred "bits" across ~64 half-hour ticks/week) is comfortably within CP-SAT's range (seconds to solve, 60s time budget cap). Rejected alternatives: `python-constraint` (too weak for this scale/optimization), OR-Tools legacy CP solver (superseded by CP-SAT), Timefold/OptaPlanner (adds a JVM dependency for no benefit in a Python-only stack).

**Grid**: enumerate the week as half-hour ticks. Mon/Wed/Thu/Fri = 6 periods × 2 ticks = 12 ticks/day. Tuesday = periods 1-4 only (short day) × 2 ticks = 8 ticks/day, **still with periods 2/3 splittable into half-hours** like other days. Only periods 2 and 3 of any day are actually independently splittable; periods 1,4,5,6 are always a whole 60-min unit, enforced as a constraint (both ticks of a non-splittable period assigned to the same bit or both empty) rather than a structural grid difference. Wall-clock times live in a separate `PeriodDefinition` config table decoupled from solver logic, which only uses ordinals — this is what makes "period 3 and 4 are consecutive despite the lunch gap" fall out naturally.

**Core modeling technique — time-indexed boolean assignment** (chosen over interval-scheduling/`NewIntervalVar`+`AddNoOverlap`, since it handles this domain's cross-cutting resource-sharing and blocking constraints more directly):
- **SessionInstance** = one concrete weekly occurrence to place, with duration in half-tick units and a resource footprint (class-group(s), teacher(s)).
- **Decision variables**: boolean `start[i, s]` per SessionInstance `i` per valid start tick `s` (domain restricted by duration/day boundaries/fixed placement rules). Constraint: `sum_s start[i,s] == 1`.
- **Occupancy**: `occ[i, t] = sum_{s <= t < s+duration_i} start[i, s]` (linear substitution, not a separate variable).
- **Resource no-overlap** (teacher, class-group): for each resource `r`, tick `t`: `sum_{i uses r} occ[i, t] <= 1`.
- **KRØV hall cap**: `sum_{i is KRØV} occ[i, t] <= 2` hard, soft penalty at 2 (prefer 1).
- **Objective**: minimize weighted sum of soft-constraint penalty booleans; weights live in data (`SolverSettings`), not hardcoded.

**Trickiest parts, modeled concretely**:
- **Co-teaching pairs** (e.g. Norsk 8B: LEN+GB together 3×/week, LEN alone 1×/week): decompose upfront into two `Activity` records (co-taught ×3, solo ×1). Each instance's teacher resource footprint is just its own leg's teachers, so shared-tick no-overlap falls out automatically for co-taught occurrences.
- **Split-class parallel sessions** (half class Mat&Helse / half class Naturfag simultaneously): one `Activity` with **two legs sharing one start-time decision variable**. Each leg contributes its own class-group/teacher to the relevant no-overlap sums; simultaneity is structural, not an extra constraint.
- **Trinnfag whole-grade blocking** (valgfag/fremmedspråk, N parallel subject-groups across a trinn's classes): same mechanism generalized to N legs sharing one start decision. "No other trinnfag for that trinn at the same time" falls out for free from the existing per-class-group no-overlap constraint — worth a code comment and a dedicated test since it's easy to assume this needs an explicit rule.
- **School-wide hall exclusivity, scoped to hall-using activities**: define `hall_active[t]` = OR over occupancy of activities flagged `uses_hall` at tick `t` (school-wide). Valgfag is `uses_hall=true`; fremmedspråk is `uses_hall=false` and must not affect this. Constrain `sum(krov_occ over ALL classes at t) + 2 * hall_active[t] <= 2` (forces KRØV to 0 school-wide only while a hall-using activity is active).
- **Half-hour adjacency** (no stranded lone 30-min slot in periods 2/3): restrict each SessionInstance's start-tick domain by construction, then add one residual linear constraint per class per day per period-pair(2,3) disallowing "exactly one of the two ticks occupied, other empty" unless the occupied tick belongs to a bit spanning the 2/3 boundary (1.5/2.5-hr subjects). Single fiddliest rule in the system — dedicate unit tests to it (two independent 0.5-hr subjects pairing up; a 90-min subject spanning the boundary; a deliberately-stranded case that must be rejected).
- **Weekly-hours → concrete sessions**: v1 does **not** auto-decompose fractional weekly hours (e.g. Norsk 3.5) into session counts/durations algorithmically — that's a human judgment call (e.g. "LEN alone for the 4th session"). Instead the user explicitly defines `Activity` records (occurrences + durations) via the UI, seeded with a sensible default (N hours → N one-hour sessions) they can edit.

## Data model

SQLAlchemy 2.x + Alembic migrations.

| Entity | Key fields | Notes |
|---|---|---|
| `SchoolYear` | id, label | Root scope for everything; supports year-over-year history |
| `PeriodDefinition` | school_year_id, day_of_week, period_number, start_time, end_time, is_splittable, is_before_lunch | Encodes the grid incl. short Tuesday, decoupled from solver ordinals |
| `Trinn` | school_year_id, level (8/9/10) | |
| `SchoolClass` | trinn_id, name ("8A") | |
| `ClassGroup` | school_class_id, label ("whole"/"half1"/"half2") | Solver's actual resource granularity; half-groups created only when a split Activity needs them |
| `Teacher` | initials, full_name | |
| `TeacherUnavailability` | teacher_id, day_of_week, period_range or all_day/half_day, school_year_id | |
| `Subject` | school_year_id, name, short_code, is_trinnfag, is_krov, uses_hall, soft-constraint applicability flags (avoid_consecutive, prefer_before_lunch, needs_consecutive_periods) | `uses_hall` drives KRØV blocking — true for valgfag, false for fremmedspråk, independent of `is_trinnfag` |
| `SubjectHourAllocation` | subject_id, trinn_id, weekly_hours (0.5 steps) | The editable UDIR-derived table |
| `Activity` | school_year_id, subject_id, activity_type (NORMAL / SPLIT_PARALLEL / TRINNFAG), duration_periods, occurrences_per_week, notes | e.g. "8B Norsk co-taught (LEN+GB), 3×/week" |
| `ActivityLeg` | activity_id, class_group_id | 1 row per participating class-group (1 for NORMAL, 2 for SPLIT_PARALLEL, N for TRINNFAG) |
| `ActivityLegTeacher` | activity_leg_id, teacher_id | Join table, supports multiple co-teachers per leg |
| `SolverSettings` | school_year_id, max/preferred concurrent KRØV, krov10_preferred_periods, fremmedspraak10_fixed_periods, soft-constraint weights | Hall exclusivity scope (school-wide, gated by `uses_hall`) is a fixed rule, not a per-year setting. Single editable row per year, tunable without code changes |
| `GeneratedTimetable` | school_year_id, created_at, solver_status, objective_value, is_active | One row per solve run |
| `TimetableSlot` | generated_timetable_id, activity_id, occurrence_index, day_of_week, start_tick, duration_ticks | Solver output; directly editable post-solve |
| `User` | google_sub, email, name | Env-var email allow-list + this table for session binding; no roles/permissions system needed |

## Backend structure

```
d:\Kode\Lise\backend\
  app\
    main.py                     # FastAPI app, CORS (dev only), routers, serves built frontend in prod
    config.py                   # pydantic-settings: DATABASE_URL, GOOGLE_CLIENT_ID/SECRET, ALLOWED_EMAILS, SESSION_SECRET
    db\
      base.py                   # Base, session factory, get_db dependency
      models\                   # school_year.py, period.py, trinn_class.py, teacher.py, subject.py, activity.py, timetable.py, user.py
      migrations\               # alembic
    schemas\                    # Pydantic request/response models
    api\
      deps.py                   # auth + db session dependencies
      routes\                   # auth.py, school_years.py, periods.py, teachers.py, subjects.py, classes.py, activities.py, constraints.py, solve.py, timetables.py
    solver\
      expand.py                 # Activity -> SessionInstance expansion
      model_builder.py          # builds CP-SAT model (time-indexed formulation)
      constraints\              # hard.py, soft.py
      solve_service.py          # orchestration: load -> build -> solve -> persist
      result_mapper.py          # CP-SAT solution -> TimetableSlot rows
      validator.py               # independent re-check of hard constraints (see Verification)
    export\
      excel_export.py           # openpyxl, one sheet per class/teacher
    auth\
      google_oauth.py            # Authlib
      session.py                 # signed session cookie (itsdangerous)
  tests\
    unit\                       # test_solver_hard_constraints.py, test_expand_activities.py, test_half_hour_adjacency.py, test_validator.py
    fixtures\ school_example_data.py   # the real example data from the school's email
    integration\                # test_api_crud.py, test_solve_endpoint.py
  alembic.ini
  pyproject.toml
```

Solve runs synchronously inside `POST /solve` with `max_time_in_seconds = 60` and parallel search workers — no job queue/websocket infra needed at this scale.

## Frontend structure

```
d:\Kode\Lise\frontend\
  src\
    main.tsx  App.tsx
    api\ client.ts  hooks\             # useSubjects, useTeachers, useActivities, useSolve, useTimetable, ...
    pages\
      LoginPage.tsx
      SubjectHoursPage.tsx             # editable subject x trinn -> hours table
      TeachersPage.tsx                  # teacher list + unavailability editor
      ActivitiesPage.tsx                # assignment-matrix / activity builder (class x subject -> legs/teachers/occurrences)
      ConstraintsPage.tsx               # soft/hard constraint weights & toggles
      SolvePage.tsx                      # trigger solve, show status/objective/infeasibility guidance
      TimetableGridPage.tsx             # main grid, per-class/per-teacher toggle
    components\
      grid\ WeekGrid.tsx  GridCell.tsx  HalfPeriodCell.tsx
      matrix\ ActivityMatrixEditor.tsx
      teacher\ TeacherUnavailabilityEditor.tsx
    types\ domain.ts                    # generated via openapi-typescript from FastAPI's OpenAPI schema
  package.json  vite.config.ts  tsconfig.json
```

Grid renders as CSS-grid: rows = periods 1-6 (Tuesday only has 1-4), columns = Mon-Fri. Periods 2/3 render as two stacked half-height sub-cells when split, collapsing to one cell for a spanning/60-min activity. Tuesday's column visually truncates after period 4 with a grayed "school day ends" band. Toggle between "by class" and "by teacher" views (teacher view doubles as a sanity check against double-booking, echoing their current manual review habit). Support inline manual editing of slots post-solve with client-triggered re-validation via the same backend validator, highlighting hard-constraint violations without blocking the edit. Use Tailwind CSS for the dense tabular UI; consult the dataviz skill when building subject color-coding.

## Phased build order

0. **Scaffolding**: FastAPI skeleton + health endpoint, Vite+React+TS skeleton, Alembic init, SQLite for local dev.
1. **Data model + CRUD** (no solver): all models/migrations/schemas/CRUD routes. Seed with the **real example data from the school's email** (UDIR hour table, 9 classes, all named teachers, and Activities covering the three tricky patterns: 8B Norsk co-teaching, 9A Mat&Helse/Naturfag split, 10th Valgfag trinnfag). This fixture becomes the primary dev dataset and automated test fixture. Verify via FastAPI's Swagger UI + integration tests; no frontend yet.
2. **Solver core, hard constraints only**: `expand.py`, `model_builder.py` with teacher/class-group no-overlap, KRØV cap, school-wide trinnfag/hall exclusivity, fixed Fremmedspråk-10-Wednesday placement, teacher unavailability, half-hour adjacency. Build the independent `validator.py` alongside. Drive via pytest against the real-data fixture; iterate via tests/CLI, no API/UI needed yet.
3. **Soft constraints & optimization**: weighted objective terms (KRØV prefer-1, 10th KRØV prefer periods 3-4, Musikk no-consecutive, Matte before lunch, Mat&Helse prefer periods 2-3-4), weights from `SolverSettings`, tuned against the fixture.
4. **Solve API + persistence**: `POST /solve` end-to-end, `GeneratedTimetable`/`TimetableSlot` persistence, graceful INFEASIBLE handling.
5. **Excel export**: openpyxl export mirroring their current sheet layout — use this as an early human-validation checkpoint (have Lise/colleague sanity-check solver output in a format they already trust) before investing in frontend polish.
6. **Auth**: Authlib Google OAuth, allow-list, session cookie, protect all routes, frontend login/guard.
7. **Frontend UI build-out**: input pages first, then solve-trigger page, then the polished grid view (half-hour rendering, short Tuesday, manual edit + re-validation, Excel export button) — deliberately last.
8. **Future/stretch (not v1)**: background job queue if solve time grows; direct Vigilo integration if an API ever surfaces; richer infeasibility diagnostics; multi-year comparison views.

## Verification

- **Independent validator** (`solver/validator.py`): a plain-Python re-implementation of every hard-constraint check (teacher/class conflicts, KRØV cap, school-wide hall exclusivity gated by `uses_hall`, fixed Fremmedspråk placement, teacher unavailability, half-hour adjacency), written separately from the CP-SAT constraint code so a modeling bug can't silently self-validate. Used both in automated tests and as a production safety net on every generated *and* manually-edited timetable.
- **Real-data fixture as primary integration test** (`test_solve_real_school_data`): full UDIR hour table, all 9 classes, all named teachers, the three tricky Activity patterns. Assert FEASIBLE/OPTIMAL within the time budget, zero validator violations, and concrete spot-checks (e.g. GB and LEN never double-booked; 10th Fremmedspråk lands in Wed periods 5-6; no tick has 3+ KRØV sessions; no KRØV anywhere while valgfag (hall-using) is active; fremmedspråk running concurrently with KRØV elsewhere is explicitly allowed and tested).
- **Property-based testing** (Hypothesis): smaller randomized-but-plausible synthetic school configs run through solver + validator to catch edge cases the fixed fixture won't reach (zero-activity classes, heavy teacher unavailability, tight KRØV capacity).
- **Assert invariants, not exact placements**: CP-SAT's parallel search can yield different equally-valid optimal solutions across runs — assert validity + objective-value-at-least-as-good-as-baseline, not exact slot assignments.
- **Negative-path coverage**: deliberately infeasible fixture variants (a teacher double-booked by construction, total hours exceeding available slots) confirm clean INFEASIBLE reporting rather than a crash or a silently broken timetable.
- **Early human validation via Excel export**: usable as soon as Phase 2/3 solver output exists, closing the loop with the school's own domain judgment before UI investment.

### Critical files
- `backend/app/solver/model_builder.py`
- `backend/app/solver/expand.py`
- `backend/app/solver/validator.py`
- `backend/app/db/models/activity.py`
- `backend/tests/fixtures/school_example_data.py`
- `frontend/src/components/grid/WeekGrid.tsx`
