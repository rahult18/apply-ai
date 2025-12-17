# Agent Context: applyai-extension

This folder contains the browser extension for the Application Tracker project. It includes the following files and directories:

## Structure
- `manifest.json`: The manifest file for the browser extension, defining permissions, scripts, and extension metadata.
- `assets/`: Directory for static assets (icons, images, etc.) used by the extension.
- `popup/`: Contains the UI and logic for the extension's popup window.
  - `popup.html`: The HTML file for the popup UI.
  - `popup.css`: Styles for the popup UI.
  - `popup.js`: JavaScript logic for the popup UI.

## Purpose
This folder is responsible for the browser extension functionality, which may interact with the main application or provide additional features for users directly in their browser. The exact services and endpoints are not defined in this folder, as it is focused on frontend extension logic and UI.

## Key Points
- No backend services or API endpoints are defined here.
- All logic is related to the browser extension's popup and static assets.
- The extension may communicate with the main application backend or frontend, but this is not defined in this folder.
