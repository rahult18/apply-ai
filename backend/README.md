# ApplyAI - Backend

FastAPI backend for the ApplyAI application tracker. Provides REST API endpoints for authentication, job extraction, autofill plan generation, resume parsing, job discovery, and browser extension integration.

**Total Application Code: ~4,000 lines**

## Setup

1. Create and activate a virtual environment:
```bash
python -m venv ../venv
source ../venv/bin/activate  # On Windows: ..\venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create `.env` file:
```bash
cp .env.example .env
```

4. Update `.env` with your credentials (see [Environment Variables](#environment-variables))

5. Run the server:
```bash
python main.py
```

The API will be available at `http://localhost:8000`

## Environment Variables

```env
# Supabase
SUPABASE_URL=
SUPABASE_KEY=

# PostgreSQL direct connection
DB_NAME=
DB_USER=
DB_PASSWORD=
DB_HOST=
DB_PORT=

# JWT / Security
SECRET_KEY=
ALGORITHM=

# Google Generative AI
GOOGLE_GENAI_API_KEY=

# Job Discovery
SERPER_API_KEY=       # Serper.dev API key for SERP-based job board discovery
INTERNAL_API_KEY=     # API key for internal-only endpoints (/discovery, /sync)
```

## Project Structure

```
backend/
├── main.py                         # Entry point — uvicorn server + logging config
├── requirements.txt
├── .env / .env.example
└── app/
    ├── api.py                      # FastAPI app, CORS, router registration
    ├── models.py                   # Pydantic request/response models
    ├── utils.py                    # Shared utilities (JD extraction, URL parsing, resume parsing)
    ├── dag_utils.py                # Autofill DAG helpers (FormField types, plan building, normalization)
    ├── repositories/               # Database repository layer
    │   ├── base.py                 # Cursor context manager + dynamic query builder
    │   ├── users.py                # UserRepository
    │   ├── job_applications.py     # JobApplicationRepository
    │   └── autofill.py             # AutofillRepository (runs, events, feedback, connect codes)
    ├── routes/                     # API route handlers
    │   ├── auth.py                 # /auth — signup, login, me
    │   ├── db.py                   # /db — profile, applications, resume upload
    │   ├── extension.py            # /extension — connect, ingest, status, autofill, resume match
    │   ├── discovery.py            # /discovery — SERP-based job board discovery (internal)
    │   ├── sync.py                 # /sync — job syncing from discovered boards (internal)
    │   └── jobs.py                 # /jobs — public job listing with search and filters
    └── services/
        ├── llm.py                  # Gemini 2.5 Flash client
        ├── supabase.py             # Supabase SDK client + psycopg2 connection
        ├── http_client.py          # Shared aiohttp client with exponential backoff retry
        ├── serper.py               # Serper.dev SERP client for job board URL discovery
        ├── autofill_agent_dag.py   # LangGraph StateGraph DAG for autofill plan generation
        └── job_providers/          # Job board API clients
            ├── base.py             # Abstract provider interface
            ├── ashby.py            # Ashby API client
            ├── lever.py            # Lever API client
            └── greenhouse.py       # Greenhouse API client
```

## API Endpoints

### Authentication (`/auth`)
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/auth/signup` | Register with email and password |
| `POST` | `/auth/login` | Login and receive access token |
| `GET` | `/auth/me` | Get current user info (requires Bearer token) |

### Database Operations (`/db`)
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/db/get-profile` | Get user profile with signed resume URL (1hr expiry) |
| `GET` | `/db/get-all-applications` | Get all job applications for user |
| `POST` | `/db/update-profile` | Update profile (multipart/form-data, optional resume upload) |

### Extension Operations (`/extension`)
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/extension/connect/start` | Generate one-time code for extension pairing |
| `POST` | `/extension/connect/exchange` | Exchange one-time code + install ID for JWT token |
| `GET` | `/extension/me` | Validate extension JWT and return user info |
| `POST` | `/extension/jobs/ingest` | Ingest job posting from URL or provided DOM HTML |
| `POST` | `/extension/jobs/status` | Check job status by current tab URL |
| `POST` | `/extension/resume-match` | Get resume-to-job match score and keywords |
| `POST` | `/extension/autofill/plan` | Generate autofill plan for an application form |
| `POST` | `/extension/autofill/event` | Log autofill telemetry event |
| `POST` | `/extension/autofill/feedback` | Submit correction for an autofill answer |
| `POST` | `/extension/autofill/submit` | Mark autofill run as submitted; update job status to applied |

### Job Discovery (`/discovery`, `/sync`, `/jobs`)
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/discovery/run` | `X-Internal-API-Key` | Discover job boards via Serper.dev SERP search |
| `POST` | `/sync/run` | `X-Internal-API-Key` | Sync jobs from discovered boards |
| `GET` | `/jobs` | None | List discovered jobs with search and filters |

