import { NextRequest, NextResponse } from "next/server";

const ROLE_HOME: Record<string, string> = {
  admin: "/admin",
  family_member: "/family",
  parent: "/parent",
  caregiver: "/caregiver",
  doctor: "/doctor",
};

const ROLE_PREFIXES: Record<string, string[]> = {
  admin: ["/admin"],
  family_member: ["/family"],
  parent: ["/parent"],
  caregiver: ["/caregiver"],
  doctor: ["/doctor"],
};

const protectedPrefixes = ["/admin", "/family", "/parent", "/caregiver", "/doctor"];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  if (!protectedPrefixes.some((prefix) => pathname.startsWith(prefix))) {
    return NextResponse.next();
  }

  const role = request.cookies.get("ec_role")?.value;
  const access = request.cookies.get("ec_access")?.value;

  if (!role || !access) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("next", pathname);
    return NextResponse.redirect(loginUrl);
  }

  const allowedPrefixes = ROLE_PREFIXES[role] || [];
  const isAllowed = allowedPrefixes.some((prefix) => pathname.startsWith(prefix));
  if (!isAllowed) {
    return NextResponse.redirect(new URL(ROLE_HOME[role] || "/login", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/admin/:path*", "/family/:path*", "/parent/:path*", "/caregiver/:path*", "/doctor/:path*"],
};
