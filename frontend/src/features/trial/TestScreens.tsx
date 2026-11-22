/** The trial's pre-test and post-test, and the screen after them
 * (docs/context/trial.md; design/TrialTests.dc.html).
 *
 * The server decides which stage a participant is in; these screens follow it.
 * Each test has its own countdown, drawn from what the server last said. Answers
 * save as they are typed, so running out of time loses nothing: the server ends
 * the test at its deadline with whatever was saved. Submitting asks first,
 * since it cannot be undone.
 *
 * The reading is never shown here, so the tests are closed book. Leaving the
 * tab and pasting are logged, as in the session, with the stage they happened
 * in. */

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, Clock } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { Button } from "../../components/ui/button";
import { getTest, getTrialStatus, saveTestAnswer, startTest, submitTest } from "../../lib/api";
import { cn } from "../../lib/utils";
import { formatClock } from "./TrialClock";
import { logTrial, setTrialContext, useTrialLogging } from "./trialLog";
import type { SavedAnswer, TestGroup, TestItem, TestView, TestWhich } from "./types";
import { useCountdown, useTrialStatus } from "./useTrial";

/** When the countdown turns amber: the post-test's last five minutes, like the
 *  session's, and the five-minute pre-test's last minute. */
const LATE_SECONDS = { pre: 60, post: 5 * 60 } as const;
/** How long typing pauses before an answer saves. */
const SAVE_AFTER_MS = 700;
const EMPTY_GROUPS: TestGroup[] = [0, 1, 2].map(() => ({ name: "", strategies: "", why: "" }));

// --------------------------------------------------------------------------- #
// shared pieces

function useTestView(which: TestWhich) {
  return useQuery({ queryKey: ["test", which], queryFn: () => getTest(which), retry: false });
}

/** Move on once the server has said where to: fetch the status fresh first, so
 *  the next screen does not act on the stage the participant has just left. */
function useMoveOn() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  return useCallback(
    async (to: string, state?: unknown) => {
      await queryClient.fetchQuery({ queryKey: ["trial"], queryFn: getTrialStatus, staleTime: 0 });
      navigate(to, { replace: true, state });
    },
    [queryClient, navigate],
  );
}

/** A test page the server will not show (its time ran out, or it was already
 *  submitted, while the page was away) sends the participant on. */
function useLeaveIfClosed(isError: boolean, moveOn: (to: string) => Promise<void>) {
  useEffect(() => {
    if (isError) void moveOn("/");
  }, [isError, moveOn]);
}

/** Log the test's tab-leaving and pastes against its stage. */
function useTestLogging(stage: "pretest" | "posttest") {
  useTrialLogging(true);
  useEffect(() => {
    setTrialContext({ stage });
    return () => setTrialContext({});
  }, [stage]);
}

const logPaste = (e: React.ClipboardEvent) =>
  logTrial("paste", { length: e.clipboardData.getData("text").length });

function TestTopBar({ saved, clock }: { saved?: boolean; clock?: React.ReactNode }) {
  return (
    <header className="flex h-14 shrink-0 items-center gap-3 border-b px-4 sm:px-5">
      <span className="text-[15px] font-semibold tracking-[-0.01em]">
        SEN<span className="text-primary">SEE-I</span>
      </span>
      <div className="ml-auto flex shrink-0 items-center gap-3">
        {saved && (
          <span className="flex items-center gap-1 text-[13px] text-muted-foreground">
            <Check className="h-3.5 w-3.5" />
            Saved
          </span>
        )}
        {clock}
      </div>
    </header>
  );
}

/** The test's countdown. At zero it says so once, and the screen asks the server. */
function TestClock({ left, which }: { left: number | null; which: TestWhich }) {
  if (left === null) return null;
  const late = left <= LATE_SECONDS[which];
  return (
    <div
      role="timer"
      aria-label="Time left"
      className={cn("flex h-8 items-center gap-1.5 rounded-md px-2.5", late && "bg-[#fffbeb]")}
    >
      <Clock className={cn("h-[15px] w-[15px]", late ? "text-[#92400e]" : "text-muted-foreground")} />
      <span
        className={cn("text-[13px] font-medium tabular-nums", late ? "text-[#92400e]" : "text-[#3f3f46]")}
      >
        {formatClock(left)} left
      </span>
    </div>
  );
}

