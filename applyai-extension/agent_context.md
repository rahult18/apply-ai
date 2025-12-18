# Agent Context: applyai-extension

This folder contains the browser extension for the Application Tracker project. It includes the following files and directories:

## Structure
- `manifest.json`: The manifest file for the browser extension. It defines essential metadata like the extension's name, version, description, and permissions. It also declares the background script (`background.js`), content script (`content.js`), and the default popup (`popup/popup.html`). **New permissions `activeTab` and `scripting` have been added to support job description extraction.**
- `background.js`: This is the service worker for the extension, running in the background. It handles:
  - `installId` generation and storage: Ensures a unique ID for the extension installation.
  - Message listening: Specifically listens for `APPLYAI_EXTENSION_CONNECT` messages from the content script, which contain a one-time code from the web page. It also listens for `APPLYAI_EXTRACT_JD` messages from the popup to initiate job description extraction.
  - Code exchange: Exchanges the one-time code with the backend (`http://localhost:8000/extension/connect/exchange`) for an extension-specific JWT token.
  - Token storage: Stores the received JWT token in `chrome.storage.local`.
  - UI update notification: Notifies the popup script (via `chrome.runtime.sendMessage`) when the connection is successful, prompting a UI update.
  - **Job Description Extraction**: Handles the extraction of DOM HTML from the active tab and sends it to the backend's `/extension/jobs/ingest` endpoint for processing. It also sends progress and result messages back to the popup.
- `content.js`: This script runs on specific web pages (defined in `manifest.json` under `content_scripts`, currently `http://localhost:3000/extension/connect*`). Its primary function is to:
  - Listen for `APPLYAI_EXTENSION_CONNECT` messages from the web page (e.g., from the frontend's `ConnectExtensionPage`).
  - Forward these messages, including the one-time code, to the extension's `background.js` script for processing.
- `assets/`: Directory for static assets (icons, images, etc.) used by the extension (e.g., in the popup UI).
- `popup/`: Contains the UI and logic for the extension's popup window.
  - `popup.html`: The HTML structure for the extension's popup. It includes elements for displaying connection status, account information, and action buttons.
  - `popup.css`: Provides styling for the `popup.html` to create a visually appealing and branded interface.
  - `popup.js`: Contains the JavaScript logic for the popup UI. It handles:
  - UI updates: Dynamically updates the connection status (e.g., "Checking…", "Connected", "Not connected") and account details based on the presence and validity of the `extensionToken`.
  - **Job Extraction UI:** Manages the UI elements for job description extraction, including status messages, a result card, and the "Extract Job Description" button state.
  - Button actions:
    - "Connect" button: Opens a new tab to the frontend's extension connection page (`http://localhost:3000/extension/connect`).
    - "Open Dashboard" button: Opens a new tab to the frontend's home dashboard (`http://localhost:3000/home`).
    - "Disconnect" button: Removes the `extensionToken` from `chrome.storage.local` and updates the UI to reflect a disconnected state.
    - **"Extract Job Description" button:** Initiates the job description extraction process from the active tab.
  - Token validation: Fetches user data from the backend's `/extension/me` endpoint using the stored `extensionToken` to verify its validity and display the connected user's information.
  - Message listener: Listens for `APPLYAI_EXTENSION_CONNECTED` messages from the background script to trigger UI updates. Also listens for `APPLYAI_EXTRACT_JD_PROGRESS` to update extraction status and `APPLYAI_EXTRACT_JD_RESULT` to display extraction outcomes.

## Purpose
This folder is responsible for the browser extension functionality, enabling users to connect their browser to the main Application Tracker application. It facilitates a secure authentication flow using one-time codes and JWT tokens, allowing the extension to interact with the backend API on behalf of the user. The extension's popup provides a user-friendly interface to manage the connection status and quickly access the main application dashboard.

## Key Points
- **Authentication Flow**: The extension uses a secure one-time code exchange mechanism to authenticate with the backend, receiving a JWT token that is stored locally.
- **Background Script**: `background.js` acts as the central hub for handling authentication logic, token storage, and communication between the content script and the backend.
- **Content Script**: `content.js` acts as a bridge, securely forwarding one-time codes from the frontend web page to the background script.
- **Popup UI**: The `popup/` folder provides the user interface for the extension, allowing users to connect, disconnect, and navigate to the main application.
- **Job Description Extraction**: The extension now includes the ability to extract job posting details from the active tab and send them to the backend for tracking and analysis.
- **Backend Interaction**: The extension now interacts with the backend's `/extension/connect/exchange`, `/extension/me`, and `/extension/jobs/ingest` endpoints for authentication, user verification, and job application ingestion.
- **Frontend Interaction**: The extension interacts with the frontend's `/extension/connect` page to initiate the connection process and potentially other pages to navigate to the dashboard.
