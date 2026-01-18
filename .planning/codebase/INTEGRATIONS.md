# External Integrations

**Analysis Date:** 2026-01-18

## APIs & External Services

**Google Generative AI (Gemini):**
- Purpose: LLM for job description extraction and form autofill answer generation
- SDK: `google-genai` Python package
- Client: `backend/app/services/llm.py` - `genai.Client()`
- Auth: `GOOGLE_GENAI_API_KEY` env var
- Usage:
  - Extract job details from HTML/text (`backend/app/utils.py`)
  - Generate form field answers via LangGraph DAG (`backend/app/services/autofill_agent_dag.py`)

**Supabase:**
- Purpose: Backend-as-a-Service (Auth + Database)
- SDK: `supabase` Python client
- Client: `backend/app/services/supabase.py` - `Supabase` class
- Auth: `SUPABASE_URL` + `SUPABASE_KEY` env vars

## Data Storage

**Primary Database - PostgreSQL (via Supabase):**
- Connection method 1: Supabase Python client (for auth operations)
- Connection method 2: Direct psycopg2 connection (for data queries)
- Connection vars: `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`
- Schema file: `supabase_schema.sql` (reference only)

**Database Tables:**
| Table | Purpose |
|-------|---------|
| `auth.users` | Supabase auth users (managed by Supabase) |
| `public.users` | User profiles, resume data, preferences |
| `public.job_applications` | Saved job postings with extracted details |
| `public.autofill_runs` | Autofill session tracking per page |
| `public.autofill_events` | Autofill action logging |
| `public.autofill_feedback` | User corrections to autofill |
| `public.extension_connect_codes` | One-time codes for extension auth |
| `public.site_configs` | Site-specific configuration |
| `public.site_domain_map` | Domain to site key mapping |

**File Storage:**
- Resume files: Stored as text in `public.users.resume` column
- Resume parsing: PDF extracted via PyMuPDF, stored in `resume_text` and `resume_profile` (JSON)

**Caching:**
- Autofill plan caching: Plans cached by `dom_html_hash` + `page_url` in `autofill_runs` table
- No Redis/Memcached detected

## Authentication & Identity

**Supabase Auth:**
- Email/password authentication
- JWT tokens issued by Supabase
- Frontend: Stores token in localStorage (via custom context)
- Backend routes: `backend/app/routes/auth.py`

**Extension Authentication:**
- Custom JWT tokens issued by backend
- Flow:
  1. User logs into web app
  2. Web app generates one-time code via `/extension/connect/start`
  3. Extension exchanges code for extension-specific JWT via `/extension/connect/exchange`
  4. Extension JWT includes: `sub` (user_id), `iss` (applyai-api), `aud` (applyai-extension)
- Token storage: Chrome `chrome.storage.local`
- Auth middleware: `backend/app/routes/extension.py` - JWT decode with `python-jose`

**Token Details:**
- Supabase tokens: Managed by Supabase Auth
- Extension tokens: Custom JWT, 180-minute expiry
- Signing: `SECRET_KEY` env var, algorithm from `ALGORITHM` env var

## Monitoring & Observability

**Error Tracking:**
- None configured (no Sentry, Bugsnag, etc. detected)

**Logging:**
- Backend: Python `logging` module
- Log files: `backend/logs/backend_{timestamp}.log`
- Log format: `%(asctime)s - %(name)s - %(levelname)s - %(message)s`
- Uvicorn access logs captured
- Frontend: None beyond console

## CI/CD & Deployment

**Hosting:**
- Not configured (local development only)
- Frontend ready for: Vercel, Netlify, or similar
- Backend ready for: Any Python host (Railway, Render, etc.)

**CI Pipeline:**
- None detected (no `.github/workflows`, no `Jenkinsfile`, etc.)

## Environment Configuration

**Required Environment Variables:**

Backend (`backend/.env`):
```
SUPABASE_URL=<supabase_project_url>
SUPABASE_KEY=<supabase_anon_key>
GOOGLE_GENAI_API_KEY=<google_ai_api_key>
DB_NAME=<database_name>
DB_USER=<database_user>
DB_PASSWORD=<database_password>
DB_HOST=<database_host>
DB_PORT=<database_port>
SECRET_KEY=<jwt_secret>
ALGORITHM=<jwt_algorithm>
```

Frontend (`frontend/.env.local`):
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

**Secrets Location:**
- Development: `.env` files (gitignored)
- Production: Platform-specific secret management needed

## Webhooks & Callbacks

**Incoming:**
- None detected

**Outgoing:**
- None detected

## Browser Extension Integration

**Extension API Communication:**
- Base URL: `http://localhost:8000` (hardcoded in `background.js`)
- Content script: Injects on `http://localhost:3000/extension/connect*`

**Extension Endpoints:**
| Endpoint | Purpose |
|----------|---------|
| `POST /extension/connect/start` | Generate one-time code for extension |
| `POST /extension/connect/exchange` | Exchange code for extension JWT |
| `GET /extension/me` | Get current user via extension token |
| `POST /extension/jobs/ingest` | Extract and save job from URL |
| `POST /extension/autofill/plan` | Generate autofill plan for form |
| `POST /extension/autofill/event` | Log autofill events |
| `POST /extension/autofill/feedback` | Submit user corrections |
| `POST /extension/autofill/submit` | Mark application as submitted |

**Extension Permissions:**
- `storage` - Local storage for tokens
- `tabs` - Access active tab info
- `activeTab` - Execute scripts in active tab
- `scripting` - Inject DOM extraction scripts
- Host permissions: `localhost:3000/*`, `localhost:8000/*`

## CORS Configuration

**Backend CORS:**
- Allowed origins: `http://localhost:3000` (Next.js dev server only)
- Credentials: Allowed
- Methods: All (`*`)
- Headers: All (`*`)
- Config location: `backend/app/api.py`

## AI/ML Pipeline

**LangGraph DAG:**
- Location: `backend/app/services/autofill_agent_dag.py`
- Nodes:
  1. `initialize` - Setup state from input
  2. `extract_form_fields` - Convert JS-extracted fields to internal format
  3. `generate_answers` - LLM generates form answers
  4. `assemble_autofill_plan` - Build final plan JSON
- State: `AutofillAgentState` TypedDict
- Persistence: Plan stored in `autofill_runs` table

**Form Field Extraction:**
- Browser-side: DOM parsing in `background.js` (`extractFormFieldsFromTab`)
- Extracts: inputs, textareas, selects, comboboxes (React Select), radio groups, checkboxes
- Handles: Dynamic React Select dropdowns via click simulation

---

*Integration audit: 2026-01-18*
