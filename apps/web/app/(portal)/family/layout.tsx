import { requireRole } from "../../../lib/auth";

export default function FamilyLayout({ children }: { children: React.ReactNode }) {
  requireRole(["family_member"]);
  return <>{children}</>;
}
