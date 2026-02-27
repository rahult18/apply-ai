# Agent Context: backend

This folder contains the FastAPI backend for the Application Tracker project. It provides RESTful API endpoints for authentication, job scraping, and integration with Supabase and Google Generative AI.

**Total Application Code: ~2,900 lines**

## Structure
- `main.py` (64 lines): Entry point for the FastAPI server. Contains `build_log_config(log_file: str) -> dict` function for logging configuration. Configures logging to both console and timestamped file (in `logs/` directory as `backend_YYYYMMDD_HHMMSS.log`), then uses `uvicorn` to run the `app` from `app.api` on `0.0.0.0:8000` with hot reload enabled.
- `requirements.txt`: Python dependencies.
- `.env` / `.env.example`: Environment variables (Supabase, Google GenAI, JWT secret key, etc.).
- `app/`: Main application package.
  - `__init__.py`: Package initializer.
  - `api.py` (41 lines): Configures the FastAPI application, sets up CORS middleware (allows `http://localhost:3000`), and includes three routers (`/auth`, `/db`, `/extension`). Defines health check endpoint at `GET /` returning `{"status": "ok"}`.
  - `models.py` (~200 lines): Defines Pydantic models for request bodies and data structures:
    - `JD`: Represents a job description with fields like `job_title`, `company`, `job_description`, `required_skills`, etc.
    - `RequestBody`: Used for authentication (e.g., `email`, `password`).
    - `UpdateProfileBody`: Used for updating user profile information.
    - `ExchangeRequestBody`: Used for the extension's one-time code exchange (e.g., `one_time_code`, `install_id`).
    - `JobsIngestRequestBody`: Used for job ingestion with `job_link` and optional `dom_html`.
    - `EducationEntry`, `ExperienceEntry` (includes `location` field), `ProjectEntry`, `CertificationEntry`: Structured models for resume components.
    - `ExtractedResumeModel`: Complete resume data model including skills, summary, experience, education, certifications, and projects.
    - `ExtractedFormField`: Model for form fields extracted by the browser extension using JavaScript DOMParser. Contains `type`, `inputType`, `name`, `id`, `label`, `placeholder`, `required`, `value` (Any type), `selector`, `autocomplete`, `isCombobox`, `options` (list[dict[str, Any]] to support boolean `checked` fields), and `maxLength`.
    - `AutofillPlanRequest`: Request model for autofill plan generation with `job_application_id`, `page_url`, `dom_html`, and **`extracted_fields`** (list of ExtractedFormField objects pre-extracted by extension).
    - `AutofillPlanResponse`: Response model containing `run_id`, `status`, `plan_json`, `plan_summary`, and `resume_url` (optional signed URL for resume file uploads).
    - `AutofillEventRequest`, `AutofillFeedbackRequest`, `AutofillSubmitRequest`: Models for autofill telemetry and feedback.
    - `AutofillAgentInput`: Comprehensive input model for the autofill agent DAG, containing run metadata, application page details, job details, and user details (profile + resume).
    - `AutofillAgentOutput`: Output model from the autofill agent with status, plan_json, and plan_summary.
    - `JobStatusRequest`: Request model for job status lookup with `url` field.
    - `JobStatusResponse`: Response model containing `found`, `page_type` (jd|application|combined|unknown), `state` (jd_extracted|autofill_generated|applied), `job_application_id`, `job_title`, `company`.
  - `utils.py` (~380 lines): Contains utility functions:
    - `extract_jd`: Extracts structured job description data from raw HTML content using the LLM service.
    - `clean_content`: Cleans HTML content by removing script/style tags, JavaScript, and normalizing whitespace.
    - `normalize_url`: Normalizes URLs by removing tracking parameters, fragments, and normalizing casing and trailing slashes.
    - `infer_job_site_type`: Infers the job board type (linkedin, y-combinator, job-board, careers page) from a URL.
    - `parse_resume`: Parses a user's resume (PDF) using an LLM and updates the user's profile in the database with the extracted information. Extracts location for each experience entry.
    - `check_if_job_application_belongs_to_user`: Verifies that a job application ID belongs to a specific user.
    - `check_if_run_id_belongs_to_user`: Verifies that an autofill run ID belongs to a specific user.
    - `extract_job_url_info`: Extracts job board type, base URL, and page type from a job URL. Handles Lever (`/apply` suffix), Ashby (`/application` suffix), and Greenhouse (combined single page). Returns dict with `job_board`, `base_url`, `page_type`.
  - `dag_utils.py` (~293 lines): Contains DAG-related utilities for autofill agent:
    - **Enums**: `InputType` (text, textarea, select, radio, checkbox, date, number, email, password, file, tel, url, hidden, unknown), `AnswerAction` (autofill, suggest, skip), `RunStatus` (running, completed, failed).
    - **TypedDicts**: `FormField` (question_signature, label, input_type, required, options, selector), `FormFieldAnswer` (value, source, confidence 0.0-1.0, action), `PlanField`, `AutofillPlanJSON`, `AutofillPlanSummary`.
    - **Pydantic Models**: `LLMAnswerItem` (value, action, confidence, source), `LLMAnswersResponse` (dict of answers keyed by field signature).
    - **Constants**: `STANDARD_COUNTRIES` - Array of 195+ country names for enriching country select fields.
    - `convert_js_fields_to_form_fields`: Converts pre-extracted form fields from browser extension's JavaScript DOMParser to internal FormField format. Maps JS field properties (type, inputType, name, id, label, selector, options) to Python FormField structure. Handles deduplication by question_signature.
    - `_enrich_country_fields`: Automatically enriches select fields containing "country", "nationality", or "citizenship" keywords with a standard list of 196 countries (useful when React Select components have empty options in static DOM).
    - `build_autofill_plan`: Builds an autofill plan JSON from form fields and answers. Normalizes answer data and includes confidence scores.
    - `summarize_autofill_plan`: Summarizes an autofill plan with counts of autofilled, suggested, and skipped fields.
    - `_normalize_answer`: **Forces all actions to 'autofill'** - converts 'suggest' and 'skip' to 'autofill' to maximize field coverage. Ensures answer has valid source, confidence values clamped to 0.0-1.0. File inputs are handled separately in generate_answers_node.
  - `routes/`: API route handlers.
    - `auth.py` (118 lines): Handles user authentication:
      - `POST /auth/signup`: Registers a new user with email and password, creates Supabase auth user, inserts row into `public.users` table, and returns a session token or a message for email confirmation.
      - `POST /auth/login`: Authenticates a user with email and password, returns access_token and user info (email, id).
      - `GET /auth/me`: Retrieves current user information using a Bearer token. Fetches from `auth.users` and `public.users` tables, returns email, id, first_name, full_name, avatar_url.
    - `db.py` (311 lines): Handles database interactions related to user profiles and job applications:
      - `GET /db/get-profile`: Retrieves the user's profile information from the `users` table, including a signed URL (1 hour expiry) for their resume if available in Supabase storage. Handles multiple signed URL response formats from Supabase SDK.
      - `GET /db/get-all-applications`: Fetches all job applications for the current user from the `job_applications` table ordered by created_at DESC. Converts tuples to dictionaries for JSON response.
      - `POST /db/update-profile`: Updates the user's profile information in the `users` table. Accepts multipart form data including optional resume file upload to `user-documents` bucket (path: `resumes/{user_id}/{filename}`). Constructs dynamic UPDATE query with only provided fields. Supports `open_to_relocation` (boolean) and `resume_profile` (JSON string) fields for editable resume data. Triggers background task to parse resume using LLM. Sets resume_parse_status to "In progress" on update. Rollback: deletes uploaded file if DB update fails.
    - `extension.py` (~580 lines): Handles authentication, connection, and autofill functionality for the browser extension:
      - `POST /extension/connect/start`: Generates a one-time code (32 char urlsafe) for the authenticated user to connect the browser extension. Stores SHA256 hash in `public.extension_connect_codes` with 10-minute expiration. Returns plaintext code.
      - `POST /extension/connect/exchange`: Exchanges a one-time code and install ID for a JWT token (180 min expiry) with claims: sub (user_id), exp, iss (applyai-api), aud (applyai-extension), install_id. Marks code as used.
      - `GET /extension/me`: Retrieves user information (email, id, full_name) using the extension's JWT token. Decodes JWT with audience validation.
      - `POST /extension/jobs/ingest`: Ingests a job application. Normalizes URL to prevent duplicates, checks if job already exists (returns cached data if so). If new: fetches content from URL (if no DOM provided) or uses provided DOM, extracts JD using LLM, creates `public.job_applications` record. Returns job_application_id, url, job_title, company.
      - `POST /extension/jobs/status`: Checks job application status by URL. Uses `extract_job_url_info()` to detect job board type (Lever, Ashby, Greenhouse) and page type (jd, application, combined). Strips `/apply` or `/application` suffixes for Lever/Ashby to match base JD URL. Returns `found`, `page_type`, `state` (jd_extracted|autofill_generated|applied), `job_application_id`, `job_title`, `company`. Enables smart button display in extension popup based on current page context.
      - `POST /extension/autofill/plan`: Generates an autofill plan for a job application form. Validates ownership of job_application_id. Generates signed URL for user's resume from Supabase storage. Checks for cached completed plan by `job_application_id + page_url` (returns existing if found, ignores DOM hash changes). If new: creates `public.autofill_runs` record with status='running', assembles AutofillAgentInput with JD and user data, invokes DAG agent. File input fields are auto-assigned `value: "resume"` (bypassing LLM). Returns run_id, status, plan_json, plan_summary, resume_url.
      - `POST /extension/autofill/event`: Logs autofill events to `public.autofill_events` table for telemetry. Validates ownership of run_id. Returns {"status": "success"}.
      - `POST /extension/autofill/feedback`: Submits user feedback/corrections for autofill answers to `public.autofill_feedback` table. Validates ownership of run_id. Returns {"status": "success"}.
      - `POST /extension/autofill/submit`: Marks autofill run as 'submitted' in `public.autofill_runs`, updates corresponding job_application status to 'applied', logs 'application_submitted' event. Returns {"status": "success"}.
  - `services/`: Service layer for external integrations and agents.
    - `llm.py` (9 lines): Initializes Google Generative AI client. Model used: `gemini-2.5-flash`.
    - `supabase.py` (32 lines): Provides a `Supabase` class with `db_connection` (psycopg2 PostgreSQL connection) and `client` (Supabase SDK for auth/storage).
    - `autofill_agent_dag.py` (~398 lines): Implements the autofill agent as a LangGraph StateGraph DAG.

      **DAG Flow**: `START → initialize → extract_form_fields → generate_answers → assemble_autofill_plan → END`

      **State Definition (AutofillAgentState)**:
      - input_data, run_id, page_url, form_fields, answers (dict keyed by question_signature), plan_json, plan_summary, status (running|completed|failed), errors (list)

      **Nodes**:
      - `initialize_node`: Extracts run_id and page_url from input_data, initializes empty state.
      - `extract_form_fields_node`: Converts pre-extracted fields from browser extension's JavaScript DOMParser to internal FormField format using `dag_utils.convert_js_fields_to_form_fields`. Handles field deduplication by question_signature. Logs field labels for debugging. Error handling with graceful failures.
      - `generate_answers_node` (~250 lines, most complex): Builds context objects (user_ctx: profile fields; job_ctx: job details; resume_ctx: parsed resume). Constructs structured JSON prompt for Gemini with **mandatory autofill rules**:
        - Prompt explicitly states: "MANDATORY: Set action='autofill' for ALL fields. Never use 'skip' or 'suggest'."
        - Requires LLM to return exactly N answers (one per field) with `action='autofill'`
        - For unknown answers: still uses `action='autofill'` with `value=''` and low confidence
        - File input fields are auto-assigned `value: "resume"` (autofill) or `value: "cover_letter"` (skip) based on label matching, bypassing LLM entirely
        - Post-processes LLM response: normalizes text for option matching, performs fuzzy matching for select options, validates confidence scores (clamped 0.0-1.0), maps values to actual options
        - Missing LLM responses default to `action: "autofill"` with empty value
        - Logs action counts and field signatures by action type
      - `assemble_autofill_plan_node`: Builds final AutofillPlanJSON from form_fields + answers, generates AutofillPlanSummary statistics. Persists plan to database: updates `public.autofill_runs` with plan_json, plan_summary, status, updated_at. Sets status to "completed" or "failed" based on errors.

      **Key Features**: Pre-extracted fields from browser, LLM-powered intelligent answers, aggressive autofill strategy (never skips fields except cover letters), confidence scoring (0.0-1.0), source tracking (profile|resume|jd|llm|unknown), fuzzy option matching, graceful error handling, comprehensive logging.

