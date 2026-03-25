import { requireRole } from "../../../lib/auth";

export default function DoctorLayout({ children }: { children: React.ReactNode }) {
  requireRole(["doctor"]);
  return <>{children}</>;
}
