# Testing Patterns

**Analysis Date:** 2026-01-18

## Test Framework

**Runner:**
- Frontend: Not configured (no Jest, Vitest, or other test runner detected)
- Backend: Not configured (no pytest or unittest setup detected)

**Assertion Library:**
- Not applicable (no testing framework installed)

**Run Commands:**
```bash
# No test commands configured
# package.json scripts do not include test commands
```

## Test File Organization

**Location:**
- No test files exist in the source code
- No `__tests__` directories
- No `.test.ts`, `.test.tsx`, `.spec.ts`, or `.spec.tsx` files in project source

**Naming:**
- Not established (no tests to infer patterns from)

**Structure:**
- Not established

## Current State

**Frontend (`frontend/package.json`):**
- No testing dependencies installed
- No test scripts defined
- Only `dev`, `build`, `start`, `lint` scripts exist

**Backend (`backend/requirements.txt`):**
- No pytest or testing libraries included
- No test directory structure

**Browser Extension (`applyai-extension/package.json`):**
- No testing dependencies
- No test scripts

## Recommended Test Setup

**For Frontend (Next.js):**
```bash
# Install dependencies
npm install -D vitest @vitejs/plugin-react jsdom @testing-library/react @testing-library/jest-dom

# Or with Jest
npm install -D jest jest-environment-jsdom @testing-library/react @testing-library/jest-dom
```

**For Backend (FastAPI):**
```bash
# Add to requirements.txt
pytest
pytest-asyncio
httpx  # for async test client
```

## Testing Gaps

**Critical Untested Areas:**
1. **Authentication Flow** (`frontend/contexts/AuthContext.tsx`, `backend/app/routes/auth.py`)
   - Login/signup logic
   - Token validation
   - Session management

2. **API Routes** (`backend/app/routes/*.py`)
   - All FastAPI endpoints
   - Authorization header validation
   - Database operations

3. **UI Components** (`frontend/components/`)
   - User interactions
   - Form submissions
   - State management

4. **Data Processing** (`backend/app/utils.py`, `backend/app/services/`)
   - LLM integration
   - Resume parsing
   - Job description extraction

## Mocking

**Framework:** Not established

**Patterns:** Not established (no tests to extract patterns from)

**What Should Be Mocked:**
- Supabase client for auth and database operations
- LLM client for AI-powered features
- External HTTP requests (aiohttp calls)
- Browser APIs (cookies, localStorage) in frontend tests

**What Should NOT Be Mocked:**
- React component rendering
- CSS class generation
- Pydantic model validation

## Fixtures and Factories

**Test Data:** Not established

**Location:** Not established

**Recommended Pattern:**
```typescript
// frontend/__tests__/fixtures/applications.ts
export const mockApplication: JobApplication = {
  id: "test-uuid",
  job_title: "Software Engineer",
  company: "Test Corp",
  status: "applied",
  // ...
}
```

```python
# backend/tests/fixtures/users.py
def create_test_user():
    return {
        "id": "test-uuid",
        "email": "test@example.com",
        # ...
    }
```

## Coverage

**Requirements:** None enforced

**View Coverage:**
```bash
# No coverage configuration exists
# Would need to add coverage tools first
```

## Test Types

**Unit Tests:**
- Not implemented
- Should cover: utility functions, Pydantic model validation, React hooks

**Integration Tests:**
- Not implemented
- Should cover: API endpoint flows, database operations, auth flows

**E2E Tests:**
- Not implemented
- Framework recommendation: Playwright or Cypress for frontend
- Should cover: full user journeys (signup -> login -> use features)

## Common Patterns (Recommended)

**Async Testing (Backend):**
```python
import pytest
from httpx import AsyncClient
from app.api import app

@pytest.mark.asyncio
async def test_health_check():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
```

**Component Testing (Frontend):**
```typescript
import { render, screen } from '@testing-library/react'
import { KPICard } from '@/components/widgets/KPICard'
import { Briefcase } from 'lucide-react'

describe('KPICard', () => {
  it('displays title and value', () => {
    render(<KPICard title="Total" value={42} icon={Briefcase} />)
    expect(screen.getByText('Total')).toBeInTheDocument()
    expect(screen.getByText('42')).toBeInTheDocument()
  })
})
```

**Error Testing (Frontend):**
```typescript
it('handles login error gracefully', async () => {
  // Mock failed login
  render(<LoginPage />)
  fireEvent.click(screen.getByText('Sign in'))
  await waitFor(() => {
    expect(screen.getByText(/login failed/i)).toBeInTheDocument()
  })
})
```

## Priority Recommendations

1. **High Priority:** Add backend API tests for auth routes
2. **High Priority:** Add frontend tests for AuthContext
3. **Medium Priority:** Add unit tests for utility functions
4. **Medium Priority:** Add component tests for data tables
5. **Low Priority:** Add E2E tests for full user flows

---

*Testing analysis: 2026-01-18*
