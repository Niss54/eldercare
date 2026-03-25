const asBoolean = (value: string | undefined, fallback = false): boolean => {
  if (value === undefined) {
    return fallback;
  }
  const normalized = value.trim().toLowerCase();
  return normalized === "1" || normalized === "true" || normalized === "yes";
};

export const webEnv = {
  apiBaseUrl: process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000",
  razorpayKeyId: process.env.NEXT_PUBLIC_RAZORPAY_KEY_ID ?? "",
  enableAiPanel: asBoolean(process.env.NEXT_PUBLIC_ENABLE_AI_PANEL, false),
  enableIotPanel: asBoolean(process.env.NEXT_PUBLIC_ENABLE_IOT_PANEL, false),
  appName: process.env.NEXT_PUBLIC_APP_NAME ?? "Eldercare",
} as const;
