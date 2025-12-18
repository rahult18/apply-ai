# Agent Context: applyai-extension

This folder contains the browser extension for the Application Tracker project. It includes the following files and directories:

## Structure
- `manifest.json`: The manifest file for the browser extension. It defines essential metadata like the extension's name, version, description, and permissions. It also declares the background script (`background.js`), content script (`content.js`), and the default popup (`popup/popup.html`).
- `background.js`: This is the service worker for the extension, running in the background. It handles:
  - `installId` generation and storage: Ensures a unique ID for the extension installation.
  - Message listening: Specifically listens for `APPLYAI_EXTENSION_CONNECT` messages from the content script, which contain a one-time code from the web page.
  - Code exchange: Exchanges the one-time code with the backend (`http://localhost:8000/extension/connect/exchange`) for an extension-specific JWT token.
  - Token storage: Stores the received JWT token in `chrome.storage.local`.
  - UI update notification: Notifies the popup script (via `chrome.runtime.sendMessage`) when the connection is successful, prompting a UI update.
- `content.js`: This script runs on specific web pages (defined in `manifest.json` under `content_scripts`, currently `http://localhost:3000/extension/connect*`). Its primary function is to:
  - Listen for `APPLYAI_EXTENSION_CONNECT` messages from the web page (e.g., from the frontend's `ConnectExtensionPage`).
  - Forward these messages, including the one-time code, to the extension's `background.js` script for processing.
- `assets/`: Directory for static assets (icons, images, etc.) used by the extension (e.g., in the popup UI).
- `popup/`: Contains the UI and logic for the extension's popup window.
  - `popup.html`: The HTML structure for the extension's popup. It includes elements for displaying connection status, account information, and action buttons.
  - `popup.css`: Provides styling for the `popup.html` to create a visually appealing and branded interface.
  - `popup.js`: Contains the JavaScript logic for the popup UI. It handles:
    - UI updates: Dynamically updates the connection status (e.g., "Checking…", "Connected", "Not connected") and account details based on the presence and validity of the `extensionToken`.
    - Button actions:
      - "Connect" button: Opens a new tab to the frontend's extension connection page (`http://localhost:3000/extension/connect`).
      - "Open Dashboard" button: Opens a new tab to the frontend's home dashboard (`http://localhost:3000/home`).
      - "Disconnect" button: Removes the `extensionToken` from `chrome.storage.local` and updates the UI to reflect a disconnected state.
    - Token validation: Fetches user data from the backend's `/extension/me` endpoint using the stored `extensionToken` to verify its validity and display the connected user's information.
    - Message listener: Listens for `APPLYAI_EXTENSION_CONNECTED` messages from the background script to trigger UI updates.

## Purpose
This folder is responsible for the browser extension functionality, enabling users to connect their browser to the main Application Tracker application. It facilitates a secure authentication flow using one-time codes and JWT tokens, allowing the extension to interact with the backend API on behalf of the user. The extension's popup provides a user-friendly interface to manage the connection status and quickly access the main application dashboard.

## Key Points
- **Authentication Flow**: The extension uses a secure one-time code exchange mechanism to authenticate with the backend, receiving a JWT token that is stored locally.
- **Background Script**: `background.js` acts as the central hub for handling authentication logic, token storage, and communication between the content script and the backend.
- **Content Script**: `content.js` acts as a bridge, securely forwarding one-time codes from the frontend web page to the background script.
- **Popup UI**: The `popup/` folder provides the user interface for the extension, allowing users to connect, disconnect, and navigate to the main application.
- **Backend Interaction**: The extension directly interacts with the backend's `/extension/connect/exchange` and `/extension/me` endpoints for authentication and user verification.
- **Frontend Interaction**: The extension interacts with the frontend's `/extension/connect` page to initiate the connection process and potentially other pages to navigate to the dashboard.
