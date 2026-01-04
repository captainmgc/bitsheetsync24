/**
 * Application Configuration
 * Centralizes all environment-dependent settings
 * 
 * Port Configuration:
 *   - Frontend: 4000 (development) / 443 (production)
 *   - Backend:  4001 (development) / 443 (production via /api)
 * 
 * Usage:
 *   import { config, apiUrl } from '@/lib/config'
 *   fetch(apiUrl('/api/tables/'))
 */

// Environment detection
export const isDevelopment = process.env.NODE_ENV === 'development'
export const isProduction = process.env.NODE_ENV === 'production'

// Default ports
const DEFAULT_FRONTEND_PORT = 4000
const DEFAULT_BACKEND_PORT = 4001

// API Configuration
export const config = {
  // Backend API URL - uses environment variable or falls back to default
  apiUrl: process.env.NEXT_PUBLIC_API_URL || (
    isDevelopment 
      ? `http://localhost:${DEFAULT_BACKEND_PORT}` 
      : 'https://etablo.japonkonutlari.com'
  ),
  
  // Frontend URL
  appUrl: process.env.NEXTAUTH_URL || (
    isDevelopment 
      ? `http://localhost:${DEFAULT_FRONTEND_PORT}` 
      : 'https://etablo.japonkonutlari.com'
  ),
  
  // Ports
  frontendPort: parseInt(process.env.FRONTEND_PORT || String(DEFAULT_FRONTEND_PORT)),
  backendPort: parseInt(process.env.BACKEND_PORT || String(DEFAULT_BACKEND_PORT)),
  
  // API timeout in milliseconds
  apiTimeout: 30000,
  
  // Pagination defaults
  defaultPageSize: 20,
  maxPageSize: 100,
}

// API Helper - creates full URL for API endpoints
export function apiUrl(path: string): string {
  const base = config.apiUrl.replace(/\/$/, '') // Remove trailing slash
  const cleanPath = path.startsWith('/') ? path : `/${path}`
  return `${base}${cleanPath}`
}

// Fetch wrapper with default config
export async function apiFetch<T>(
  path: string, 
  options: RequestInit = {}
): Promise<T> {
  const url = apiUrl(path)
  
  const defaultOptions: RequestInit = {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  }
  
  const response = await fetch(url, { ...defaultOptions, ...options })
  
  if (!response.ok) {
    throw new Error(`API Error: ${response.status} ${response.statusText}`)
  }
  
  return response.json()
}

export default config