/** A small modal: one sentence and its buttons. */
function Dialog({ body, children }: { body: string; children: React.ReactNode }) {
  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/30 sm:items-center sm:p-4">
      <div
        role="alertdialog"
        aria-modal="true"
        className="w-full max-w-[420px] rounded-t-lg bg-background p-6 shadow-lg sm:rounded-lg"
      >
        <p className="text-[14px] leading-[1.6]">{body}</p>
        <div className="mt-5 flex justify-end gap-2">{children}</div>
      </div>
    </div>
  );
}

function Notice({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-full items-center justify-center px-6 text-center text-[14px] text-muted-foreground">
      {children}
    </div>
  );
}

/** Answers held on screen and saved to the server shortly after each change.
 *  Each question saves on its own timer, so typing in one never delays another. */
function useAnswers(view: TestView | undefined) {
  const which = view?.which;
  const [answers, setAnswers] = useState<Record<string, SavedAnswer>>({});
  const [pending, setPending] = useState(0);
  const timers = useRef<Record<string, ReturnType<typeof setTimeout>>>({});
  const queued = useRef<Record<string, Omit<SavedAnswer, "item">>>({});
  const loaded = useRef(false);

  useEffect(() => {
    if (!view || loaded.current) return;
    loaded.current = true;
    setAnswers(Object.fromEntries(view.answers.map((a) => [a.item, a])));
  }, [view]);

  const send = useCallback(
    async (item: string) => {
      const patch = queued.current[item];
      delete queued.current[item];
      delete timers.current[item];
      if (!patch || !which) return;
      try {
        await saveTestAnswer(which, item, patch);
      } catch {
        // The test has ended, or the connection dropped; the server keeps what
        // it already had, and the screen follows the next status.
      } finally {
        setPending((n) => n - 1);
      }
    },
    [which],
  );

  const change = useCallback(
    (item: string, patch: Omit<SavedAnswer, "item">, now = false) => {
      setAnswers((a) => ({ ...a, [item]: { ...a[item], item, ...patch } }));
      if (!timers.current[item]) setPending((n) => n + 1);
      else clearTimeout(timers.current[item]);
      queued.current[item] = { ...queued.current[item], ...patch };
      timers.current[item] = setTimeout(() => void send(item), now ? 0 : SAVE_AFTER_MS);
    },
    [send],
  );

  /** Save everything waiting, now: before submitting, or as time runs out. */
  const flush = useCallback(async () => {
    const items = Object.keys(timers.current);
    for (const item of items) clearTimeout(timers.current[item]);
    await Promise.all(items.map((item) => send(item)));
  }, [send]);

  return { answers, change, flush, saved: pending === 0 };
}

function isAnswered(item: TestItem, a: SavedAnswer | undefined): boolean {
  if (!a) return false;
  if (item.kind === "choice") return !!a.choice;
  if (item.kind === "text") return !!a.text?.trim();
  return !!a.groups?.some((g) => g.name.trim() || g.strategies.trim() || g.why.trim());
}

/** `q5` reads as 5, `q12a` as 12a. */
const label = (id: string) => id.replace(/^q/, "");
/** The number a question is listed under: 12a and 12b are both question 12. */
const number = (id: string) => label(id).replace(/[a-z]$/, "");

// --------------------------------------------------------------------------- #
// the pre-test

