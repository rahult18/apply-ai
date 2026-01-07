# Agent Context: frontend

This folder contains the Next.js 14 frontend for the Application Tracker (ApplyAI) project. Built with TypeScript, React, and Tailwind CSS, it provides the user interface for authentication, job application tracking, profile management, and browser extension integration.

## Tech Stack
- **Framework**: Next.js 14 with App Router
- **Language**: TypeScript 5.5
- **Styling**: Tailwind CSS 3.4 with tailwindcss-animate
- **UI Components**: shadcn/ui (built on Radix UI primitives)
- **Icons**: Lucide React
- **Charts**: Recharts 3.5
- **State Management**: React Context API
- **Font**: Inter (Google Fonts)

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

- **`login/page.tsx`**: Login page (~137 lines)
  - Client component with email/password form
  - Google OAuth login button with Google logo SVG
  - Form validation with error display
  - Loading states ("Logging in...")
  - Link to signup page
  - Calls `login()` and `loginWithGoogle()` from AuthContext
  - Card-based centered layout

- **`signup/page.tsx`**: Signup page (~135 lines)
  - Client component with email/password registration form
  - Google OAuth signup button with Google logo SVG
  - Form validation with error display
  - Loading states ("Creating account...")
  - Link to login page
  - Calls `signup()` and `signupWithGoogle()` from AuthContext
  - Identical layout to login page for consistency

- **`extension/connect/page.tsx`**: Browser extension authentication (~99 lines)
  - Client component for connecting browser extension
  - Requires user authentication (redirects to login if not authenticated)
  - Status states: idle, loading, success, error
  - Fetches one-time code from `POST /extension/connect/start`
  - Sends code to extension via `window.postMessage()` with type `APPLYAI_EXTENSION_CONNECT`
  - Shows success message: "Connected! You can close this tab."
  - Retry button on error
  - Protected route with loading state

- **`home/page.tsx`**: Main dashboard (~218 lines)
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

- **`home/profile/page.tsx`**: User profile management (~801 lines)
  - Client component with comprehensive profile editing
  - Fetches profile from `GET /db/get-profile`
  - Updates profile with `POST /db/update-profile` (multipart/form-data)

  **Profile Sections**:
  1. **Personal Information**: full_name, email, first_name, last_name, phone_number
  2. **Links**: linkedin_url, github_url, portfolio_url, other_url
  3. **Address**: address, city, state, zip_code, country
  4. **Work Authorization**:
     - authorized_to_work_in_us (checkbox)
     - visa_sponsorship (checkbox)
     - visa_sponsorship_type (select: H1B, OPT, F1, J1, L1, O1, Other)
  5. **Job Preferences**:
     - desired_salary (number)
     - desired_location (comma-separated input, stored as JSON array)
  6. **Resume**:
     - File upload (accepts .pdf, .doc, .docx)
     - Current resume display with View and Download buttons
     - Resume URL from backend
  7. **Resume Parsing Status**:
     - Monitors parse status: PENDING, COMPLETED, FAILED
     - Auto-retries status check every 30 seconds (max 2 retries)
     - Initial 5-second delay after upload before first check
     - Shows parsing progress messages
     - Displays parsed_at timestamp on completion
  8. **Parsed Resume Data** (displayed when available):
     - Summary (text)
     - Skills (comma-separated list)
     - Experience (cards with company, position, dates, description)
     - Education (cards with degree, field, institution, dates, description)
     - Projects (cards with name, description, link)
     - Certifications (cards with name, issuer, dates, credential URL)
  9. **Demographic Information (Optional)**:
     - gender (select: Male, Female, Non-binary, Prefer not to say)
     - race (select: multiple options)
     - veteran_status (select: Yes, No, Prefer not to say)
     - disability_status (select: Yes, No, Prefer not to say)

  - Success/error notifications with auto-dismiss (3 seconds)
  - Save/Cancel buttons
  - Protected route with auth check
  - Complex state management for resume parsing status

### `components/` - Reusable Components

- **`Navbar.tsx`**: Navigation bar (~73 lines)
  - Client component with sticky positioning (top-0 z-50)
  - Displays "ApplyAI" brand title
  - Navigation menu with active state highlighting:
    - Home (`/home`)
    - Profile (`/home/profile`)
  - User info display (email)
  - Logout button
  - Uses `usePathname()` for active route detection
  - Uses `useAuth()` for user state and logout function