## Services
- **Authentication**: User signup, login, and user info managed via Supabase's authentication service. Supports email/password and Google OAuth (configured via Supabase Auth providers). Extension authentication uses custom JWT tokens with one-time code exchange.
- **Job Ingestion**: Utilizes Google Generative AI (Gemini 2.5 Flash) to extract structured job descriptions from raw HTML content, either fetched from a URL or provided directly by the browser extension. Includes URL normalization and job site type inference.
- **Resume Parsing**: Parses uploaded PDF resumes using PyMuPDF (fitz) for text extraction and Gemini 2.5 Flash for structured data extraction. Updates user profile with parsed resume data (skills, experience, education, certifications, projects).
- **Autofill Agent**: LangGraph-based DAG that receives pre-extracted form fields from the browser extension (extracted using JavaScript DOMParser in the actual browser environment), converts them to internal format, enriches country fields automatically, generates contextual answers using LLM with user profile and resume data, and creates autofill plans. Supports telemetry, feedback collection, and submission tracking.
- **Supabase Integration**: Handles user management, profile storage, job application storage, resume storage, autofill runs, autofill events, and autofill feedback in Supabase. Direct `psycopg2` connections are used for database operations.
- **Google Generative AI Integration**: Used for job description extraction, resume parsing, and autofill answer generation with structured JSON schema responses.

