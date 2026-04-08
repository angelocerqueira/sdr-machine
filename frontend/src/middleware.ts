import { NextRequest, NextResponse } from "next/server";
import { getSessionCookie } from "better-auth/cookies";

const PUBLIC_PATHS = ["/login", "/lp"];

// Backend API prefixes — these go through Next.js rewrites to FastAPI,
// which has its own auth middleware. Don't block them here.
const BACKEND_API_PREFIXES = ["/api/leads", "/api/dashboard", "/api/jobs", "/api/pipeline", "/api/settings", "/api/health"];

function isPublicPath(pathname: string): boolean {
  if (pathname === "/favicon.ico") return true;
  if (pathname.startsWith("/_next")) return true;
  if (pathname.startsWith("/api/auth")) return true;
  if (BACKEND_API_PREFIXES.some((p) => pathname.startsWith(p))) return true;
  return PUBLIC_PATHS.some((p) => pathname === p || pathname.startsWith(p + "/"));
}

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  if (isPublicPath(pathname)) {
    return NextResponse.next();
  }

  const sessionCookie = getSessionCookie(request);

  // Usuário autenticado tentando acessar /login → redireciona pro dashboard
  if (pathname === "/login") {
    if (sessionCookie) {
      return NextResponse.redirect(new URL("/", request.url));
    }
    return NextResponse.next();
  }

  // Rotas protegidas: sem sessão → login
  if (!sessionCookie) {
    return NextResponse.redirect(new URL("/login", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
