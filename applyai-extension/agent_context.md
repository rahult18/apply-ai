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
  - **Autofill application**: `applyAutofillPlanToTab(tabId, planJson)` applies autofill plans with sophisticated form filling:
    - Supports text inputs, native selects, React Select components, radio groups, and checkbox groups
    - React Select detection via `role="combobox"` or `aria-autocomplete="list"`
    - Advanced option matching with text normalization and synonym support (e.g., "US" → "United States")
    - Triggers proper React events (input, change, keydown) for framework compatibility
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
     - Receives `plan_json` with fields array (each field has: action, selector, input_type, value, question_signature, options)
     - Applies plan to page using `applyAutofillPlanToTab()`
     - Sends progress messages: `APPLYAI_AUTOFILL_PROGRESS` (stages: starting, extracting_dom, extracting_fields, planning, autofilling)
     - Sends result: `APPLYAI_AUTOFILL_RESULT` (includes ok, run_id, plan_summary, filled, skipped, errors)

- `content.js`: Content script bridge (~18 lines)
  - Listens for `APPLYAI_EXTENSION_CONNECT` messages from web page via `window.addEventListener("message")`
  - Only accepts messages from same origin (security check)
  - Forwards messages to background script via `chrome.runtime.sendMessage()`

- `assets/`: Directory for static assets (icons, images) used by the extension

- `popup/`: Extension popup UI (React + Vite + Tailwind)
  - `index.html` (13 lines): Entry point that loads the built popup.js from Vite
  - `src/main.jsx` (11 lines): React entry point that renders Popup component into #root
  - `src/Popup.jsx` (194 lines): Main popup component with:
    - Header with logo (blue-purple gradient badge), "ApplyAI" title, subtitle "Autofill applications faster", and status pill
    - Account info display with connection status (shows userName or userEmail when connected)
    - Status messages for operation progress (conditional rendering based on sessionState)
    - Job card display for extracted job info (job_title, company, "Saved to tracker" meta)
    - Autofill stats display (green success box showing "Filled X fields, skipped Y")
    - Action buttons: Connect, Extract Job/Generate Autofill (dynamic), Dashboard, Debug, Disconnect
    - Contextual hints for user guidance based on current state
    - Layout: 380px width, 500px min-height, gray background
  - `src/style.css` (25 lines): Tailwind CSS styles (light theme with good contrast)
  - `src/components/`:
    - `ActionButton.jsx` (52 lines): Reusable button component with variants (primary, secondary, danger, ghost)
      - Primary: Blue background (#0284c7) with white text, shadow
      - Secondary: White background with dark text and gray border
      - Danger: Red background with white text and red border
      - Ghost: Gray background with dark text
      - Features: Loading state with spinner, disabled state styling, flex layout
    - `StatusPill.jsx` (24 lines): Status indicator badge with color-coded states
      - checking: Gray
      - connected: Green
      - disconnected: Amber/Yellow
      - error: Red
      - working: Blue with pulse animation
    - `StatusMessage.jsx` (52 lines): Alert/notification component
      - Types: info, success, error, warning with color-coded backgrounds
      - Icons: Info circle, check circle, alert circle, warning triangle
      - Features: Slide-up animation
    - `JobCard.jsx` (56 lines): Card displaying extracted job information
      - Job icon (briefcase in blue badge)
      - Job title (bold, truncated)
      - Company name (gray text, truncated)
      - "Saved to tracker" badge with checkmark
      - Styling: White background, light border, shadow, slide-up animation
  - `src/hooks/`:
    - `useExtension.js` (202 lines): Custom hook managing extension state and messaging
      - State: connectionStatus, userEmail, userName, sessionState, statusMessage, extractedJob, autofillStats
      - Functions: checkConnection(), connect(), disconnect(), openDashboard(), extractJob(), generateAutofill(), debugExtractFields()
      - Message listeners for: APPLYAI_EXTENSION_CONNECTED, APPLYAI_EXTRACT_JD_PROGRESS, APPLYAI_EXTRACT_JD_RESULT, APPLYAI_AUTOFILL_PROGRESS, APPLYAI_AUTOFILL_RESULT
      - API URLs: APP_BASE_URL (localhost:3000), API_BASE_URL (localhost:8000)

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
   - Handles various input types (text, select, radio, checkbox, React Select)
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
- **Progress Tracking**: Real-time progress messages for all async operations
- **Session State Management**: Tracks user flow through idle → extracting → extracted → autofilling states
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
- `POST /extension/autofill/plan`: Generate autofill plan for application form
  - Accepts `extracted_fields` (array of structured field objects extracted by extension)
  - **Extension now provides dropdown options**: React Select options are pre-extracted by opening dropdowns programmatically
  - Backend converts JS field format to internal FormField format
  - Backend enriches country fields automatically (fallback if options missing)
  - Returns autofill plan with field values, actions, and confidence scores

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

## UI Improvements (v0.1.0+)

- **High Contrast Design**: All text is clearly visible on light backgrounds
  - Button text: Bold, larger font size (text-base), increased padding (py-3)
  - Primary button: Blue background (#0284c7) with white text
  - Secondary button: White background with dark text (#111827) and visible border
  - Danger button: Red background with white text
  - Ghost/Debug button: Gray background with dark text
- **Status Indicators**: Color-coded status pills with high contrast
  - Connected: Green background with dark green text
  - Disconnected: Yellow background with dark yellow text
  - Error: Red background with dark red text
  - Working: Blue background with animation and dark blue text
- **Status Messages**: High contrast colored alerts matching message type
  - Info: Blue background with dark blue text
  - Success: Green background with dark green text
  - Error: Red background with dark red text
  - Warning: Amber background with dark amber text

## Storage Schema
- `installId`: Unique UUID for extension installation
- `extensionToken`: JWT token for backend authentication
- `lastIngest`: Last job extraction result (includes job_application_id, job_title, company, timestamp, success status)
