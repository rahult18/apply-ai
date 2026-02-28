# Agent Context: applyai-extension

This folder contains the browser extension for the ApplyAI project. It includes the following files and directories:

## Structure
- `manifest.json`: The manifest file for the browser extension. It defines essential metadata like the extension's name ("ApplyAI"), version (0.1.0), description, and permissions. It declares:
  - Background service worker: `background.js`
  - Content script: `content.js` (runs on `http://localhost:3000/extension/connect*`)
  - Default popup: `popup/popup.html`
  - Permissions: `storage`, `tabs`, `activeTab`, `scripting`
  - Host permissions: `http://localhost:3000/*`, `http://localhost:8000/*`

- `background.js`: The main service worker running in the background (~1,650 lines). Key functionality:
  - **Storage helpers**: `storageGet()` and `storageSet()` for Chrome local storage
  - **Install ID management**: `ensureInstallId()` generates and stores a unique installation UUID
  - **Tab interaction**: `getActiveTab()` gets the current active tab
  - **DOM extraction**: `extractDomHtmlFromTab(tabId)` injects script into tab to extract full DOM HTML and URL
  - **Form field extraction with dropdown interaction**: `extractFormFieldsFromTab(tabId)` extracts structured form fields using JavaScript DOMParser with enhanced React Select support:
    - **Programmatically opens React Select dropdowns** before extraction using `tryOpenReactSelect()`:
      - Focuses combobox element and dispatches proper MouseEvent and KeyboardEvent objects
      - Tries clicking dropdown indicator elements
      - Waits 300ms for options to render in DOM
    - Detects inputs, textareas, selects, comboboxes (React Select), radio groups, and checkbox groups
    - Generates CSS selectors for each field (#id or [name="..."])
    - Extracts labels via multiple strategies (for attribute, parent label, aria-label, placeholder)
    - Determines if fields are required (required attribute, aria-required, asterisk in label)
    - **Enhanced option extraction**: Checks multiple locations for React Select options:
      - aria-controls listbox (primary method)
      - Menu containers with `[class*="menu"]` (fallback for opened dropdowns)
    - Filters out React Select internal validation inputs (.requiredInput, hidden inputs in .select__container)
    - Returns structured JSON: type, inputType, name, id, label, placeholder, required, selector, options, autocomplete, isCombobox
  - **Debug form field extraction**: `extractFormFieldsWithDropdownInteraction(tabId)` provides verbose debugging:
    - Same extraction logic as production with detailed console logging
    - Shows step-by-step progress, field counts, and option extraction results
    - Displays summary table with all extracted fields
    - Warns about any dropdowns that failed to extract options
    - Outputs full field data as JSON for analysis
  - **Autofill application**: `applyAutofillPlanToTab(tabId, planJson, resumeUrl)` applies autofill plans with sophisticated form filling:
    - Supports text inputs, native selects, React Select components, radio groups, checkbox groups, and **file uploads**
    - React Select detection via `role="combobox"` or `aria-autocomplete="list"`
    - Advanced option matching with text normalization and synonym support (e.g., "US" → "United States")
    - Triggers proper React events (input, change, keydown) for framework compatibility
    - **File upload support**: `fillFileInput(el, fileUrl)` fetches resume from signed URL, creates `File` object via `DataTransfer` API, and attaches to file input elements
    - Returns detailed debug information with filled/skipped counts
  - **URL security**: `isRestrictedUrl(url)` prevents access to chrome://, edge://, about:, and file:// URLs

  **Message handlers**:
  1. `APPLYAI_EXTENSION_CONNECT`: Connection flow
     - Exchanges one-time code with backend at `/extension/connect/exchange`
     - Stores JWT token in `chrome.storage.local`
     - Notifies popup with `APPLYAI_EXTENSION_CONNECTED`

  2. `APPLYAI_DEBUG_EXTRACT_FIELDS`: Debug form field extraction
     - Validates active tab and URL restrictions
     - Runs `extractFormFieldsWithDropdownInteraction()` with verbose logging
     - Returns field count and full field data to popup
     - Logs detailed extraction results to page console (summary, table, warnings)
     - Used by debug button for troubleshooting dropdown extraction issues

  3. `APPLYAI_EXTRACT_JD`: Job description extraction
     - Validates token and active tab
     - Extracts DOM HTML from current page
     - Enforces 2.5MB size limit on DOM HTML
     - POSTs to `/extension/jobs/ingest` with `job_link` and `dom_html`
     - Stores result in `lastIngest` (includes job_application_id, job_title, company)
     - Sends progress messages: `APPLYAI_EXTRACT_JD_PROGRESS` (stages: starting, extracting_dom, sending_to_backend)
     - Sends result: `APPLYAI_EXTRACT_JD_RESULT` (includes ok, url, job_application_id, job_title, company)

  4. `APPLYAI_AUTOFILL_PLAN`: Autofill generation and application
     - Validates token, retrieves job_application_id from message or lastIngest
     - Extracts DOM HTML from active tab (enforces 2.5MB limit)
     - **Extracts structured form fields with dropdown interaction** using `extractFormFieldsFromTab()`:
       - Programmatically opens all React Select dropdowns before extraction
       - Waits for dropdown options to render in DOM (300ms delay)
       - Extracts options from opened dropdowns via aria-controls listboxes or menu containers
       - Returns complete field data including all dropdown options
     - POSTs to `/extension/autofill/plan` with `job_application_id`, `page_url`, `dom_html`, and `extracted_fields`
     - Backend receives pre-extracted fields with dropdown options already populated (no server-side parsing needed)
     - Backend enriches country fields automatically (adds 196 countries to select fields with "country", "nationality", or "citizenship" keywords)
     - Receives `plan_json` with fields array (each field has: action, selector, input_type, value, question_signature, options) and `resume_url` (signed URL for file uploads)
     - Applies plan to page using `applyAutofillPlanToTab()`, passing `resume_url` for file input fields
     - File input fields with `value: "resume"` trigger resume download and attachment via DataTransfer API
     - Sends progress messages: `APPLYAI_AUTOFILL_PROGRESS` (stages: starting, extracting_dom, extracting_fields, planning, autofilling)
     - Sends result: `APPLYAI_AUTOFILL_RESULT` (includes ok, run_id, plan_summary, filled, skipped, errors)

  5. `APPLYAI_MARK_APPLIED`: Mark application as applied
     - Validates token and run_id from message
     - POSTs to `/extension/autofill/submit` with run_id
     - Sends result: `APPLYAI_MARK_APPLIED_RESULT` (includes ok, error)

- `content.js`: Content script bridge (~18 lines)
  - Listens for `APPLYAI_EXTENSION_CONNECT` messages from web page via `window.addEventListener("message")`
  - Only accepts messages from same origin (security check)
  - Forwards messages to background script via `chrome.runtime.sendMessage()`

- `assets/`: Directory for static assets (icons, images) used by the extension

- `popup/`: Extension popup UI (React + Vite + Tailwind)
  - `index.html` (13 lines): Entry point that loads the built popup.js from Vite
  - `src/main.jsx` (11 lines): React entry point that renders Popup component into #root
  - `src/Popup.jsx` (~284 lines): Main popup component with stepper-driven architecture:
    - Uses `useExtension` hook for state/actions and `useStepperState` hook for UI derivation
    - **Outer container**: 380px width, 500px min-height, `shadow-[inset_0_0_0_1px_rgba(0,0,0,0.07)]` to soften native popup border (replaces harsh black edge)
    - **Header** (floating, no card): Sky gradient logo badge (BoltIcon), "ApplyAI" title, StatusPill — `px-4 pt-4 pb-3` with no card border
    - **ProgressStepper**: 4-step progress bar wrapped in `px-4 pb-3`, followed by `border-t border-gray-100` divider
    - **Tabbed interface** (when connected + job found): Autofill tab and Resume Score tab
      - Resume Score tab lazy-loads match data via `fetchResumeMatch()` when selected
    - **Content card**: `m-3 bg-white rounded-2xl border border-gray-100 shadow-md overflow-hidden`
      - Skeleton loader: animated 3-line shimmer when `isCheckingStatus && !jobStatus && connected`
      - **Autofill tab** content (when not skeleton):
        - StatusMessage for operation progress/errors
        - JobCard with extracted job info + "Extracted Xm ago" timestamp
        - **NavCue** (amber banner): shown when `jobStatus?.page_type === 'jd' && showJobCard` — guides user to navigate to application page for Lever/Ashby jobs
        - Autofill stats (green box: "Filled X fields, skipped Y · Xm ago")
        - **"Mark as Applied"** (lg primary, sole CTA when `sessionState === 'autofilled'`)
        - **Applied badge** (green pill, when `sessionState === 'applied'`)
        - **Primary action button** (hidden when autofilled or applied): driven by `useStepperState`, changes label/icon contextually
        - Hint text when primary action is disabled
      - **Resume Score tab**: ResumeMatchCard component
    - **Footer utility strip** (inside card, below `p-4` div, `border-t border-gray-100 bg-gray-50 rounded-b-2xl`):
      - Only shown when `connectionStatus === 'connected'`
      - `autofilled` state: 3 items — `[↺ Run Again]` `[⊞ Dashboard]` `[→ Disconnect]`
      - All other connected states: 2 items — `[⊞ Dashboard]` `[→ Disconnect]`
      - Each item: `flex-1`, icon + text, `text-xs`, hover highlight (white bg), no borders
      - Disconnect: `text-red-400 hover:text-red-600 hover:bg-red-50`
  - `src/style.css`: Tailwind CSS with explicit animation fixes for Chrome extension popup throttling
    - **Root cause fix**: Chrome extension popups throttle CSS animations. All keyframes defined explicitly in CSS and forced with `animation-play-state: running !important`
    - `@keyframes spin` → `.animate-spin` (0.85s linear infinite, play-state forced)
    - `@keyframes pulse-subtle` → `.animate-pulse-subtle` (3s ease-in-out infinite)
    - `@keyframes slide-up` → `.animate-slide-up` (0.3s ease-out)
    - `@keyframes shimmer` → `.skeleton` utility class (shimmer gradient, 1.4s infinite) for skeleton loaders
    - Custom scrollbar: 6px width, rounded thumb
  - `src/components/`:
    - `ActionButton.jsx` (55 lines): Reusable button component with variants and sizes
      - Variants: primary (sky-600), secondary (white/border), ghost (gray-100), danger (red-50/border)
      - Sizes: lg (py-3.5, text-base, rounded-xl), md (py-2.5, text-sm, rounded-lg), sm (py-2, text-xs)
      - Features: Loading state with SpinnerIcon, optional icon prop, disabled state, focus ring
    - `StatusPill.jsx` (22 lines): Status indicator badge with color-coded states
      - connected: Green
      - disconnected: Amber/Yellow
      - error: Red
      - working: Sky blue with pulse animation
      - Accepts custom `text` prop (no longer hardcoded labels)
    - `Icons.jsx`: SVG icon components used throughout the popup
      - CheckIcon, LinkIcon, DocumentTextIcon, SparklesIcon, CheckBadgeIcon
      - Squares2X2Icon (dashboard), BoltIcon (logo), BriefcaseIcon (job card)
      - ArrowRightOnRectangleIcon (disconnect), ArrowPathIcon (run again / circular refresh), SpinnerIcon (loading animation)
    - `ProgressStepper.jsx`: Visual 4-step progress indicator (flat, no card wrapper)
      - Steps: Connect → Extract → Autofill → Applied
      - Step states: completed (green circle + checkmark), active (sky circle + ring), pending (gray circle)
      - Connector lines between steps (green when completed, gray otherwise)
      - Component renders a bare `flex items-center` row — caller handles padding
    - `StatusMessage.jsx` (52 lines): Alert/notification component
      - Types: info, success, error, warning with color-coded backgrounds
      - Icons: Info circle, check circle, alert circle, warning triangle
      - Features: Slide-up animation
    - `JobCard.jsx`: Compact card displaying extracted job information
      - BriefcaseIcon in sky gradient badge
      - Job title (semibold, truncated) and company name (gray, truncated)
      - **`extractedAt` prop**: displays "Extracted Xm ago" inline with company name (using `timeAgo()` helper)
      - Styling: `bg-sky-50 border-sky-100` rounded-xl
    - `NavCue.jsx` (new): Amber navigation banner for Lever/Ashby job boards
      - Shown when user is on JD page with a saved job (needs to navigate to application form)
      - Props: `applyUrl` (nullable string)
      - If `applyUrl` provided (Lever/Ashby): shows "Open Application" button that calls `chrome.tabs.create({ url: applyUrl })`
      - If no `applyUrl`: shows instructional text only ("Navigate to the application form page")
      - Styling: `bg-amber-50 border-amber-200` with warning triangle icon, `animate-slide-up` entrance
    - `Tabs.jsx`: Tab navigation component for switching between Autofill and Resume Score views
      - Accepts tabs array, activeTab, and onTabChange callback
      - Renders horizontal tab bar with active state styling
    - `ResumeMatchCard.jsx`: Displays resume-to-job match analysis
      - Shows match score (percentage), matched keywords (green badges), missing keywords (red badges)
      - Loading state with skeleton UI
      - Helps users understand how well their resume matches the job requirements
  - `src/hooks/`:
    - `useExtension.js` (~452 lines): Custom hook managing extension state and messaging
      - State: connectionStatus, userEmail, userName, sessionState, statusMessage, extractedJob, autofillStats, **jobStatus**, **isCheckingStatus**, **resumeMatch**, **isLoadingMatch**, **lastRunId**, **isMarkingApplied**, **currentTabUrl**, **applyUrl**, **extractedAt**, **autofilledAt**
      - SessionState values: idle, extracting, extracted, autofilling, autofilled, **applied**, error
      - Refs: `skipNextResetRef` (prevents state reset after completing actions), `currentJobIdRef` (always holds current job_application_id for async message handlers)
      - Functions: checkConnection(), connect(), disconnect(), openDashboard(), extractJob(), generateAutofill(), **checkJobStatus()**, **fetchResumeMatch()**, **markAsApplied()**
      - **`deriveApplyUrl(tabUrl, pageType)`**: Client-side helper that constructs the application form URL from the current tab URL. Detects Lever (`lever.co` → appends `/apply`) and Ashby (`ashbyhq.com` → appends `/application`). No backend required.
      - **`checkJobStatus()`**: Calls `POST /extension/jobs/status` with current tab URL. Updates sessionState, sets `currentTabUrl`, `applyUrl` (via `deriveApplyUrl`), and restores timestamps from `chrome.storage.local`. Handles provisional timestamp association (see Storage Schema). Uses `skipNextResetRef` to prevent state reset after completing actions.
      - **`generateAutofill()`**: Sends `APPLYAI_AUTOFILL_PLAN` message with `job_application_id` from `jobStatus` state
      - **`fetchResumeMatch()`**: Calls `POST /extension/resume-match` with job_application_id. Returns score, matched_keywords, missing_keywords.
      - **`markAsApplied()`**: Sends `APPLYAI_MARK_APPLIED` message with `lastRunId`. Updates sessionState to 'applied' on success.
      - **Timestamp handling**: After extraction, saves provisional `{ extractedAt, autofilledAt: null }` to storage (no job_application_id yet). `checkJobStatus()` detects provisional entry and associates it with the correct `job_application_id`. After autofill, saves `{ job_application_id, extractedAt, autofilledAt }` using `currentJobIdRef.current`.
      - Message listeners for: APPLYAI_EXTENSION_CONNECTED, APPLYAI_EXTRACT_JD_PROGRESS, APPLYAI_EXTRACT_JD_RESULT, APPLYAI_AUTOFILL_PROGRESS, APPLYAI_AUTOFILL_RESULT, **APPLYAI_MARK_APPLIED_RESULT**
      - Initialization: Checks connection on mount, then checks job status if connected
      - API URLs: APP_BASE_URL (localhost:3000), API_BASE_URL (localhost:8000)
    - `useStepperState.js` (~144 lines): Custom hook deriving all UI state from extension state
      - Input: connectionStatus, sessionState, jobStatus, isCheckingStatus, statusMessage, **extractedJob**
      - **hasJob logic**: Considers job found if either `jobStatus?.found` OR `extractedJob` has title+company (handles race condition after extraction)
      - **Step computation**: Maps current state to 4-step progress (connect=0, extract=1, autofill=2, applied=3). Each step gets state: completed, active, or pending.
      - **Pill status/text**: Derives StatusPill props (disconnected, working, error, connected) with dynamic text
      - **Primary action**: Returns { label, handler, icon, loading, disabled, hint } based on:
        - Not connected → "Connect to ApplyAI" (handler: connect)
        - No job + non-application page → "Extract Job" (handler: extractJob)
        - No job + application page → "Extract Job First" (disabled, with hint)
        - Job found → "Generate Autofill" / "Autofill Again" (uses `current_page_autofilled` for page-specific label)
      - **Visibility flags**: showJobCard (currentStepIndex >= 2 && hasJob), showStatusMessage, messageType
      - All values memoized via `useMemo` on input dependencies

## Purpose
This folder provides the browser extension for the ApplyAI project. The extension enables users to:
1. **Connect** their browser to their ApplyAI account via secure one-time code authentication
2. **Extract** job descriptions from job posting pages and save them to the tracker
3. **Autofill** job application forms using AI-generated plans based on user profile and saved job data
4. **Track** application state (extracted → autofilled → applied) with timestamps and resume match scoring

The extension acts as a bridge between the user's browser and the ApplyAI backend, providing seamless integration for job application tracking and form automation.

## Key Workflows

### 1. Connection Flow
1. User clicks "Connect" in popup → Opens frontend `/extension/connect` page
2. Frontend generates one-time code and sends `APPLYAI_EXTENSION_CONNECT` message to page
3. Content script forwards message to background script
4. Background script exchanges code for JWT token at `/extension/connect/exchange`
5. Token stored in `chrome.storage.local` and popup notified

### 2. Job Extraction Flow
1. User navigates to job posting page
2. User clicks "Extract Job Description" in popup
3. Background script extracts DOM HTML from active tab
4. DOM sent to `/extension/jobs/ingest` with JWT authentication
5. Backend parses job details (title, company) and creates job_application record
6. Result displayed in popup with job title and company
7. Button changes to "Generate Autofill"

### 3. Autofill Flow
1. User navigates to job application form page
2. User clicks "Generate Autofill" in popup (after extracting a job)
3. Background script extracts DOM HTML from active tab
4. **Background script extracts structured form fields with dropdown interaction** using `extractFormFieldsFromTab()`:
   - Finds all React Select components (`[role="combobox"]`)
   - **Programmatically opens each dropdown** by:
     - Focusing the element
     - Dispatching MouseEvent (mousedown, mouseup, click)
     - Dispatching KeyboardEvent (ArrowDown)
     - Clicking dropdown indicator if found
     - Waiting 300ms for options to render
   - Identifies all form inputs, textareas, selects, and React Select components
   - Generates CSS selectors and extracts labels, options, and metadata
   - **Extracts options from opened dropdowns** via aria-controls listbox or menu containers
   - Filters out React Select internal validation inputs
5. Both DOM HTML and structured fields (with dropdown options) sent to `/extension/autofill/plan` with job_application_id
6. Backend processes pre-extracted fields:
   - Converts JavaScript field format to internal FormField format
   - Enriches country/nationality fields with standard country list (196 countries) if options are missing
   - Generates answers using LLM based on user profile, resume, job requirements, and available dropdown options
7. Backend generates autofill plan (field selectors, values, actions, confidence scores)
8. Plan applied to page via `applyAutofillPlanToTab()`:
   - Identifies form fields by CSS selectors
   - Handles various input types (text, select, radio, checkbox, React Select, **file upload**)
   - For file inputs with `value: "resume"`, fetches resume PDF from signed URL and attaches via DataTransfer API
   - Fills values and triggers appropriate events
9. Popup displays filled field count

## Key Technical Features
- **Secure Authentication**: One-time code exchange for JWT tokens, stored in chrome.storage.local
- **DOM Extraction**: On-demand script injection to capture full page HTML (with 2.5MB size limit)
- **Intelligent Form Field Extraction with Dropdown Interaction**: JavaScript DOMParser-based extraction in browser context
  - Parses live DOM (handles React and JavaScript-rendered forms)
  - **Programmatic dropdown opening**: Automatically opens React Select components before extraction
    - Dispatches proper MouseEvent and KeyboardEvent objects to trigger dropdown menus
    - Finds and clicks dropdown indicator elements
    - Waits for options to render in DOM (300ms delay)
  - **Enhanced option extraction**: Checks multiple locations for React Select options
    - Primary: aria-controls listbox with `[role="option"]` elements
    - Fallback: Menu containers (`[class*="menu"]`) for dynamically positioned dropdowns
  - Multi-strategy label detection (for attribute, parent labels, aria-label, placeholder)
  - Required field detection (required attribute, aria-required, asterisk in labels)
  - React Select component detection and option extraction (both static and dynamically loaded)
  - Filters out framework internal inputs (React Select validation inputs)
  - Country field enrichment (backend automatically adds 196 countries to country/nationality fields when options missing)
- **Smart Form Filling**:
  - React framework compatibility via native property setters and proper event triggering
  - React Select component detection and interaction
  - Text normalization and synonym matching for robust option selection
  - Support for multiple input types with appropriate handling
  - **Resume file upload**: Fetches resume PDF from backend-provided signed URL, creates File object via DataTransfer API, attaches to `<input type="file">` elements
  - **Aggressive autofill**: LLM instructed to always use `action='autofill'` (skip only for unsupported file types like cover letters). Missing LLM responses default to `autofill` instead of `skip`.
- **Progress Tracking**: Real-time progress messages for all async operations
- **Session State Management**: Tracks user flow through idle → extracting → extracted → autofilling → autofilled → applied states
- **Job Status Awareness**: On popup open, calls `/extension/jobs/status` to check current page context:
  - Detects job board type (Lever, Ashby, Greenhouse) and page type (JD page vs application form)
  - For Lever/Ashby: Matches application form URLs (with `/apply` or `/application` suffix) to base JD URLs
  - Restores job context (title, company) and application state from server
  - Enables smart button display based on page type and job state
- **URL Security**: Prevents access to restricted URLs (chrome://, edge://, about:, file://)
- **Debug Tools**: `extractFormFieldsWithDropdownInteraction()` in background.js for verbose console-level extraction analysis (not exposed in popup UI)

## Backend API Endpoints
- `POST /extension/connect/exchange`: Exchange one-time code for JWT token
- `GET /extension/me`: Validate token and get user info
- `POST /extension/jobs/ingest`: Submit job posting URL and DOM for extraction
- `POST /extension/jobs/status`: Check job application status by URL
  - Accepts `url` (current tab URL)
  - Detects job board type (Lever, Ashby, Greenhouse) and page type (jd, application, combined)
  - For Lever/Ashby: Strips `/apply` or `/application` suffix to match base JD URL
  - Returns `found`, `page_type`, `state` (jd_extracted|autofill_generated|applied), `job_application_id`, `job_title`, `company`, `run_id` (page-specific, for restoring "Mark as Applied" functionality), `current_page_autofilled` (bool), `plan_summary` (for restoring autofill stats)
- `POST /extension/resume-match`: Get resume-to-job match analysis
  - Accepts `job_application_id`
  - Returns `score` (0-100), `matched_keywords` (array), `missing_keywords` (array)
  - Used by Resume Score tab to show how well user's resume matches the job
- `POST /extension/autofill/plan`: Generate autofill plan for application form
  - Accepts `extracted_fields` (array of structured field objects extracted by extension)
  - **Extension now provides dropdown options**: React Select options are pre-extracted by opening dropdowns programmatically
  - Backend converts JS field format to internal FormField format
  - Backend enriches country fields automatically (fallback if options missing)
  - **Plan caching**: Returns cached completed plan if one exists for same `job_application_id + page_url` (ignores DOM hash changes)
  - Returns autofill plan with field values, actions, confidence scores, and `resume_url` (signed URL for file uploads)

## Frontend Integration
- `/extension/connect`: Connection page that generates one-time codes
- `/home`: Main dashboard for viewing saved applications

## Build and Development

- **Build Tool**: Vite with React plugin
- **Build Output**: All files compiled to `dist/` folder (gitignored)
- **Build Process**:
  - `vite.config.js` (42 lines) configures build with:
    - React plugin for JSX transformation
    - Custom copy plugin that copies manifest.json, background.js, and content.js to dist after build
    - Popup entry point: `popup/index.html`
    - Output naming: entryFileNames `[name].js`, chunkFileNames `[name].js`, assetFileNames `[name].[ext]`
- **Development Scripts**:
  - `npm run dev`: Watch mode (`vite build --watch --mode development`) - rebuilds automatically on source changes
  - `npm run build`: Production build - generates optimized dist folder
  - `npm run preview`: Preview the built extension
- **Loading in Chrome**:
  - Build first with `npm run build`
  - Go to `chrome://extensions/` → Enable Developer mode
  - Click "Load unpacked" and select the `dist/` folder (not the root folder)
  - Extension reloads on each rebuild

## Configuration Files

- **package.json** (26 lines):
  - Name: `applyai-extension`, Version: `0.1.0`, Type: `module` (ES modules)
  - Dependencies: react ^18.2.0, react-dom ^18.2.0
  - DevDependencies: @tailwindcss/postcss ^4.1.18, @types/chrome ^0.0.254, @vitejs/plugin-react ^4.2.1, autoprefixer ^10.4.23, postcss ^8.5.6, tailwindcss ^4.1.18, vite ^5.0.8

- **tailwind.config.js** (52 lines):
  - Content paths: `./popup/**/*.{html,js,jsx}`
  - Custom Colors:
    - `primary`: Blue scale (50-900) - #f0f9ff to #0c4a6e, primary-600 is #0284c7
    - `accent`: Purple scale (50-900) - #faf5ff to #581c87, accent-500 is #a855f7
  - Custom Animations:
    - `fade-in`: 0.2s ease-in fadeIn
    - `slide-up`: 0.3s ease-out slideUp
    - `pulse-subtle`: 3s infinite pulse (cubic-bezier timing)
  - Custom Keyframes:
    - `fadeIn`: opacity 0 → 1
    - `slideUp`: translateY(10px) + opacity 0 → translateY(0) + opacity 1

- **postcss.config.js** (7 lines):
  - Plugins: @tailwindcss/postcss, autoprefixer

- **style.css**:
  - Imports Tailwind CSS via `@import "tailwindcss";`
  - Body: background #f9fafb (light gray), color #111827 (dark gray)
  - Custom scrollbar: 6px width, gray track (#f3f4f6), rounded thumb (#d1d5db → #9ca3af on hover)
  - **Explicit animation keyframes** (required for Chrome extension popup animation throttling):
    - `@keyframes spin` → `.animate-spin` (0.85s linear, forced running)
    - `@keyframes pulse-subtle` → `.animate-pulse-subtle` (3s, forced running)
    - `@keyframes slide-up` → `.animate-slide-up` (0.3s ease-out)
    - `@keyframes shimmer` → `.skeleton` (shimmer gradient bg-size 400px, 1.4s infinite)
  - All animation classes include `animation-play-state: running !important` to override Chrome's throttling

## UI Architecture (v0.2.0+)

- **Three-tier visual hierarchy**:
  1. **Primary zone**: Single dominant CTA (the natural next step) — `size="lg"` sky-600 ActionButton
  2. **Content card**: Job info, stats, status messages — `bg-white rounded-2xl shadow-md`
  3. **Footer utility strip**: Compact icon+text row for secondary/utility/destructive actions
- **Stepper-Driven Design**: All UI state derived from `useStepperState` hook
  - Single source of truth: connectionStatus + sessionState + jobStatus → derived UI
  - 4-step progress visualization: Connect → Extract → Autofill → Applied
  - Dynamic primary action button changes label, icon, loading/disabled state contextually
  - Primary action button is **hidden** in `autofilled` and `applied` states (footer and badge take over)
- **Footer Strip** (Grammarly-inspired compact bottom bar):
  - Inside card, separated by `border-t border-gray-100`, `bg-gray-50 rounded-b-2xl`
  - `autofilled`: 3 items — ↺ Run Again, ⊞ Dashboard, → Disconnect
  - All other connected states: 2 items — ⊞ Dashboard, → Disconnect
  - Disconnected: footer hidden entirely
- **Nav Cue** (Lever/Ashby flow): Amber banner shown when user is on JD page with saved job, guiding them to navigate to application form. Optionally includes direct link button for known platform URLs.
- **Timestamps**: Extraction and autofill times stored locally in `chrome.storage.local` (backend doesn't return them). Displayed as relative time ("3m ago") in JobCard and autofill stats.
- **Skeleton Loader**: 3-line shimmer animation during initial status check (`isCheckingStatus && !jobStatus`)
- **Animation Fix**: Chrome extension popups throttle CSS animations — all keyframes defined explicitly in `style.css` with `animation-play-state: running !important`
- **Component Library**: Reusable SVG icon components (`Icons.jsx`) replace inline SVGs
- **Color System**: Sky-600 primary, green for success/completed, amber for warnings/nav cues, red for errors/disconnect
- **Status Indicators**: StatusPill with dynamic text from stepper state

## Storage Schema
- `installId`: Unique UUID for extension installation
- `extensionToken`: JWT token for backend authentication
- `lastIngest`: Last job extraction result (includes job_application_id, job_title, company, timestamp, success status)
- `jobTimestamps`: Timestamps for the most recently interacted job application
  - Shape: `{ job_application_id?: string, extractedAt?: string (ISO), autofilledAt?: string (ISO) }`
  - Written provisionally (without `job_application_id`) immediately after extraction, then associated with the correct ID by `checkJobStatus()` once the backend returns it
  - Keyed by `job_application_id` — if the current job doesn't match, timestamps are ignored
  - Cleared on disconnect or when a new job is extracted on a different page
