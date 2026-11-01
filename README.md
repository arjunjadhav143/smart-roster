# Smart Roster Management System

A full-stack workforce scheduling application for multi-brand D2C operations. It uses FastAPI, SQLAlchemy and Google OR-Tools CP-SAT to generate monthly rosters from real employee, assignment, leave, calendar, and staffing-rule records.

## What is implemented

- Seeded operational dataset: 30 employees, 4 pods, 10 brands and 30 brand/process rules.
- Employee, brand, process, pod, assignment, leave and holiday persistence APIs.
- A CP-SAT roster engine that only selects qualified, assigned staff; excludes approved leave, unavailable shifts, weekly-off days and double bookings; enforces staffing and weekly-hour constraints.
- Explicit infeasibility response with affected process/date and available-versus-required staffing.
- Conflict validation for coverage shortfalls, approved-leave violations and overlapping shifts.
- Manual roster entry update followed by immediate server-side revalidation.
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

Tables are created at backend startup for a quick local evaluation, and `app.seed.seed()` seeds only an empty database. The initial Alembic revision marker is under `backend/alembic/versions`; production teams should run a generated Alembic revision against their Supabase database as part of their release pipeline. Historical roster entries retain foreign-key references, so DELETE `/employees/{id}` deactivates rather than deletes.

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

1. Employees belong to optional pods; brands own processes; `employee_assignments` is the many-to-many qualified work mapping. Rosters and daily entries remain historical records.
2. CP-SAT creates a binary employee/process/day variable and imposes coverage, qualification, leave, availability, weekly-off, single-assignment-per-day and weekly-hours constraints. It returns `INFEASIBLE` rather than publishing an invalid plan.
3. Both cases use the same assignment table: one dedicated employee may be eligible for every process, while multiple people can qualify for distinct or shared processes.
4. Approved leave removes that employee from the solver candidate set. If no backup is eligible, the API returns the dated process shortage; the recommendation endpoint ranks real eligible backups.
5. Mandatory constraints are model constraints. Preferences/weekly offs are availability inputs in this compact implementation; insufficient mandatory coverage is surfaced as an infeasible explanation.
6. Generation, validation and candidate screening are automated. A manager retains manual edits and publication control; publication is blocked by high/critical conflicts.
7. At larger scale, partition solving by pod/brand where dependencies permit, add asynchronous jobs/caching, database indexes and a queue-backed generation worker.
8. With another week, add Supabase JWT/RLS integration, complete Alembic operations, richer shift intervals and full form-based CRUD/report exports.

## Current scope notes

The API exposes the core scheduling workflow and the dashboard displays it. Supabase Auth/RLS, Excel export, role-based UI forms, full audit history and LLM explanations are documented expansion points rather than falsely simulated features. The deterministic API explanations remain the source of truth.