export function PreTestScreen() {
  const { data: view, isError, dataUpdatedAt } = useTestView("pre");
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const moveOn = useMoveOn();
  useLeaveIfClosed(isError, moveOn);
  const { answers, change, flush } = useAnswers(view);
  const [confirming, setConfirming] = useState(false);
  const [timeUp, setTimeUp] = useState(false);
  useTestLogging("pretest");

  // The clock starts on Start, like the post-test's, not when the screen opens.
  const [starting, setStarting] = useState(false);
  async function start() {
    setStarting(true);
    queryClient.setQueryData(["test", "pre"], await startTest("pre"));
    setStarting(false);
  }

  const left = useCountdown(view?.seconds_left, dataUpdatedAt);
  useEffect(() => {
    if (left !== 0 || timeUp) return;
    setTimeUp(true);
    void flush();
  }, [left, timeUp, flush]);

  async function submit() {
    setConfirming(false);
    await flush();
    queryClient.setQueryData(["trial"], await submitTest("pre"));
    navigate("/", { replace: true });
  }
  const onward = () => moveOn("/");

  if (isError || !view) return <Notice>Loading&hellip;</Notice>;
  if (!view.started) {
    return (
      <div className="flex h-full flex-col">
        <TestTopBar />
        <main className="flex flex-1 items-center justify-center px-6">
          <div className="-mt-16 max-w-[420px] text-center">
            <h1 className="text-[24px] font-semibold tracking-[-0.02em]">Pre-test</h1>
            <p className="mt-1.5 text-[14px] text-muted-foreground">
              You have {view.minutes} minutes.
            </p>
            <Button className="mt-6" onClick={() => void start()} disabled={starting}>
              Start
            </Button>
          </div>
        </main>
      </div>
    );
  }
  const item = view.items[0];

  return (
    <div className="flex h-full flex-col">
      <TestTopBar clock={<TestClock left={left} which="pre" />} />
      <main className="min-h-0 flex-1 overflow-y-auto">
        <div className="mx-auto max-w-[960px] px-4 py-10 sm:px-6 sm:py-16">
          <h1 className="text-[24px] font-semibold tracking-[-0.02em]">Pre-test</h1>
          <p className="mt-1.5 text-[14px] text-muted-foreground">
            Answer this in your own words before you read.
          </p>
          <label htmlFor="pre-answer" className="mt-7 block text-[15px] font-medium">
            {item.question}
          </label>
          <textarea
            id="pre-answer"
            className="mt-2.5 h-[320px] w-full resize-none rounded-md border px-4 py-3.5 text-[15px] leading-[1.6] outline-none focus:ring-2 focus:ring-ring"
            placeholder="Type your answer"
            value={answers[item.id]?.text ?? ""}
            onChange={(e) => change(item.id, { text: e.target.value })}
            onPaste={logPaste}
            disabled={timeUp}
          />
          <div className="mt-4 flex justify-end">
            <Button onClick={() => setConfirming(true)} disabled={timeUp}>
              Submit
            </Button>
          </div>
        </div>
      </main>
      {confirming && (
        <Dialog body="You can't change your answer after submitting.">
          <Button variant="secondary" size="sm" onClick={() => setConfirming(false)} autoFocus>
            Go back
          </Button>
          <Button size="sm" onClick={() => void submit()}>
            Submit
          </Button>
        </Dialog>
      )}
      {timeUp && (
        <Dialog body="Time's up, and your answer was saved.">
          <Button size="sm" onClick={() => void onward()} autoFocus>
            Continue
          </Button>
        </Dialog>
      )}
    </div>
  );
}

// --------------------------------------------------------------------------- #
// the post-test

