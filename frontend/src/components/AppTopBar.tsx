import { useQueryClient } from "@tanstack/react-query";
import { LogOut, User } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";

import { useMe } from "../features/auth/useAuth";
import { JoinClassDialog } from "../features/readings/JoinClassDialog";
import { logout } from "../lib/api";
import { Button } from "./ui/button";

/** The app shell's top bar: the wordmark, the instructor's two sections, Join a
 *  class, and the account menu. Join a class is for students only; instructors
 *  make classes rather than join them. The sections are for instructors only;
 *  a student has one page to be on. On a phone the sections drop to a row of
 *  their own under the bar, where there is room for them. */
export function AppTopBar() {
  const { data: user } = useMe();
  const [joining, setJoining] = useState(false);
  const instructor = user?.role === "instructor";

  return (
    <header className="shrink-0 border-b">
      <div className="flex h-14 items-center justify-between px-4 sm:px-6">
        <div className="flex items-center gap-8">
          {/* SEE-I is set in the accent colour: the framework name sits inside
              the product name (design/README.md). */}
          <span className="text-[15px] font-semibold tracking-[-0.01em]">
            SEN<span className="text-primary">SEE-I</span>
          </span>
          {instructor && <Sections className="hidden h-14 sm:flex" />}
        </div>

        <div className="flex items-center gap-3">
          {user?.role === "student" && (
            <Button variant="secondary" size="sm" onClick={() => setJoining(true)}>
              Join a class
            </Button>
          )}
          <AccountMenu />
        </div>
      </div>
      {instructor && <Sections className="flex h-12 px-4 sm:hidden" />}
      {joining && <JoinClassDialog onClose={() => setJoining(false)} />}
    </header>
  );
}

function Sections({ className }: { className: string }) {
  const tab = ({ isActive }: { isActive: boolean }) =>
    `-mb-px flex items-center border-b-2 text-[14px] font-medium ${
      isActive
        ? "border-foreground text-foreground"
        : "border-transparent text-muted-foreground hover:text-foreground"
    }`;
  return (
    <nav className={`gap-6 ${className}`}>
      <NavLink to="/classes" className={tab}>
        Classes
      </NavLink>
      <NavLink to="/library" className={tab}>
        Readings
      </NavLink>
    </nav>
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