- **`ui/`**: shadcn/ui component primitives
  - All built on Radix UI with Tailwind CSS styling
  - Accessible, customizable, and composable
  - Components: badge, button, card, checkbox, input, label, navigation-menu, select, textarea

- **`widgets/`**: Dashboard visualization components

  - **`KPICard.tsx`** (~46 lines):
    - Displays single metric with icon
    - Props: title, value (number), icon (LucideIcon), optional trend
    - Trend shows percentage change with ↑/↓ arrow and color (green/red)
    - Icon displayed in muted background circle
    - Value shown as large bold text (3xl)

  - **`ApplicationsTable.tsx`** (~119 lines):
    - Table of all applications with 7 columns:
      1. Job Title (bold)
      2. Company
      3. Status (colored badge)
      4. Application Date (formatted: "MMM DD, YYYY")
      5. Source (capitalized job_site_type)
      6. Visa Sponsorship (CheckCircle2 icon if true, XCircle if false)
      7. Actions (external link to job URL)
    - Status badge variants: saved, applied, interviewing, rejected, offer, withdrawn
    - Hover effect on rows (bg-muted/50)
    - Empty state message
    - Responsive with horizontal scroll

  - **`StatusChart.tsx`** (~61 lines):
    - Pie chart using Recharts
    - Color mapping for statuses:
      - saved: #94a3b8 (gray)
      - applied: #3b82f6 (blue)
      - interviewing: #f59e0b (amber)
      - rejected: #ef4444 (red)
      - offer: #10b981 (green)
      - withdrawn: #6b7280 (gray)
    - Labels show "Status: XX%" on each slice
    - Includes tooltip and legend
    - Height: 300px

  - **`ApplicationsOverTimeChart.tsx`** (~47 lines):
    - Bar chart using Recharts
    - X-axis: month (formatted strings)
    - Y-axis: application count
    - Blue bars (#3b82f6)
    - Grid, tooltip, and legend included
    - Height: 300px

### `contexts/` - React Context

- **`AuthContext.tsx`**: Authentication state management (~146 lines)
  - **State**:
    - `user`: User object with email and optional name
    - `loading`: boolean for auth check in progress

  - **Functions**:
    - `login(email, password)`: POST to `/auth/login`, sets cookie, redirects to /home
    - `signup(email, password)`: POST to `/auth/signup`, sets cookie, redirects to /home
    - `loginWithGoogle()`: Redirects to `/auth/google/login`
    - `signupWithGoogle()`: Redirects to `/auth/google/signup`
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
  - Error handling with custom error messages from backend

### `lib/` - Utilities

- **`utils.ts`**: Utility functions
  - `cn()`: Combines Tailwind classes using clsx and tailwind-merge
  - Used throughout app for conditional className styling

## Backend API Integration

The frontend communicates with the backend API at `http://localhost:8000` (configurable via `NEXT_PUBLIC_API_URL`).

### Authentication Endpoints
- `POST /auth/login` - Email/password login
- `POST /auth/signup` - Email/password signup
- `GET /auth/me` - Validate token and get user info
- `GET /auth/google/login` - Google OAuth login (redirect)
- `GET /auth/google/signup` - Google OAuth signup (redirect)

### Database Endpoints
- `GET /db/get-all-applications` - Fetch all user's applications
- `GET /db/get-profile` - Fetch user profile
- `POST /db/update-profile` - Update user profile (multipart/form-data)

### Extension Endpoints
- `POST /extension/connect/start` - Generate one-time code for extension authentication

## Data Models

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
├── /home (dashboard)
│   └── /home/profile
└── /extension/connect
```

All routes except `/login` and `/signup` are protected and require authentication.

## Known Patterns

- **Protected Routes**: All pages (except login/signup) check auth in `useEffect` and redirect if not authenticated
- **Token Extraction**: Cookie parsing done manually via `document.cookie.split()`
- **Loading States**: Dual loading states (auth + data) for smooth UX
- **Error Handling**: Try-catch with user-friendly error messages
- **Form Handling**: Controlled inputs with React state
- **Data Fetching**: `useEffect` hooks with fetch API
- **Optimistic Updates**: None (refetches data after mutations)

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