## API Endpoints

### Authentication (`/auth`)
- `POST /auth/signup`: Create a new user account.
- `POST /auth/login`: Login with email and password.
- `GET /auth/me`: Get current user (requires Bearer token).

### Database Operations (`/db`)
- `GET /db/get-profile`: Get current user's profile with signed resume URL.
- `GET /db/get-all-applications`: Get all job applications for current user.
- `POST /db/update-profile`: Update current user's profile (multipart form data, includes optional resume upload).

### Extension Operations (`/extension`)
- `POST /extension/connect/start`: Generate a one-time code for extension connection.
- `POST /extension/connect/exchange`: Exchange one-time code for an extension JWT token.
- `GET /extension/me`: Get current user info using extension token.
- `POST /extension/jobs/ingest`: Ingest a job application from URL or DOM HTML.
- `POST /extension/jobs/status`: Check job application status by URL. Supports Lever/Ashby URL pattern matching (strips `/apply` or `/application` suffixes). Returns page type, application state, job details, and `run_id` (for restoring "Mark as Applied" functionality).
- `POST /extension/resume-match`: Get resume-to-job match analysis. Returns score (0-100), matched_keywords, and missing_keywords for display in extension's Resume Score tab.
- `POST /extension/autofill/plan`: Generate autofill plan for a job application form.
- `POST /extension/autofill/event`: Log autofill telemetry events.
- `POST /extension/autofill/feedback`: Submit feedback/corrections for autofill answers.
- `POST /extension/autofill/submit`: Mark autofill run as submitted and update job application status.

