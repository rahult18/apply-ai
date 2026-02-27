# Agent Context: frontend

This folder contains the Next.js 14 frontend for the Application Tracker (ApplyAI) project. Built with TypeScript, React, and Tailwind CSS, it provides the user interface for authentication, job application tracking, profile management, and browser extension integration.

**Total Source Files**: ~55 files (excluding node_modules and .next)

## Tech Stack
- **Framework**: Next.js 14.2.0 with App Router
- **Language**: TypeScript 5.5.0
- **Styling**: Tailwind CSS 3.4.0 with tailwindcss-animate, class-variance-authority
- **UI Components**: shadcn/ui (New York style, built on Radix UI primitives)
- **Icons**: Lucide React 0.378.0
- **Charts**: Recharts 2.15.4
- **Toast Notifications**: Sonner 2.0.7
- **Theme**: next-themes 0.4.6 (dark mode support)
- **State Management**: React Context API
- **Font**: Inter (Google Fonts)
- **Authentication**: @supabase/supabase-js 2.97.0, @supabase/ssr 0.8.0 (Google OAuth via Supabase)

## Structure

### `app/` - Application Routes (Next.js App Router)

- **`layout.tsx`**: Root layout (~26 lines)
  - Sets up Inter font from Google Fonts
  - Defines metadata: title "Application Tracker", description "Track your job applications"
  - Wraps entire app in `AuthProvider` for global auth state
  - Renders `children` within `<html>` and `<body>` tags

- **`page.tsx`**: Landing page / route handler (~14 lines)
  - Server component that checks for authentication token in cookies
  - Redirects to `/login` if no token found
  - Redirects to `/home` if authenticated
  - Acts as gateway to determine initial route

- **`globals.css`**: Global styles with Tailwind directives and CSS variables for theming

- **`login/page.tsx`**: Login page (~199 lines)
  - Client component with two-column design (hidden on mobile)
  - **Left Side**: Branding panel with ApplyAI logo (`/logo.png`), gradient background, and value proposition text
  - **Right Side**: Login form in card layout
  - Email/password authentication with validation
  - Google OAuth login button
  - Error state handling and loading spinner
  - Link to signup page
  - Calls `login()` and `loginWithGoogle()` from AuthContext

- **`signup/page.tsx`**: Signup page (~203 lines)
  - Client component with two-column design (hidden on mobile)
  - **Left Side**: Branding panel with features list (checkmarks for: Automatic job tracking, Dashboard analytics, Visa sponsorship filtering, Resume parsing)
  - **Right Side**: Registration form in card layout
  - Email/password signup with validation (8 character minimum hint)
  - Google OAuth signup button
  - Error handling and loading states
  - Link to login page
  - Calls `signup()` and `signupWithGoogle()` from AuthContext

- **`auth/callback/route.ts`**: OAuth callback handler (~50 lines)
  - Server-side route handler for Google OAuth callback
  - Uses server-side Supabase client (`@/lib/supabase/server`)
  - Exchanges OAuth code for session via `exchangeCodeForSession()`
  - Sets `token` cookie with access token for backend API auth
  - Handles OAuth errors and redirects to login with error message
  - Redirects to `/home` on successful authentication

- **`extension/layout.tsx`**: Extension section layout (~68 lines)
  - Client component with sidebar navigation
  - Uses SidebarProvider, AppSidebar components
  - Authentication check with redirect to /login if not authenticated
  - Breadcrumb navigation with "Connect Extension" title
  - Loading skeleton while checking authentication

- **`extension/connect/page.tsx`**: Browser extension authentication (~128 lines)
  - Client component for connecting browser extension
  - Three states: idle, loading, success, error
  - Fetches one-time code from `POST /extension/connect/start`
  - Sends code to extension via `window.postMessage()` with type `APPLYAI_EXTENSION_CONNECT`
  - Window origin verification for security
  - Shows success confirmation with green checkmark
  - Retry button on error
  - Instructions for user (extension must be installed and popup open)

