# ApplyAI Browser Extension

Chrome extension for AI-powered job application autofill, job description extraction, and application tracking. Built with React, Vite, and Tailwind CSS.

## Features

- **Secure Connection**: One-time code authentication with your ApplyAI account
- **Job Extraction**: Capture job descriptions from any job posting page (Lever, Ashby, Greenhouse, LinkedIn, etc.)
- **AI Autofill**: Generate and apply intelligent form-filling plans using your profile and resume
  - React Select component support (programmatic dropdown opening to extract options)
  - Native `<select>`, radio groups, checkbox groups, and text inputs
  - Resume file upload via DataTransfer API
  - Text normalization and synonym matching (e.g. "US" → "United States")
- **Resume Match Score**: See how well your resume matches a job (score, matched/missing keywords)
- **Application Tracking**: Track state through extracted → autofilled → applied with timestamps
- **Smart Page Detection**: Detects job board type and page type (JD vs application form) on popup open
- **NavCue**: Amber banner guiding users from JD pages to application form pages (Lever/Ashby)

## Development Setup

### Prerequisites

- Node.js 16+ and npm
- Chrome browser
- Backend running at `http://localhost:8000`
- Frontend running at `http://localhost:3000`

### Installation

```bash
npm install
```

### Development (watch mode)

```bash
npm run dev
```

Rebuilds automatically on file changes. Reload the extension in `chrome://extensions/` after each build.

### Production Build

```bash
npm run build
```

Output is in `dist/`.

### Load Extension in Chrome

1. Run `npm run build`
2. Go to `chrome://extensions/`
3. Enable **Developer mode** (toggle in top right)
4. Click **Load unpacked** and select the `dist/` folder
5. Reload after each build (`npm run dev` → save a file → reload extension)

## Project Structure

```
applyai-extension/
├── popup/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ActionButton.jsx      # Button with variants, sizes, loading state
│   │   │   ├── Icons.jsx             # SVG icon components
│   │   │   ├── JobCard.jsx           # Extracted job info card with timestamp
│   │   │   ├── NavCue.jsx            # Amber banner for JD → application navigation
│   │   │   ├── ProgressStepper.jsx   # 4-step progress bar (Connect → Extract → Autofill → Applied)
│   │   │   ├── ResumeMatchCard.jsx   # Resume match score and keyword display
│   │   │   ├── StatusMessage.jsx     # Alert/notification with type-based colors
│   │   │   ├── StatusPill.jsx        # Connection status badge
│   │   │   └── Tabs.jsx              # Tab bar for Autofill / Resume Score views
│   │   ├── hooks/
│   │   │   ├── useExtension.js       # Core state and messaging hook (~452 lines)
│   │   │   └── useStepperState.js    # Derived UI state hook (~144 lines)
│   │   ├── Popup.jsx                 # Main popup component (~284 lines)
│   │   ├── main.jsx                  # React entry point
│   │   └── style.css                 # Tailwind + explicit animation keyframes
│   └── index.html
├── background.js                     # Service worker (~1,650 lines)
├── content.js                        # Content script bridge (~18 lines)
├── manifest.json                     # Extension manifest (Manifest V3)
├── vite.config.js                    # Vite build config with copy plugin
└── package.json
```

## Key Workflows

### 1. Connection Flow
1. User clicks **Connect** in popup → opens `/extension/connect` in frontend
2. Frontend generates one-time code → sends `APPLYAI_EXTENSION_CONNECT` via `window.postMessage()`
3. Content script forwards message to background script
4. Background exchanges code for JWT at `POST /extension/connect/exchange`
5. Token stored in `chrome.storage.local`; popup notified and updates UI

### 2. Job Extraction Flow
1. User navigates to a job posting page
2. User clicks **Extract Job** in popup
3. Background extracts full DOM HTML from active tab (2.5MB limit)
4. DOM sent to `POST /extension/jobs/ingest` with JWT
5. Backend uses Gemini to parse job title, company, and description
6. Popup displays job card; button changes to **Generate Autofill**

### 3. Autofill Flow
1. User navigates to the job application form page
2. User clicks **Generate Autofill** in popup
3. Background extracts DOM HTML and structured form fields:
   - Finds all React Select components (`[role="combobox"]`)
   - Programmatically opens each dropdown (MouseEvent + KeyboardEvent dispatch, 300ms wait)
   - Extracts options from opened dropdowns via aria-controls listbox or menu containers
   - Extracts labels, selectors, types, and required status for all fields
