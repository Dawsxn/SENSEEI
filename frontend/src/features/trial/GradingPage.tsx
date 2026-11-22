/** Grading the trial's tests, one participant at a time
 * (docs/context/trial.md; design/TrialGrading.dc.html).
 *
 * The grader and the research team see the same page. It shows participant IDs
 * and never a group, so grading stays blind. Multiple choice is scored already;
 * the grader scores each written answer against the rubric beside it, and a
 * score saves as soon as it is clicked. Scores can be changed any time. */

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { AppTopBar } from "../../components/AppTopBar";
import { getGrading, getGradingList, setScore } from "../../lib/api";
import { cn } from "../../lib/utils";
import type { GradingDetail, GradingWritten, TestGroup } from "./types";

const label = (w: Pick<GradingWritten, "test" | "item">) =>
  w.test === "pre" ? "Pre-test" : `Q${w.item.replace(/^q/, "")}`;
const key = (w: Pick<GradingWritten, "test" | "item">) => `${w.test}/${w.item}`;

export function GradingPage() {
  const [params, setParams] = useSearchParams();
  const list = useQuery({ queryKey: ["grading"], queryFn: getGradingList });
  const people = list.data ?? [];
  const selected = params.get("id") ?? people[0]?.code ?? null;
  const graded = people.filter((p) => p.posttest_ended && p.left === 0).length;

  return (
    <div className="flex h-full flex-col">
      <AppTopBar />
      <main className="min-h-0 flex-1 overflow-y-auto">
        <div className="mx-auto max-w-[1280px] px-4 py-6 sm:px-6 sm:py-8">
          <div className="mb-5 flex items-baseline justify-between">
            <h1 className="text-[24px] font-semibold tracking-[-0.02em]">Grading</h1>
            {people.length > 0 && (
              <span className="text-[13px] text-muted-foreground">
                {graded} of {people.length} participants graded
              </span>
            )}
          </div>

          {list.isLoading && <Muted>Loading&hellip;</Muted>}
          {list.isError && <Muted>Couldn&rsquo;t load the answers.</Muted>}
          {list.data && people.length === 0 && <Muted>No answers to grade yet.</Muted>}

          {people.length > 0 && (
            <div className="grid grid-cols-1 items-start gap-5 lg:grid-cols-[240px_1fr_380px]">
              <div className="overflow-hidden rounded-lg border bg-card">
                {people.map((p) => {
                  const done = p.posttest_ended && p.left === 0;
                  return (
                    <button
                      key={p.code}
                      onClick={() => setParams({ id: p.code })}
                      className={cn(
                        "flex w-full items-center justify-between border-b border-l-[3px] px-3.5 py-2.5 text-left last:border-b-0",
                        p.code === selected
                          ? "border-l-foreground bg-muted"
                          : "border-l-transparent hover:bg-muted/50",
                      )}
                    >
                      <span className="font-mono text-[13px] tracking-[0.05em]">{p.code}</span>
                      <span className={cn("text-[12px]", done ? "text-primary" : "text-muted-foreground")}>
                        {done ? "Graded" : `${p.left} left`}
                      </span>
                    </button>
                  );
                })}
              </div>
              {selected && <Participant code={selected} />}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

function Participant({ code }: { code: string }) {
  const queryClient = useQueryClient();
  const { data, isLoading, isError } = useQuery({
    queryKey: ["grading", code],
    queryFn: () => getGrading(code),
  });
  const [focus, setFocus] = useState<string | null>(null);

  // The rubric follows the first answer still to grade, until one is chosen.
  useEffect(() => {
    if (!data) return;
    if (focus && data.written.some((w) => key(w) === focus)) return;
    const next = data.written.find((w) => w.score === null) ?? data.written[0];
    setFocus(next ? key(next) : null);
  }, [data, focus]);
  useEffect(() => setFocus(null), [code]);

  async function score(w: GradingWritten, points: number) {
    setFocus(key(w));
    const next = await setScore(code, w.test, w.item, points);
    queryClient.setQueryData(["grading", code], next);
    void queryClient.invalidateQueries({ queryKey: ["grading"], exact: true });
  }

  if (isLoading) return <Muted>Loading&hellip;</Muted>;
  if (isError || !data) return <Muted>Couldn&rsquo;t load this participant.</Muted>;
  const focused = data.written.find((w) => key(w) === focus) ?? null;

  return (
    <>
      <div className="min-w-0">
        <span className="mb-3 block font-mono text-[15px] font-medium tracking-[0.05em]">{data.code}</span>
        <Summary data={data} />
        {data.posttest_ended && data.left === 0 && (
          <div className="mb-3 rounded-md border border-accent-soft-border bg-accent-soft px-3.5 py-2.5 text-[13px] text-accent-soft-foreground">
            All of this participant&rsquo;s answers are graded.
          </div>
        )}
        {data.choices.length > 0 && (
          <div className="mb-3 overflow-hidden rounded-lg border bg-card">
            <div className="border-b px-4 py-2.5 text-[12px] font-semibold">
              Multiple choice <span className="font-normal text-muted-foreground">&middot; scored automatically</span>
            </div>
            {data.choices.map((c) => (
              <div
                key={c.item}
                className="grid grid-cols-[40px_1fr_80px] items-center border-b px-4 py-2 text-[13px] last:border-b-0"
              >
                <span className="font-semibold">Q{c.item.replace(/^q/, "")}</span>
                <span className={c.correct ? "text-primary" : "text-fail-foreground"}>
                  {c.choice ? `Picked ${c.choice} · ` : "No answer · "}
                  {c.correct ? "Correct" : `Answer is ${c.answer}`}
                </span>
                <span className="text-right text-muted-foreground">{tick(c.sure)}</span>
              </div>
            ))}
          </div>
        )}
        {data.written.map((w) => (
          <WrittenCard
            key={key(w)}
            w={w}
            groups={w.item === "q12b" ? data.groups : null}
            focused={key(w) === focus}
            onFocus={() => setFocus(key(w))}
            onScore={(points) => void score(w, points)}
          />
        ))}
      </div>
      {focused && <Rubric w={focused} />}
    </>
  );
}

function tick(sure: boolean | null): string {
  return sure === null ? "" : sure ? "Sure" : "Not sure";
}

function Summary({ data }: { data: GradingDetail }) {
  const preMax = data.written.find((w) => w.test === "pre")?.points;
  const cells = [
    {
      label: "Pre-test",
      value: data.pretest_score === null ? null : `${data.pretest_score} / ${preMax ?? 3}`,
    },
    { label: "Post-test", value: data.posttest_total === null ? null : `${data.posttest_total} / 20` },
    {
      label: "Calibration",
      value:
        data.calibration !== null
          ? `${Math.round(data.calibration * 100)}%`
          : data.posttest_total !== null
            ? // Everything is scored, so the only reason is that nothing was ticked.
              "No ticks"
            : null,
    },
  ];
  return (
    <div className="mb-3 grid grid-cols-3 gap-2.5">
      {cells.map((c) => (
        <div key={c.label} className="rounded-lg border bg-card px-3.5 py-2.5">
          <div className="text-[12px] text-muted-foreground">{c.label}</div>
          <div className={cn("mt-0.5 text-[18px] font-semibold", c.value === null && "text-placeholder")}>
            {c.value ?? "Not graded yet"}
          </div>
        </div>
      ))}
    </div>
  );
}

function WrittenCard({
  w,
  groups,
  focused,
  onFocus,
  onScore,
}: {
  w: GradingWritten;
  groups: TestGroup[] | null;
  focused: boolean;
  onFocus: () => void;
  onScore: (points: number) => void;
}) {
  const answered = !!w.text?.trim();
  return (
    <div
      onClick={onFocus}
      className={cn(
        "mb-3 cursor-pointer rounded-lg border bg-card",
        focused ? "border-primary shadow-[0_0_0_3px_hsl(var(--ring)/0.3)]" : "border-border",
      )}
    >
      <div className="flex items-start gap-3 px-4 pt-3">
        <span className="flex-1">
          <span className="text-[12px] font-semibold">{label(w)}</span>
          <span className="ml-1.5 text-[13px] text-muted-foreground">{w.question}</span>
        </span>
        <span className="whitespace-nowrap text-[12px] text-muted-foreground">{tick(w.sure)}</span>
      </div>
      {groups && groups.some((g) => g.name || g.strategies || g.why) && (
        <div className="mx-4 mt-2.5 overflow-hidden rounded-md border text-[12.5px]">
          <div className="grid grid-cols-[120px_1fr_1fr] border-b bg-muted font-medium text-muted-foreground">
            <span className="px-2 py-1.5">Group name</span>
            <span className="border-l px-2 py-1.5">Strategies</span>
            <span className="border-l px-2 py-1.5">Why</span>
          </div>
          {groups
            .filter((g) => g.name || g.strategies || g.why)
            .map((g, i) => (
              <div key={i} className="grid grid-cols-[120px_1fr_1fr] border-b last:border-b-0">
                <span className="px-2 py-1.5">{g.name}</span>
                <span className="border-l px-2 py-1.5">{g.strategies}</span>
                <span className="border-l px-2 py-1.5">{g.why}</span>
              </div>
            ))}
        </div>
      )}
      <p
        className={cn(
          "mx-4 mt-2 whitespace-pre-wrap text-[14px] leading-[1.6]",
          !answered && "text-placeholder",
        )}
      >
        {answered ? w.text : "No answer"}
      </p>
      <div className="flex justify-end gap-1.5 px-4 py-3">
        {Array.from({ length: w.points + 1 }, (_, n) => (
          <button
            key={n}
            onClick={(e) => {
              e.stopPropagation();
              onScore(n);
            }}
            aria-label={`Score ${n}`}
            aria-pressed={w.score === n}
            className={cn(
              "h-8 w-9 rounded-md border text-[14px] font-semibold",
              w.score === n
                ? "border-primary bg-accent-soft text-accent-soft-foreground"
                : "border-border bg-background hover:bg-muted",
            )}
          >
            {n}
          </button>
        ))}
      </div>
    </div>
  );
}

function Rubric({ w }: { w: GradingWritten }) {
  return (
    <div className="sticky top-4 rounded-lg border bg-card px-5 py-4">
      <div className="text-[12px] font-medium uppercase tracking-[0.04em] text-muted-foreground">
        {w.test === "pre" ? "Pre-test" : `Question ${w.item.replace(/^q/, "")}`}
      </div>
      <div className="mt-3.5 text-[12px] font-medium uppercase tracking-[0.04em] text-muted-foreground">
        Reference answer
      </div>
      <p className="mt-2 text-[13px] leading-[1.6] text-body">{w.reference}</p>
      <div className="mt-4 overflow-hidden rounded-md border">
        {w.criteria.map((c) => (
          <div key={c.points} className="grid grid-cols-[36px_1fr] border-b text-[12.5px] leading-[1.5] last:border-b-0">
            <span className="border-r bg-muted py-2 text-center font-semibold">{c.points}</span>
            <span className="px-2.5 py-2 text-body">{c.text}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function Muted({ children }: { children: React.ReactNode }) {
  return <p className="py-10 text-center text-[14px] text-muted-foreground">{children}</p>;
}