export function PostTestScreen() {
  const { data: view, isError, dataUpdatedAt } = useTestView("post");
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const moveOn = useMoveOn();
  useLeaveIfClosed(isError, moveOn);
  const { answers, change, flush, saved } = useAnswers(view);
  const [confirming, setConfirming] = useState(false);
  const [starting, setStarting] = useState(false);
  useTestLogging("posttest");

  const left = useCountdown(view?.seconds_left, dataUpdatedAt);
  const ended = useRef(false);
  useEffect(() => {
    if (left !== 0 || ended.current) return;
    ended.current = true;
    // The server ends the test at its deadline with what was saved.
    void flush().then(() => moveOn("/finished", { timeUp: true }));
  }, [left, flush, moveOn]);

  const items = view?.items ?? [];
  const parts = useMemo(() => {
    const out: { part: string; items: TestItem[]; points: number }[] = [];
    for (const item of items) {
      let p = out.find((x) => x.part === item.part);
      if (!p) out.push((p = { part: item.part, items: [], points: 0 }));
      p.items.push(item);
      p.points += item.points;
    }
    return out;
  }, [items]);

  // Numbered questions, for the list on the left: 12a and 12b are one.
  const numbered = useMemo(() => {
    const byNumber = new Map<string, TestItem[]>();
    for (const item of items) {
      const n = number(item.id);
      byNumber.set(n, [...(byNumber.get(n) ?? []), item]);
    }
    return byNumber;
  }, [items]);
  const answeredNumbers = [...numbered].filter(([, its]) =>
    its.some((i) => isAnswered(i, answers[i.id])),
  ).length;
  const blanks = numbered.size - answeredNumbers;

  async function start() {
    setStarting(true);
    queryClient.setQueryData(["test", "post"], await startTest("post"));
    setStarting(false);
  }
  async function submit() {
    setConfirming(false);
    await flush();
    ended.current = true;
    queryClient.setQueryData(["trial"], await submitTest("post"));
    navigate("/finished", { replace: true });
  }

  if (isError || !view) return <Notice>Loading&hellip;</Notice>;

  if (!view.started) {
    return (
      <div className="flex h-full flex-col">
        <TestTopBar />
        <main className="flex flex-1 items-center justify-center px-6">
          <div className="-mt-16 max-w-[420px] text-center">
            <h1 className="text-[24px] font-semibold tracking-[-0.02em]">Post-test</h1>
            <p className="mt-1.5 text-[14px] text-muted-foreground">
              You have {view.minutes} minutes, and the reading won&rsquo;t be shown.
            </p>
            <Button className="mt-6" onClick={() => void start()} disabled={starting}>
              Start
            </Button>
          </div>
        </main>
      </div>
    );
  }

  const jump = (n: string) =>
    document.getElementById(`question-${n}`)?.scrollIntoView({ behavior: "smooth", block: "start" });

  return (
    <div className="flex h-full flex-col">
      <TestTopBar saved={saved} clock={<TestClock left={left} which="post" />} />
      <main className="min-h-0 flex-1 overflow-y-auto">
        <div className="mx-auto flex max-w-[1140px] gap-14 px-4 sm:px-6">
          {/* Where each part starts, what is answered, and Submit. */}
          <aside className="sticky top-0 hidden w-[220px] shrink-0 self-start pt-10 lg:block">
            {parts.map((p) => (
              <div key={p.part} className="mb-5">
                <div className="mb-2 text-[13px] font-semibold text-muted-foreground">Part {p.part}</div>
                <div className="flex flex-wrap gap-1.5">
                  {[...new Set(p.items.map((i) => number(i.id)))].map((n) => {
                    const done = numbered.get(n)!.some((i) => isAnswered(i, answers[i.id]));
                    return (
                      <button
                        key={n}
                        onClick={() => jump(n)}
                        aria-label={`Question ${n}${done ? ", answered" : ""}`}
                        className={cn(
                          "flex h-8 w-8 items-center justify-center rounded-md border text-[13px] font-medium",
                          done
                            ? "border-[#bbf7d0] bg-[#f0fdf4] text-[#15803d]"
                            : "border-border bg-background text-muted-foreground hover:text-foreground",
                        )}
                      >
                        {n}
                      </button>
                    );
                  })}
                </div>
              </div>
            ))}
            <div className="border-t pt-4">
              <div className="mb-3 text-[13px] text-muted-foreground">
                {answeredNumbers} of {numbered.size} answered
              </div>
              <Button className="w-full" onClick={() => setConfirming(true)}>
                Submit
              </Button>
            </div>
          </aside>

          <div className="min-w-0 flex-1 pb-16 pt-10">
            <h1 className="text-[24px] font-semibold tracking-[-0.02em]">Post-test</h1>
            <p className="mt-1.5 text-[14px] text-muted-foreground">
              Answer every question in your own words, without mentioning how you studied the reading.
            </p>
            {parts.map((p) => (
              <section key={p.part}>
                <div className="mt-9 flex items-baseline justify-between border-b pb-2">
                  <h2 className="text-[16px] font-semibold">Part {p.part}</h2>
                  <span className="text-[13px] text-muted-foreground">{p.points} points</span>
                </div>
                {view.strategy_list_parts.includes(p.part) && <StrategyList strategies={view.strategies} />}
                {p.items.map((item) => (
                  <Question
                    key={item.id}
                    item={item}
                    answer={answers[item.id]}
                    onChange={(patch, now) => change(item.id, patch, now)}
                    anchor={item.id === numbered.get(number(item.id))![0].id ? number(item.id) : undefined}
                  />
                ))}
              </section>
            ))}
            <div className="mt-9 flex justify-end border-t pt-5">
              <Button onClick={() => setConfirming(true)}>Submit</Button>
            </div>
          </div>
        </div>
      </main>
      {confirming && (
        <Dialog
          body={
            blanks > 0
              ? `${blanks} ${blanks === 1 ? "question has" : "questions have"} no answer, and you can't change your answers after submitting.`
              : "You can't change your answers after submitting."
          }
        >
          <Button variant="secondary" size="sm" onClick={() => setConfirming(false)} autoFocus>
            Go back
          </Button>
          <Button size="sm" onClick={() => void submit()}>
            Submit
          </Button>
        </Dialog>
      )}
    </div>
  );
}

