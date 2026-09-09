import { useQuery } from "@tanstack/react-query";

import { getAuthConfig, getMe } from "../../lib/api";

/** The signed-in user, or an error when not authenticated (used as the guard). */
export function useMe() {
  return useQuery({ queryKey: ["me"], queryFn: getMe, retry: false });
}

/** What the sign-in screen needs before anyone is signed in. */
export function useAuthConfig() {
  return useQuery({ queryKey: ["auth-config"], queryFn: getAuthConfig });
}