### Health Check
- `GET /`: Health check endpoint.

## Notes
- All environment variables are loaded from `.env` (Supabase URL/keys, Google GenAI API key, JWT secret key and algorithm).
- The backend runs on `http://0.0.0.0:8000` with auto-reload enabled.
- Logging is configured to output to both console and timestamped log files in the `logs/` directory.
- CORS is configured to allow requests from `http://localhost:3000` (Next.js frontend dev server).
- Authentication uses two token systems:
  - Supabase JWT tokens for web frontend (via `POST /auth/login`, Google OAuth, and `GET /auth/me`)
  - Custom JWT tokens for browser extension (via one-time code exchange at `POST /extension/connect/exchange` and `GET /extension/me`)
- Google OAuth is handled by Supabase Auth on the frontend; the backend receives the same Supabase JWT tokens regardless of auth method.
- The autofill agent uses LangGraph for DAG execution and Gemini 2.5 Flash for LLM-powered form field answer generation.
- Database operations use direct `psycopg2` connections for better control and transaction management.
- Resume parsing and autofill plan generation are resource-intensive operations that use LLM API calls.
- The system supports multiple job board types: LinkedIn, Y Combinator, job boards (Greenhouse, Ashby, Lever), and generic careers pages.

## Database Schema References

Tables referenced in code:
- `auth.users` - Supabase authentication (managed by Supabase)
- `public.users` - User profiles and resume data (first_name, full_name, avatar_url, resume_url, resume_parse_status, open_to_relocation, resume_profile JSONB, etc.)
- `public.job_applications` - Job postings with normalized_url and jd_dom_html
- `public.extension_connect_codes` - One-time codes for extension pairing (code_hash, expires_at, used)
- `public.autofill_runs` - Autofill execution history (dom_html_hash, plan_json, plan_summary, status)
- `public.autofill_events` - Event logs for autofill runs (run_id, event_type, payload)
- `public.autofill_feedback` - User corrections to autofill answers (run_id, question_signature, correction)
- `public.site_configs` - Site configuration data (read-only for authenticated users)
- `public.site_domain_map` - Site domain mapping (read-only for authenticated users)

