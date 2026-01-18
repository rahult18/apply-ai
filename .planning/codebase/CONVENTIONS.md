# Coding Conventions

**Analysis Date:** 2026-01-18

## Naming Patterns

**Files:**
- React components: PascalCase (`Navbar.tsx`, `AppSidebar.tsx`, `KPICard.tsx`)
- UI primitives: kebab-case (`button.tsx`, `dialog.tsx`, `scroll-area.tsx`)
- Pages: `page.tsx` following Next.js App Router conventions
- Layouts: `layout.tsx` following Next.js App Router conventions
- Python modules: snake_case (`auth.py`, `supabase.py`, `autofill_agent_dag.py`)
- Hooks: `use-{name}.tsx` (kebab-case, e.g., `use-mobile.tsx`)

**Functions:**
- React components: PascalCase (`function Navbar()`, `function AppSidebar()`)
- React hooks: camelCase with `use` prefix (`useAuth`, `useIsMobile`)
- TypeScript helper functions: camelCase (`formatDate`, `toggleSort`, `getInitials`)
- Python functions: snake_case (`get_profile`, `update_profile`, `extract_jd`)
- Python route handlers: snake_case (`signup`, `login`, `get_current_user`)

**Variables:**
- TypeScript/React: camelCase (`searchQuery`, `statusFilter`, `loadingApplications`)
- React state: camelCase with descriptive names (`[user, setUser]`, `[loading, setLoading]`)
- Constants: SCREAMING_SNAKE_CASE (`API_URL`, `ITEMS_PER_PAGE`, `MOBILE_BREAKPOINT`)
- Python: snake_case (`user_id`, `one_time_code`, `db_connection`)

**Types/Interfaces:**
- TypeScript interfaces: PascalCase (`JobApplication`, `UserProfile`, `AuthContextType`)
- Props interfaces: `{ComponentName}Props` pattern (`ApplicationsTableProps`, `KPICardProps`)
- Pydantic models: PascalCase (`RequestBody`, `JD`, `AutofillPlanRequest`)

## Code Style

**Formatting:**
- Frontend: No explicit Prettier config detected; relies on ESLint defaults
- Indentation: 2 spaces for TypeScript/React, 4 spaces for Python
- Quotes: Double quotes in TypeScript/React, single/double mixed in Python
- Semicolons: Not required (Next.js default)
- Line length: No strict limit observed

**Linting:**
- Frontend: ESLint with `eslint-config-next` (`frontend/package.json`)
- Backend: No linting configuration detected
- Run lint: `npm run lint` in frontend directory

## Import Organization

**Order (TypeScript/React):**
1. React and core framework imports (`import { useState } from "react"`, `import Link from "next/link"`)
2. Third-party UI libraries (`@radix-ui/*`, `lucide-react`, `@fortawesome/*`)
3. Internal components using path aliases (`@/components/ui/*`, `@/contexts/*`)
4. Relative imports (rare, avoided via aliases)

**Order (Python):**
1. Standard library imports (`from datetime import datetime`, `import os`, `import logging`)
2. Third-party imports (`from fastapi import APIRouter`, `from pydantic import BaseModel`)
3. Local application imports (`from app.models import RequestBody`, `from app.services.supabase import Supabase`)

**Path Aliases:**
- Frontend uses `@/*` alias mapping to root directory
- Configured in `frontend/tsconfig.json`:
  ```json
  "paths": {
    "@/*": ["./*"]
  }
  ```
- Common patterns:
  - `@/components/ui/*` for shadcn/ui components
  - `@/contexts/*` for React contexts
  - `@/lib/*` for utility functions
  - `@/hooks/*` for custom hooks

## Error Handling

**Frontend Patterns:**
- Try-catch with user-friendly error messages
- Error state managed with `useState<string>("")`
- Display errors in styled alert components:
  ```tsx
  {error && (
    <div className="p-3 rounded-lg bg-destructive/10 text-destructive text-sm">
      {error}
    </div>
  )}
  ```
- Type-safe error extraction: `err instanceof Error ? err.message : "Default message"`

**Backend Patterns:**
- FastAPI `HTTPException` for API errors with status codes
- Try-except blocks wrapping entire route handlers
- Re-raise `HTTPException` after catching to preserve error details:
  ```python
  except HTTPException:
      raise
  except Exception as e:
      logger.info(f"Error message: {str(e)}")
      raise HTTPException(status_code=500, detail="User-friendly message")
  ```
- Logging errors before raising exceptions

## Logging

**Framework (Backend):** Python `logging` module

**Patterns:**
- Logger per module: `logger = logging.getLogger(__name__)`
- Use `logger.info()` for operational messages (not `logger.error()` for user errors)
- Log format: `%(asctime)s - %(name)s - %(levelname)s - %(message)s`
- Log file rotation by timestamp (`backend_{timestamp}.log`)
- Console + file handlers configured in `backend/main.py`

**Frontend:**
- `console.error()` for debugging failed operations
- No structured logging library

## Comments

**When to Comment:**
- Inline comments for non-obvious logic
- Section comments to separate route handlers in Python
- JSDoc/TSDoc: Not used consistently

**Style:**
- Use `#` comments in Python for section headers
- Brief inline comments explaining "why" not "what"

## Function Design

**Size:**
- Route handlers can be large (100+ lines) in backend
- React components vary; widgets tend to be self-contained
- Prefer extraction of complex logic into helper functions

**Parameters:**
- TypeScript: Destructured props with interface types
- Python: Type hints using Pydantic models and `Optional[T]`

**Return Values:**
- React components return JSX
- API routes return dictionaries (auto-serialized to JSON)
- Async functions use explicit `async/await`

## Module Design

**Exports:**
- Named exports preferred for components: `export function Navbar()`
- Named exports for hooks: `export function useAuth()`
- Default exports only for page components (Next.js convention)

**Barrel Files:**
- Not used; direct imports from component files
- UI components imported individually from `@/components/ui/`

## Component Patterns

**"use client" Directive:**
- Required for components using React hooks, browser APIs, or event handlers
- Place at top of file: `"use client"`
- Server components (default in App Router) have no directive

**shadcn/ui Integration:**
- UI primitives in `frontend/components/ui/`
- Use `cn()` utility from `@/lib/utils` for conditional classes
- Variant patterns using `class-variance-authority` (cva)
- Component composition with Radix UI primitives

**State Management:**
- React Context for global state (`AuthContext`)
- Local state with `useState` for component-specific state
- `useMemo` for derived/computed values

## API Integration Patterns

**Frontend:**
- Fetch API for HTTP requests (no axios)
- Token from cookies: `document.cookie.split("; ").find(row => row.startsWith("token="))`
- API URL from environment: `process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"`
- Bearer token in Authorization header

**Backend:**
- FastAPI `APIRouter` for route grouping
- Dependency injection via `Header(None)` for authorization
- Pydantic models for request/response validation
- Direct psycopg2 cursor operations for database access

---

*Convention analysis: 2026-01-18*
