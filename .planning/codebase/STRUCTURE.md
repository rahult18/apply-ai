# Codebase Structure

**Analysis Date:** 2026-01-18

## Directory Layout

```
application-tracker/
├── .claude/                    # Claude Code configuration
├── .planning/                  # Planning documents
│   └── codebase/              # Codebase analysis docs
├── backend/                    # Python FastAPI backend
│   ├── app/                   # Application code
│   │   ├── routes/            # API route handlers
│   │   └── services/          # Service classes
│   ├── logs/                  # Log files (gitignored)
│   ├── venv/                  # Python virtual environment (gitignored)
│   ├── main.py                # Server entry point
│   └── .env                   # Environment variables (gitignored)
├── frontend/                   # Next.js React frontend
│   ├── app/                   # App Router pages
│   │   ├── home/              # Dashboard pages
│   │   ├── extension/         # Extension connection pages
│   │   ├── login/             # Login page
│   │   └── signup/            # Signup page
│   ├── components/            # React components
│   │   ├── ui/                # shadcn/ui base components
│   │   └── widgets/           # Dashboard widgets
│   ├── contexts/              # React contexts
│   ├── hooks/                 # Custom React hooks
│   ├── lib/                   # Utility functions
│   └── public/                # Static assets
├── applyai-extension/          # Chrome browser extension
│   ├── popup/                 # Extension popup UI
│   │   └── src/               # Popup React components
│   │       ├── components/    # Popup-specific components
│   │       └── hooks/         # Extension hooks
│   ├── assets/                # Extension icons
│   ├── dist/                  # Built extension (gitignored)
│   ├── background.js          # Service worker
│   ├── content.js             # Content script
│   └── manifest.json          # Extension manifest
├── supabase_schema.sql         # Database schema reference
├── .mcp.json                   # MCP configuration
└── README.md                   # Project documentation
```

## Directory Purposes

**`backend/`:**
- Purpose: Python FastAPI REST API server
- Contains: API routes, services, models, utilities
- Key files:
  - `main.py`: Server startup and logging config
  - `app/api.py`: FastAPI app instance and router registration
  - `app/models.py`: Pydantic models for request/response validation
  - `app/utils.py`: Utility functions (URL normalization, content cleaning, resume parsing)

**`backend/app/routes/`:**
- Purpose: API endpoint handlers organized by domain
- Contains:
  - `auth.py`: Authentication endpoints (`/auth/signup`, `/auth/login`, `/auth/me`)
  - `db.py`: Database operations (`/db/get-profile`, `/db/get-all-applications`, `/db/update-profile`)
  - `extension.py`: Extension-specific endpoints (`/extension/connect/*`, `/extension/jobs/ingest`, `/extension/autofill/*`)

**`backend/app/services/`:**
- Purpose: Business logic and external service integrations
- Contains:
  - `supabase.py`: Supabase client class with Auth SDK and psycopg2 connection
  - `llm.py`: Google Gemini AI client wrapper
  - `autofill_agent_dag.py`: LangGraph DAG for autofill plan generation

**`frontend/app/`:**
- Purpose: Next.js App Router pages and layouts
- Contains: Page components following file-based routing
- Key files:
  - `layout.tsx`: Root layout with AuthProvider
  - `page.tsx`: Root page (redirects to /login or /home)
  - `globals.css`: Global Tailwind CSS styles

**`frontend/app/home/`:**
- Purpose: Authenticated dashboard pages
- Contains:
  - `layout.tsx`: Dashboard layout with sidebar
  - `page.tsx`: Main dashboard with KPIs and applications table
  - `profile/page.tsx`: User profile settings

**`frontend/app/extension/connect/`:**
- Purpose: Extension connection flow page
- Contains: `page.tsx` - Displays one-time code for extension linking

**`frontend/components/ui/`:**
- Purpose: Reusable shadcn/ui base components
- Contains: `button.tsx`, `card.tsx`, `dialog.tsx`, `sidebar.tsx`, etc.
- Pattern: Components generated via `npx shadcn-ui@latest add`

**`frontend/components/widgets/`:**
- Purpose: Dashboard-specific composite components
- Contains:
  - `KPICard.tsx`: Metric display card
  - `StatusChart.tsx`: Pie chart for application status distribution
  - `ApplicationsOverTimeChart.tsx`: Bar chart for applications timeline
  - `ApplicationsTable.tsx`: Data table for job applications

**`frontend/contexts/`:**
- Purpose: React Context providers
- Contains: `AuthContext.tsx` - Authentication state and methods

**`frontend/hooks/`:**
- Purpose: Custom React hooks
- Contains: `use-mobile.tsx` - Mobile breakpoint detection

**`frontend/lib/`:**
- Purpose: Shared utility functions
- Contains: `utils.ts` - cn() helper for Tailwind class merging

**`applyai-extension/`:**
- Purpose: Chrome Manifest V3 browser extension
- Contains: Background script, content script, popup UI, manifest

