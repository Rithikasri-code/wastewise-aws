// All API calls go through relative /api paths, proxied to the backend by Vite
// (see vite.config.js). No backend URL is hardcoded in components.
const BASE = '/api'

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    throw new Error(`Request to ${path} failed with status ${res.status}`)
  }
  return res.json()
}

export const getHealth = () => request('/health')
export const getBranding = () => request('/branding')
export const getLanguage = () => request('/language')
export const getConfig = () => request('/config')
export const getDemoAccount = () => request('/demo/account')
export const quotePrice = (payload) =>
  request('/pricing/quote', { method: 'POST', body: JSON.stringify(payload) })
