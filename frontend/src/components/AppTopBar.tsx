import { useQueryClient } from "@tanstack/react-query";
import { LogOut, User } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import { useMe } from "../features/auth/useAuth";
import { logout } from "../lib/api";
import { Button } from "./ui/button";

/** The app shell's top bar: the wordmark, Join a class, and the account menu.
 *  Join a class is a placeholder until enrolment exists; the account menu shows
 *  the signed-in user and signs them out. */
export function AppTopBar() {
  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b px-4 sm:px-6">
      {/* SEE-I is set in the accent colour: the framework name sits inside the
          product name (design/README.md). */}
      <span className="text-[15px] font-semibold tracking-[-0.01em]">
        SEN<span className="text-primary">SEE-I</span>
      </span>

      <div className="flex items-center gap-3">
        <Button variant="secondary" size="sm">
          Join a class
        </Button>
        <AccountMenu />
      </div>
    </header>
  );
}

function AccountMenu() {
  const { data: user } = useMe();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  async function signOut() {
    await logout();
    await queryClient.invalidateQueries({ queryKey: ["me"] });
    navigate("/login");
  }

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen((v) => !v)}
        aria-label="Account"
        className="flex h-8 w-8 items-center justify-center rounded-full bg-muted text-muted-foreground hover:text-foreground"
      >
        <User className="h-4 w-4" />
      </button>
      {open && (
        <div className="absolute right-0 top-10 z-50 w-56 overflow-hidden rounded-md border bg-background shadow-raised">
          {user && (
            <div className="border-b px-3 py-2.5">
              <div className="truncate text-[14px] font-medium">{user.name}</div>
              <div className="truncate text-[12px] text-muted-foreground">
                {user.email}
              </div>
            </div>
          )}
          <button
            onClick={signOut}
            className="flex w-full items-center gap-2 px-3 py-2.5 text-left text-[14px] hover:bg-muted"
          >
            <LogOut className="h-4 w-4 text-muted-foreground" />
            Sign out
          </button>
        </div>
      )}
    </div>
  );
}
