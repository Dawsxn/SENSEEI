/** The trial's briefing screens, added after the user acceptance test, where
 * participants went in without knowing what the study or SEE-I was:
 *
 * - `Welcome`: every group, before the pre-test. What the study is for and the
 *   steps their group will take, with each step's time.
 * - `AboutSeei` and `SessionGuide`: the SEE-I group only, after the pre-test and
 *   before the reading, so the pre-test is answered without SEE-I in mind.
 *
 * None of them is timed: each stage's clock starts on its own Start button. */

import { ArrowRight } from "lucide-react";

import { Button } from "../../components/ui/button";
import { useReading } from "../readings/useReadings";
import type { ClassMode } from "../classes/types";
import { useTrialStatus } from "./useTrial";
import { Logo } from "../../components/Logo";

/** The concept the reading teaches, for the instructions: its title, in a
 *  sentence ("the concept of strategic offensives"). */
export function useConcept(): string {
  const { data } = useTrialStatus();
  const { data: reading } = useReading(data?.reading_id ?? undefined);
  return reading?.title.toLowerCase() ?? "the reading";
}

function TopBar() {
  return (
    <header className="flex h-14 shrink-0 items-center border-b px-4 sm:px-5">
      <Logo />
    </header>
  );
}

function Page({ children, wide = false }: { children: React.ReactNode; wide?: boolean }) {
  return (
    <div className="flex h-full flex-col">
      <TopBar />
      <main className="min-h-0 flex-1 overflow-y-auto">
        <div className={wide ? "mx-auto max-w-[1344px] px-4 py-8 sm:px-6 sm:py-10" : "mx-auto max-w-[760px] px-4 py-10 sm:px-6 sm:py-16"}>
          {children}
        </div>
      </main>
    </div>
  );
}

const P = ({ children }: { children: React.ReactNode }) => (
  <p className="mt-3 text-[15px] leading-[1.65] text-body">{children}</p>
);

function Continue({ onClick }: { onClick: () => void }) {
  return (
    <div className="mt-8 flex justify-end">
      <Button onClick={onClick} autoFocus>
        Continue
      </Button>
    </div>
  );
}

// --------------------------------------------------------------------------- #
// welcome

/** The group's name, as the consent form gives it. Plain names that say what
 *  each group does: never "control" or "experimental", which can change how
 *  hard a participant tries. */
const GROUP_NAME: Record<ClassMode, string> = {
  seei: "SENSEE-I group",
  chatbot: "Chatbot group",
  reading_only: "Reading-only group",
};

const STEP_NAME: Record<ClassMode, string> = {
  seei: "Reading and tutoring session",
  chatbot: "Reading with a chatbot",
  reading_only: "Reading",
};

export function Welcome({ onContinue }: { onContinue: () => void }) {
  const { data } = useTrialStatus();
  if (!data) {
    return (
      <Page>
        <p className="text-[14px] text-muted-foreground">Loading&hellip;</p>
      </Page>
    );
  }
  const pre = data.test_minutes?.pre ?? 0;
  const post = data.test_minutes?.post ?? 0;
  const steps: [string, string][] = [
    ["Pre-test", `${pre} min`],
    ...(data.mode === "seei" ? [["About SENSEE-I", "A short guide"] as [string, string]] : []),
    [STEP_NAME[data.mode], `${data.minutes} min`],
    ["Post-test", `${post} min`],
  ];
  return (
    <Page>
      <h1 className="text-[24px] font-semibold tracking-[-0.02em]">Good day!</h1>
      <P>
        Thank you for agreeing to take part today. This study examines which way of studying an
        expository text best improves your understanding of the concept it explains.
      </P>
      <P>
        You will complete the steps below. They depend on the group you were randomly assigned to
        through the ID slip you drew.
      </P>
      <p className="mt-5 text-[15px] leading-[1.65]">
        You are in the <span className="font-semibold">{GROUP_NAME[data.mode]}</span>.
      </p>
      <ol
        aria-label="Your steps"
        className="mt-8 flex flex-col items-stretch gap-3 rounded-lg border bg-card px-5 py-6 sm:flex-row sm:items-start sm:justify-center sm:gap-0"
      >
        {steps.map(([name, time], i) => (
          <li key={name} className="flex items-center gap-3 sm:contents">
            {i > 0 && (
              <ArrowRight className="hidden h-4 w-7 shrink-0 self-start text-muted-foreground/60 sm:mt-2.5 sm:block" aria-hidden />
            )}
            <div className="flex items-center gap-3 sm:w-[160px] sm:flex-col sm:text-center">
              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border-[1.5px] border-primary text-[15px] font-semibold text-primary">
                {i + 1}
              </span>
              <span>
                <span className="block text-[14px] font-medium leading-[1.4] sm:mt-1">{name}</span>
                <span className="block text-[13px] text-muted-foreground">{time}</span>
              </span>
            </div>
          </li>
        ))}
      </ol>
      <p className="mt-2.5 text-center text-[13px] text-muted-foreground">
        {pre + data.minutes + post} minutes in total
      </p>
      <P>
        Each step has its own time limit. You won&rsquo;t see a timer, but we&rsquo;ll let you know
        when time is running low. If you finish a step early, you go on to the next one.
      </P>
      <Continue onClick={onContinue} />
    </Page>
  );
}

