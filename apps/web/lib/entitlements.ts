export type EntitlementMap = Record<string, boolean>;

export const PLAN_ENTITLEMENT_MATRIX: Record<string, EntitlementMap> = {
  free: {
    "marketplace.booking": false,
    "advanced.analytics": false,
    "billing.portal": false,
    "sos.premium_cascade": false,
    "doctor.collaboration": false,
  },
  plus: {
    "marketplace.booking": true,
    "advanced.analytics": true,
    "billing.portal": true,
    "sos.premium_cascade": true,
    "doctor.collaboration": false,
  },
  clinical: {
    "marketplace.booking": true,
    "advanced.analytics": true,
    "billing.portal": true,
    "sos.premium_cascade": true,
    "doctor.collaboration": true,
  },
};

export function hasPlanEntitlement(planCode: string, feature: string): boolean {
  const matrix = PLAN_ENTITLEMENT_MATRIX[planCode] ?? PLAN_ENTITLEMENT_MATRIX.free;
  return Boolean(matrix[feature]);
}
