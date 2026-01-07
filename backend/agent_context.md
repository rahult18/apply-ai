# Agent Context: backend

This folder contains the FastAPI backend for the Application Tracker project. It provides RESTful API endpoints for authentication, job scraping, and integration with Supabase and Google Generative AI.

## Structure
- `main.py`: Entry point for the FastAPI server. Configures logging to both console and file (in `logs/` directory with timestamps), then uses `uvicorn` to run the `app` from `app.api` on `0.0.0.0:8000`.
- `requirements.txt`: Python dependencies.
- `.env` / `.env.example`: Environment variables (Supabase, Google GenAI, JWT secret key, etc.).
- `app/`: Main application package.
  - `__init__.py`: Package initializer.
  - `api.py`: Configures the FastAPI application, sets up CORS middleware (allows `http://localhost:3000`), and includes all API routers. It also defines a health check endpoint at `/`.
  - `models.py`: Defines Pydantic models for request bodies and data structures:
    - `JD`: Represents a job description with fields like `job_title`, `company`, `job_description`, `required_skills`, etc.
    - `RequestBody`: Used for authentication (e.g., `email`, `password`).
    - `UpdateProfileBody`: Used for updating user profile information.
    - `ExchangeRequestBody`: Used for the extension's one-time code exchange (e.g., `one_time_code`, `install_id`).
    - `JobsIngestRequestBody`: Used for job ingestion with `job_link` and optional `dom_html`.
    - `EducationEntry`, `ExperienceEntry`, `ProjectEntry`, `CertificationEntry`: Structured models for resume components.
    - `ExtractedResumeModel`: Complete resume data model including skills, summary, experience, education, certifications, and projects.
    - `AutofillPlanRequest`: Request model for autofill plan generation with `job_application_id`, `page_url`, and `dom_html`.
    - `AutofillPlanResponse`: Response model containing `run_id`, `status`, `plan_json`, and `plan_summary`.
    - `AutofillEventRequest`, `AutofillFeedbackRequest`, `AutofillSubmitRequest`: Models for autofill telemetry and feedback.
    - `AutofillAgentInput`: Comprehensive input model for the autofill agent DAG, containing job details, user profile, resume data, and DOM HTML.
    - `AutofillAgentOutput`: Output model from the autofill agent with status and plan information.
  - `utils.py`: Contains utility functions:
    - `extract_jd`: Extracts structured job description data from raw HTML content using the LLM service.
    - `clean_content`: Cleans HTML content by removing script/style tags, JavaScript, and normalizing whitespace.
    - `normalize_url`: Normalizes URLs by removing tracking parameters, fragments, and normalizing casing and trailing slashes.
    - `infer_job_site_type`: Infers the job board type (linkedin, y-combinator, job-board, careers page) from a URL.
    - `parse_resume`: Parses a user's resume (PDF) using an LLM and updates the user's profile in the database with the extracted information.
    - `check_if_job_application_belongs_to_user`: Verifies that a job application ID belongs to a specific user.
    - `check_if_run_id_belongs_to_user`: Verifies that an autofill run ID belongs to a specific user.
  - `dag_utils.py`: Contains DAG-related utilities for autofill agent:
    - Type definitions: `FormField`, `FormFieldAnswer`, `PlanField`, `AutofillPlanJSON`, `AutofillPlanSummary`, `LLMAnswerItem`, `LLMAnswersResponse`.
    - `extract_form_fields_from_dom_html`: Parses DOM HTML to extract form fields, handles native inputs, textareas, selects, and ARIA combobox widgets (React-Select).
    - `build_autofill_plan`: Builds an autofill plan JSON from form fields and answers.
    - `summarize_autofill_plan`: Summarizes an autofill plan with counts of autofilled, suggested, and skipped fields.
    - Helper functions for label extraction, requirement detection, selector generation, and option matching.
  - `routes/`: API route handlers.
    - `auth.py`: Handles user authentication:
      - `POST /auth/signup`: Registers a new user with email and password, stores user in Supabase, and returns a session token or a message for email confirmation.
      - `POST /auth/login`: Authenticates a user with email and password, and returns a session token.
      - `GET /auth/me`: Retrieves current user information using a Bearer token.
    - `db.py`: Handles database interactions related to user profiles and job applications:
      - `GET /db/get-profile`: Retrieves the user's profile information from the `users` table, including a signed URL for their resume if available in Supabase storage.
      - `GET /db/get-all-applications`: Fetches all job applications for the current user from the `job_applications` table.
      - `POST /db/update-profile`: Updates the user's profile information in the `users` table. Accepts multipart form data including optional resume file upload. Triggers background task to parse resume using LLM.
    - `extension.py`: Handles authentication, connection, and autofill functionality for the browser extension:
      - `POST /extension/connect/start`: Generates a one-time code for the authenticated user to connect the browser extension. The code is hashed and stored with an expiration.
      - `POST /extension/connect/exchange`: Exchanges a one-time code and install ID for a JWT token specifically for the browser extension.
      - `GET /extension/me`: Retrieves user information (email, id, full_name) using the extension's JWT token.
      - `POST /extension/jobs/ingest`: Ingests a job application either by scraping a provided `job_link` or by extracting information from `dom_html` provided by the extension. It cleans the content, extracts structured data using the LLM service, normalizes the URL, infers job site type, and stores the job application in the `job_applications` table for the authenticated user.
      - `POST /extension/autofill/plan`: Generates an autofill plan for a job application form. Checks for existing plans with matching DOM hash, or creates a new autofill run and invokes the DAG agent to extract form fields, generate answers using LLM with user/job/resume context, and assemble the autofill plan.
      - `POST /extension/autofill/event`: Logs autofill events (user interactions, errors, etc.) to the `autofill_events` table for telemetry.
      - `POST /extension/autofill/feedback`: Submits user feedback/corrections for autofill answers to the `autofill_feedback` table for model improvement.
      - `POST /extension/autofill/submit`: Marks an autofill run as 'submitted' and updates the corresponding job application status to 'applied'.
  - `services/`: Service layer for external integrations and agents.
    - `llm.py`: Integrates with Google Generative AI (Gemini 2.5 Flash) for tasks like job description extraction, resume parsing, and autofill answer generation.
    - `supabase.py`: Provides a client for interacting with Supabase, including authentication and database operations using `psycopg2` for direct database connections.
    - `autofill_agent_dag.py`: Implements the autofill agent as a LangGraph DAG with four nodes:
      - `initialize_node`: Initializes the DAG state with input data.
      - `extract_form_fields_node`: Extracts form fields from DOM HTML using `dag_utils.extract_form_fields_from_dom_html`.
      - `generate_answers_node`: Generates answers for form fields using Gemini 2.5 Flash with structured JSON output. Sends user context, job context, resume profile, and form field specifications to LLM. Performs option matching for select/radio/checkbox fields.
      - `assemble_autofill_plan_node`: Builds the final autofill plan JSON and summary, then updates the `autofill_runs` table in the database.

