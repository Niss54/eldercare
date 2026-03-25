import "server-only";

import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { APP_ROLES, AppRole, ROLE_HOME } from "./roles";

const roleSet = new Set<AppRole>(APP_ROLES);

export function getRoleFromCookies(): AppRole | null {
  const value = cookies().get("ec_role")?.value;
  if (!value || !roleSet.has(value as AppRole)) {
    return null;
  }
  return value as AppRole;
}

export function requireSignedInRole(): AppRole {
  const role = getRoleFromCookies();
  if (!role) {
    redirect("/login");
  }
  return role;
}

export function requireRole(allowedRoles: AppRole[]): AppRole {
  const role = requireSignedInRole();
  if (!allowedRoles.includes(role)) {
    redirect(ROLE_HOME[role]);
  }
  return role;
}
