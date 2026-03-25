import { webEnv } from "./env";

export class ApiClientError extends Error {
  status: number;
  detail: string;
  payload: unknown;

  constructor(status: number, detail: string, payload: unknown) {
    super(detail);
    this.name = "ApiClientError";
    this.status = status;
    this.detail = detail;
    this.payload = payload;
  }
}

export type ApiRequestOptions = {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  token?: string;
  headers?: Record<string, string>;
  body?: unknown;
  cache?: RequestCache;
  signal?: AbortSignal;
  parseAs?: "json" | "blob" | "text";
};

const parseErrorDetail = (payload: unknown, fallback: string) => {
  if (!payload || typeof payload !== "object") {
    return fallback;
  }

  const typedError = (payload as { error?: { message?: unknown } }).error;
  if (typedError && typeof typedError === "object") {
    const message = (typedError as { message?: unknown }).message;
    if (typeof message === "string" && message.trim()) {
      return message;
    }
  }

  const detail = (payload as { detail?: unknown }).detail;
  if (typeof detail === "string" && detail.trim()) {
    return detail;
  }
  return fallback;
};

const buildUrl = (path: string) => {
  if (path.startsWith("http://") || path.startsWith("https://")) {
    return path;
  }
  if (path.startsWith("/")) {
    return `${webEnv.apiBaseUrl}${path}`;
  }
  return `${webEnv.apiBaseUrl}/${path}`;
};

export async function apiRequest<T = unknown>(path: string, options: ApiRequestOptions = {}): Promise<T> {
  const method = options.method ?? "GET";
  const headers: Record<string, string> = {
    ...(options.headers ?? {}),
  };

  if (options.token) {
    headers.Authorization = `Bearer ${options.token}`;
  }

  let body: BodyInit | undefined;
  if (options.body !== undefined) {
    headers["Content-Type"] = headers["Content-Type"] ?? "application/json";
    body = JSON.stringify(options.body);
  }

  const response = await fetch(buildUrl(path), {
    method,
    headers,
    body,
    cache: options.cache,
    signal: options.signal,
  });

  const parseAs = options.parseAs ?? "json";
  let payload: unknown = null;
  if (parseAs === "blob") {
    payload = await response.blob();
  } else if (parseAs === "text") {
    payload = await response.text();
  } else {
    payload = await response.json().catch(() => null);
  }

  if (!response.ok) {
    throw new ApiClientError(response.status, parseErrorDetail(payload, "Request failed"), payload);
  }

  return payload as T;
}

export const getApiErrorMessage = (error: unknown, fallback: string) => {
  if (error instanceof ApiClientError) {
    return error.detail;
  }
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return fallback;
};