## Services
- **Authentication**: User signup, login, and user info managed via Supabase's authentication service. Extension authentication uses custom JWT tokens with one-time code exchange.
- **Job Ingestion**: Utilizes Google Generative AI (Gemini 2.5 Flash) to extract structured job descriptions from raw HTML content, either fetched from a URL or provided directly by the browser extension. Includes URL normalization and job site type inference.
- **Resume Parsing**: Parses uploaded PDF resumes using PyMuPDF (fitz) for text extraction and Gemini 2.5 Flash for structured data extraction. Updates user profile with parsed resume data (skills, experience, education, certifications, projects).
- **Autofill Agent**: LangGraph-based DAG that extracts form fields from DOM HTML, generates contextual answers using LLM with user profile and resume data, and creates autofill plans. Supports telemetry, feedback collection, and submission tracking.
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
  - Supabase JWT tokens for web frontend (via `POST /auth/login` and `GET /auth/me`)
  - Custom JWT tokens for browser extension (via one-time code exchange at `POST /extension/connect/exchange` and `GET /extension/me`)
- The autofill agent uses LangGraph for DAG execution and Gemini 2.5 Flash for LLM-powered form field answer generation.
- Database operations use direct `psycopg2` connections for better control and transaction management.
- Resume parsing and autofill plan generation are resource-intensive operations that use LLM API calls.
- The system supports multiple job board types: LinkedIn, Y Combinator, job boards (Greenhouse, Ashby, Lever), and generic careers pages.