### Health Check
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Returns `{"status": "ok"}` |

## Key Services

### Autofill Agent DAG (`autofill_agent_dag.py`)
LangGraph `StateGraph` DAG with four nodes:

```
START → initialize → extract_form_fields → generate_answers → assemble_autofill_plan → END
```

- **`initialize`**: Extracts run metadata from input
- **`extract_form_fields`**: Converts pre-extracted browser fields (JS DOMParser format) to internal `FormField` format; deduplicates by `question_signature`; enriches country/nationality fields with 196 standard countries
- **`generate_answers`**: Builds user/job/resume context; constructs structured JSON prompt for Gemini; enforces `action='autofill'` for all fields (never skips except cover letter file inputs); performs fuzzy option matching; clamps confidence scores 0.0–1.0
- **`assemble_autofill_plan`**: Builds `AutofillPlanJSON`, generates summary statistics, persists plan to `autofill_runs` table

**Autofill strategy**: LLM is explicitly instructed to always set `action='autofill'`. For unknown answers, it uses `value=''` with low confidence rather than skipping. File inputs are handled separately — resume → `value: "resume"`, cover letter → `action: skip`.

### Resume Parsing (`utils.py → parse_resume`)
Extracts text from uploaded PDF using PyMuPDF, then sends to Gemini for structured extraction (skills, experience with location, education, certifications, projects). Updates `public.users.resume_profile` JSONB column.

### Job Ingestion (`extension.py → POST /extension/jobs/ingest`)
Normalizes URL to prevent duplicates, checks for existing record, fetches DOM if not provided, extracts structured JD via Gemini (`extract_jd`), creates `job_applications` record.

### Plan Caching (`extension.py → POST /extension/autofill/plan`)
Returns existing completed plan for the same `job_application_id + page_url` pair without re-running the DAG or re-charging LLM tokens.

### Job Board Discovery (Two-Phase)
1. **Discovery** (`/discovery/run`): SERP-searches Google for Ashby/Lever/Greenhouse board URLs; parses board identifiers; upserts into `company_boards`
2. **Sync** (`/sync/run`): Calls each provider's public API, deduplicates by `(board_id, external_id)`, updates `discovered_jobs`. Auto-deactivates boards after 5 consecutive failures.

## Authentication

Two token systems run in parallel:

| Context | Mechanism | Endpoint |
|---------|-----------|----------|
| Web frontend | Supabase JWT (email/password or Google OAuth) | `POST /auth/login` or Supabase OAuth flow |
| Browser extension | Custom JWT (7-day expiry, `aud: applyai-extension`) | `POST /extension/connect/exchange` |

Extension JWTs are issued after a one-time code (32-char urlsafe, SHA256-hashed, 10-min expiry) is exchanged from the frontend connection page.

## Database

Direct `psycopg2` connections are used for all database operations (bypasses Supabase RLS — backend connects as `postgres` superuser). The Supabase SDK is used only for auth and storage operations.

### Tables

| Table | Description |
|-------|-------------|
| `auth.users` | Supabase-managed auth users |
| `public.users` | User profiles (name, resume, resume_profile JSONB, etc.) |
| `public.job_applications` | Extracted job postings per user |
| `public.extension_connect_codes` | One-time codes for extension pairing |
| `public.autofill_runs` | Autofill execution history with plan JSON |
| `public.autofill_events` | Telemetry events per run |
| `public.autofill_feedback` | User corrections per question_signature |
| `public.company_boards` | Discovered job boards (provider + board_identifier) |
| `public.discovered_jobs` | Jobs fetched from boards with full-text search vector |

### Database Trigger
`handle_new_user` — fires on `auth.users` insert; creates `public.users` row automatically. For Google OAuth users, extracts `full_name` and `avatar_url` from `raw_user_meta_data`.

## Tech Stack

- **FastAPI** + Uvicorn (hot reload enabled)
- **LangGraph** — DAG orchestration for autofill agent
- **Google Generative AI** — Gemini 2.5 Flash (JD extraction, resume parsing, autofill answers)
- **Supabase** — Auth + Storage SDK
- **psycopg2-binary** — Direct PostgreSQL connection
- **PyMuPDF (fitz)** — PDF text extraction
- **BeautifulSoup4** — HTML parsing and cleaning
- **python-jose** — JWT encoding/decoding
- **aiohttp** — Async HTTP with exponential backoff retry (1s → 2s → 4s → 8s → 16s)
- **Serper.dev** — SERP API for job board discovery
- **python-dotenv**, **pydantic**, **tenacity**, **tiktoken**

## Logging

On startup, `main.py` configures logging to:
- **Console** (stdout)
- **Timestamped file** in `logs/backend_YYYYMMDD_HHMMSS.log`

## CORS

Configured to allow requests from `http://localhost:3000` (Next.js frontend dev server).
