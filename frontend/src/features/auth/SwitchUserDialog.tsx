/** Switch to another seeded person, for QA.
 *
 * Offered only when the server says so (`can_switch` on /auth/me): locally with
 * the dev bypass on, or on the deployed development environment to someone on
 * its QA list who signed in with Google first. Never in production.
 *
 * Switching resets everything cached, since every query so far was answered for
 * the previous person.
 */

import { useEffect } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";

import { devLogin, getDevUsers } from "../../lib/api";
import { useMe } from "./useAuth";

export function SwitchUserDialog({ onClose }: { onClose: () => void }) {
  const { data: me } = useMe();
  const { data: users } = useQuery({ queryKey: ["dev-users"], queryFn: getDevUsers });
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);

  async function switchTo(id: string) {
    await devLogin(id);
    // Reset rather than clear: clearing drops the cache but leaves a page that
    // is already showing to keep its old answers, so switching from home to
    // home would show the previous person. Resetting refetches what is on
    // screen, as the new person.
    await queryClient.resetQueries();
    onClose();
    navigate("/");
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-black/30 p-0 sm:items-center sm:p-4"
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Switch user"
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-[380px] rounded-t-lg bg-background p-5 shadow-lg sm:rounded-lg"
      >
        <h2 className="text-[16px] font-semibold">Switch user</h2>
        <div className="mt-4 flex max-h-[60vh] flex-col gap-1.5 overflow-y-auto">
          {(users ?? []).map((u) => {
            const current = u.id === me?.id;
            return (
              <button
                key={u.id}
                onClick={() => switchTo(u.id)}
                disabled={current}
                className="flex items-center justify-between rounded-md border px-3 py-2 text-left text-[13px] enabled:hover:bg-muted disabled:bg-muted/60"
              >
                <span className="truncate">{u.name}</span>
                <span className="shrink-0 capitalize text-muted-foreground">
                  {current ? "You" : u.role}
                </span>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
