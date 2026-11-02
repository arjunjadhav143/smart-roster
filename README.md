# Smart Roster Management System

A full-stack workforce scheduling application for multi-brand D2C operations. It uses FastAPI, SQLAlchemy and Google OR-Tools CP-SAT to generate monthly rosters from real employee, assignment, leave, calendar, and staffing-rule records.

## What is implemented

- Seeded operational dataset: 30 employees, 4 pods, 10 brands, eight deliberate single-resource brands and two multi-resource brands. The four pod leads are real employee records.
- Employee, brand, process, pod, assignment, leave, comp-off and holiday persistence APIs, including record updates, lifecycle deactivation, leave approval/rejection/cancellation, approved comp-offs, and scoped (global or brand) holidays.
- A CP-SAT roster engine that only selects qualified, assigned staff; excludes approved leave, approved comp-offs, unavailable shifts and double bookings; enforces staffing and weekly-hour constraints.
- Explicit infeasibility response with affected process/date and available-versus-required staffing.
- Independent full-month conflict validation for every active process/date, including requirements that have no roster entry at all; coverage, approved leave, pending-leave risk, double booking, qualification, shift availability, holiday coverage and rolling weekly-hour checks.
- Monthly calendar with company, pod, brand, process and employee views, inline edit dialog and immediate server-side revalidation.
- Availability-based backup recommendations with a reason for each candidate.
- Responsive React/Vite operations dashboard that consumes the API (no frontend fixture data), roster generator, data tables, and conflict view.
- Pytest smoke coverage, health check, CORS, `.env.example`, Render and Netlify configuration.

## Architecture

`React/Vite UI -> FastAPI REST API -> SQLAlchemy -> PostgreSQL (or SQLite locally)`

The OR-Tools engine is deliberately backend-only and authoritative. The UI never claims a roster is valid; `/rosters/{id}/validate` and `/rosters/{id}/publish` enforce that decision server-side.

## Local run

Requirements: Python 3.11+ and Node 20+.

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload
```

In another terminal:

```powershell
cd frontend
npm install
Copy-Item .env.example .env
npm run dev
```

Open `http://localhost:5173`; API documentation is at `http://localhost:8000/docs`.

## Environment

`backend/.env`: `DATABASE_URL`, `SECRET_KEY`, `CORS_ORIGINS`.
Use a Supabase PostgreSQL connection string in production. Do not put Supabase service-role keys in the frontend.

`frontend/.env`: `VITE_API_URL`, pointing at the deployed API.

## Database and seeding

Tables are created at backend startup for a quick local evaluation, and `app.seed.seed()` seeds only an empty database. Historical roster entries retain foreign-key references, so DELETE `/employees/{id}` deactivates rather than deletes. Never point the local seeder at production: inspect and migrate the production schema with Alembic before release.

Holiday scope is global when `brand_id` is null and brand-specific otherwise. A brand holiday does not suppress another brand's process requirement.

## Validation and publication

`POST /rosters/{id}/validate` returns `valid`, total/critical/warning counts and persisted conflict details. It iterates the complete monthly operational matrix, rather than merely counting existing roster rows. `POST /rosters/{id}/publish` reruns that validation and rejects critical/high conflicts. `PUT /rosters/{id}/entries/{entry_id}` always revalidates after a manual change.

## API highlights

Core lifecycle endpoints are available for employees, pods, brands, processes, assignments, leaves and holidays. `GET /health` is safe for load balancers and does not reveal secrets. Interactive OpenAPI documentation is available at `/docs`.

## Tests and build

```powershell
cd backend; pytest -q
cd frontend; npm run build
```

## Deployment

- Backend: create a Render service from `backend/render.yaml`, then configure `DATABASE_URL`, `SECRET_KEY`, and the Netlify origin in `CORS_ORIGINS`.
- Frontend: deploy the `frontend` directory to Netlify; `frontend/netlify.toml` handles SPA routes. Set `VITE_API_URL` to the Render URL before building.
- Database: create a Supabase Postgres project, use its pooled connection string, and apply schema migrations. Add RLS policies when Supabase Auth is connected.

## Assessment design answers

### 1. How did you model the operational relationships?

Employees optionally belong to a pod, and a pod can have an employee as its lead. Brands own one or more processes. `employee_assignments` is the important many-to-many table: it records which employees are qualified to work each process, rather than assuming an employee can work every process for a brand. A monthly roster is a historical parent record with daily roster entries, so subsequent staffing changes do not rewrite the history of an already generated plan.

### 2. How does the system generate and validate a roster?

The generator uses OR-Tools CP-SAT. It creates a decision variable for each eligible employee, process, and required date, then requires minimum coverage while enforcing qualification, approved leave, comp-offs, shift availability, one assignment per employee per day, and rolling weekly-hour limits. Weekly offs are optimized as preferences after required coverage. Validation independently walks the entire process/date matrix, including dates with no roster row, and records coverage, leave, qualification, availability, double-booking, holiday, and hours conflicts. A roster cannot be published while critical or high conflicts exist.

### 3. How are single-resource and multi-resource brands different?

They use the same data model instead of separate code paths. A single-resource brand has one qualified assignment that can cover its process or processes. A multi-resource brand has several assignments, which may be to separate processes or to the same process for shared coverage. The sample data deliberately includes both patterns, and `minimum_staff` lets a process require more than one person.

### 4. What happens when a sole owner is unavailable on a required day?

An approved leave or comp-off removes that employee from the solver's candidate set. The engine either selects another qualified, available assignee or returns an infeasible result that names the date, brand, process, required headcount, and available headcount. For a generated roster that later changes, validation raises a coverage conflict and the roster editor can request ranked backup candidates for that exact process and date.

### 5. How are conflicting requirements and insufficient staffing handled?

Coverage, leave, comp-off, availability, qualification, no double booking, and hour limits are mandatory. The engine never silently produces an invalid plan to satisfy a preference. If mandatory rules cannot all be met, it reports infeasibility; if a manual change introduces a problem, validation persists a clear conflict with a suggested next step. Weekly-off preferences are intentionally softer than contractual coverage requirements.

### 6. What is automated and what remains under human control?

Generation, conflict detection, coverage checks, backup screening, CSV export, and revalidation after manual roster edits are automated. Operations managers retain control of employee and assignment management, leave approval, comp-offs, manual schedule edits, and final publication. This separation keeps the system fast and consistent without hiding operational exceptions or policy decisions behind automation.

### 7. What would change at double the team and brand count?

I would move generation to queue-backed background jobs, partition solves by pod or brand when there are no cross-boundary assignments, cache read-heavy roster views, and add database indexes around assignments, work dates, leaves, and conflicts. I would also replace startup schema creation with fully reviewed Alembic migrations and add observability for solver duration and infeasibility rates.

### 8. What would you improve with one additional week?

My first priority would be authentication and role-based access with Supabase JWT verification and RLS, followed by a complete audit trail for roster and approval decisions. I would then add automatic draft regeneration after approved availability changes, in-app notifications for published-roster changes, and a comparison view that lets an operations manager review alternative feasible plans before choosing one.

## Current scope notes

The API exposes the core scheduling workflow and the dashboard displays it. Supabase Auth/RLS, full audit history, automatic regeneration, notifications, and process-scoped/region-scoped holidays are not yet implemented; they are deliberately not represented as complete. The deterministic API explanations remain the source of truth.
