import { useQueryClient } from "@tanstack/react-query";
import { LogOut, User, Users } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";

import { SwitchUserDialog } from "../features/auth/SwitchUserDialog";
import { useMe, useTrialMode } from "../features/auth/useAuth";
import { logout } from "../lib/api";

/** The app shell's top bar: the wordmark, the instructor's two sections, and
 *  the account menu. The sections are for instructors only; a student moves
 *  between their classes from the pages themselves, and joins one from the
 *  Classes page. On a phone the sections drop to a row of their own under the
 *  bar, where there is room for them. */
export function AppTopBar() {
  const { data: user } = useMe();
  const instructor = user?.role === "instructor";
  // A grader sees one section, Grading, and nothing else.
  const sections = instructor || user?.role === "grader";

  return (
    <header className="shrink-0 border-b">
      <div className="flex h-14 items-center justify-between px-4 sm:px-6">
        <div className="flex items-center gap-8">
          {/* SEE-I is set in the accent colour: the framework name sits inside
              the product name (design/README.md). */}
          <span className="text-[15px] font-semibold tracking-[-0.01em]">
            SEN<span className="text-primary">SEE-I</span>
          </span>
          {sections && <Sections className="hidden h-14 sm:flex" />}
        </div>

        <AccountMenu />
      </div>
      {sections && <Sections className="flex h-12 px-4 sm:hidden" />}
    </header>
  );
}

function Sections({ className }: { className: string }) {
  // The trial instance adds the participant IDs and grading. A grader has
  // grading alone.
  const trial = useTrialMode();
  const { data: user } = useMe();
  const grader = user?.role === "grader";
  const tab = ({ isActive }: { isActive: boolean }) =>
    `-mb-px flex items-center border-b-2 text-[14px] font-medium ${
      isActive
        ? "border-foreground text-foreground"
        : "border-transparent text-muted-foreground hover:text-foreground"
    }`;
  return (
    <nav className={`gap-6 ${className}`}>
      {!grader && (
        <>
          <NavLink to="/classes" className={tab}>
            Classes
          </NavLink>
          <NavLink to="/library" className={tab}>
            Readings
          </NavLink>
        </>
      )}
      {trial && !grader && (
        <NavLink to="/participants" className={tab}>
          Participants
        </NavLink>
      )}
      {trial && (
        <NavLink to="/grading" className={tab}>
          Grading
        </NavLink>
      )}
    </nav>
  );
}

function AccountMenu() {
  const { data: user } = useMe();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [switching, setSwitching] = useState(false);
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
          {/* QA only: the server decides who may switch. */}
          {user?.can_switch && (
            <button
              onClick={() => {
                setOpen(false);
                setSwitching(true);
              }}
              className="flex w-full items-center gap-2 px-3 py-2.5 text-left text-[14px] hover:bg-muted"
            >
              <Users className="h-4 w-4 text-muted-foreground" />
              Switch user
            </button>
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
      {switching && <SwitchUserDialog onClose={() => setSwitching(false)} />}
    </div>
  );
}
