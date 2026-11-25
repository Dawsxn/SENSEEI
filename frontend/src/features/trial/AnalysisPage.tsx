/** The trial's descriptive figures, for the research team (docs/context/trial.md).
 *
 * Everything comes from the server, computed from the same tables as the export,
 * so a figure here is one a reader of the zip can reproduce. A Batch menu shows
 * one sitting at a time, kept in the URL. Unticking an ID in Participants leaves
 * it out of every figure; nothing is saved or deleted, and a reload puts
 * everyone back.
 *
 * The figures name each ID's group, so this page is never shown to the grader. */

import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { ArrowDown, ArrowUp } from "lucide-react";
import { Fragment, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { AppTopBar } from "../../components/AppTopBar";
import { Badge } from "../../components/ui/badge";
import { Checkbox } from "../../components/ui/checkbox";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../../components/ui/table";
import { Tabs, TabsList, TabsTrigger } from "../../components/ui/tabs";
import { getAnalysis } from "../../lib/api";
import { DistributionChart } from "./DistributionChart";
import { cn } from "../../lib/utils";
import type {
  Analysis,
  AnalysisColumn,
  AnalysisFormat,
  AnalysisParticipant,
  AnalysisRow,
} from "./types";

const TABS = [
  { key: "comparison", label: "Group comparison" },
  { key: "seei", label: "SEE-I sessions" },
  { key: "behaviour", label: "Behaviour" },
  { key: "participants", label: "Participants" },
] as const;
type Tab = (typeof TABS)[number]["key"];

const GROUP: Record<string, string> = {
  seei: "SEE-I",
  chatbot: "Chatbot",
  reading_only: "Reading only",
};

/** The first of the SEE-I split columns. A hairline on its left separates the
 *  three groups from the SEE-I group's two parts. */
const SPLIT = "seei_completed";

/** How a SEE-I session ended. "Completed" rather than "Finished": Finished is the
 *  batch page's word for a participant whose post-test has ended. */
const STATUS: Record<string, string> = {
  complete: "Completed",
  timed_out: "Timed out",
  fallback: "Fallback",
  in_progress: "In progress",
};

export function AnalysisPage() {
  const [params, setParams] = useSearchParams();
  const batch = params.get("batch");
  const tab = (TABS.find((t) => t.key === params.get("tab"))?.key ?? "comparison") as Tab;
  const [exclude, setExclude] = useState<string[]>([]);

  const query = useQuery({
    queryKey: ["analysis", batch, [...exclude].sort()],
    queryFn: () => getAnalysis(batch, exclude),
    // Ticking an ID refetches; keep the last figures on screen meanwhile.
    placeholderData: keepPreviousData,
  });
  const data = query.data;

  const go = (next: { batch?: string | null; tab?: Tab }) => {
    const out = new URLSearchParams(params);
    if (next.batch !== undefined) {
      if (next.batch) out.set("batch", next.batch);
      else out.delete("batch");
    }
    if (next.tab) out.set("tab", next.tab);
    setParams(out);
  };
  const toggle = (code: string) =>
    setExclude((now) => (now.includes(code) ? now.filter((c) => c !== code) : [...now, code]));

  return (
    <div className="flex h-full flex-col">
      <AppTopBar />
      <main className="min-h-0 flex-1 overflow-y-auto">
        <div className="mx-auto max-w-[1280px] px-4 py-6 sm:px-6 sm:py-8">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <h1 className="text-[24px] font-semibold tracking-[-0.02em]">Analysis</h1>
            <div className="flex flex-wrap items-center gap-3">
              {data && (
                <span className="text-[13px] text-muted-foreground">
                  {data.included} of {data.finished} finished participants included
                  {exclude.length > 0 && (
                    <>
                      {" "}
                      &middot;{" "}
                      <button onClick={() => setExclude([])} className="underline underline-offset-2 hover:text-foreground">
                        Include everyone
                      </button>
                    </>
                  )}
                </span>
              )}
              {data && data.batches.length > 0 && (
                <label className="flex items-center gap-2 text-[13px] text-muted-foreground">
                  Batch
                  <select
                    value={batch ?? ""}
                    onChange={(e) => {
                      setExclude([]);
                      go({ batch: e.target.value || null });
                    }}
                    className="h-8 rounded-md border bg-background px-2 text-[13px] text-foreground"
                  >
                    <option value="">All batches</option>
                    {data.batches.map((b) => (
                      <option key={b.id} value={b.id}>
                        {b.name}
                      </option>
                    ))}
                  </select>
                </label>
              )}
            </div>
          </div>

          {query.isLoading && <Muted>Loading&hellip;</Muted>}
          {query.isError && <Muted>Couldn&rsquo;t load the figures.</Muted>}
          {data && data.used === 0 && (
            <Muted>
              {data.unused > 0
                ? "No one has signed in with these IDs yet."
                : "No participants yet. Make a batch of IDs on the Participants tab."}
            </Muted>
          )}

          {data && data.used > 0 && (
            <>
              <p className="mb-4 text-[13px] leading-[1.6] text-muted-foreground">
                Only participants marked Finished on the batch page are counted
                {(() => {
                  const out = [
                    data.used > data.finished && `${data.used - data.finished} signed in but didn't finish`,
                    data.unused > 0 && `${data.unused} IDs were never used`,
                  ].filter(Boolean);
                  return out.length ? ` (not counted: ${out.join(", ")})` : "";
                })()}
                . The groups are small, so one person can change an average a lot.
              </p>
              <Tabs value={tab} onValueChange={(v) => go({ tab: v as Tab })}>
                <TabsList className="mb-5 h-auto max-w-full justify-start overflow-x-auto">
                  {TABS.map((t) => (
                    <TabsTrigger key={t.key} value={t.key} className="text-[14px]">
                      {t.label}
                    </TabsTrigger>
                  ))}
                </TabsList>
              </Tabs>
              <div className={cn(query.isFetching && "opacity-60 transition-opacity")}>
                {tab === "comparison" && <Comparison data={data} />}
                {tab === "seei" && <Seei data={data} />}
                {tab === "behaviour" && <Behaviour data={data} />}
                {tab === "participants" && <Participants data={data} onToggle={toggle} />}
              </div>
            </>
          )}
        </div>
      </main>
    </div>
  );
}

// --------------------------------------------------------------------------- //
// formatting

function fmt(value: number | [number, number] | null | undefined, format: AnalysisFormat): string {
  if (value === null || value === undefined) return "—";
  // Quartiles and range: each end in the measure's own format.
  if (Array.isArray(value)) return `${fmt(value[0], format)}–${fmt(value[1], format)}`;
  switch (format) {
    case "share":
      return `${Math.round(value * 100)}%`;
    case "minutes":
      return `${value.toFixed(1)} min`;
    case "seconds":
      return `${Math.round(value)} s`;
    case "people":
    case "count":
      return String(Math.round(value));
    default:
      return trim(value);
  }
}

/** In the figures: Finished on the batch page, and not unticked. */
function counted(p: AnalysisParticipant): boolean {
  return p.finished && !p.excluded;
}

/** 16, 16.2, 1.67: at most two decimals, and none that say nothing. */
function trim(value: number): string {
  return String(Math.round(value * 100) / 100);
}

// --------------------------------------------------------------------------- //
// the best group

/** The three groups compared for "best". The SEE-I split columns are parts of
 *  the SEE-I group, not rivals to it, so they are never in the running. */
const COMPARED = ["chatbot", "reading_only", "seei"];

/** Measures where a lower value is the better one: fewer sure-but-wrong
 *  answers. Everywhere else higher is better. */
const LOWER_IS_BETTER = ["sure_but_wrong"];

/** Measures with no better direction: time. Less time is not better (finishing
 *  too fast is an exclusion rule), and more is not either, so none is marked. */
const NO_BEST = ["pretest_minutes", "posttest_minutes", "total_minutes"];

const isMeasure = (r: AnalysisRow, keys: string[]) => keys.some((k) => r.key.startsWith(`${k}_`));

function lowerIsBetter(r: AnalysisRow): boolean {
  return isMeasure(r, LOWER_IS_BETTER);
}

/** Rows where a best group means something: a mean, a median, or a
 *  dimension's share, on a measure that has a better direction. Never n, SD,
 *  quartiles or range, and never a time. */
function comparable(r: AnalysisRow): boolean {
  if (isMeasure(r, NO_BEST)) return false;
  return r.section === "dimensions" || (r.section === "scores" && (r.label === "Mean" || r.label === "Median"));
}

/** The group(s) with the best value of the three, ties included: the highest,
 *  or the lowest where lower is better. None when fewer than two groups have a
 *  value, or all of them are equal. */
function best(r: AnalysisRow): string[] {
  const got = COMPARED.flatMap((k) => {
    const v = r.values[k];
    return typeof v === "number" ? [[k, v] as const] : [];
  });
  if (got.length < 2) return [];
  const pick = lowerIsBetter(r) ? Math.min : Math.max;
  const top = pick(...got.map(([, v]) => v));
  if (got.every(([, v]) => v === top)) return [];
  return got.filter(([, v]) => v === top).map(([k]) => k);
}

/** The best value, marked in the success treatment: green here means "best",
 *  as it means a pass everywhere else in the app. */
function Best({ children }: { children: React.ReactNode }) {
  return (
    <span className="inline-flex rounded-md border border-[#bbf7d0] bg-[#f0fdf4] px-2 py-0.5 font-semibold text-[#15803d]">
      {children}
    </span>
  );
}

// --------------------------------------------------------------------------- //
// the tabs

function Comparison({ data }: { data: Analysis }) {
  const { columns, rows, distributions } = data.comparison;
  const scores = rows.filter((r) => r.section === "scores");
  const dims = rows.filter((r) => r.section === "dimensions");
  const [measure, setMeasure] = useState("posttest_total");
  const dist = distributions.find((d) => d.key === measure) ?? distributions[0];
  return (
    <>
      {dist && (
        <Card
          title="Distributions"
          note="Each dot under the axis is one participant. The curves are drawn from each group's mean and SD."
        >
          <Tabs value={dist.key} onValueChange={setMeasure}>
            <TabsList className="mb-4 h-auto max-w-full flex-wrap justify-start">
              {distributions.map((d) => (
                <TabsTrigger key={d.key} value={d.key} className="text-[13px]">
                  {d.label}
                </TabsTrigger>
              ))}
            </TabsList>
          </Tabs>
          <div className="pb-4">
            <DistributionChart dist={dist} />
          </div>
        </Card>
      )}
      <Card
        title="Descriptive statistics"
        note={`Calibration is how often a participant's "sure" or "not sure" matched whether they got full marks. Green shows the best of Chatbot, Reading only and SEE-I all. For sure but wrong, lower is better.`}
      >
        <FigureTable columns={columns} rows={scores} />
      </Card>
      {dims.length > 0 && (
        <Card
          title="Post-test by dimension"
          note="The share of available points each group scored. Green shows the highest of Chatbot, Reading only and SEE-I all."
        >
          <FigureTable columns={columns} rows={dims} />
        </Card>
      )}
    </>
  );
}

function Behaviour({ data }: { data: Analysis }) {
  const rows = data.comparison.rows.filter((r) => r.section === "behaviour");
  const flagged = data.participants.filter((p) => p.flags.length > 0);
  const chat = data.participants.filter((p) => p.group === "chatbot" && counted(p));
  const reading = data.participants.filter((p) => p.group === "reading_only" && counted(p));
  return (
    <>
      <Card title="By group" note="Only the length of a paste is recorded, not the text. Thinking time is how long someone waited after a reply before they started typing.">
        <FigureTable columns={data.comparison.columns} rows={rows} />
      </Card>
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
        <Card title="Chatbot use" note="Use this to check the exclusion rule on session length and words typed.">
          <SimpleTable
            head={["ID", "Questions", "Words typed", "Session"]}
            rows={chat.map((p) => [
              <Code key="c">{p.code}</Code>,
              p.chat_questions ?? 0,
              p.chat_words ?? 0,
              fmt(p.total_minutes, "minutes"),
            ])}
            empty="No chatbot participants included."
          />
        </Card>
        <Card title="Reading only" note="Use this to check the exclusion rule on time before pressing Done.">
          <SimpleTable
            head={["ID", "Time to Done", "Pre-test", "Post-test"]}
            rows={reading.map((p) => [
              <Code key="c">{p.code}</Code>,
              p.minutes_to_done === null ? "Never pressed" : fmt(p.minutes_to_done, "minutes"),
              fmt(p.pretest_score, "number"),
              fmt(p.posttest_total, "number"),
            ])}
            empty="No reading-only participants included."
          />
        </Card>
      </div>
      <Card title="Worth a second look" note="These are only flags. Decide on exclusions using the cut-offs from the dry run.">
        <SimpleTable
          head={["ID", "Group", "Flags", "Test pastes", "Test tab leaves"]}
          rows={flagged.map((p) => [
            <Code key="c" muted={!counted(p)}>{p.code}</Code>,
            GROUP[p.group] ?? p.group,
            <Flags key="f" flags={p.flags} />,
            p.test_pastes,
            p.test_tab_left,
          ])}
          empty="Nothing flagged."
        />
      </Card>
    </>
  );
}

function Seei({ data }: { data: Analysis }) {
  const { sessions, steps, criteria, fixes, fixed_overall } = data.seei;
  if (sessions.length === 0) return <Muted>No SEE-I sessions among the included participants.</Muted>;
  const finished = sessions.filter((s) => s.completed).length;
  return (
    <>
      <div className="mb-5 grid grid-cols-1 gap-2.5 sm:grid-cols-3">
        <Stat label="Sessions" value={String(sessions.length)} />
        <Stat label="Completed all four steps" value={`${finished} of ${sessions.length}`} />
        <Stat label="Feedback fixed a failed criterion" value={fmt(fixed_overall.rate, "share")} sub={`${fixed_overall.fixed} of ${fixed_overall.failed} on the next attempt`} />
      </div>
      <Card title="Sessions">
        <SimpleTable
          head={["ID", "Ended", "Last step", "Reading", "Tutoring", "Turns", "Pre-test", "Post-test"]}
          rows={sessions.map((s) => [
            <Code key="c">{s.code}</Code>,
            <StatusBadge key="s" status={s.status} />,
            s.last_step ?? "—",
            fmt(s.reading_minutes, "minutes"),
            fmt(s.session_minutes, "minutes"),
            s.turns ?? 0,
            fmt(s.pretest_score, "number"),
            fmt(s.posttest_total, "number"),
          ])}
        />
      </Card>
      <Card title="Steps" note="Attempts to pass is the average attempt on which participants passed the step. It only counts those who passed.">
        <SimpleTable
          head={["Step", "Reached", "Passed", "Attempts", "Pass rate", "Attempts to pass", "Most attempts"]}
          rows={steps.map((s) => [
            s.step,
            s.reached,
            s.passed,
            s.attempts,
            fmt(s.pass_rate, "share"),
            fmt(s.attempts_to_pass, "number"),
            s.most_attempts ?? "—",
          ])}
        />
      </Card>
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
        <Card title="Criteria, most failed first">
          <SimpleTable
            head={["Step", "Criterion", "Judged", "Failed", "Fail rate"]}
            rows={criteria.map((c) => [c.step, c.criterion, c.judged, c.failed, fmt(c.fail_rate, "share")])}
          />
        </Card>
        <Card title="Fixed on the next attempt" note="How often a failed criterion was passed on the next attempt. A fail on someone's last attempt isn't counted.">
          <SimpleTable
            head={["Criterion", "Failed", "Fixed", "Rate"]}
            rows={fixes.map((f) => [f.criterion, f.failed, f.fixed, fmt(f.rate, "share")])}
            empty="No failed criterion had a next attempt."
          />
        </Card>
      </div>
    </>
  );
}

type SortKey = "code" | "group" | "pretest_score" | "posttest_total" | "calibration" | "sure_but_wrong" | "total_minutes" | "pastes" | "flags";

function Participants({ data, onToggle }: { data: Analysis; onToggle: (code: string) => void }) {
  const [sort, setSort] = useState<{ key: SortKey; down: boolean }>({ key: "group", down: false });
  const people = useMemo(() => {
    const value = (p: AnalysisParticipant): string | number | null =>
      sort.key === "flags" ? p.flags.length : sort.key === "group" ? `${p.group} ${p.code}` : p[sort.key];
    return [...data.participants].sort((a, b) => {
      const x = value(a);
      const y = value(b);
      if (x === y) return 0;
      if (x === null) return 1; // blanks last, either way
      if (y === null) return -1;
      return (x < y ? -1 : 1) * (sort.down ? -1 : 1);
    });
  }, [data.participants, sort]);

  const head = (key: SortKey, label: string, right = false) => (
    <TableHead className={cn("px-3", right && "text-right")}>
      <button
        onClick={() => setSort((s) => ({ key, down: s.key === key ? !s.down : key !== "code" && key !== "group" }))}
        className="inline-flex items-center gap-1 hover:text-foreground"
      >
        {label}
        {sort.key === key &&
          (sort.down ? <ArrowDown className="h-3.5 w-3.5" /> : <ArrowUp className="h-3.5 w-3.5" />)}
      </button>
    </TableHead>
  );

  return (
    <Card title="Every participant" note="Untick an ID to leave it out of the figures. This isn't saved, so reloading or changing batch brings everyone back.">
      <div className="-mx-5">
        <Table className="min-w-[960px] whitespace-nowrap text-[13px]">
          <TableHeader className="text-[12px]">
            <TableRow className="hover:bg-transparent">
              <TableHead className="w-10 pl-5">In</TableHead>
              {head("code", "ID")}
              {head("group", "Group")}
              <TableHead className="px-3">SEE-I</TableHead>
              {head("pretest_score", "Pre", true)}
              {head("posttest_total", "Post", true)}
              {head("calibration", "Calibration", true)}
              {head("sure_but_wrong", "Sure but wrong", true)}
              {head("total_minutes", "Time", true)}
              <TableHead className="px-3 text-right">Turns / questions</TableHead>
              {head("pastes", "Pastes", true)}
              {head("flags", "Flags")}
            </TableRow>
          </TableHeader>
          <TableBody>
            {people.map((p) => (
              <TableRow key={p.code} className={cn(!counted(p) && "bg-muted/50 text-muted-foreground")}>
                <TableCell className="py-2 pl-5">
                  {/* Not finished: never counted, so there is nothing to tick. */}
                  <Checkbox
                    checked={counted(p)}
                    disabled={!p.finished}
                    onCheckedChange={() => onToggle(p.code)}
                    aria-label={`Include ${p.code}`}
                  />
                </TableCell>
                <TableCell className="px-3">
                  <Code muted={!counted(p)}>{p.code}</Code>
                  {data.batch_id === null && data.batches.length > 1 && (
                    <div className="text-[12px] text-muted-foreground">{p.batch}</div>
                  )}
                </TableCell>
                <TableCell className="px-3">{GROUP[p.group] ?? p.group}</TableCell>
                <TableCell className="px-3">{p.group === "seei" ? <StatusBadge status={p.status} /> : ""}</TableCell>
                <TableCell className="px-3 text-right tabular-nums">{fmt(p.pretest_score, "number")}</TableCell>
                <TableCell className="px-3 text-right tabular-nums">{fmt(p.posttest_total, "number")}</TableCell>
                <TableCell className="px-3 text-right tabular-nums">{fmt(p.calibration, "share")}</TableCell>
                <TableCell className="px-3 text-right tabular-nums">{fmt(p.sure_but_wrong, "count")}</TableCell>
                <TableCell className="px-3 text-right tabular-nums">{fmt(p.total_minutes, "minutes")}</TableCell>
                <TableCell className="px-3 text-right tabular-nums">
                  {p.group === "seei" ? p.turns ?? 0 : p.group === "chatbot" ? p.chat_questions ?? 0 : ""}
                </TableCell>
                <TableCell className="px-3 text-right tabular-nums">
                  {p.pastes + p.test_pastes}
                  {p.test_pastes > 0 && <span className="text-[#b91c1c]"> ({p.test_pastes} in test)</span>}
                </TableCell>
                <TableCell className="px-3">
                  <Flags flags={p.flags} />
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </Card>
  );
}

// --------------------------------------------------------------------------- //
// pieces

function FigureTable({ columns, rows }: { columns: AnalysisColumn[]; rows: AnalysisRow[] }) {
  return (
    <div className="-mx-5">
      <Table className="min-w-[720px] text-[13px]">
        <TableHeader className="text-[12px]">
          <TableRow className="hover:bg-transparent">
            <TableHead className="pl-5" />
            {columns.map((c) => (
              <TableHead
                key={c.key}
                className={cn("h-auto px-3 py-2.5 text-right last:pr-5", c.key === SPLIT && "border-l")}
              >
                <div className="text-foreground">{c.label}</div>
                <div className="font-normal">n = {c.n}</div>
              </TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.map((r, i) => (
            <Fragment key={r.key}>
              {r.measure && r.measure !== rows[i - 1]?.measure && (
                <TableRow className="bg-muted/50 hover:bg-muted/50">
                  <TableCell colSpan={columns.length + 1} className="py-2 pl-5 pr-5 text-[13px] font-medium">
                    {r.measure}
                    {lowerIsBetter(r) && (
                      <span className="ml-2 font-normal text-muted-foreground">· lower is better</span>
                    )}
                  </TableCell>
                </TableRow>
              )}
              <TableRow>
                <TableCell className={cn("py-2.5 pr-3 text-[#3f3f46]", r.measure ? "pl-8" : "pl-5")}>
                  {r.label}
                </TableCell>
                {columns.map((c) => {
                  const top = comparable(r) && best(r).includes(c.key);
                  return (
                    <TableCell
                      key={c.key}
                      title={
                        top
                          ? `Best of Chatbot, Reading only and SEE-I all (${lowerIsBetter(r) ? "lowest" : "highest"})`
                          : undefined
                      }
                      className={cn(
                        "px-3 py-2.5 text-right tabular-nums last:pr-5",
                        c.key === SPLIT && "border-l",
                        c.n === 0 && "text-[#a1a1aa]",
                      )}
                    >
                      {top ? <Best>{fmt(r.values[c.key], r.format)}</Best> : fmt(r.values[c.key], r.format)}
                    </TableCell>
                  );
                })}
              </TableRow>
            </Fragment>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

function SimpleTable({
  head,
  rows,
  empty,
}: {
  head: string[];
  rows: React.ReactNode[][];
  empty?: string;
}) {
  if (rows.length === 0) return <p className="py-3 text-[13px] text-muted-foreground">{empty ?? "Nothing yet."}</p>;
  return (
    <div className="-mx-5">
      <Table className="text-[13px]">
        <TableHeader className="text-[12px]">
          <TableRow className="hover:bg-transparent">
            {head.map((h) => (
              <TableHead key={h} className="whitespace-nowrap px-3 first:pl-5 last:pr-5">
                {h}
              </TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.map((cells, i) => (
            <TableRow key={i}>
              {cells.map((cell, j) => (
                <TableCell key={j} className="whitespace-nowrap px-3 tabular-nums first:pl-5 last:pr-5">
                  {cell}
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

function Card({ title, note, children }: { title: string; note?: string; children: React.ReactNode }) {
  return (
    <section className="mb-5 rounded-lg border px-5 pb-1 pt-4">
      <h2 className="text-[14px] font-medium">{title}</h2>
      {note && <p className="mt-1 text-[13px] leading-[1.5] text-muted-foreground">{note}</p>}
      <div className="mt-3">{children}</div>
    </section>
  );
}

function Stat({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="rounded-lg border px-3.5 py-2.5">
      <div className="text-[12px] text-muted-foreground">{label}</div>
      <div className="mt-0.5 text-[18px] font-semibold">{value}</div>
      {sub && <div className="text-[12px] text-muted-foreground">{sub}</div>}
    </div>
  );
}

function StatusBadge({ status }: { status: string | null }) {
  if (!status) return <span className="text-muted-foreground">No session</span>;
  return (
    <Badge variant={status === "complete" ? "success" : "neutral"} className="px-2 text-[12px]">
      {STATUS[status] ?? status}
    </Badge>
  );
}

function Flags({ flags }: { flags: string[] }) {
  if (flags.length === 0) return <span className="text-[#a1a1aa]">—</span>;
  return (
    <div className="flex flex-wrap gap-1">
      {flags.map((f) => (
        <Badge key={f} variant="failure" className="whitespace-nowrap px-2 text-[12px]">
          {f}
        </Badge>
      ))}
    </div>
  );
}

function Code({ children, muted }: { children: React.ReactNode; muted?: boolean }) {
  return <span className={cn("font-mono tracking-[0.05em]", muted && "line-through")}>{children}</span>;
}

function Muted({ children }: { children: React.ReactNode }) {
  return <p className="py-10 text-center text-[14px] text-muted-foreground">{children}</p>;
}