function StrategyList({ strategies }: { strategies: string[] }) {
  return (
    <div className="mt-4 rounded-lg border bg-[#fafafa] px-4 py-3.5">
      <div className="mb-1 text-[13px] font-semibold">The seven offensive strategies from the reading</div>
      <ol className="space-y-0.5 text-[13px] leading-[1.55] text-[#3f3f46]">
        {strategies.map((s, i) => (
          <li key={s}>
            {i + 1}.&nbsp; {s}
          </li>
        ))}
      </ol>
    </div>
  );
}

function Radio({
  checked,
  onChange,
  name,
  children,
}: {
  checked: boolean;
  onChange: () => void;
  name: string;
  children: React.ReactNode;
}) {
  return (
    // `relative` keeps the hidden input inside the label; without it the input
    // sits outside the scrolling area and makes the whole page scroll too.
    <label className="relative flex cursor-pointer items-start gap-2.5">
      <input type="radio" name={name} checked={checked} onChange={onChange} className="peer sr-only" />
      <span
        className={cn(
          "mt-[3px] flex h-4 w-4 shrink-0 items-center justify-center rounded-full border-[1.5px] peer-focus-visible:ring-2 peer-focus-visible:ring-ring",
          checked ? "border-primary" : "border-[#a1a1aa]",
        )}
      >
        {checked && <span className="h-2 w-2 rounded-full bg-primary" />}
      </span>
      <span>{children}</span>
    </label>
  );
}

