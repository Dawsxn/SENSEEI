export type Role = "student" | "instructor";

export interface AuthUser {
  id: string;
  name: string;
  email: string;
  role: Role;
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
