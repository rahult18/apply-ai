# Architecture

**Analysis Date:** 2026-01-18

## Pattern Overview

**Overall:** Monorepo with Three-Tier Architecture

The application follows a three-tier architecture distributed across a monorepo with three independent subsystems:
1. **Frontend** - Next.js React application (dashboard/web UI)
2. **Backend** - FastAPI Python service (REST API + business logic)
3. **Extension** - Chrome extension (browser automation + form autofill)

**Key Characteristics:**
- Monorepo structure with separate package management per component
- API-first design with clear frontend/backend separation
- Browser extension acts as a bridge between job sites and the backend
- LLM-powered job description extraction and form autofill generation
- Supabase for authentication (via their Auth service) and PostgreSQL database access
- LangGraph DAG for orchestrating the autofill generation pipeline

## Layers

**Presentation Layer (Frontend):**
- Purpose: User-facing dashboard for managing job applications
- Location: `frontend/`
- Contains: Next.js App Router pages, React components, contexts
- Depends on: Backend API (`/auth/*`, `/db/*`)
- Used by: End users via browser

**API Layer (Backend):**
- Purpose: REST API providing authentication, data access, and AI-powered features
- Location: `backend/app/`
- Contains: FastAPI routers, Pydantic models, request/response handlers
- Depends on: Services layer, Supabase, LLM services
- Used by: Frontend, Browser Extension

**Services Layer (Backend):**
- Purpose: Business logic, external service integrations, AI pipelines
- Location: `backend/app/services/`
- Contains: Supabase client, LLM client, Autofill DAG
- Depends on: External APIs (Supabase, Google Gemini)
- Used by: API Layer (routes)

**Browser Extension:**
- Purpose: Job extraction from job posting pages, form autofill on application pages
- Location: `applyai-extension/`
- Contains: Background script, content script, popup UI, DOM extraction logic
- Depends on: Backend API (`/extension/*`)
- Used by: End users via Chrome browser

## Data Flow

**Job Application Tracking Flow:**

1. User visits a job posting page in their browser
2. Extension's popup triggers "Extract JD" action
3. Background script injects script to extract DOM HTML from the active tab
4. DOM content sent to backend `/extension/jobs/ingest` endpoint
5. Backend uses LLM (Gemini) to extract structured job details from HTML
6. Job application record created in `job_applications` table
7. Frontend dashboard displays all tracked applications from `/db/get-all-applications`

**Autofill Generation Flow:**

1. User navigates to a job application form page
2. Extension's popup triggers "Autofill" action
3. Background script extracts form fields from the page DOM using custom DOM parser
4. Form fields + DOM sent to backend `/extension/autofill/plan` endpoint
5. Backend runs LangGraph DAG:
   - `initialize_node`: Sets up state with run context
   - `extract_form_fields_node`: Converts JS-extracted fields to internal format
   - `generate_answers_node`: LLM generates answers using user profile + job context
   - `assemble_autofill_plan_node`: Builds final autofill plan JSON and summary
6. Plan returned to extension, applied to page via `chrome.scripting.executeScript`
7. Form fields filled with generated values

**Authentication Flow:**

1. User signs up/logs in via frontend (`/login`, `/signup`)
2. Frontend calls backend `/auth/signup` or `/auth/login`
3. Backend authenticates with Supabase Auth
4. JWT token returned, stored in browser cookie (`token`)
5. Frontend includes token in `Authorization: Bearer` header for subsequent requests
6. Backend validates token via `supabase.client.auth.get_user(jwt=token)`

**Extension Connection Flow:**