- **`home/layout.tsx`**: Dashboard layout (~77 lines)
  - Client component with sidebar-based navigation
  - Uses SidebarProvider, SidebarInset, SidebarTrigger, AppSidebar
  - Authentication check with redirect to /login if not authenticated
  - Dynamic page title based on pathname:
    - "/home" → "Dashboard"
    - "/home/discover" → "Discover Jobs"
    - "/home/profile" → "Profile Settings"
  - Breadcrumb navigation
  - Loading skeleton while checking authentication

- **`home/discover/page.tsx`**: Discover Jobs page (~277 lines)
  - Client component for browsing discovered jobs from `GET /jobs` API
  - **State Management**:
    - `filters` (UI state for responsive typing)
    - `debouncedFilters` (API-triggering state with 400ms debounce for text inputs)
    - `jobs`, `totalCount`, `currentPage`, `isLoading`, `error`
  - **Debouncing**: Text inputs (keyword, location) debounced at 400ms; dropdown changes (provider, remote) apply immediately
  - **Features**:
    - Keyword search (full-text)
    - Provider filter (All, Ashby, Lever, Greenhouse)
    - Remote filter (Any, Remote Only, On-site Only)
    - Location text filter
    - Pagination (20 items per page)
    - Clear filters button
  - **Layout**:
    - Header with title and description
    - JobFilters component
    - Results count
    - 3-column grid (lg), 2-column (md), 1-column (mobile)
    - Pagination controls
  - **States**: Loading skeletons, empty state, error state with retry
  - Uses `JobCard` and `JobFilters` widgets

- **`home/page.tsx`**: Main dashboard (~270 lines)
  - Client component displaying job application analytics
  - Fetches all applications from `GET /db/get-all-applications`
  - **KPI Calculations** (computed via `useMemo`):
    - Total Applications count
    - Applied status count
    - Interviewing status count
    - Offers count
    - Visa Sponsorship count (open_to_visa_sponsorship === true)
    - Status distribution for pie chart
    - Applications over time grouped by month (formatted as "MMM YYYY")
  - **Layout**:
    - 5 KPI cards (grid: md:2 cols, lg:5 cols)
    - 2 charts in row (Status pie chart, Applications over time bar chart)
    - Applications table below
  - Empty state message when no applications
  - Protected route with auth check
  - Loading states for both auth and data fetching

- **`home/profile/page.tsx`**: User profile management (~936 lines)
  - Client component with comprehensive profile editing
  - Fetches profile from `GET /db/get-profile`
  - Updates profile with `POST /db/update-profile` (multipart/form-data)

  **Tabbed Interface (6 tabs)**:
  1. **Personal Tab**: full_name, email, first_name, last_name, phone_number
  2. **Links Tab**: linkedin_url, github_url, portfolio_url, other_url
  3. **Location Tab**: address, city, state, zip_code, country, open_to_relocation (checkbox)
  4. **Work Tab**:
     - authorized_to_work_in_us (checkbox)
     - visa_sponsorship (checkbox)
     - visa_sponsorship_type (select: H1B, OPT, F1, J1, L1, O1, Other)
  5. **Resume Tab**:
     - File upload (accepts .pdf, .doc, .docx)
     - Current resume display with View and Download buttons
     - Resume URL from backend
     - **Resume Parsing Status Indicator**:
       - "Pending" state with animated clock icon
       - "Completed" state with parsed data display
       - "Failed" state with retry button
       - Auto-retries up to 2 times with 30-second intervals
     - **Editable Resume Data Section** (always visible when not parsing):
       - Summary: editable textarea
       - Skills: badges with X delete button + input to add new skills (Enter key or Add button)
       - Experience: editable cards with position, company, location, start_date, end_date, description; Add/Delete buttons per entry
       - Education: editable cards with degree, field_of_study, institution, start_date, end_date; Add/Delete buttons per entry
       - Supports manual entry without uploading a resume
       - Submits `resume_profile` as JSON string in FormData on save
  6. **Demographics Tab (Optional)**:
     - gender (select: Male, Female, Non-binary, Prefer not to say)
     - race (select: multiple options)
     - veteran_status (select: Yes, No, Prefer not to say)
     - disability_status (select: Yes, No, Prefer not to say)

  **State Management**:
  - profile (UserProfile), loadingProfile, saving
  - error, success messages
  - resumeFile, desiredLocationInput
  - isParsingResume, retryCount

  - Success notification on save
  - Form validation and error handling
  - Protected route with auth check

