# Agent Context: backend

This folder contains the FastAPI backend for the Application Tracker project. It provides RESTful API endpoints for authentication, job scraping, and integration with Supabase and Google Generative AI.

## Structure
- `main.py`: Entry point for the FastAPI server
- `requirements.txt`: Python dependencies
- `.env` / `.env.example`: Environment variables (Supabase, Google GenAI, etc.)
- `app/`: Main application package
  - `__init__.py`: Package initializer
  - `api.py`: API setup and routing
  - `models.py`: Data models (likely Pydantic models for requests/responses)
  - `utils.py`: Utility functions
  - `routes/`: API route handlers
    - `auth.py`: Authentication endpoints (signup, login, user info)
    - `db.py`: Database-related endpoints or helpers
    - `scrape.py`: Job scraping endpoints
    - `__init__.py`: Route package initializer
  - `services/`: Service layer
    - `llm.py`: Logic for Google Generative AI integration
    - `supabase.py`: Logic for Supabase integration
    - `__init__.py`: Service package initializer

## Services
- **Authentication**: User signup, login, and user info (Supabase-based)
- **Job Scraping**: Scrape and extract job descriptions from URLs using AI
- **Supabase Integration**: User management and database operations
- **Google Generative AI Integration**: For job description extraction

## API Endpoints
- `POST /auth/signup`: Create a new user account
- `POST /auth/login`: Login with email and password
- `GET /auth/me`: Get current user (requires Bearer token)
- `POST /scrape?job_link=<url>`: Scrape and extract job description from URL

## Notes
- All environment variables are loaded from `.env`
- The backend runs on `http://localhost:8000`
- No frontend or UI logic is present here; this is a backend-only folder
- All business logic, data models, and integrations are defined in this folder
