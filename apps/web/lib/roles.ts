export type AppRole = "admin" | "family_member" | "parent" | "caregiver" | "doctor";

export const APP_ROLES: AppRole[] = ["admin", "family_member", "parent", "caregiver", "doctor"];

export const ROLE_LABELS: Record<AppRole, string> = {
  admin: "Admin",
  family_member: "Family Member",
  parent: "Parent",
  caregiver: "Caregiver",
  doctor: "Doctor",
};

export const ROLE_HOME: Record<AppRole, string> = {
  admin: "/admin",
  family_member: "/family",
  parent: "/parent",
  caregiver: "/caregiver",
  doctor: "/doctor",
};
