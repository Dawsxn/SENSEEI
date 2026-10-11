export type Role = "student" | "instructor";

export interface AuthUser {
  id: string;
  name: string;
  email: string;
  role: Role;
  /** Whether the account menu offers Switch user. QA only, never production. */
  can_switch?: boolean;
}

export interface AuthConfig {
  dev_bypass: boolean;
  google_configured: boolean;
}

export interface DevUser {
  id: string;
  name: string;
  email: string;
  role: Role;
}
