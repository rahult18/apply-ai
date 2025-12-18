# Agent Context: backend

This folder contains the FastAPI backend for the Application Tracker project. It provides RESTful API endpoints for authentication, job scraping, and integration with Supabase and Google Generative AI.

## Structure
- `main.py`: Entry point for the FastAPI server. It uses `uvicorn` to run the `app` from `app.api`.
- `requirements.txt`: Python dependencies.
- `.env` / `.env.example`: Environment variables (Supabase, Google GenAI, etc.).
- `app/`: Main application package.
  - `__init__.py`: Package initializer.
  - `api.py`: Configures the FastAPI application, sets up CORS middleware, and includes all API routers. It also defines a health check endpoint at `/`.
  - `models.py`: Defines Pydantic models for request bodies and data structures:
    - `JD`: Represents a job description with fields like `job_title`, `company`, `job_description`, `required_skills`, etc.
    - `RequestBody`: Used for authentication (e.g., `email`, `password`).
    - `UpdateProfileBody`: Used for updating user profile information.
    - `ExchangeRequestBody`: Used for the extension's one-time code exchange (e.g., `one_time_code`, `install_id`).
  - `utils.py`: Contains utility functions:
    - `extract_jd`: Extracts structured job description data from raw HTML content using the LLM service.
    - `clean_content`: Cleans HTML content by removing script/style tags, JavaScript, and normalizing whitespace.
    - `normalize_url`: Normalizes URLs by removing tracking parameters, fragments, and normalizing casing and trailing slashes.
    - `parse_resume`: Parses a user's resume (PDF) using an LLM and updates the user's profile in the database with the extracted information.
  - `routes/`: API route handlers.
    - `auth.py`: Handles user authentication:
      - `POST /auth/signup`: Registers a new user with email and password, stores user in Supabase, and returns a session token or a message for email confirmation.
      - `POST /auth/login`: Authenticates a user with email and password, and returns a session token.
      - `GET /auth/me`: Retrieves current user information using a Bearer token.
    - `db.py`: Handles database interactions related to user profiles and job applications:
      - `GET /db/get-profile`: Retrieves the user's profile information from the `users` table, including a signed URL for their resume if available in Supabase storage.
      - `GET /db/get-all-applications`: Fetches all job applications for the current user from the `job_applications` table.
      - `POST /db/update-profile`: Updates the user's profile information in the `users` table.
      - `POST /db/upload-resume`: Uploads a resume file to Supabase storage for the current user.
      - `POST /db/delete-resume`: Deletes the user's resume from Supabase storage and updates the database.
      - `POST /db/create-application`: Creates a new job application entry in the `job_applications` table.
      - `POST /db/delete-application`: Deletes a job application entry by its ID.
      - `POST /db/update-application-status`: Updates the status of a job application.
      - `GET /db/get-kpi-data`: Retrieves Key Performance Indicator (KPI) data for job applications (e.g., total applications, interviews).
      - `GET /db/get-applications-over-time`: Retrieves job application data over a specified time period for charting.
      - `GET /db/get-status-distribution`: Retrieves the distribution of job application statuses.
    - `extension.py`: Handles authentication and connection for the browser extension:
      - `POST /extension/connect/start`: Generates a one-time code for the authenticated user to connect the browser extension. The code is hashed and stored with an expiration.
      - `POST /extension/connect/exchange`: Exchanges a one-time code and install ID for a JWT token specifically for the browser extension.
    - `scrape.py`: Handles job scraping functionality:
      - `POST /scrape?job_link=<url>`: Scrapes a job description from the provided URL, cleans the HTML content, extracts structured data using the LLM service, and stores the job application in the `job_applications` table for the authenticated user.
  - `services/`: Service layer for external integrations.
    - `llm.py`: Integrates with Google Generative AI for tasks like job description extraction.
    - `supabase.py`: Provides a client for interacting with Supabase, including authentication and database operations using `psycopg2` for direct database connections.

## Services
- **Authentication**: User signup, login, and user info managed via Supabase's authentication service.
- **Job Scraping**: Utilizes Google Generative AI (LLM) to extract structured job descriptions from raw HTML content.
- **Supabase Integration**: Handles user management, profile storage, job application storage, and resume storage in Supabase. Direct `psycopg2` connections are used for database operations.
- **Google Generative AI Integration**: Used primarily for intelligent extraction of job description details.

## API Endpoints
- `GET /`: Health check endpoint.
- `POST /auth/signup`: Create a new user account.
- `POST /auth/login`: Login with email and password.
- `GET /auth/me`: Get current user (requires Bearer token).
- `GET /db/get-profile`: Get current user's profile.
- `POST /db/update-profile`: Update current user's profile.
- `POST /db/upload-resume`: Upload resume for current user.
- `POST /db/delete-resume`: Delete resume for current user.
- `GET /db/get-all-applications`: Get all job applications for current user.
- `POST /db/create-application`: Create a new job application.
- `POST /db/delete-application`: Delete a job application.
- `POST /db/update-application-status`: Update the status of a job application.
- `GET /db/get-kpi-data`: Get KPI data for job applications.
- `GET /db/get-applications-over-time`: Get job application data over time.
- `GET /db/get-status-distribution`: Get distribution of job application statuses.
- `POST /extension/connect/start`: Generate a one-time code for extension connection.
- `POST /extension/connect/exchange`: Exchange one-time code for an extension token.
- `POST /scrape?job_link=<url>`: Scrape and extract job description from URL.

## Notes
- All environment variables are loaded from `.env`.
- The backend runs on `http://localhost:8000`.
- The `app.api` module sets up CORS to allow requests from `http://localhost:3000` (Next.js frontend dev server).
- No frontend or UI logic is present here; this is a backend-only folder.
- All business logic, data models, and integrations are defined in this folder.
