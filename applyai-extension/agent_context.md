# Agent Context: applyai-extension

This folder contains the browser extension for the Application Tracker project. It includes the following files and directories:

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
  - `src/Popup.jsx` (~220 lines): Main popup component with stepper-driven architecture:
    - Uses `useExtension` hook for state/actions and `useStepperState` hook for UI derivation
    - Header card: Logo (sky gradient badge with BoltIcon), "ApplyAI" title, subtitle, StatusPill
    - **ProgressStepper**: 4-step visual progress bar (Connect → Extract → Autofill → Applied)
    - **Tabbed interface** (when connected + job extracted): Autofill tab and Resume Score tab
      - Tabs component switches between autofill workflow and resume match display
      - Resume Score tab lazy-loads match data via `fetchResumeMatch()` when selected
    - Main content card with conditional sections:
      - StatusMessage for operation progress/errors
      - JobCard for extracted job info
      - Autofill stats (green success box: "Filled X fields, skipped Y")
      - **"Mark as Applied" button**: Appears after autofill completion, calls `markAsApplied()`
      - Applied badge (green checkmark pill)
      - **ResumeMatchCard**: Displays resume match score, matched/missing keywords (in Resume Score tab)
    - **Single dynamic primary action button** driven by `useStepperState`:
      - Disconnected → "Connect to ApplyAI"
      - No job + JD page → "Extract Job"
      - No job + application page → "Extract Job First" (disabled, with hint)
      - Job found → "Generate Autofill" / "Autofill Again"
    - Secondary buttons (when connected): Dashboard, Debug (2-column grid), Disconnect
    - Layout: 380px width, 500px min-height, gray background
  - `src/style.css` (25 lines): Tailwind CSS styles (light theme with good contrast)
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
    - `Icons.jsx` (80 lines): SVG icon components used throughout the popup
      - CheckIcon, LinkIcon, DocumentTextIcon, SparklesIcon, CheckBadgeIcon
      - Squares2X2Icon (dashboard), BugAntIcon (debug), BoltIcon (logo), BriefcaseIcon (job card)
      - ArrowRightOnRectangleIcon (disconnect), SpinnerIcon (loading animation)
    - `ProgressStepper.jsx` (77 lines): Visual 4-step progress indicator
      - Steps: Connect → Extract → Autofill → Applied
      - Step states: completed (green circle + checkmark), active (sky circle + ring), pending (gray circle)
      - Connector lines between steps (green when completed, gray otherwise)
      - Icons mapped per step: LinkIcon, DocumentTextIcon, SparklesIcon, CheckBadgeIcon
    - `StatusMessage.jsx` (52 lines): Alert/notification component
      - Types: info, success, error, warning with color-coded backgrounds
      - Icons: Info circle, check circle, alert circle, warning triangle
      - Features: Slide-up animation
    - `JobCard.jsx` (27 lines): Compact card displaying extracted job information
      - BriefcaseIcon in sky gradient badge
      - Job title (semibold, truncated) and company name (gray, truncated)
      - Styling: White background, border, rounded-xl, shadow-sm
    - `Tabs.jsx`: Tab navigation component for switching between Autofill and Resume Score views
      - Accepts tabs array, activeTab, and onTabChange callback
      - Renders horizontal tab bar with active state styling
    - `ResumeMatchCard.jsx`: Displays resume-to-job match analysis
      - Shows match score (percentage), matched keywords (green badges), missing keywords (red badges)
      - Loading state with skeleton UI
      - Helps users understand how well their resume matches the job requirements
  - `src/hooks/`:
    - `useExtension.js` (~376 lines): Custom hook managing extension state and messaging
      - State: connectionStatus, userEmail, userName, sessionState, statusMessage, extractedJob, autofillStats, **jobStatus**, **isCheckingStatus**, **resumeMatch**, **isLoadingMatch**, **lastRunId**, **isMarkingApplied**
      - SessionState values: idle, extracting, extracted, autofilling, autofilled, **applied**, error
      - Functions: checkConnection(), connect(), disconnect(), openDashboard(), extractJob(), generateAutofill(), debugExtractFields(), **checkJobStatus()**, **fetchResumeMatch()**, **markAsApplied()**
      - **generateAutofill()**: Sends `APPLYAI_AUTOFILL_PLAN` message with `job_application_id` from `jobStatus` state (not relying on background script's `lastIngest` storage)
      - **checkJobStatus()**: Calls `POST /extension/jobs/status` with current tab URL to get job application state. Updates sessionState based on response (applied, autofilled, extracted, idle). Restores `lastRunId` from status response. Uses `skipNextResetRef` to prevent state reset after completing actions. Auto-refreshes after JD extraction.
      - **fetchResumeMatch()**: Calls `POST /extension/resume-match` with job_application_id. Returns score, matched_keywords, missing_keywords for display in ResumeMatchCard.
      - **markAsApplied()**: Sends `APPLYAI_MARK_APPLIED` message with `lastRunId` (stored from autofill result). Updates sessionState to 'applied' on success.
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
        - Job found → "Generate Autofill" / "Autofill Again" (handler: generateAutofill)
      - **Visibility flags**: showJobCard, showStatusMessage, messageType
      - All values memoized via `useMemo` on input dependencies

## Purpose
This folder provides the browser extension for the Application Tracker project. The extension enables users to:
1. **Connect** their browser to their ApplyAI account via secure one-time code authentication
2. **Extract** job descriptions from job posting pages and save them to the tracker
3. **Autofill** job application forms using AI-generated plans based on user profile and saved job data

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

### 4. Debug Extraction Flow (For Troubleshooting)
1. User navigates to job application form page
2. User clicks "🐛 Extract Form Fields (Debug)" button in popup
3. Background script runs `extractFormFieldsWithDropdownInteraction()`:
   - Same extraction logic as production autofill
   - Detailed console logging to page console showing:
     - Total field count
     - Fields with options count
     - Warnings for dropdowns with no options
     - Summary table of all fields
     - Full JSON data for analysis
4. Popup displays field count and success status
5. Developer opens page console to view detailed extraction results

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
- **Debug Tools**: Verbose extraction mode with detailed console logging for troubleshooting
  - Always-visible debug button in popup
  - Comprehensive field extraction analysis
  - Warnings for failed dropdown extractions
  - Full JSON output for manual inspection

## Backend API Endpoints
- `POST /extension/connect/exchange`: Exchange one-time code for JWT token
- `GET /extension/me`: Validate token and get user info
- `POST /extension/jobs/ingest`: Submit job posting URL and DOM for extraction
- `POST /extension/jobs/status`: Check job application status by URL
  - Accepts `url` (current tab URL)
  - Detects job board type (Lever, Ashby, Greenhouse) and page type (jd, application, combined)
  - For Lever/Ashby: Strips `/apply` or `/application` suffix to match base JD URL
  - Returns `found`, `page_type`, `state` (jd_extracted|autofill_generated|applied), `job_application_id`, `job_title`, `company`, `run_id` (for restoring "Mark as Applied" functionality)
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

- **style.css** (25 lines):
  - Imports Tailwind CSS via `@import "tailwindcss";`
  - Body: background #f9fafb (light gray), color #111827 (dark gray)
  - Custom scrollbar: 8px width, gray track (#f3f4f6), rounded thumb (#d1d5db → #9ca3af on hover)

## UI Architecture (v0.1.0+)

- **Stepper-Driven Design**: All UI state derived from `useStepperState` hook
  - Single source of truth: connectionStatus + sessionState + jobStatus → derived UI
  - 4-step progress visualization: Connect → Extract → Autofill → Applied
  - Dynamic primary action button changes label, icon, loading/disabled state contextually
- **Component Library**: Reusable SVG icon components (`Icons.jsx`) replace inline SVGs and emojis
- **Card-Based Layout**: Header card, stepper card, and content card with consistent rounded-xl styling
- **Color System**: Sky-600 primary, green for success/completed, amber for warnings, red for errors
- **Button Sizes**: lg (primary actions), md (secondary grid), sm (disconnect)
- **Status Indicators**: StatusPill with dynamic text from stepper state
- **Responsive Animations**: pulse-subtle for working state, transition-all on step circles/connectors

## Storage Schema
- `installId`: Unique UUID for extension installation
- `extensionToken`: JWT token for backend authentication
- `lastIngest`: Last job extraction result (includes job_application_id, job_title, company, timestamp, success status)
