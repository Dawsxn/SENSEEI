/** Sign out, for a trial participant, locally only.
 *
 * Participants have no way out on purpose (docs/context/trial.md). Testing the
 * trial locally means switching between IDs, though, so when the dev sign-in
 * picker is on, a small Sign out sits in the corner of their screens. The
 * server turns the picker off everywhere but locally, so the trial site never
 * shows this. */

import { useQueryClient } from "@tanstack/react-query";
import { LogOut } from "lucide-react";
import { useNavigate } from "react-router-dom";

import { logout } from "../../lib/api";
import { useAuthConfig } from "../auth/useAuth";
import { useIsParticipant } from "./useTrial";

export function DevSignOut() {
  const { data: config } = useAuthConfig();
  const participant = useIsParticipant();
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  if (!participant || !config?.dev_bypass) return null;

  async function signOut() {
    await logout();
    await queryClient.resetQueries();
    navigate("/login", { replace: true });
  }

  return (
    <button
      onClick={signOut}
      className="fixed bottom-3 left-3 z-50 flex items-center gap-1.5 rounded-md border border-dashed bg-background px-2.5 py-1.5 text-[12px] text-muted-foreground shadow-sm hover:text-foreground"
    >
      <LogOut className="h-3.5 w-3.5" />
      Dev · sign out
    </button>
  );
}
