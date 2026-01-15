# ApplyAI Browser Extension

Modern Chrome extension built with React, Vite, and Tailwind CSS for autofilling job applications.

## Features

- 🎨 **Modern UI**: Built with React and Tailwind CSS
- ⚡ **Fast Development**: Powered by Vite with hot reload
- 🎯 **Enhanced UX**: Smooth animations and clear visual hierarchy
- 📊 **Better Status Display**: Improved messaging with icons and animations
- 🧩 **Component-Based**: Modular and maintainable architecture

## Development Setup

### Prerequisites

- Node.js 16+ and npm
- Chrome browser

### Installation

```bash
# Install dependencies
npm install
```

### Development

```bash
# Build in watch mode (rebuilds on file changes)
npm run dev
```

### Production Build

```bash
# Build for production
npm run build
```

The extension will be built to the `dist/` folder.

### Load Extension in Chrome

1. Build the extension (`npm run build`)
2. Open Chrome and navigate to `chrome://extensions/`
3. Enable "Developer mode" (toggle in top right)
4. Click "Load unpacked"
5. Select the `dist/` folder from this project

## Project Structure

```
applyai-extension/
├── popup/
│   ├── src/
│   │   ├── components/        # React components
│   │   │   ├── ActionButton.jsx
│   │   │   ├── JobCard.jsx
│   │   │   ├── StatusMessage.jsx
│   │   │   └── StatusPill.jsx
│   │   ├── hooks/             # Custom React hooks
│   │   │   └── useExtension.js
│   │   ├── Popup.jsx          # Main popup component
│   │   └── main.jsx           # React entry point
│   └── index.html             # HTML entry point
├── background.js              # Service worker
├── content.js                 # Content script
├── manifest.json              # Extension manifest
├── vite.config.js             # Vite configuration
└── package.json               # Dependencies
```

## Tech Stack

- **React 18**: UI framework
- **Vite 5**: Build tool and dev server
- **Tailwind CSS 3**: Utility-first styling (via CDN)
- **Chrome Extension API**: Browser integration

## UI Improvements

### Status Messages
- Clear visual hierarchy with icons
- Animated transitions (slide-up, fade-in)
- Color-coded by type (info, success, error, warning)

### Button Layout
- Primary action button always visible
- Secondary actions in grid layout
- Loading states with spinners
- Smooth hover effects

### Components
- **StatusPill**: Real-time connection/activity status
- **StatusMessage**: Detailed progress messages with icons
- **JobCard**: Enhanced job display with metadata
- **ActionButton**: Reusable button with loading states

## Scripts

- `npm run dev`: Build in watch mode for development
- `npm run build`: Production build
- `npm run preview`: Preview production build (Vite server)

## Notes

- The extension requires the backend API running at `http://localhost:8000`
- Frontend must be running at `http://localhost:3000` for OAuth connection flow
- Build output is in `dist/` (not tracked in git)