1. User opens extension popup, clicks "Connect"
2. Extension opens `http://localhost:3000/extension/connect` in new tab
3. Frontend requests one-time code from `/extension/connect/start` (with user's auth token)
4. One-time code displayed to user, hash stored in `extension_connect_codes` table
5. Content script forwards code to background script
6. Background script exchanges code for extension token via `/extension/connect/exchange`
7. Extension token (JWT) stored in `chrome.storage.local`, used for subsequent API calls

**State Management:**
- Frontend: React Context (`AuthContext`) for user state, component-level state via `useState`
- Backend: Stateless request handling, state stored in PostgreSQL via Supabase
- Extension: `chrome.storage.local` for extension token and session state

## Key Abstractions

**Supabase Service (`backend/app/services/supabase.py`):**
- Purpose: Encapsulates database access and Supabase Auth client
- Pattern: Singleton-like class instantiated per request (no connection pooling)
- Provides: `client` (Supabase SDK), `db_connection` (psycopg2 connection)

**LLM Service (`backend/app/services/llm.py`):**
- Purpose: Wrapper around Google Gemini AI client
- Pattern: Simple class instantiating `genai.Client()`
- Used for: Job description extraction, resume parsing, form answer generation

**Autofill DAG (`backend/app/services/autofill_agent_dag.py`):**
- Purpose: Orchestrates the multi-step autofill plan generation
- Pattern: LangGraph StateGraph with sequential node execution
- Nodes: initialize -> extract_form_fields -> generate_answers -> assemble_autofill_plan

**AuthContext (`frontend/contexts/AuthContext.tsx`):**
- Purpose: Client-side authentication state management
- Pattern: React Context with Provider pattern
- Provides: `user`, `login`, `signup`, `logout`, `loading` state

**Pydantic Models (`backend/app/models.py`):**
- Purpose: Request/response validation and serialization
- Examples: `JD`, `RequestBody`, `AutofillPlanRequest`, `AutofillAgentInput`
- Pattern: Pydantic BaseModel with type hints and optional fields

## Entry Points

**Backend Entry Point:**
- Location: `backend/main.py`
- Triggers: `python main.py` or `uvicorn app.api:app`
- Responsibilities: Configure logging, start uvicorn server on port 8000

**Frontend Entry Point:**
- Location: `frontend/app/layout.tsx` (root layout)
- Triggers: `npm run dev` or `next dev`
- Responsibilities: Wrap app in `AuthProvider`, set up global styles

**Extension Entry Point (Background):**
- Location: `applyai-extension/background.js`
- Triggers: Extension installation or browser startup
- Responsibilities: Handle messages from popup/content script, orchestrate API calls

**Extension Entry Point (Popup):**
- Location: `applyai-extension/popup/index.html` + `popup/src/`
- Triggers: User clicks extension icon
- Responsibilities: Display connection status, trigger job extraction and autofill

## Error Handling

**Strategy:** Exception-based with HTTP status codes

**Backend Patterns:**
- FastAPI `HTTPException` for API errors with status codes (401, 403, 404, 500)
- Try/catch blocks around database and external service calls
- Logging via Python `logging` module to file and console
- Pydantic validation errors automatically converted to 422 responses

**Frontend Patterns:**
- Try/catch in async functions with error state in components
- `AuthContext` handles auth errors by clearing token and redirecting
- API response checking with `response.ok` before parsing JSON

**Extension Patterns:**
- Try/catch around all message handlers and injected scripts
- Error messages propagated back via `sendResponse({ ok: false, error: msg })`
- Fallback values for missing data (e.g., `result || []`)

## Cross-Cutting Concerns

**Logging:**
- Backend: Python `logging` module, file + console handlers configured in `main.py`
- Logs stored in `backend/logs/backend_YYYYMMDD_HHMMSS.log`
- Frontend: `console.error` for client-side errors
- Extension: `console.log/error` with prefixes like `ApplyAI:`

**Validation:**
- Backend: Pydantic models validate all request bodies
- Frontend: Basic form validation in components
- Extension: Minimal validation, relies on backend

**Authentication:**
- Two token types: Supabase JWT (frontend) and custom JWT (extension)
- Frontend tokens validated via Supabase Auth SDK
- Extension tokens validated via `python-jose` JWT decode with custom secret
- Tokens passed in `Authorization: Bearer {token}` header

**CORS:**
- Backend allows `http://localhost:3000` (Next.js dev server)
- Extension requires `host_permissions` in manifest for API access

---

*Architecture analysis: 2026-01-18*
