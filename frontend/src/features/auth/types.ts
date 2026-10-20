export type Role = "student" | "instructor";

export interface AuthUser {
  id: string;
  name: string;
  email: string;
  role: Role;
  /** Whether the account menu offers Switch user. QA only, never production. */
  can_switch?: boolean;
  /** Trial mode: signed in with a participant ID rather than Google. */
  participant?: boolean;
}

export interface AuthConfig {
  dev_bypass: boolean;
  google_configured: boolean;
  /** The trial instance: participants sign in by ID, and classes have modes. */
  trial_mode?: boolean;
}

export interface DevUser {
  id: string;
  name: string;
  email: string;
  role: Role;
}
