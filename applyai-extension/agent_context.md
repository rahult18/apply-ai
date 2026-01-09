# Agent Context: applyai-extension

This folder contains the browser extension for the Application Tracker project. It includes the following files and directories:

## Structure
- `manifest.json`: The manifest file for the browser extension. It defines essential metadata like the extension's name ("ApplyAI"), version (0.1.0), description, and permissions. It declares:
  - Background service worker: `background.js`
  - Content script: `content.js` (runs on `http://localhost:3000/extension/connect*`)
  - Default popup: `popup/popup.html`
  - Permissions: `storage`, `tabs`, `activeTab`, `scripting`
  - Host permissions: `http://localhost:3000/*`, `http://localhost:8000/*`

- `background.js`: The main service worker running in the background (~1111 lines). Key functionality:
  - **Storage helpers**: `storageGet()` and `storageSet()` for Chrome local storage
  - **Install ID management**: `ensureInstallId()` generates and stores a unique installation UUID
  - **Tab interaction**: `getActiveTab()` gets the current active tab
  - **DOM extraction**: `extractDomHtmlFromTab(tabId)` injects script into tab to extract full DOM HTML and URL
  - **Form field extraction**: `extractFormFieldsFromTab(tabId)` extracts structured form fields using JavaScript DOMParser:
    - Detects inputs, textareas, selects, comboboxes (React Select), radio groups, and checkbox groups
    - Generates CSS selectors for each field (#id or [name="..."])
    - Extracts labels via multiple strategies (for attribute, parent label, aria-label, placeholder)
    - Determines if fields are required (required attribute, aria-required, asterisk in label)
    - Extracts options from native selects and React Select components (when expanded)
    - Filters out React Select internal validation inputs (.requiredInput, hidden inputs in .select__container)
    - Returns structured JSON: type, inputType, name, id, label, placeholder, required, selector, options, autocomplete, isCombobox
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

  2. `APPLYAI_EXTRACT_JD`: Job description extraction
     - Validates token and active tab
     - Extracts DOM HTML from current page
     - Enforces 2.5MB size limit on DOM HTML
     - POSTs to `/extension/jobs/ingest` with `job_link` and `dom_html`
     - Stores result in `lastIngest` (includes job_application_id, job_title, company)
     - Sends progress messages: `APPLYAI_EXTRACT_JD_PROGRESS` (stages: starting, extracting_dom, sending_to_backend)
     - Sends result: `APPLYAI_EXTRACT_JD_RESULT` (includes ok, url, job_application_id, job_title, company)

  3. `APPLYAI_AUTOFILL_PLAN`: Autofill generation and application
     - Validates token, retrieves job_application_id from message or lastIngest
     - Extracts DOM HTML from active tab (enforces 2.5MB limit)
     - **Extracts structured form fields** using `extractFormFieldsFromTab()` (JavaScript DOMParser)
     - POSTs to `/extension/autofill/plan` with `job_application_id`, `page_url`, `dom_html`, and `extracted_fields`
     - Backend receives pre-extracted fields (no server-side parsing needed)
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

- `popup/`: Extension popup UI
  - `popup.html`: Popup structure with:
    - Header with logo, "ApplyAI" title, subtitle "Autofill job applications faster", and status pill
    - Card with account info display
    - Action buttons: Connect, Extract/Autofill (dynamic), Open Dashboard, Disconnect
    - Result card for displaying extracted job info (job_title, company, "Saved to tracker" meta)
    - Status messages for operation progress
    - Contextual hints for user guidance
    - **Note**: References `.result*` CSS classes that are not defined in popup.css

  - `popup.css`: Dark theme styling with:
    - CSS variables for colors (dark background with gradient overlays)
    - Status pill styles for different states: idle, ok (green), warn (yellow), err (red)
    - Button styles: primary (gradient), ghost, danger
    - Card layouts with borders and shadows
    - **Missing**: `.result`, `.result__title`, `.result__company`, `.result__divider`, `.result__meta` styles (referenced in HTML but not defined)

  - `popup.js`: Popup UI logic (~293 lines)
    - **Session state management**: idle → extracting → extracted → autofilling → autofilled → error
    - **Connection status checking**: Calls `/extension/me` on load to validate token
    - **Dynamic UI modes**:
      - Disconnected: Shows "Connect" button
      - Connected: Shows "Extract Job Description" button, "Open Dashboard", and "Disconnect"
      - After extraction: Button changes to "Generate Autofill", shows result card with job info
      - During operations: Button disabled with progress text
    - **Button handlers**:
      - Connect: Opens `http://localhost:3000/extension/connect`
      - Extract/Autofill: Sends `APPLYAI_EXTRACT_JD` (idle state) or `APPLYAI_AUTOFILL_PLAN` (extracted state)
      - Open Dashboard: Opens `http://localhost:3000/home`
      - Disconnect: Removes token from storage
    - **Message listeners**:
      - `APPLYAI_EXTENSION_CONNECTED`: Refreshes UI after connection
      - `APPLYAI_EXTRACT_JD_PROGRESS`: Updates status during extraction
      - `APPLYAI_EXTRACT_JD_RESULT`: Shows result card with job title/company, changes button to "Generate Autofill"
      - `APPLYAI_AUTOFILL_PROGRESS`: Updates status during autofill
      - `APPLYAI_AUTOFILL_RESULT`: Shows filled field count, updates status pill

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
4. **Background script extracts structured form fields** using JavaScript DOMParser:
   - Identifies all form inputs, textareas, selects, and React Select components
   - Generates CSS selectors and extracts labels, options, and metadata
   - Filters out React Select internal validation inputs
5. Both DOM HTML and structured fields sent to `/extension/autofill/plan` with job_application_id
6. Backend processes pre-extracted fields:
   - Converts JavaScript field format to internal FormField format
   - Enriches country/nationality fields with standard country list (196 countries)
   - Generates answers using LLM based on user profile, resume, and job requirements
7. Backend generates autofill plan (field selectors, values, actions, confidence scores)
8. Plan applied to page via `applyAutofillPlanToTab()`:
   - Identifies form fields by CSS selectors
   - Handles various input types (text, select, radio, checkbox, React Select)
   - Fills values and triggers appropriate events
9. Popup displays filled field count

## Key Technical Features
- **Secure Authentication**: One-time code exchange for JWT tokens, stored in chrome.storage.local
- **DOM Extraction**: On-demand script injection to capture full page HTML (with 2.5MB size limit)
- **Intelligent Form Field Extraction**: JavaScript DOMParser-based extraction in browser context
  - Parses live DOM (handles React and JavaScript-rendered forms)
  - Multi-strategy label detection (for attribute, parent labels, aria-label, placeholder)
  - Required field detection (required attribute, aria-required, asterisk in labels)
  - React Select component detection and option extraction
  - Filters out framework internal inputs (React Select validation inputs)
  - Country field enrichment (backend automatically adds 196 countries to country/nationality fields)
- **Smart Form Filling**:
  - React framework compatibility via native property setters and proper event triggering
  - React Select component detection and interaction
  - Text normalization and synonym matching for robust option selection
  - Support for multiple input types with appropriate handling
- **Progress Tracking**: Real-time progress messages for all async operations
- **Session State Management**: Tracks user flow through idle → extracting → extracted → autofilling states
- **URL Security**: Prevents access to restricted URLs (chrome://, edge://, about:, file://)

## Backend API Endpoints
- `POST /extension/connect/exchange`: Exchange one-time code for JWT token
- `GET /extension/me`: Validate token and get user info
- `POST /extension/jobs/ingest`: Submit job posting URL and DOM for extraction
- `POST /extension/autofill/plan`: Generate autofill plan for application form
  - **New**: Accepts `extracted_fields` (array of structured field objects extracted by extension)
  - Backend converts JS field format to internal FormField format
  - Backend enriches country fields automatically
  - Returns autofill plan with field values, actions, and confidence scores

## Frontend Integration
- `/extension/connect`: Connection page that generates one-time codes
- `/home`: Main dashboard for viewing saved applications

## Known Issues
- **Missing CSS**: popup.html references `.result*` CSS classes that are not defined in popup.css (result card may not display properly)

## Storage Schema
- `installId`: Unique UUID for extension installation
- `extensionToken`: JWT token for backend authentication
- `lastIngest`: Last job extraction result (includes job_application_id, job_title, company, timestamp, success status)