### Row Level Security (RLS)

All public tables have RLS enabled with policies scoped to authenticated users:
- **users**: SELECT + UPDATE own profile (`auth.uid() = id`)
- **job_applications**: SELECT + INSERT + UPDATE own applications (`auth.uid() = user_id`)
- **extension_connect_codes**: SELECT + INSERT own codes (`auth.uid() = user_id`)
- **autofill_runs**: SELECT + INSERT + UPDATE own runs (`auth.uid() = user_id`)
- **autofill_events**: SELECT + INSERT own events (`auth.uid() = user_id`)
- **autofill_feedback**: SELECT + INSERT own feedback (`auth.uid() = user_id`)
- **site_configs**: SELECT for all authenticated users (`USING (true)`)
- **site_domain_map**: SELECT for all authenticated users (`USING (true)`)

> **Note**: RLS applies to Supabase Data API (anon/authenticated roles). Direct `psycopg2` connections (used by the backend) bypass RLS as they connect as the `postgres` superuser.

### Database Triggers

- **handle_new_user**: Trigger function on `auth.users` that automatically creates a corresponding row in `public.users` when a new user signs up. For Google OAuth users, it also extracts and stores `full_name` and `avatar_url` from the user's Google metadata (`raw_user_meta_data`).

## Dependencies (requirements.txt)

**Core Framework:**
- fastapi, uvicorn, python-multipart

**AI/ML:**
- google-genai (Gemini models)
- langgraph (DAG orchestration)
- langchain (LLM utilities)

**Database:**
- supabase (Auth + Storage SDK)
- psycopg2-binary (PostgreSQL client)
- sqlalchemy

**Data Processing:**
- pydantic (Data validation)
- fitz / pymupdf (PDF parsing)
- beautifulsoup4 (HTML parsing)
- requests, aiohttp (HTTP clients)

**Utilities:**
- python-dotenv (Environment variables)
- python-jose (JWT encoding/decoding)
- tiktoken (Token counting)
- jsonschema (JSON validation)
- tenacity (Retry logic)
- cssselect (CSS selectors)

## Environment Variables

```
# Supabase
SUPABASE_URL=
SUPABASE_KEY=

# Database (PostgreSQL direct connection)
DB_NAME=
DB_USER=
DB_PASSWORD=
DB_HOST=
DB_PORT=

# JWT/Security
SECRET_KEY=
ALGORITHM=
```
