/** How SENSEE-I works: three screens on SEE-I, how a session runs, and what the
 *  core components and the rubric are.
 *
 * Shown two ways. Before a student's first session, the reading page sends
 * them here with `?next=` the reading step, and the last screen carries on into
 * it. From the help icon, it opens on its own, with a close button and Done at
 * the end, both going back to where the student was. Either way, finishing or
 * leaving marks it seen, so it never opens unasked again.
 */

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { BookOpen, Component, X } from "lucide-react";
import { useState } from "react";
import { useLocation, useNavigate, useSearchParams } from "react-router-dom";

import { Button } from "../../components/ui/button";
import { cn } from "../../lib/utils";
import { getRubric, markIntroSeen } from "../../lib/api";
import { useMe } from "../auth/useAuth";
import { SEEI } from "../trial/Briefing";
import { MAX_ATTEMPTS } from "../tutoring/types";

const LAST = 2;

export function HowItWorks() {
  const navigate = useNavigate();
  const location = useLocation();
  const [params] = useSearchParams();
  // Only a path inside the app; anything else is ignored rather than followed.
  const next = params.get("next")?.startsWith("/") ? params.get("next") : null;
  const { data: me } = useMe();
  const queryClient = useQueryClient();
  const [screen, setScreen] = useState(0);

  async function finish() {
    if (me && !me.seen_intro) {
      try {
        await markIntroSeen();
        await queryClient.invalidateQueries({ queryKey: ["me"] });
      } catch {
        // Not recorded: it shows once more next time, which is harmless.
      }
    }
    if (next) navigate(next, { replace: true });
    // Back where the student came from, or home if they arrived here directly
    // (the router marks the first page of a visit `default`).
    else if (location.key !== "default") navigate(-1);
    else navigate("/");
  }

  return (
    <div className="flex h-full flex-col">
      <header className="flex h-14 shrink-0 items-center justify-between border-b px-4 sm:px-6">
        <span className="text-[15px] font-semibold tracking-[-0.01em]">
          SEN<span className="text-primary">SEE-I</span>
        </span>
        {!next && (
          <button
            type="button"
            onClick={finish}
            aria-label="Close"
            className="rounded-md p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground"
          >
            <X className="h-5 w-5" />
          </button>
        )}
      </header>
      <main className="min-h-0 flex-1 overflow-y-auto">
        <div className="mx-auto max-w-[688px] px-4 pb-10 pt-6 sm:px-6 sm:pt-10">
          <div className="mb-2.5 text-[13px] text-muted-foreground">
            {screen + 1} of {LAST + 1}
          </div>
          {screen === 0 && <AboutSeei />}
          {screen === 1 && <SessionFlow />}
          {screen === 2 && <ComponentsAndRubric />}

          <div className="mt-7 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
            {screen > 0 && (
              <Button
                variant="secondary"
                className="h-10 w-full sm:h-9 sm:w-auto"
                onClick={() => setScreen((s) => s - 1)}
              >
                Back
              </Button>
            )}
            <Button
              className="h-10 w-full px-5 sm:h-9 sm:w-auto"
              onClick={() => (screen < LAST ? setScreen((s) => s + 1) : finish())}
            >
              {screen < LAST || next ? "Continue" : "Done"}
            </Button>
          </div>
        </div>
      </main>
    </div>
  );
}

function Title({ children }: { children: React.ReactNode }) {
  return <h1 className="text-[22px] font-semibold tracking-[-0.02em] sm:text-[24px]">{children}</h1>;
}

function P({ children }: { children: React.ReactNode }) {
  return <p className="mt-3 text-[15px] leading-[1.65] text-foreground/80">{children}</p>;
}

function AboutSeei() {
  return (
    <>
      <Title>How SEE-I works</Title>
      <P>In SENSEE-I, you learn a concept from a reading by going through the four steps of SEE-I:</P>
      <dl className="mt-5 rounded-lg border">
        {SEEI.map(([step, text], i) => (
          <div
            key={step}
            className={`flex flex-col gap-1 px-4 py-3.5 sm:flex-row sm:gap-5 sm:px-5 sm:py-4 ${i ? "border-t" : ""}`}
          >
            <dt className="w-[96px] shrink-0 pt-0.5 text-[12px] font-semibold uppercase tracking-[0.06em] text-primary">
              {step}
            </dt>
            <dd className="text-[15px] leading-[1.6]">{text}</dd>
          </div>
        ))}
      </dl>
    </>
  );
}

/** A drawing of the screen at each stage, made of shapes so it fits any width.
 *  The session screen itself splits only from laptop width (`lg`); narrower, it
 *  switches between the reading and the chat, and so does the drawing. */
