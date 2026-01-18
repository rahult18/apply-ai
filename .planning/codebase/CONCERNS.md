# Codebase Concerns

**Analysis Date:** 2026-01-18

## Tech Debt

**Hardcoded localhost URLs in extension:**
- Issue: Extension code uses hardcoded `http://localhost:8000` and `http://localhost:3000` instead of configurable URLs
- Files: `applyai-extension/background.js:1`, `applyai-extension/popup/src/hooks/useExtension.js:3-4`
- Impact: Extension cannot work in production without manual code changes and rebuild
- Fix approach: Introduce environment-based configuration or manifest settings for base URLs

**Duplicated form field extraction logic:**
- Issue: Two nearly identical functions (`extractFormFieldsFromTab` and `extractFormFieldsWithDropdownInteraction`) with ~400 lines of duplicated code
- Files: `applyai-extension/background.js:55-426`, `applyai-extension/background.js:432-835`
- Impact: Bug fixes must be applied twice, risk of logic drift between implementations
- Fix approach: Consolidate into single function with optional dropdown interaction parameter

**Repeated JWT token validation boilerplate:**
- Issue: Every protected endpoint in extension routes repeats the same 15-line JWT decoding pattern
- Files: `backend/app/routes/extension.py` (lines 114-129, 157-172, 252-267, 391-406, 427-440, 459-473)
- Impact: Inconsistent error handling possible, maintenance burden when changing auth logic
- Fix approach: Create a dependency injection decorator or middleware for token validation

**Database connection management:**
- Issue: Supabase class creates a single psycopg2 connection at init time with no pooling or reconnection logic
- Files: `backend/app/services/supabase.py:24-30`
- Impact: Connection may go stale, no graceful handling of database restarts, potential connection leaks
- Fix approach: Implement connection pooling (e.g., psycopg2.pool) or use SQLAlchemy session management

**Large monolithic components:**
- Issue: Profile page is 935 lines with multiple tab panels in a single component
- Files: `frontend/app/home/profile/page.tsx` (935 lines)
- Impact: Difficult to test, maintain, and reason about; slow renders
- Fix approach: Split into separate tab components (`PersonalInfoTab.tsx`, `ResumeTab.tsx`, etc.)

**Extension background.js size:**
- Issue: Single 1647-line JavaScript file with no modularization
- Files: `applyai-extension/background.js` (1647 lines)
- Impact: Hard to navigate, test, and maintain; tight coupling between features
- Fix approach: Split into modules (auth.js, formExtraction.js, autofill.js) using bundler

## Known Bugs

**Debug code left in production:**
- Symptoms: Excessive console logging with emoji prefixes in production
- Files: `applyai-extension/background.js:436-437`, `applyai-extension/background.js:805-828`, `applyai-extension/background.js:1308-1345`
- Trigger: Any autofill operation triggers debug output
- Workaround: Filter console messages in browser devtools

**Deprecated datetime API usage:**
- Symptoms: Deprecation warnings in Python logs
- Files: `backend/app/routes/extension.py:91` (uses `datetime.utcnow()` instead of `datetime.now(timezone.utc)`)
- Trigger: Token generation operations
- Workaround: None needed for functionality, warning only

## Security Considerations

**Token stored in plain cookie without Secure flag:**
- Risk: Token potentially sent over non-HTTPS connections; no HttpOnly flag exposes to XSS
- Files: `frontend/contexts/AuthContext.tsx:83`, `frontend/contexts/AuthContext.tsx:104`
- Current mitigation: None observed
- Recommendations: Add `; Secure; HttpOnly; SameSite=Strict` to cookie settings in production

**CORS allows all methods and headers:**
- Risk: Overly permissive CORS policy could expose endpoints to unintended cross-origin requests
- Files: `backend/app/api.py:23-29`
- Current mitigation: Origin restricted to localhost:3000
- Recommendations: Restrict `allow_methods` to only necessary HTTP methods; add production origin

**Extension token expiry too long:**
- Risk: 180-minute JWT lifespan (3 hours) without refresh mechanism
- Files: `backend/app/routes/extension.py:91`
- Current mitigation: None
- Recommendations: Reduce expiry to 15-30 minutes with refresh token pattern

**Sensitive user data in localStorage via chrome.storage.local:**
- Risk: Extension stores `extensionToken` in browser storage accessible to other extensions with proper permissions
- Files: `applyai-extension/background.js:3-9`
- Current mitigation: None
- Recommendations: Consider using session storage or implementing token encryption

## Performance Bottlenecks