### `components/` - Reusable Components

- **`AppSidebar.tsx`**: Sidebar navigation (~164 lines)
  - Client component using shadcn SidebarProvider
  - **Navigation Items** (4 items):
    - Dashboard → /home (LayoutDashboard icon)
    - Discover Jobs → /home/discover (Compass icon)
    - Profile → /home/profile (User icon)
    - Connect Extension → /extension/connect (Puzzle icon)
  - Active route highlighting based on pathname
  - Logo section with ApplyAI branding
  - User dropdown menu in footer:
    - Profile Settings link
    - Logout action
  - User avatar with profile picture (Google OAuth) or initials fallback
    - Uses `AvatarImage` for Google profile pictures (`user.avatar_url`)
    - Falls back to `AvatarFallback` with initials (first 2 characters of email)
  - Uses `usePathname()` for active route detection
  - Uses `useAuth()` for user state and logout function

- **`Navbar.tsx`**: Navigation bar (~73 lines)
  - Legacy component (replaced by AppSidebar in current layout)
  - Client component with sticky positioning (top-0 z-50)
  - Navigation menu with active state highlighting
  - User info display and logout button

- **`ui/`**: shadcn/ui component primitives (20+ components)
  - All built on Radix UI with Tailwind CSS styling
  - Accessible, customizable, and composable
  - **Core Components**: badge, button, card, checkbox, input, label, select, textarea
  - **Navigation**: navigation-menu, breadcrumb, sidebar (complex with context & layout)
  - **Layout**: avatar, separator, scroll-area, skeleton
  - **Overlays**: dialog, dropdown-menu, sheet, tooltip
  - **Data Display**: table, tabs, chart (Recharts integration)
  - **Feedback**: sonner (toast notifications)

