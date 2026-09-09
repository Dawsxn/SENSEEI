import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate, useSearchParams } from "react-router-dom";

import { Button } from "../../components/ui/button";
import { devLogin, getDevUsers } from "../../lib/api";
import { useAuthConfig } from "./useAuth";

export function SignInScreen() {
  const [params] = useSearchParams();
  const { data: config } = useAuthConfig();
  const error = params.get("error");

  return (
    <div className="flex h-full flex-col items-center justify-center px-4">
      <div className="mb-6 text-[22px] font-semibold tracking-[-0.01em]">
        SEN<span className="text-primary">SEE-I</span>
      </div>

      <div className="w-full max-w-[380px] rounded-lg border p-6 shadow-raised">
        <h1 className="text-[16px] font-semibold">Sign in</h1>
        <p className="mt-1 text-[13px] text-muted-foreground">
          Use your DLSU Google account.
        </p>

        {error === "not_dlsu" && (
          <p className="mt-3 rounded-md border border-fail-border bg-fail px-3 py-2 text-[13px] text-fail-foreground">
            That account isn't a DLSU address. Sign in with your @dlsu.edu.ph account.
          </p>
        )}
        {error === "oauth" && (
          <p className="mt-3 rounded-md border border-fail-border bg-fail px-3 py-2 text-[13px] text-fail-foreground">
            Sign-in didn't complete. Please try again.
          </p>
        )}

        <Button
          variant="secondary"
          className="mt-4 w-full"
          onClick={() => {
            window.location.href = "/auth/login";
          }}
        >
          Continue with Google
        </Button>

        {config?.dev_bypass && <DevBypass />}
      </div>
    </div>
  );
}

/** Local/dev only: sign in as a seeded user without Google. */
function DevBypass() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { data: users } = useQuery({ queryKey: ["dev-users"], queryFn: getDevUsers });

  async function actAs(id: string) {
    await devLogin(id);
    await queryClient.invalidateQueries({ queryKey: ["me"] });
    navigate("/");
  }

  return (
    <div className="mt-6 border-t pt-4">
      <p className="mb-2 text-[12px] font-medium uppercase tracking-wide text-muted-foreground">
        Dev · act as
      </p>
      <div className="flex flex-col gap-2">
        {(users ?? []).map((u) => (
          <button
            key={u.id}
            onClick={() => actAs(u.id)}
            className="flex items-center justify-between rounded-md border px-3 py-2 text-left text-[13px] hover:bg-muted"
          >
            <span>{u.name}</span>
            <span className="text-muted-foreground capitalize">{u.role}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