**Synchronous LLM calls blocking request:**
- Problem: Autofill plan generation makes synchronous LLM API call
- Files: `backend/app/services/autofill_agent_dag.py:213-221`
- Cause: `llm.client.models.generate_content()` is blocking, holding HTTP connection open
- Improvement path: Make endpoint async with background task queue, return run_id immediately, poll for results

**Full DOM HTML stored in database:**
- Problem: Entire page DOM stored in `jd_dom_html` column for every job application
- Files: `backend/app/routes/extension.py:228-229`
- Cause: Design decision to preserve original DOM for debugging
- Improvement path: Store compressed or extract only relevant sections; add size limits

**No pagination on applications list:**
- Problem: All applications fetched at once with no server-side pagination
- Files: `backend/app/routes/db.py:100-105`, `frontend/app/home/page.tsx:86-107`
- Cause: Query fetches all rows for user
- Improvement path: Add LIMIT/OFFSET params, implement cursor-based pagination

## Fragile Areas

**Resume parsing status polling:**
- Files: `frontend/app/home/profile/page.tsx:171-182`
- Why fragile: Uses arbitrary retry count (2) and setTimeout (30s) for polling; no exponential backoff
- Safe modification: Check `resume_parse_status` field before making changes to polling logic
- Test coverage: None observed

**Extension-to-backend connection flow:**
- Files: `applyai-extension/background.js:1267-1305`, `backend/app/routes/extension.py:34-109`
- Why fragile: Multi-step flow (start -> exchange) with one-time codes that expire in 10 minutes; no retry logic
- Safe modification: Test full flow manually after any auth changes
- Test coverage: None observed

**Autofill plan caching:**
- Files: `backend/app/routes/extension.py:276-293`
- Why fragile: Cache key uses DOM HTML hash; any whitespace change in page triggers full LLM re-generation
- Safe modification: Consider content-based hashing that normalizes whitespace
- Test coverage: None observed

## Scaling Limits

**Single database connection per service instance:**
- Current capacity: 1 concurrent query per Supabase instance
- Limit: Heavy load will queue requests; potential timeouts
- Scaling path: Implement connection pooling, horizontal scaling with multiple workers

**LLM provider single-threaded:**
- Current capacity: One LLM call at a time per DAG execution
- Limit: User-facing latency scales linearly with form field count
- Scaling path: Batch fields into chunks, parallelize LLM calls, or use async/await

## Dependencies at Risk

**psycopg2 direct connection management:**
- Risk: Not using connection pooling or ORM; manual cursor management throughout
- Impact: Connection leaks, no automatic reconnection on database restart
- Migration plan: Migrate to SQLAlchemy with async support or psycopg2.pool.ThreadedConnectionPool

**Supabase Python SDK:**
- Risk: Used primarily for auth but also raw psycopg2 for queries; mixing paradigms
- Impact: Maintenance overhead, potential version conflicts
- Migration plan: Standardize on either Supabase SDK or direct PostgreSQL with SQLAlchemy

## Missing Critical Features

**No test suite:**
- Problem: Zero test files found in frontend, backend, or extension directories
- Blocks: Safe refactoring, CI/CD quality gates, regression detection

**No error tracking/monitoring:**
- Problem: Errors only logged to console; no alerting or aggregation
- Blocks: Production debugging, incident response, error trend analysis

**No rate limiting:**
- Problem: API endpoints have no rate limiting
- Blocks: Protection against abuse, LLM cost control

**No input validation on extension messages:**
- Problem: Background script trusts message payloads without schema validation
- Blocks: Security hardening, malformed request handling

## Test Coverage Gaps

**Backend routes:**
- What's not tested: All auth, db, and extension routes
- Files: `backend/app/routes/auth.py`, `backend/app/routes/db.py`, `backend/app/routes/extension.py`
- Risk: Auth bypass, data corruption, SQL injection vulnerabilities
- Priority: High

**Autofill DAG logic:**
- What's not tested: Field extraction, answer generation, plan assembly
- Files: `backend/app/services/autofill_agent_dag.py`
- Risk: Silent failures, incorrect form filling, LLM response parsing errors
- Priority: High

**Frontend components:**
- What's not tested: Auth flow, profile management, application table
- Files: `frontend/contexts/AuthContext.tsx`, `frontend/app/home/profile/page.tsx`, `frontend/components/widgets/ApplicationsTable.tsx`
- Risk: Auth state bugs, form submission errors, data display issues
- Priority: Medium

**Chrome extension:**
- What's not tested: Message passing, DOM extraction, autofill application
- Files: `applyai-extension/background.js`, `applyai-extension/popup/src/*`
- Risk: Cross-browser compatibility issues, form filling failures on different job sites
- Priority: High

---

*Concerns audit: 2026-01-18*
