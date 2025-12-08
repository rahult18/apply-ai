# Application Tracker

A full-stack application for tracking job applications with AI-powered job description extraction.

## Project Structure

This is a monorepo containing both the backend and frontend:

```
application-tracker/
├── backend/          # FastAPI REST API
├── frontend/         # Next.js web application
└── venv/             # Python virtual environment (not committed)
```

## Prerequisites

- Python 3.13+
- Node.js 18+
- Supabase account and project
- Google Generative AI API key

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

5. Update `.env` in the `backend/` directory with your credentials:
   - `SUPABASE_URL` - Your Supabase project URL
   - `SUPABASE_KEY` - Your Supabase anon/service key
   - `GOOGLE_GENAI_API_KEY` - Your Google Generative AI API key

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

5. Run the development server:
```bash
npm run dev
```

The frontend will be available at `http://localhost:3000`

## Features

### Backend (FastAPI)
- RESTful API for authentication (login, signup, user info)
- Job description scraping and extraction using AI
- Supabase integration for user management

### Frontend (Next.js)
- User authentication (email/password)
- Protected routes
- Modern UI with shadcn/ui components
- Responsive design

## API Endpoints

### Authentication
- `POST /auth/signup` - Create a new user account
- `POST /auth/login` - Login with email and password
- `GET /auth/me` - Get current user (requires Bearer token)

### Job Scraping
- `POST /scrape?job_link=<url>` - Scrape and extract job description from URL

## Development

### Running Both Services

You'll need two terminal windows:

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

## Tech Stack

### Backend
- FastAPI
- Supabase (authentication & database)
- Google Generative AI
- Python 3.13+

### Frontend
- Next.js 14 (App Router)
- TypeScript
- Tailwind CSS
- shadcn/ui
- React Context API

## Environment Variables

See `.env.example` files in respective directories for required environment variables.

## License

MIT