**`applyai-extension/popup/`:**
- Purpose: Extension popup interface (React + Vite)
- Contains: Separate React app built with Vite for the extension popup
- Key files:
  - `index.html`: Popup HTML entry
  - `src/hooks/useExtension.js`: Extension state management hook

## Key File Locations

**Entry Points:**
- `backend/main.py`: Backend server entry
- `frontend/app/layout.tsx`: Frontend root layout
- `applyai-extension/background.js`: Extension service worker
- `applyai-extension/manifest.json`: Extension configuration

**Configuration:**
- `backend/.env`: Backend environment variables (Supabase, JWT secrets)
- `frontend/.env.local`: Frontend environment variables (API URL)
- `frontend/tailwind.config.ts`: Tailwind CSS configuration
- `frontend/next.config.js`: Next.js configuration
- `applyai-extension/vite.config.js`: Vite config for popup build

**Core Logic:**
- `backend/app/routes/extension.py`: Extension API endpoints (job ingest, autofill)
- `backend/app/services/autofill_agent_dag.py`: Autofill generation DAG
- `backend/app/utils.py`: Job extraction, resume parsing, URL normalization
- `frontend/contexts/AuthContext.tsx`: Authentication state management
- `applyai-extension/background.js`: Extension orchestration (message handling, API calls)

**Database Schema:**
- `supabase_schema.sql`: Reference SQL for all tables

**Testing:**
- No dedicated test files detected in the codebase

## Naming Conventions

**Files:**
- React components: PascalCase (`AppSidebar.tsx`, `KPICard.tsx`)
- Utility/config files: kebab-case or camelCase (`use-mobile.tsx`, `utils.ts`)
- Python modules: snake_case (`autofill_agent_dag.py`, `supabase.py`)
- API routes: snake_case (`auth.py`, `extension.py`)

**Directories:**
- lowercase with hyphens for multi-word (`components/ui/`)
- lowercase for Python packages (`app/routes/`, `app/services/`)

**Components:**
- React components: PascalCase function names matching filename
- shadcn/ui components: lowercase filenames, PascalCase exports

**API Endpoints:**
- kebab-case paths (`/extension/connect/start`, `/db/get-all-applications`)
- RESTful resource naming where applicable

**Database:**
- Tables: snake_case plural (`job_applications`, `autofill_runs`)
- Columns: snake_case (`user_id`, `created_at`, `job_title`)

## Where to Add New Code

**New API Endpoint:**
- Create or extend route file in `backend/app/routes/`
- Register router in `backend/app/api.py` with `app.include_router()`
- Add Pydantic models to `backend/app/models.py`

**New Frontend Page:**
- Create directory under `frontend/app/` following App Router conventions
- Add `page.tsx` for the route content
- Add `layout.tsx` if custom layout needed
- Update navigation in `frontend/components/AppSidebar.tsx`

**New UI Component:**
- shadcn/ui base: Use `npx shadcn-ui@latest add <component>`
- Custom widget: Add to `frontend/components/widgets/`
- Shared component: Add to `frontend/components/`

**New Service/Integration:**
- Add service class to `backend/app/services/`
- Initialize in route files as needed
- Add environment variables to `backend/.env`

**New Extension Feature:**
- Add message handler in `applyai-extension/background.js`
- Add UI trigger in popup components
- Use `useExtension` hook for state management

**New Utility Function:**
- Backend: Add to `backend/app/utils.py` or create domain-specific module
- Frontend: Add to `frontend/lib/utils.ts`

**New Database Table:**
- Add migration SQL to appropriate location
- Update `supabase_schema.sql` for documentation
- Add Pydantic models in `backend/app/models.py`

## Special Directories

**`backend/venv/`:**
- Purpose: Python virtual environment
- Generated: Yes (via `python -m venv venv`)
- Committed: No (gitignored)

**`backend/logs/`:**
- Purpose: Application log files
- Generated: Yes (at runtime by `main.py`)
- Committed: No (gitignored)

**`frontend/node_modules/`:**
- Purpose: NPM dependencies
- Generated: Yes (via `npm install`)
- Committed: No (gitignored)

**`frontend/.next/`:**
- Purpose: Next.js build cache
- Generated: Yes (during `npm run dev` or `npm run build`)
- Committed: No (gitignored)

**`applyai-extension/node_modules/`:**
- Purpose: NPM dependencies for popup build
- Generated: Yes (via `npm install`)
- Committed: No (gitignored)

**`applyai-extension/dist/`:**
- Purpose: Built extension files
- Generated: Yes (via popup build process)
- Committed: No (gitignored)

**`.claude/`:**
- Purpose: Claude Code agent configuration
- Contains: `settings.local.json` with allowed/denied tools
- Committed: Yes

**`.planning/`:**
- Purpose: Project planning and analysis documents
- Contains: Codebase analysis, planning docs
- Committed: Yes

---

*Structure analysis: 2026-01-18*
