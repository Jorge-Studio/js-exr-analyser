/**
 * API base URL for backend. When deployed on Vercel, set VITE_API_URL to your
 * backend origin (e.g. https://your-app.railway.app) in Vercel env vars.
 * Leave unset for local dev (Vite proxies /api to backend).
 */
const origin = import.meta.env.VITE_API_URL || ''
export const API_BASE = origin ? `${origin.replace(/\/$/, '')}/api` : '/api'
