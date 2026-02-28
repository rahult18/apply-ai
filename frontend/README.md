# ApplyAI - Frontend

Next.js 14 frontend for the ApplyAI application tracker. Provides user authentication, job application dashboard, job discovery, profile management, and browser extension integration.

## Setup

1. Install dependencies:
```bash
npm install
```

2. Create `.env.local` file:
```bash
cp .env.local.example .env.local
```

3. Update `.env.local`:
   - `NEXT_PUBLIC_API_URL` - Backend API URL (default: `http://localhost:8000`)
   - `NEXT_PUBLIC_SUPABASE_URL` - Your Supabase project URL
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY` - Your Supabase anon key

4. Run development server:
```bash
npm run dev
```

The app will be available at `http://localhost:3000`

## Features

- **Login Page** (`/login`): Email/password and Google OAuth authentication
- **Sign Up Page** (`/signup`): Email/password and Google OAuth registration
- **Dashboard** (`/home`): KPI cards (total, applied, interviewing, offers, visa sponsorship), status pie chart, applications-over-time bar chart, and applications table with search/sort/filter/pagination
- **Discover Jobs** (`/home/discover`): Browse and search jobs from Ashby, Lever, and Greenhouse boards with keyword, provider, remote, and location filters
- **Profile** (`/home/profile`): Six-tab profile editor (Personal, Links, Location, Work Authorization, Resume, Demographics) with resume upload, LLM-based resume parsing, and editable parsed resume data
- **Connect Extension** (`/extension/connect`): Browser extension authentication via one-time code exchange

## Navigation Structure

```
/ (root)
├── /login
├── /signup
├── /home (dashboard)         ── Sidebar Layout
│   ├── /home/discover
│   └── /home/profile
└── /extension/connect        ── Sidebar Layout
```

All routes except `/login` and `/signup` require authentication.

## API Endpoints Used

### Authentication
- `POST /auth/login` - Email/password login
- `POST /auth/signup` - Email/password signup
- `GET /auth/me` - Validate token and get user info

### Google OAuth (via Supabase)
- Frontend calls `supabase.auth.signInWithOAuth({ provider: 'google' })`
- Callback handled at `/auth/callback` — exchanges code for session and sets token cookie

### Database
- `GET /db/get-all-applications` - Fetch all user applications
- `GET /db/get-profile` - Fetch user profile (includes signed resume URL)
- `POST /db/update-profile` - Update profile (multipart/form-data, includes optional resume upload)

### Job Discovery (Public)
- `GET /jobs` - Fetch discovered jobs with filters (keyword, provider, location, remote, limit, offset)

### Extension
- `POST /extension/connect/start` - Generate one-time code for extension authentication

## Tech Stack

- Next.js 14.2.0 (App Router)
- TypeScript 5.5.0
- Tailwind CSS 3.4.0
- shadcn/ui (New York style, built on Radix UI)
- Recharts 2.15.4 (dashboard charts)
- Sonner 2.0.7 (toast notifications)
- Lucide React (icons)
- @supabase/supabase-js + @supabase/ssr (Google OAuth)
- React Context API (auth state)
- Inter font (Google Fonts)

## Key Components

- **`AppSidebar`**: Sidebar navigation with active route highlighting, user avatar/initials, and logout
- **`ApplicationsTable`**: Full-featured data table with search, sort, filter by status, and pagination
- **`KPICard`**: Metric card with optional trend indicator
- **`StatusChart`**: Pie chart for application status distribution
- **`ApplicationsOverTimeChart`**: Bar chart for applications grouped by month
- **`JobCard`**: Discovered job card with provider badge, remote tag, and apply button
- **`JobFilters`**: Filter bar with keyword, provider, remote, and location inputs

## Authentication Flow

1. User visits `/` → server component checks token cookie → redirects to `/login` or `/home`
2. Login/signup returns JWT token → stored in `token` cookie (24-hour expiry)
3. All API requests send `Authorization: Bearer <token>` header
4. Invalid/expired token triggers logout and redirect to `/login`
5. Google OAuth: Supabase redirects to `/auth/callback` → code exchanged for session → token cookie set

## Resume Upload & Parsing Flow

1. User uploads PDF/DOC/DOCX on Profile → Resume tab
2. File sent via multipart form data to `POST /db/update-profile`
3. Backend sets `resume_parse_status` to `PENDING` and parses via LLM in background
4. Frontend polls every 30 seconds (max 2 retries) until status is `COMPLETED` or `FAILED`
5. Parsed data (summary, skills, experience, education, certifications, projects) displayed and editable
