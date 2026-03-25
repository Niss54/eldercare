import { webEnv } from "../env";

export type SdkClient = {
  get: <T>(path: string, options?: { query?: Record<string, string | number | undefined>; cache?: RequestCache }) => Promise<T>;
  post: <T>(path: string, body?: unknown) => Promise<T>;
  put: <T>(path: string, body?: unknown) => Promise<T>;
};

const buildUrl = (path: string, query?: Record<string, string | number | undefined>) => {
  const url = new URL(path, webEnv.apiBaseUrl);
  if (query) {
    Object.entries(query).forEach(([key, value]) => {
      if (value !== undefined) {
        url.searchParams.set(key, String(value));
      }
    });
  }
  return url.toString();
};

const parsePayload = async (response: Response) => {
  const contentType = response.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) {
    return response.json().catch(() => null);
  }
  return response.text().catch(() => null);
};

export const createSdkClient = (accessToken?: string | null): SdkClient => {
  const headers: Record<string, string> = {};
  if (accessToken) {
    headers.Authorization = `Bearer ${accessToken}`;
  }

  const request = async <T>(method: "GET" | "POST" | "PUT", path: string, body?: unknown, cache?: RequestCache, query?: Record<string, string | number | undefined>) => {
    const response = await fetch(buildUrl(path, query), {
      method,
      headers: {
        ...headers,
        ...(body !== undefined ? { "Content-Type": "application/json" } : {}),
      },
      body: body !== undefined ? JSON.stringify(body) : undefined,
      cache,
    });

    const payload = await parsePayload(response);
    if (!response.ok) {
      const detail =
        payload && typeof payload === "object" && "detail" in payload && typeof (payload as { detail?: unknown }).detail === "string"
          ? ((payload as { detail: string }).detail)
          : "Request failed";
      throw new Error(detail);
    }
    return payload as T;
  };

  return {
    get: (path, options) => request("GET", path, undefined, options?.cache, options?.query),
    post: (path, body) => request("POST", path, body),
    put: (path, body) => request("PUT", path, body),
  };
};
