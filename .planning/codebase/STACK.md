# Technology Stack

**Analysis Date:** 2026-01-18

## Languages

**Primary:**
- TypeScript ^5.5.0 - Frontend (Next.js), shared types
- Python 3.13 - Backend API, AI/ML services
- JavaScript ES2017+ - Browser extension

**Secondary:**
- SQL - Database schema (PostgreSQL via Supabase)
- CSS - Styling via Tailwind

## Runtime

**Frontend:**
- Node.js (Next.js runtime)
- Target: ES2017

**Backend:**
- Python 3.13
- Virtual environment: `backend/venv/`

**Extension:**
- Chrome Extension (Manifest V3)
- Service Worker background script

**Package Managers:**
- npm (Frontend + Extension)
- pip (Backend)
- Lockfiles: `frontend/package-lock.json` present, `backend/requirements.txt` (no lock)

## Frameworks

**Frontend (Next.js App):**
- Next.js ^14.2.0 - React framework with App Router
- React ^18.3.0 - UI library
- Tailwind CSS ^3.4.0 - Utility-first styling
- shadcn/ui (via Radix UI) - Component library

**Backend (FastAPI):**
- FastAPI - Async Python web framework
- Uvicorn - ASGI server
- Pydantic - Data validation and serialization
- LangGraph + LangChain - AI agent orchestration

**Extension:**
- Vite 5.0.8 - Build tool
- React 18.2.0 - Popup UI
- Tailwind CSS 4.1.18 - Styling

## Key Dependencies

**Frontend Critical:**
- `next` ^14.2.0 - Core framework
- `@radix-ui/*` (multiple) - Accessible UI primitives for shadcn/ui
- `class-variance-authority` ^0.7.1 - Component variant management
- `recharts` ^2.15.4 - Charting library
- `sonner` ^2.0.7 - Toast notifications
- `next-themes` ^0.4.6 - Dark mode support
- `lucide-react` ^0.378.0 - Icon library
- `@fortawesome/*` - Additional icons

**Backend Critical:**
- `fastapi` - HTTP API
- `uvicorn` - ASGI server
- `google-genai` - Google Gemini AI SDK
- `langgraph` + `langchain` - AI agent workflow orchestration
- `supabase` - Supabase Python client
- `psycopg2-binary` - PostgreSQL driver (direct DB access)
- `python-jose` - JWT token handling
- `pymupdf` (fitz) - PDF parsing for resume extraction
- `beautifulsoup4` - HTML parsing
- `tiktoken` - Token counting for LLM
- `tenacity` - Retry logic
- `aiohttp` - Async HTTP client

**Extension Critical:**
- `@vitejs/plugin-react` - Vite React plugin
- `@types/chrome` - Chrome extension type definitions
- `sharp` - Image processing for icons

## Configuration

**Frontend Environment:**
- Config file: `frontend/.env.local`
- Required vars:
  - `NEXT_PUBLIC_API_URL` - Backend API URL (default: http://localhost:8000)

**Backend Environment:**
- Config file: `backend/.env`
- Required vars:
  - `SUPABASE_URL` - Supabase project URL
  - `SUPABASE_KEY` - Supabase anon key
  - `GOOGLE_GENAI_API_KEY` - Google AI API key
  - `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` - Direct PostgreSQL connection
  - `SECRET_KEY` - JWT signing key
  - `ALGORITHM` - JWT algorithm

**Build Configuration:**
- Frontend: `frontend/next.config.js` - React strict mode enabled
- Frontend: `frontend/tailwind.config.ts` - shadcn/ui theming with CSS variables
- Frontend: `frontend/tsconfig.json` - ES2017 target, bundler module resolution, `@/*` path alias
- Frontend: `frontend/components.json` - shadcn/ui new-york style configuration
- Extension: `applyai-extension/vite.config.js` - Custom plugin copies manifest/background/content scripts

**Linting/Formatting:**
- ESLint ^8.57.0 with eslint-config-next
- No Prettier config detected (uses ESLint formatting rules)

## Platform Requirements

**Development:**
- Node.js (version not pinned, recommend 18+)
- Python 3.13
- PostgreSQL (via Supabase or local)
- Chrome browser (for extension testing)

**Production:**
- Frontend: Vercel or similar (Next.js optimized)
- Backend: Any Python 3.13+ host with PostgreSQL access
- Database: Supabase (PostgreSQL)

## Run Commands

**Frontend:**
```bash
cd frontend
npm install
npm run dev      # Development server on :3000
npm run build    # Production build
npm run lint     # ESLint check
```

**Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py   # Starts Uvicorn on :8000
```

**Extension:**
```bash
cd applyai-extension
npm install
npm run dev      # Watch mode build
npm run build    # Production build to dist/
# Load dist/ as unpacked extension in Chrome
```

---

*Stack analysis: 2026-01-18*
