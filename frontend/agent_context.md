# Agent Context: frontend

This folder contains the Next.js frontend for the Application Tracker project. It is responsible for the user interface, authentication, and communication with the backend API.

## Structure
- `app/`: Main application pages and routes (using Next.js App Router)
  - `globals.css`: Global Tailwind CSS styles and custom CSS variables for theming.
  - `layout.tsx`: Root layout for the application, setting up metadata, importing global styles, and providing the `AuthProvider` for the entire app.
  - `page.tsx`: The main landing page. If a user is not authenticated, it redirects to `/login`, otherwise to `/home`.
  - `extension/`: Pages related to browser extension connection.
    - `connect/page.tsx`: Handles the connection process for the browser extension. It fetches a one-time code from the backend and uses `window.postMessage` to send it to the extension for authentication.
  - `home/`: Main user dashboard.
    - `page.tsx`: The home dashboard displays job application statistics, charts (Applications Over Time, Status Distribution), and a table of all applications. It fetches application data and KPI data from the backend.

    - `profile/page.tsx`: Displays and allows editing of the user's profile information. It fetches and updates profile data (including resume upload/deletion, monitoring resume parsing status, and displaying parsed resume data) via backend API calls.
  - `login/page.tsx`: User login page, allowing users to log in with email/password or Google. Interacts with `AuthContext` for authentication logic.
  - `signup/page.tsx`: User signup page, allowing new users to register with email/password or Google. Interacts with `AuthContext` for registration logic.
- `components/`: Reusable UI components.
  - `Navbar.tsx`: The main navigation bar, displaying links to Home, Add to Tracker, and Profile, along with user's email and a logout button. It uses `next/navigation` and `AuthContext`.
  - `ui/`: UI primitives (built with shadcn/ui and Tailwind CSS).
    - `badge.tsx`: A customizable badge component with various status-specific variants (e.g., saved, applied, interviewing).
    - `button.tsx`: A customizable button component with different variants and sizes.
    - `card.tsx`: Components for displaying content in a card format, including `Card`, `CardHeader`, `CardTitle`, `CardDescription`, `CardContent`, and `CardFooter`.
    - `checkbox.tsx`: A customizable checkbox component.
    - `input.tsx`: A customizable input field component.
    - `label.tsx`: A customizable label component for form elements.
    - `navigation-menu.tsx`: A navigation menu component for building accessible navigation.
    - `select.tsx`: A customizable select dropdown component.
    - `textarea.tsx`: A customizable textarea component.
  - `widgets/`: Dashboard widgets.
    - `ApplicationsOverTimeChart.tsx`: Displays a bar chart showing the number of applications over time using `recharts`.
    - `ApplicationsTable.tsx`: Displays a table of all job applications with details like job title, company, status, application date, source, and visa sponsorship, using the `Badge` component for status visualization.
    - `KPICard.tsx`: A generic card component to display Key Performance Indicator (KPI) values with an icon and optional trend information.
    - `StatusChart.tsx`: Displays a pie chart showing the distribution of job application statuses using `recharts`.
- `contexts/`: React Contexts.
  - `AuthContext.tsx`: Provides authentication state (`user`, `loading`) and functions (`login`, `signup`, `logout`, `loginWithGoogle`, `signupWithGoogle`) to the entire application. It manages user sessions using cookies and interacts with the backend authentication endpoints.
- `lib/`: Utility functions.
  - `utils.ts`: Contains general utility functions, including `cn` for conditionally joining Tailwind CSS classes.
- `public/`: Static assets (not shown above, but standard for Next.js).

## Services & Endpoints
- Communicates with the backend API (default: `http://localhost:8000`), configurable via the `NEXT_PUBLIC_API_URL` environment variable.
- Handles authentication (login, signup, user info) through `AuthContext` interacting with `/auth/*` backend endpoints.
- Manages job application data (add, view, profile, dashboard) by interacting with `/db/*` and `/scrape` backend endpoints.
- Facilitates connection with the browser extension via `/extension/connect/*` backend endpoints.

## Key Components
- **Authentication**: Implemented through `AuthContext` for consistent state management across login, signup, and protected routes.
- **Dashboard**: The `/home` page serves as the central dashboard, utilizing various widgets to visualize application data.
- **Widgets**: Reusable components like `ApplicationsOverTimeChart`, `ApplicationsTable`, `KPICard`, and `StatusChart` for data display.
- **UI Primitives**: A comprehensive set of `shadcn/ui` components ensures a consistent and modern look and feel.
- **Context**: `AuthContext` is crucial for managing and providing user authentication state throughout the application.

## Notes
- All API endpoints are provided by the backend (see backend context for details).
- No backend logic or endpoints are defined here; this is a frontend-only folder.
- Uses `shadcn/ui` for modern UI components.
- Responsive design is implemented using Tailwind CSS.
- `next/navigation` hooks are used for client-side routing and programmatic navigation.
- Data fetching is typically handled within `useEffect` hooks or event handlers, making calls to the backend API.