- **`widgets/`**: Dashboard and job discovery components

  - **`JobCard.tsx`** (~113 lines): Displays a discovered job posting
    - Provider badge with color coding:
      - Ashby: purple (bg-purple-100, text-purple-700)
      - Lever: green (bg-green-100, text-green-700)
      - Greenhouse: orange (bg-orange-100, text-orange-700)
    - Relative date formatting (Today, Yesterday, X days ago, X weeks ago, etc.)
    - Job title, company name
    - Location with MapPin icon
    - Remote badge (blue) if `is_remote` is true
    - Department with Building2 icon
    - Description preview (truncated, HTML stripped)
    - Apply button opens `apply_url` in new tab

  - **`JobFilters.tsx`** (~116 lines): Filter controls for job search
    - Search input with Search icon (keyword search)
    - Provider dropdown: All, Ashby, Lever, Greenhouse
    - Remote dropdown: Any, Remote Only, On-site Only
    - Location text input
    - Clear filters button (X icon) when any filter is active
    - All inputs disabled during loading

  - **`KPICard.tsx`** (~50 lines):
    - Displays single metric with icon
    - Props: title, value (number), icon (LucideIcon), optional trend, optional className
    - Trend shows percentage change with ↑/↓ arrow and color (green/red)
    - Icon displayed in colored badge on the right
    - Value shown as large bold text (3xl)
    - Hover shadow effect

  - **`ApplicationsTable.tsx`** (~351 lines):
    - Complex data table with advanced features
    - **Search**: Real-time search by job_title or company
    - **Status Filter**: Dropdown filter by status
    - **Sorting**: Click column headers to sort by job_title, company, status, application_date (toggle ASC/DESC)
    - **Pagination**: 10 items per page with Previous/Next buttons, page numbers (max 5 shown), results counter
    - **Table Columns** (7 columns):
      1. Job Title (truncated, max 200px)
      2. Company (truncated, max 150px)
      3. Status (colored badge)
      4. Date (formatted: "MMM DD, YYYY")
      5. Source (job_site_type)
      6. Visa (checkmark icon if open_to_visa_sponsorship)
      7. Actions (dropdown with "View Job Posting" link)
    - **Status Colors**: saved (slate), applied (blue), interviewing (amber), rejected (red), offer (green), withdrawn (gray)
    - Hover effect on rows
    - Empty state message
    - Responsive with horizontal scroll

  - **`StatusChart.tsx`** (~55 lines):
    - Pie chart using Recharts
    - Color mapping for statuses:
      - saved: #94a3b8 (slate)
      - applied: #3b82f6 (blue)
      - interviewing: #f59e0b (amber)
      - rejected: #ef4444 (red)
      - offer: #10b981 (green)
      - withdrawn: #6b7280 (gray)
    - Percentage labels on each slice
    - Includes tooltip and legend
    - Responsive container

  - **`ApplicationsOverTimeChart.tsx`** (~47 lines):
    - Bar chart using Recharts
    - X-axis: month (formatted strings)
    - Y-axis: application count
    - Blue bars (#3b82f6)
    - Grid, tooltip, and legend included
    - Height: 300px, fully responsive

### `hooks/` - Custom React Hooks

- **`use-mobile.tsx`** (~20 lines):
  - Returns boolean for mobile view detection
  - Breakpoint: 768px (md breakpoint)
  - Watches media query changes via event listener
  - Cleanup on unmount

### `contexts/` - React Context

- **`AuthContext.tsx`**: Authentication state management (~175 lines)
  - **User Interface**:
    - email: string
    - id: string
    - first_name?: string | null
    - full_name?: string | null
    - avatar_url?: string | null (Google profile picture URL)

  - **State**:
    - `user`: User object (see interface above)
    - `loading`: boolean for auth check in progress

  - **Functions**:
    - `login(email, password)`: POST to `/auth/login`, sets cookie, redirects to /home
    - `signup(email, password)`: POST to `/auth/signup`, sets cookie, redirects to /home
    - `loginWithGoogle()`: Uses Supabase `signInWithOAuth({ provider: 'google' })`, redirects to `/auth/callback`
    - `signupWithGoogle()`: Same as loginWithGoogle (OAuth handles both)
    - `logout()`: Clears cookie, redirects to /login

  - **Cookie Management**:
    - Token stored in `token` cookie with 24-hour max-age (86400 seconds)
    - Path set to `/` for app-wide access
    - Cleared on logout or invalid auth check

  - **Auth Check** (runs on mount):
    - Reads token from cookie
    - Validates with `GET /auth/me`
    - Sets user state if valid
    - Clears cookie if invalid

  - **Export**: `AuthProvider` component and `useAuth()` hook
  - Error handling with custom error messages from backend (detail field)

### `types/` - TypeScript Type Definitions

- **`jobs.ts`** (~35 lines): Types for job discovery feature
  - `JobBoardProvider`: Union type `"ashby" | "lever" | "greenhouse"`
  - `DiscoveredJob`: Interface matching backend response (id, board_id, provider, company_name, external_id, title, location, is_remote, department, team, apply_url, description, posted_at)
  - `JobsListResponse`: Paginated response (jobs array, total_count, limit, offset, has_more)
  - `JobFilters`: Filter state interface (keyword, provider, remote, location)

### `lib/` - Utilities

- **`utils.ts`**: Utility functions
  - `cn()`: Combines Tailwind classes using clsx and tailwind-merge
  - Used throughout app for conditional className styling

- **`api/`**: API client functions
  - **`jobs.ts`** (~51 lines): Fetches discovered jobs from backend
    - `FetchJobsParams`: Interface for query params (keyword, provider, location, remote, limit, offset)
    - `fetchJobs(params)`: Calls `GET /jobs` endpoint with URL params
    - Uses `NEXT_PUBLIC_API_URL` (defaults to `http://localhost:8000`)
    - Returns `JobsListResponse`

- **`supabase/`**: Supabase client utilities for Google OAuth
  - **`client.ts`** (~8 lines): Browser-side Supabase client
    - Uses `createBrowserClient()` from `@supabase/ssr`
    - Configured with `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY`
    - Used in AuthContext for `signInWithOAuth()` calls
  - **`server.ts`** (~27 lines): Server-side Supabase client
    - Uses `createServerClient()` from `@supabase/ssr`
    - Configured with cookie handling via `next/headers`
    - Used in `/auth/callback` route for `exchangeCodeForSession()`
    - Supports reading and writing cookies for PKCE flow

## Backend API Integration

The frontend communicates with the backend API at `http://localhost:8000` (configurable via `NEXT_PUBLIC_API_URL`).

### Authentication Endpoints
- `POST /auth/login` - Email/password login
- `POST /auth/signup` - Email/password signup
- `GET /auth/me` - Validate token and get user info (includes avatar_url)

### Google OAuth (via Supabase)
- Google OAuth is handled directly by Supabase, not through the backend
- Frontend calls `supabase.auth.signInWithOAuth({ provider: 'google' })`
- Supabase redirects to Google consent screen
- Google redirects back to `/auth/callback` with OAuth code
- Callback route exchanges code for session and sets token cookie

### Database Endpoints
- `GET /db/get-all-applications` - Fetch all user's applications
- `GET /db/get-profile` - Fetch user profile
- `POST /db/update-profile` - Update user profile (multipart/form-data)

### Job Discovery Endpoints (Public)
- `GET /jobs` - Fetch discovered jobs with filters (keyword, provider, location, remote, limit, offset)

### Extension Endpoints
- `POST /extension/connect/start` - Generate one-time code for extension authentication

## Data Models

### DiscoveredJob Interface
```typescript
{
  id: string
  board_id: string
  provider: "ashby" | "lever" | "greenhouse"
  company_name: string | null
  external_id: string
  title: string
  location: string | null
  is_remote: boolean
  department: string | null
  team: string | null
  apply_url: string
  description: string | null
  posted_at: string | null
}
```

### JobApplication Interface
```typescript
{
  id: string
  user_id: string
  job_title: string
  company: string
  job_posted: string
  job_description: string
  url: string
  required_skills: string[]
  preferred_skills: string[]
  education_requirements: string[]
  experience_requirements: string[]
  keywords: string[]
  job_site_type: string
  open_to_visa_sponsorship: boolean
  status: string  // saved | applied | interviewing | rejected | offer | withdrawn
  notes: string | null
  application_date: string
  created_at: string
  updated_at: string
}
```

### UserProfile Interface
```typescript
{
  full_name?: string
  first_name?: string
  last_name?: string
  email?: string
  phone_number?: string
  linkedin_url?: string
  github_url?: string
  portfolio_url?: string
  other_url?: string
  address?: string
  city?: string
  state?: string
  zip_code?: string
  country?: string
  authorized_to_work_in_us?: boolean
  visa_sponsorship?: boolean
  visa_sponsorship_type?: string
  desired_salary?: number
  desired_location?: string[]
  gender?: string
  race?: string
  veteran_status?: string
  disability_status?: string
  resume?: string
  resume_url?: string
  resume_text?: string
  resume_profile?: {
    summary?: string
    skills?: string[]
    experience?: Array<{
      company: string
      position: string
      start_date?: string
      end_date?: string
      description?: string
    }>
    education?: Array<{
      institution: string
      degree: string
      field_of_study: string
      start_date?: string
      end_date?: string
      description?: string
    }>
    certifications?: Array<{
      name: string
      issuing_organization?: string
      issue_date?: string
      expiration_date?: string
      credential_id?: string
      credential_url?: string
    }>
    projects?: Array<{
      name: string
      description?: string
      link?: string
    }>
  }
  resume_parsed_at?: string
  resume_parse_status?: 'PENDING' | 'COMPLETED' | 'FAILED'
}
```

## Key Features

### Authentication Flow
1. User visits root `/` → redirects to `/login` or `/home` based on token
2. User logs in via email/password or Google OAuth
3. Backend returns JWT token
4. Frontend stores token in cookie (24-hour expiry)
5. Token sent as `Authorization: Bearer <token>` header on all API requests
6. Invalid token triggers logout and redirect to `/login`

### Extension Connection Flow
1. User navigates to `/extension/connect`
2. Page fetches one-time code from backend
3. Code sent to extension via `window.postMessage()`
4. Extension content script receives and forwards to background script
5. Background exchanges code for extension-specific JWT token
6. Success message shown to user

### Resume Upload & Parsing Flow
1. User uploads resume file (PDF/DOC/DOCX) on profile page
2. File sent to backend via multipart form data
3. Backend processes file and sets `resume_parse_status` to 'PENDING'
4. Frontend polls profile endpoint every 30 seconds (max 2 retries)
5. When status becomes 'COMPLETED', parsed data displayed in UI
6. Parsed data includes summary, skills, experience, education, projects, certifications

### Dashboard Analytics
- All calculations done client-side using `useMemo` for performance
- Data grouped and aggregated from raw application list
- Charts rendered with Recharts library
- Responsive grid layouts with Tailwind CSS

## Styling Approach

- **Tailwind CSS**: Utility-first styling throughout
- **shadcn/ui**: Pre-built accessible components
- **Custom theming**: CSS variables in globals.css
- **Responsive design**: Mobile-first with md/lg breakpoints
- **Color scheme**: Professional with status-specific colors
- **Typography**: Inter font, semantic text sizes

## Navigation Structure

```
/ (root)
├── /login
├── /signup
├── /home (dashboard) ─── Sidebar Layout
│   ├── /home/discover
│   └── /home/profile
└── /extension/connect ─── Sidebar Layout
```

**Sidebar Navigation** (AppSidebar):
- Dashboard → /home
- Discover Jobs → /home/discover
- Profile → /home/profile
- Connect Extension → /extension/connect

All routes except `/login` and `/signup` are protected and require authentication.

## Known Patterns

- **Protected Routes**: All pages (except login/signup) check auth in `useEffect` and redirect if not authenticated
- **Token Extraction**: Cookie parsing done manually via `document.cookie.split()`
- **Loading States**: Dual loading states (auth + data) for smooth UX
- **Error Handling**: Try-catch with user-friendly error messages
- **Form Handling**: Controlled inputs with React state
- **Data Fetching**: `useEffect` hooks with fetch API
- **Optimistic Updates**: None (refetches data after mutations)

## Configuration Files

- **`package.json`** (~48 lines):
  - Version: 0.1.0
  - React 18.3.0, Next.js 14.2.0
  - TypeScript 5.5.0, ESLint
  - shadcn CLI 3.6.3

- **`tailwind.config.ts`** (~106 lines):
  - Dark mode: Class-based support
  - CSS Variables: HSL color values for theming
  - Custom colors: primary (blue), chart colors (5-color palette), sidebar colors
  - Tailwind Animate plugin enabled

- **`tsconfig.json`** (~27 lines):
  - Target: ES2017, Module: ESNext
  - Path alias: `@/*` maps to root directory
  - Strict mode enabled

- **`components.json`** (~23 lines):
  - shadcn/ui: New York style
  - RSC support enabled
  - Aliases configured for @/components, @/utils, @/ui, @/lib, @/hooks

## Environment Variables

- `NEXT_PUBLIC_API_URL`: Backend API base URL (default: `http://localhost:8000`)

## Development Notes

- Uses Next.js 14 App Router (not Pages Router)
- All pages are client components ("use client" directive)
- Server components only used for root page.tsx (cookie reading)
- No server-side rendering for authenticated pages
- No data caching or revalidation strategies implemented
- Icons imported from lucide-react
- Charts use Recharts with ResponsiveContainer for responsive sizing
- Sidebar-based layouts for authenticated pages (home, extension)
- Dark mode support via CSS variables and next-themes
- Toast notifications via Sonner
