// Single source of truth for environment-specific URLs.
// Vite replaces import.meta.env.* at build time from the active .env file.
// - Development: .env.development (localhost)
// - Production:  .env.production  (deployed URLs)

export const APP_BASE_URL = import.meta.env.VITE_APP_BASE_URL;
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;