function Question({
  item,
  answer,
  onChange,
  anchor,
}: {
  item: TestItem;
  answer: SavedAnswer | undefined;
  onChange: (patch: Omit<SavedAnswer, "item">, now?: boolean) => void;
  anchor?: string;
}) {
  const groups = answer?.groups?.length ? answer.groups : EMPTY_GROUPS;
  const setGroup = (row: number, key: keyof TestGroup, value: string) => {
    const next = [0, 1, 2].map((i) => ({ ...(groups[i] ?? EMPTY_GROUPS[i]) }));
    next[row][key] = value;
    onChange({ groups: next });
  };

  return (
    <div id={anchor ? `question-${anchor}` : undefined} className="scroll-mt-6">
      <div className="mt-6 flex gap-2.5 text-[14px] leading-[1.6]">
        <span className="min-w-[28px] font-semibold">{label(item.id)}.</span>
        <span>{item.question}</span>
      </div>
      <div className="ml-[38px]">
        {item.kind === "choice" && (
          <div className="mt-2 space-y-2 text-[14px] leading-[1.5]">
            {item.options.map((o) => (
              <Radio
                key={o.key}
                name={item.id}
                checked={answer?.choice === o.key}
                onChange={() => onChange({ choice: o.key }, true)}
              >
                {o.key}. {o.text}
              </Radio>
            ))}
          </div>
        )}
        {item.kind === "text" && (
          <textarea
            aria-label={`Answer to question ${label(item.id)}`}
            className="mt-2.5 h-[110px] w-full resize-y rounded-md border px-3 py-2.5 text-[14px] leading-[1.6] outline-none focus:ring-2 focus:ring-ring"
            placeholder="Type your answer"
            value={answer?.text ?? ""}
            onChange={(e) => onChange({ text: e.target.value })}
            onPaste={logPaste}
          />
        )}
        {item.kind === "groups" && (
          <div className="mt-3 overflow-hidden rounded-md border">
            <div className="grid grid-cols-[150px_1fr_1fr] border-b bg-[#fafafa] text-[12px] font-medium text-muted-foreground">
              <span className="px-2.5 py-2">Group name</span>
              <span className="border-l px-2.5 py-2">Strategies in this group</span>
              <span className="border-l px-2.5 py-2">Why they belong together</span>
            </div>
            {[0, 1, 2].map((row) => (
              <div key={row} className={cn("grid grid-cols-[150px_1fr_1fr]", row < 2 && "border-b")}>
                {(["name", "strategies", "why"] as const).map((key, col) => (
                  <textarea
                    key={key}
                    aria-label={`Group ${row + 1}, ${key === "name" ? "name" : key === "strategies" ? "strategies" : "why they belong together"}`}
                    className={cn(
                      "h-[64px] resize-none px-2.5 py-2 text-[13px] leading-[1.5] outline-none focus:bg-[#f0fdf4]",
                      col > 0 && "border-l",
                    )}
                    value={groups[row]?.[key] ?? ""}
                    onChange={(e) => setGroup(row, key, e.target.value)}
                    onPaste={logPaste}
                  />
                ))}
              </div>
            ))}
          </div>
        )}
        {item.ticked && (
          <div className="mt-3 flex items-center gap-5 text-[13px]">
            <span className="italic text-muted-foreground">How sure are you?</span>
            <Radio name={`${item.id}-sure`} checked={answer?.sure === true} onChange={() => onChange({ sure: true }, true)}>
              I&rsquo;m sure
            </Radio>
            <Radio name={`${item.id}-sure`} checked={answer?.sure === false} onChange={() => onChange({ sure: false }, true)}>
              I&rsquo;m not sure
            </Radio>
          </div>
        )}
      </div>
    </div>
  );
}

// --------------------------------------------------------------------------- #
// done

export function TestDoneScreen() {
  const { state } = useLocation() as { state: { timeUp?: boolean } | null };
  const { data } = useTrialStatus();
  const navigate = useNavigate();
  // Anyone not actually done is sent where they belong.
  useEffect(() => {
    if (data && data.test_stage !== "done") navigate("/", { replace: true });
  }, [data, navigate]);
  return (
    <div className="flex h-full flex-col">
      <TestTopBar />
      <main className="flex flex-1 items-center justify-center px-6">
        <div className="-mt-16 text-center">
          <h1 className="text-[24px] font-semibold tracking-[-0.02em]">
            {state?.timeUp ? "Time’s up" : "You’re done"}
          </h1>
          <p className="mt-1.5 text-[14px] text-muted-foreground">
            {state?.timeUp
              ? "Your answers were saved, so please wait for the next instructions."
              : "Please wait for the next instructions."}
          </p>
        </div>
      </main>
    </div>
  );
}
