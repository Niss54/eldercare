import { requireRole } from "../../../lib/auth";

export default function CaregiverLayout({ children }: { children: React.ReactNode }) {
  requireRole(["caregiver"]);
  return <>{children}</>;
}
