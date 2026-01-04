import { auth } from "@/auth"
import { NextResponse } from "next/server"
import type { NextRequest } from "next/server"

/**
 * Middleware for BitSheet24
 * Protects API routes and dashboard pages from unauthenticated access
 */

// Public paths that don't require authentication
const publicPaths = [
  "/",
  "/auth",
  "/api/auth",
  "/privacy-policy",
  "/terms",
  "/_next",
  "/favicon.ico",
]

// Check if path is public
function isPublicPath(pathname: string): boolean {
  return publicPaths.some(path => 
    pathname === path || pathname.startsWith(path + "/")
  )
}

export default auth((req) => {
  const { pathname } = req.nextUrl
  
  // Allow public paths
  if (isPublicPath(pathname)) {
    return NextResponse.next()
  }
  
  // Check authentication
  const isAuthenticated = !!req.auth
  
  // Redirect unauthenticated users to sign in
  if (!isAuthenticated) {
    // For API routes, return 401
    if (pathname.startsWith("/api/")) {
      return NextResponse.json(
        {
          error: "UNAUTHORIZED",
          message: "Bu API kaynağına erişmek için giriş yapmanız gerekmektedir.",
          detail: "Authentication required"
        },
        { status: 401 }
      )
    }
    
    // For pages, redirect to sign in
    const signInUrl = new URL("/auth/signin", req.url)
    signInUrl.searchParams.set("callbackUrl", pathname)
    return NextResponse.redirect(signInUrl)
  }
  
  return NextResponse.next()
})

export const config = {
  // Match all paths except static files and public assets
  matcher: [
    /*
     * Match all request paths except:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - public folder files
     */
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)",
  ],
}
