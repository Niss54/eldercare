import { AppRole } from "../lib/roles";

export type RoleSession = {
  role: AppRole;
  displayName: string;
  userId: string;
  username: string;
  accessToken: string;
  refreshToken: string;
  sessionId: string;
  permissions: string[];
};

export type ApiError = {
  type: string;
  title: string;
  status: number;
  detail?: string;
  instance?: string;
};

export type PaginatedResult<T> = {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
};
