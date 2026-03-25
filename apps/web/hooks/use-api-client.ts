"use client";

import { useMemo } from "react";

import { ApiRequestOptions, apiRequest } from "../lib/api-client";
import { useAuth } from "../providers/auth-provider";

export function useApiClient() {
  const { session } = useAuth();

  return useMemo(
    () => ({
      request: <T = unknown>(path: string, options: ApiRequestOptions = {}) =>
        apiRequest<T>(path, {
          ...options,
          token: options.token ?? session?.accessToken,
        }),
      accessToken: session?.accessToken ?? null,
    }),
    [session?.accessToken],
  );
}
