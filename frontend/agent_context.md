# Agent Context: frontend

This folder contains the Next.js frontend for the Application Tracker project. It is responsible for the user interface, authentication, and communication with the backend API.

## Structure
- `app/`: Main application pages and routes (using Next.js App Router)
  - `globals.css`: Global styles
  - `layout.tsx`: Root layout for the app
  - `page.tsx`: Main landing page
  - `extension/`: Pages related to browser extension connection
    - `connect/page.tsx`: Extension connection page
  - `home/`: Main user dashboard
    - `page.tsx`: Home dashboard
    - `add/page.tsx`: Add new application page
    - `profile/page.tsx`: User profile page
  - `login/page.tsx`: Login page
  - `signup/page.tsx`: Signup page
- `components/`: Reusable UI components
  - `Navbar.tsx`: Navigation bar
  - `ui/`: UI primitives (badge, button, card, checkbox, input, label, navigation-menu, select, textarea)
  - `widgets/`: Dashboard widgets (ApplicationsOverTimeChart, ApplicationsTable, KPICard, StatusChart)
- `contexts/`: React Contexts
  - `AuthContext.tsx`: Authentication context provider
- `lib/`: Utility functions
  - `utils.ts`: General utilities
- `public/`: Static assets (not shown above, but standard for Next.js)

## Services & Endpoints
- Communicates with the backend API (default: `http://localhost:8000`)
- Uses environment variable `NEXT_PUBLIC_API_URL` for backend URL
- Handles authentication (login, signup, user info)
- Handles job application data (add, view, profile, dashboard)

## Key Components
- **Authentication**: Login, signup, and protected routes
- **Dashboard**: Home page with charts and tables for applications
- **Widgets**: Visual components for displaying application data
- **UI Primitives**: Reusable styled components
- **Context**: AuthContext for managing user authentication state

## Notes
- All API endpoints are provided by the backend (see backend context)
- No backend logic or endpoints are defined here; this is a frontend-only folder
- Uses shadcn/ui for modern UI components
- Responsive design with Tailwind CSS