4. Fields and DOM sent to `POST /extension/autofill/plan`
5. Backend generates autofill plan using LLM with user profile and resume context
6. Plan applied to page: fills text inputs, selects, React Selects, radios, checkboxes, and file inputs
7. Popup shows filled/skipped counts; **Mark as Applied** CTA appears

### 4. Mark as Applied Flow
1. User clicks **Mark as Applied** after autofill
2. Background calls `POST /extension/autofill/submit` with `run_id`
3. Backend marks run as submitted and updates job application status to `applied`
4. Popup shows applied badge

## Architecture

### `background.js` (Service Worker)
Core logic running as a Manifest V3 service worker:
- **Storage helpers**: `storageGet()` / `storageSet()` for `chrome.storage.local`
- **DOM extraction**: `extractDomHtmlFromTab()` — injects script to capture full page HTML
- **Form field extraction**: `extractFormFieldsFromTab()` — DOMParser-based extraction with React Select dropdown interaction
- **Autofill application**: `applyAutofillPlanToTab()` — applies plan with full framework compatibility
- **URL security**: `isRestrictedUrl()` — blocks chrome://, edge://, about:, file:// URLs

Message handlers: `APPLYAI_EXTENSION_CONNECT`, `APPLYAI_DEBUG_EXTRACT_FIELDS`, `APPLYAI_EXTRACT_JD`, `APPLYAI_AUTOFILL_PLAN`, `APPLYAI_MARK_APPLIED`

### `useExtension.js` (Core Hook)
Manages all extension state and backend communication:
- **State**: `connectionStatus`, `sessionState`, `jobStatus`, `extractedJob`, `autofillStats`, `resumeMatch`, `lastRunId`, timestamps
- **Session states**: `idle → extracting → extracted → autofilling → autofilled → applied → error`
- **Key functions**: `checkConnection()`, `connect()`, `disconnect()`, `extractJob()`, `generateAutofill()`, `checkJobStatus()`, `fetchResumeMatch()`, `markAsApplied()`
- `checkJobStatus()` runs on popup open to restore prior session state from the backend and local storage

### `useStepperState.js` (UI Derivation Hook)
Derives all UI state from extension state — single source of truth for button labels, stepper steps, visibility flags, and status pill text.

## Storage Schema

| Key | Value |
|-----|-------|
| `installId` | Unique UUID for this installation |
| `extensionToken` | JWT for backend authentication |
| `lastIngest` | Last extraction result (job_application_id, job_title, company) |
| `jobTimestamps` | `{ job_application_id?, extractedAt?, autofilledAt? }` |

## UI Architecture

- **3-zone layout**: Header (logo + status) → ProgressStepper → Content card
- **Tabbed interface**: Autofill tab + Resume Score tab (when job found and connected)
- **Footer strip**: Compact utility actions (Dashboard, Disconnect, Run Again) inside content card
- **Primary CTA**: Single dominant action button driven by stepper state; hidden in `autofilled`/`applied` states
- **Animation fix**: Chrome extension popups throttle CSS animations — all keyframes defined explicitly in `style.css` with `animation-play-state: running !important`

## Backend API Endpoints

| Endpoint | Description |
|----------|-------------|
| `POST /extension/connect/exchange` | Exchange one-time code for JWT |
| `GET /extension/me` | Validate token and get user info |
| `POST /extension/jobs/ingest` | Submit job posting URL/DOM for extraction |
| `POST /extension/jobs/status` | Check job status by current tab URL |
| `POST /extension/resume-match` | Get resume-to-job match score |
| `POST /extension/autofill/plan` | Generate autofill plan (cached by job_id + page_url) |
| `POST /extension/autofill/submit` | Mark application as submitted |

## Tech Stack

- **React 18** — UI framework
- **Vite 5** — Build tool with watch mode
- **Tailwind CSS 4** — Utility-first styling (via PostCSS)
- **Chrome Extension Manifest V3** — Service worker + content script architecture

## Scripts

| Script | Description |
|--------|-------------|
| `npm run dev` | Watch mode — rebuild on file changes |
| `npm run build` | Production build to `dist/` |
| `npm run preview` | Preview production build via Vite server |

## Notes

- Requires backend at `http://localhost:8000` and frontend at `http://localhost:3000`
- Build output in `dist/` is gitignored — always load from `dist/` not the source root
- Plan caching: backend returns existing completed plan for same `job_application_id + page_url` pair
- Country fields are automatically enriched with 196 countries by the backend if options are missing from the DOM
