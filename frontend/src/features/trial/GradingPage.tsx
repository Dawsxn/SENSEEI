/** Grading the trial's tests, one participant at a time
 * (docs/context/trial.md; design/TrialGrading.dc.html).
 *
 * The grader and the research team see the same page. It shows participant IDs
 * and never a group, so grading stays blind. True/false sets (and multiple
 * choice) are scored already; the grader scores each written answer against the
 * rubric and reference answer beside it, and a score saves as soon as it is
 * clicked. Scores can be changed any time. */

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { AppTopBar } from "../../components/AppTopBar";
import { getGrading, getGradingList, setScore } from "../../lib/api";
import { cn } from "../../lib/utils";
import type { GradingDetail, GradingSet, GradingWritten } from "./types";

const label = (w: Pick<GradingWritten, "test" | "item">) =>
  w.test === "pre" ? "Pre-test" : `Q${w.item.replace(/^q/, "")}`;
const key = (w: Pick<GradingWritten, "test" | "item">) => `${w.test}/${w.item}`;

export function GradingPage() {
  const [params, setParams] = useSearchParams();
  const list = useQuery({ queryKey: ["grading"], queryFn: getGradingList });
  const everyone = list.data ?? [];
  // One sitting at a time, so a dry run stays out of the way. Kept in the URL.
  const batches = [...new Map(everyone.map((p) => [p.batch_id, p.batch_name])).entries()];
  const batch = params.get("batch");
  const people = batch ? everyone.filter((p) => p.batch_id === batch) : everyone;
  const selected = params.get("id") ?? people[0]?.code ?? null;
  const graded = people.filter((p) => p.posttest_ended && p.left === 0).length;
  const show = (next: { batch?: string | null; id?: string | null }) => {
    const out = new URLSearchParams();
    const b = next.batch === undefined ? batch : next.batch;
    const id = next.id === undefined ? params.get("id") : next.id;
    if (b) out.set("batch", b);
    if (id) out.set("id", id);
    setParams(out);
  };

  return (
    <div className="flex h-full flex-col">
      <AppTopBar />
      <main className="min-h-0 flex-1 overflow-y-auto">
        <div className="mx-auto max-w-[1280px] px-4 py-6 sm:px-6 sm:py-8">
          <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
            <h1 className="text-[24px] font-semibold tracking-[-0.02em]">Grading</h1>
            <div className="flex items-center gap-3">
              {batches.length > 1 && (
                <label className="flex items-center gap-2 text-[13px] text-muted-foreground">
                  Batch
                  <select
                    value={batch ?? ""}
                    onChange={(e) => show({ batch: e.target.value || null, id: null })}
                    className="h-8 rounded-md border bg-background px-2 text-[13px] text-foreground"
                  >
                    <option value="">All batches</option>
                    {batches.map(([id, name]) => (
                      <option key={id} value={id}>
                        {name}
                      </option>
                    ))}
                  </select>
                </label>
              )}
              {people.length > 0 && (
                <span className="text-[13px] text-muted-foreground">
                  {graded} of {people.length} participants graded
                </span>
              )}
            </div>
          </div>

          {list.isLoading && <Muted>Loading&hellip;</Muted>}
          {list.isError && <Muted>Couldn&rsquo;t load the answers.</Muted>}
          {list.data && people.length === 0 && <Muted>No answers to grade yet.</Muted>}

          {people.length > 0 && (
            <div className="grid grid-cols-1 items-start gap-5 lg:grid-cols-[240px_1fr_380px]">
              <div className="overflow-hidden rounded-lg border">
                {people.map((p) => {
                  const done = p.posttest_ended && p.left === 0;
                  return (
                    <button
                      key={p.code}
                      onClick={() => show({ id: p.code })}
                      className={cn(
                        "flex w-full items-center justify-between border-b border-l-[3px] px-3.5 py-2.5 text-left last:border-b-0",
                        p.code === selected
                          ? "border-l-foreground bg-muted"
                          : "border-l-transparent hover:bg-muted/50",
                      )}
                    >
                      <span className="font-mono text-[13px] tracking-[0.05em]">{p.code}</span>
                      <span className={cn("text-[12px]", done ? "text-[#15803d]" : "text-muted-foreground")}>
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
          <div className="mb-3 rounded-md border border-[#bbf7d0] bg-[#f0fdf4] px-3.5 py-2.5 text-[13px] text-[#15803d]">
            All of this participant&rsquo;s answers are graded.
          </div>
        )}
        {data.choices.length > 0 && (
          <div className="mb-3 overflow-hidden rounded-lg border">
            <div className="border-b px-4 py-2.5 text-[12px] font-semibold">
              Multiple choice <span className="font-normal text-muted-foreground">&middot; scored automatically</span>
            </div>
            {data.choices.map((c) => (
              <div
                key={c.item}
                className="grid grid-cols-[40px_1fr_80px] items-center border-b px-4 py-2 text-[13px] last:border-b-0"
              >
                <span className="font-semibold">Q{c.item.replace(/^q/, "")}</span>
                <span className={c.correct ? "text-[#15803d]" : "text-[#b91c1c]"}>
                  {c.choice ? `Picked ${c.choice} · ` : "No answer · "}
                  {c.correct ? "Correct" : `Answer is ${c.answer}`}
                </span>
                <span className="text-right text-muted-foreground">{tick(c.sure)}</span>
              </div>
            ))}
          </div>
        )}
        {data.sets.map((set) => (
          <SetCard key={set.item} set={set} />
        ))}
        {data.written.map((w) => (
          <WrittenCard
            key={key(w)}
            w={w}
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
  const postMax =
    data.sets.reduce((n, s) => n + s.points, 0) +
    data.choices.length +
    data.written.filter((w) => w.test === "post").reduce((n, w) => n + w.points, 0);
  const cells = [
    {
      label: "Pre-test",
      value: data.pretest_score === null ? null : `${data.pretest_score} / ${preMax ?? 3}`,
    },
    { label: "Post-test", value: data.posttest_total === null ? null : `${data.posttest_total} / ${postMax}` },
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
        <div key={c.label} className="rounded-lg border px-3.5 py-2.5">
          <div className="text-[12px] text-muted-foreground">{c.label}</div>
          <div className={cn("mt-0.5 text-[18px] font-semibold", c.value === null && "text-[#a1a1aa]")}>
            {c.value ?? "Not graded yet"}
          </div>
        </div>
      ))}
    </div>
  );
}

/** A true/false set: each statement, what they marked, and the key. Scored
 *  automatically, 1 point per statement marked right. */
function SetCard({ set }: { set: GradingSet }) {
  const mark = (v: boolean | null) => (v === null ? "Blank" : v ? "True" : "False");
  return (
    <div className="mb-3 overflow-hidden rounded-lg border">
      <div className="flex items-baseline gap-3 border-b px-4 py-2.5">
        <span className="flex-1 text-[13px]">
          <span className="text-[12px] font-semibold">Q{set.item.replace(/^q/, "")}</span>
          <span className="ml-1.5 text-muted-foreground">{set.question}</span>
        </span>
        <span className="whitespace-nowrap text-[12px] text-muted-foreground">
          {set.score} / {set.points} &middot; scored automatically
          {set.sure !== null && <> &middot; {tick(set.sure)}</>}
        </span>
      </div>
      {set.statements.map((st) => {
        const right = st.picked === st.answer;
        return (
          <div
            key={st.key}
            className="grid grid-cols-[1fr_auto] gap-3 border-b px-4 py-2 text-[13px] leading-[1.5] last:border-b-0"
          >
            <span className="text-[#3f3f46]">
              <span className="mr-1.5 font-medium text-muted-foreground">{st.key}.</span>
              {st.text}
            </span>
            <span className={cn("whitespace-nowrap", right ? "text-[#15803d]" : "text-[#b91c1c]")}>
              {mark(st.picked)} &middot; {right ? "Correct" : `Answer is ${mark(st.answer)}`}
            </span>
          </div>
        );
      })}
    </div>
  );
}

function WrittenCard({
  w,
  focused,
  onFocus,
  onScore,
}: {
  w: GradingWritten;
  focused: boolean;
  onFocus: () => void;
  onScore: (points: number) => void;
}) {
  const answered = w.parts ? w.parts.some((p) => !!p.text?.trim()) : !!w.text?.trim();
  return (
    <div
      onClick={onFocus}
      className={cn(
        "mb-3 cursor-pointer rounded-lg border",
        focused ? "border-primary shadow-[0_0_0_3px_#dcfce7]" : "border-border",
      )}
    >
      <div className="flex items-start gap-3 px-4 pt-3">
        <span className="flex-1">
          <span className="text-[12px] font-semibold">{label(w)}</span>
          <span className="ml-1.5 whitespace-pre-line text-[13px] text-muted-foreground">{w.question}</span>
        </span>
        <span className="whitespace-nowrap text-[12px] text-muted-foreground">{tick(w.sure)}</span>
      </div>
      {w.parts ? (
        // A question in steps: each part's prompt, then what they wrote.
        <div className="mx-4 mt-2 space-y-2.5">
          {w.parts.map((part) => (
            <div key={part.key}>
              <p className="text-[12.5px] leading-[1.5] text-muted-foreground">
                <span className="mr-1 font-semibold">({part.key})</span>
                {part.prompt}
              </p>
              <p
                className={cn(
                  "mt-1 whitespace-pre-wrap text-[14px] leading-[1.6]",
                  !part.text?.trim() && "text-[#a1a1aa]",
                )}
              >
                {part.text?.trim() ? part.text : "No answer"}
              </p>
            </div>
          ))}
        </div>
      ) : (
        <p
          className={cn(
            "mx-4 mt-2 whitespace-pre-wrap text-[14px] leading-[1.6]",
            !answered && "text-[#a1a1aa]",
          )}
        >
          {answered ? w.text : "No answer"}
        </p>
      )}
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
                ? "border-primary bg-[#f0fdf4] text-[#15803d]"
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
    <div className="sticky top-4 rounded-lg border px-5 py-4">
      <div className="text-[12px] font-medium uppercase tracking-[0.04em] text-muted-foreground">
        {w.test === "pre" ? "Pre-test" : `Question ${w.item.replace(/^q/, "")}`}
      </div>
      <div className="mt-3.5 text-[12px] font-medium uppercase tracking-[0.04em] text-muted-foreground">
        Reference answer
      </div>
      <p className="mt-2 text-[13px] leading-[1.6] text-[#3f3f46]">{w.reference}</p>
      <div className="mt-4 overflow-hidden rounded-md border">
        {w.criteria.map((c) => (
          <div key={c.points} className="grid grid-cols-[36px_1fr] border-b text-[12.5px] leading-[1.5] last:border-b-0">
            <span className="border-r bg-[#fafafa] py-2 text-center font-semibold">{c.points}</span>
            <span className="px-2.5 py-2 text-[#3f3f46]">{c.text}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function Muted({ children }: { children: React.ReactNode }) {
  return <p className="py-10 text-center text-[14px] text-muted-foreground">{children}</p>;
}