// --------------------------------------------------------------------------- #
// the SEE-I group's guide

export const SEEI: [string, string][] = [
  ["State", "Say what the concept is, briefly and clearly."],
  ["Elaborate", "Explain it in more detail, in your own words."],
  ["Exemplify", "Give your own example of it, plus one thing that is not an example."],
  ["Illustrate", "Compare it to something outside the reading, like an analogy or metaphor, that is easy to picture."],
];

export function AboutSeei({ onContinue }: { onContinue: () => void }) {
  return (
    <Page>
      <h1 className="text-[24px] font-semibold tracking-[-0.02em]">About SENSEE-I</h1>
      <P>
        SENSEE-I is a learning tool that helps you understand a concept from a reading. It uses
        SEE-I, four steps that show how well you understand something:
      </P>
      <dl className="mt-5 rounded-lg border bg-card">
        {SEEI.map(([step, text], i) => (
          <div key={step} className={i ? "flex flex-col gap-1 border-t px-5 py-4 sm:flex-row sm:gap-5" : "flex flex-col gap-1 px-5 py-4 sm:flex-row sm:gap-5"}>
            <dt className="w-[96px] shrink-0 pt-0.5 text-[12px] font-semibold uppercase tracking-[0.06em] text-primary">
              {step}
            </dt>
            <dd className="text-[15px] leading-[1.6]">{text}</dd>
          </div>
        ))}
      </dl>
      <P>
        The learning tool checks each answer. If something is missing, it tells you what, and you
        try again. Once your answer passes, you move to the next step.
      </P>
      <Continue onClick={onContinue} />
    </Page>
  );
}

/** Where each numbered mark sits on the picture, as a share of its size. */
const GUIDE: { name: string; text: string; x: number; y: number }[] = [
  { name: "Reading", text: "Stays open the whole session.", x: 23, y: 50 },
  { name: "Steps", text: "Shows which SEE-I step you are on.", x: 23.8, y: 8 },
  {
    name: "Components",
    text: "The key ideas of the reading. Your State and Elaborate answers need to cover all of them.",
    x: 87.8, y: 9,
  },
  { name: "Rubric", text: "What your answer is graded on. It changes with each step.", x: 96, y: 9 },
  { name: "Chat box", text: "Type your answer here. Enter sends, Shift+Enter starts a new line.", x: 74, y: 91.5 },
];

function Mark({ n }: { n: number }) {
  return (
    <span className="flex h-[26px] w-[26px] shrink-0 items-center justify-center rounded-full bg-primary text-[13px] font-semibold text-primary-foreground shadow-[0_0_0_3px_#fff]">
      {n}
    </span>
  );
}

export function SessionGuide({ onContinue }: { onContinue: () => void }) {
  return (
    <Page wide>
      <h1 className="text-[24px] font-semibold tracking-[-0.02em]">How the session works</h1>
      <div className="mt-6 flex flex-col gap-8 lg:flex-row lg:items-start">
        <div className="relative w-full overflow-hidden rounded-lg border bg-card lg:w-[880px] lg:shrink-0">
          <img
            src="/guide/session-guide.png"
            alt="The tutoring session: the reading on the left, the chat on the right"
            className="block w-full"
          />
          <div className="pointer-events-none absolute inset-y-0 left-0 w-[46%] outline outline-2 -outline-offset-2 outline-primary" />
          {GUIDE.map((g, i) => (
            <span
              key={g.name}
              className="absolute -translate-x-1/2 -translate-y-1/2"
              style={{ left: `${g.x}%`, top: `${g.y}%` }}
            >
              <Mark n={i + 1} />
            </span>
          ))}
        </div>
        <ol className="flex flex-col gap-5">
          {GUIDE.map((g, i) => (
            <li key={g.name} className="flex gap-3.5">
              <Mark n={i + 1} />
              <p className="text-[15px] leading-[1.6]">
                <span className="font-semibold">{g.name}.</span>{" "}
                <span className="text-body">{g.text}</span>
              </p>
            </li>
          ))}
        </ol>
      </div>
      <Continue onClick={onContinue} />
    </Page>
  );
}
