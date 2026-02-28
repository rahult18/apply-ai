# ApplyAI - Application Tracker

A full-stack platform for tracking job applications with AI-powered job extraction, autofill, and resume matching.

## Project Structure

This is a monorepo containing the backend, frontend, and browser extension:

```
apply-ai/
├── backend/              # FastAPI REST API
├── frontend/             # Next.js web application
├── applyai-extension/    # Chrome browser extension
└── venv/                 # Python virtual environment (not committed)
```

## Prerequisites

- Python 3.13+
- Node.js 18+
- Supabase account and project
- Google Generative AI API key (Gemini 2.5 Flash)

## Quick Start

### Backend Setup

1. Navigate to the backend directory:
```bash
cd backend
```

2. Create a virtual environment (if not already created):
```bash
python -m venv ../venv
source ../venv/bin/activate  # On Windows: ..\venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create `.env` file in the `backend/` directory:
```bash
cp .env.example .env
```

5. Update `.env` with your credentials:
   - `SUPABASE_URL` - Your Supabase project URL
   - `SUPABASE_KEY` - Your Supabase anon/service key
   - `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` - PostgreSQL direct connection
   - `GOOGLE_GENAI_API_KEY` - Your Google Generative AI API key
   - `SECRET_KEY`, `ALGORITHM` - JWT configuration
   - `SERPER_API_KEY` - Serper.dev API key for job discovery
   - `INTERNAL_API_KEY` - API key for internal endpoints

6. Run the FastAPI server:
```bash
python main.py
```

The backend will be available at `http://localhost:8000`

### Frontend Setup

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Create `.env.local` file:
```bash
cp .env.local.example .env.local
```

4. Update `.env.local`:
   - `NEXT_PUBLIC_API_URL` - Backend API URL (default: `http://localhost:8000`)
   - `NEXT_PUBLIC_SUPABASE_URL` - Your Supabase project URL
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY` - Your Supabase anon key

5. Run the development server:
```bash
npm run dev
```

The frontend will be available at `http://localhost:3000`

### Browser Extension Setup

1. Navigate to the extension directory:
```bash
cd applyai-extension
```

2. Install dependencies:
```bash
npm install
```

3. Build the extension:
```bash
npm run build
```

4. Load in Chrome:
   - Go to `chrome://extensions/`
   - Enable Developer mode
   - Click "Load unpacked" and select the `dist/` folder

## Features

### Backend (FastAPI)
- RESTful API for authentication (email/password and Google OAuth via Supabase)
- AI-powered job description extraction using Gemini 2.5 Flash
- LangGraph DAG-based autofill agent with intelligent form field answer generation
- Resume parsing from PDF using PyMuPDF and Gemini
- Resume-to-job match analysis (score, matched/missing keywords)
- Job board discovery via Serper.dev SERP search (Ashby, Lever, Greenhouse)
- Job syncing from discovered boards with deduplication and failure tracking
- Plan caching to avoid redundant autofill generation
- Supabase integration for auth, storage, and database

### Frontend (Next.js)
- User authentication (email/password and Google OAuth)
- Dashboard with KPI cards and charts (status distribution, applications over time)
- Applications table with search, sort, filter, and pagination
- Job discovery with full-text search and provider/remote/location filters
- Profile management with resume upload and parsed resume editing
- Browser extension connection flow (one-time code exchange)
- Responsive sidebar-based navigation

### Browser Extension (Chrome)
- Secure connection to ApplyAI account via one-time code
- Job description extraction from any job posting page
- Intelligent form autofill using AI-generated plans
  - React Select component support with programmatic dropdown opening
  - File upload support (resume attachment via DataTransfer API)
  - Text normalization and synonym matching
- Resume-to-job match scoring tab
- Application state tracking (extracted → autofilled → applied)
- Real-time progress indicators and session state management

## API Endpoints

### Authentication
- `POST /auth/signup` - Create a new user account
- `POST /auth/login` - Login with email and password
- `GET /auth/me` - Get current user (requires Bearer token)

### Database Operations
- `GET /db/get-profile` - Get user profile with signed resume URL
- `GET /db/get-all-applications` - Get all job applications for user
- `POST /db/update-profile` - Update profile (multipart/form-data, includes resume upload)

### Extension Operations
- `POST /extension/connect/start` - Generate one-time code for extension connection
- `POST /extension/connect/exchange` - Exchange one-time code for extension JWT
- `GET /extension/me` - Validate extension token and get user info
- `POST /extension/jobs/ingest` - Ingest job posting from URL or DOM HTML
- `POST /extension/jobs/status` - Check job status by current tab URL
- `POST /extension/resume-match` - Get resume-to-job match score and keywords
- `POST /extension/autofill/plan` - Generate autofill plan for application form
- `POST /extension/autofill/event` - Log autofill telemetry events
- `POST /extension/autofill/feedback` - Submit corrections for autofill answers
- `POST /extension/autofill/submit` - Mark application as submitted

### Job Discovery
- `POST /discovery/run` - Discover job boards via SERP search (internal)
- `POST /sync/run` - Sync jobs from discovered boards (internal)
- `GET /jobs` - List discovered jobs with filters (public, no auth)

### Health Check
- `GET /` - Health check endpoint

## Development

### Running All Services

You'll need three terminal windows:

**Terminal 1 - Backend:**
```bash
cd backend
source ../venv/bin/activate
python main.py
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

**Terminal 3 - Extension (watch mode):**
```bash
cd applyai-extension
npm run build
```

## Tech Stack

### Backend
- FastAPI + Uvicorn
- LangGraph (autofill DAG orchestration)
- Google Generative AI (Gemini 2.5 Flash)
- Supabase (auth + storage SDK)
- psycopg2 (direct PostgreSQL connection)
- PyMuPDF / BeautifulSoup4 (document and HTML parsing)
- python-jose (JWT), aiohttp (async HTTP)
- Python 3.13+

### Frontend
- Next.js 14 (App Router)
- TypeScript
- Tailwind CSS + shadcn/ui (Radix UI)
- Recharts (dashboard charts)
- Sonner (toast notifications)
- Supabase SSR (Google OAuth)

### Browser Extension
- React 18 + Vite
- Tailwind CSS
- Chrome Extension Manifest V3
- LangGraph-backed AI autofill via backend API

## Environment Variables

See `.env.example` files in respective directories for required environment variables.

## License

MIT