function SessionFlow() {
  return (
    <>
      <Title>How a session works</Title>
      <div className="mt-6 flex flex-col gap-4">
        <Stage
          title="1. Read"
          text="The session starts on a reading-only screen, where you read the material in full. Press Done once you've finished."
          picture={
            <Frame>
              <Pane>
                <Lines />
                <span className="absolute bottom-1.5 right-1.5 rounded bg-primary px-1.5 py-0.5 text-[9px] font-semibold text-primary-foreground">
                  Done
                </span>
              </Pane>
            </Frame>
          }
        />
        <Stage
          title="2. Answer"
          text={`You then move to the tutoring screen, where you answer each SEE-I step with the reading still available. Each step allows up to ${MAX_ATTEMPTS} tries, and the count starts over at the next step.`}
          picture={
            <>
              <Frame className="hidden lg:flex">
                <Pane>
                  <Lines />
                </Pane>
                <Chat />
              </Frame>
              <Frame className="flex-col lg:hidden">
                <div className="flex gap-1">
                  <span className="flex-1 rounded py-0.5 text-center text-[10px] font-medium text-muted-foreground">
                    Reading
                  </span>
                  <span className="flex-1 rounded bg-border py-0.5 text-center text-[10px] font-medium">
                    Chat
                  </span>
                </div>
                <Chat />
              </Frame>
            </>
          }
        />
        <Stage
          title="3. Finish"
          text={`The session ends once you pass all four steps, or if you use all ${MAX_ATTEMPTS} tries on a step without passing it.`}
          picture={
            <Frame className="flex-col items-start justify-center gap-1.5 bg-background px-3.5">
              {SEEI.map(([step]) => (
                <span
                  key={step}
                  className="rounded-full border border-accent-soft-border bg-accent-soft px-2 text-[11px] font-semibold text-accent-soft-foreground"
                >
                  ✓ {step}
                </span>
              ))}
            </Frame>
          }
        />
      </div>
    </>
  );
}

function Stage({ title, text, picture }: { title: string; text: string; picture: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-3.5 rounded-lg border p-4 sm:flex-row sm:items-center sm:gap-5">
      <div className="w-full shrink-0 sm:w-[200px]">{picture}</div>
      <div className="flex flex-col gap-1">
        <span className="text-[15px] font-semibold">{title}</span>
        <span className="text-[15px] leading-[1.6] text-foreground/80">{text}</span>
      </div>
    </div>
  );
}

function Frame({ className = "", children }: { className?: string; children: React.ReactNode }) {
  return (
    <div aria-hidden className={cn("flex h-[112px] gap-1.5 rounded-md border bg-muted/50 p-2", className)}>
      {children}
    </div>
  );
}

function Pane({ children }: { children: React.ReactNode }) {
  return (
    <div className="relative flex flex-1 flex-col gap-1.5 rounded border bg-background p-2">{children}</div>
  );
}

function Lines() {
  return (
    <>
      {["w-full", "w-full", "w-2/3", "w-full", "w-2/3"].map((w, i) => (
        <i key={i} className={`block h-[5px] rounded bg-border ${w}`} />
      ))}
    </>
  );
}

function Chat() {
  return (
    <Pane>
      <i className="block h-[5px] w-4/5 rounded bg-border" />
      <i className="ml-auto block h-3.5 w-3/5 rounded bg-accent-soft-border/60" />
      <i className="block h-[5px] w-1/2 rounded bg-border" />
      <i className="mt-auto block h-3.5 rounded border" />
    </Pane>
  );
}

function ComponentsAndRubric() {
  const { data: rubric } = useQuery({ queryKey: ["rubric"], queryFn: getRubric });
  // A real criterion, word for word from the rubric in use: Brevity under State
  // where it exists, or else the first one there is.
  const state = rubric?.steps.find((s) => s.step === "State") ?? rubric?.steps[0];
  const example = state?.criteria.find((c) => c.name === "Brevity") ?? state?.criteria[0];

  return (
    <>
      <Title>Core components and the rubric</Title>
      <section className="mt-6 rounded-lg border px-4 py-4 sm:px-5">
        <ButtonLook icon={<Component className="h-4 w-4" />}>Components</ButtonLook>
        <P>
          These are the key ideas of the reading, which you should keep in mind as the session
          revolves around them. Some criteria from the rubric also reference them.
        </P>
      </section>
      <section className="mt-4 rounded-lg border px-4 py-4 sm:px-5">
        <ButtonLook icon={<BookOpen className="h-4 w-4" />}>Rubric</ButtonLook>
        <P>
          The rubric holds the criteria that each of your answers is graded on. Each SEE-I step has
          its own, which describes the traits of an expected answer for that specific step.
        </P>
        {example && (
          <>
            <div className="mt-3.5 text-[12px] font-medium uppercase tracking-[0.04em] text-muted-foreground">
              Example
            </div>
            <div className="mt-1.5 flex gap-3 rounded-md bg-muted/50 p-3 text-[13px] leading-[1.55] text-foreground/70">
              <span className="inline-flex h-5 shrink-0 items-center self-start rounded-full border bg-background px-2 text-[11px] font-medium text-foreground/80">
                {example.name}
              </span>
              <span>{example.requirement}</span>
            </div>
          </>
        )}
        <P>When an answer fails a certain criterion, its name shows as a red tag under the tutor's reply.</P>
      </section>
    </>
  );
}

/** What the session screen's button looks like, so the student knows it there. */
function ButtonLook({ icon, children }: { icon: React.ReactNode; children: React.ReactNode }) {
  return (
    <span className="inline-flex h-[30px] items-center gap-1.5 rounded-md border px-3 text-[13px] font-medium">
      {icon}
      {children}
    </span>
  );
}
