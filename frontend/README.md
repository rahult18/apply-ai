# Application Tracker - Frontend

Next.js frontend application with authentication.

## Setup

1. Install dependencies:
```bash
npm install
```

2. Create `.env.local` file:
```bash
cp .env.local.example .env.local
```

3. Update `NEXT_PUBLIC_API_URL` in `.env.local` to match your FastAPI backend URL (default: `http://localhost:8000`)

4. Run development server:
```bash
npm run dev
```

The app will be available at `http://localhost:3000`

## Features

- **Login Page** (`/login`): Email/password and Google SSO authentication
- **Sign Up Page** (`/signup`): Email/password and Google SSO registration
- **Home Page** (`/home`): Protected route accessible after login

## API Endpoints Expected

The frontend expects the following REST API endpoints:

- `POST /auth/login` - Email/password login
- `POST /auth/signup` - Email/password signup
- `GET /auth/google/login` - Google SSO login redirect
- `GET /auth/google/signup` - Google SSO signup redirect
- `GET /auth/me` - Get current user (requires Bearer token)

## Tech Stack

- Next.js 14 (App Router)
- TypeScript
- Tailwind CSS
- shadcn/ui components
- React Context for auth state

