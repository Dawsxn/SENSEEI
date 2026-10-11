/** The three statistics, over a class or over one reading in it.
 *
 * One component for both, because the two views must count the same things and
 * say so the same way. What changes is `scope`, the tooltip on the heading that
 * says which sessions these numbers cover.
 *
 * A step nobody has reached is missing from the data rather than zero, and is
 * left out here too: no data and a pass rate of zero are different, and only one
 * of them is bad news.
 */

import { InfoTip } from "../../components/ui/Tooltip";
import type { Statistics } from "./types";

/** What each number is counting, for anyone who has not read the rubric. */
const TIPS = {
  pass: "Share of attempts that passed each step.",
  criteria: "Criteria that failed most often.",
  attempts: "Tries needed to pass, counting only students who passed.",
};

interface StatisticsSectionProps {
  statistics: Statistics;
  /** Which sessions the numbers cover, as the heading's tooltip. */
  scope: string;
}

export function StatisticsSection({ statistics, scope }: StatisticsSectionProps) {
  const empty = statistics.session_count === 0;

  return (
    <section className="flex flex-col gap-2.5">
      <h2 className="flex items-center gap-1.5 text-[16px] font-semibold">
        Statistics
        <InfoTip text={scope} />
      </h2>

      {empty ? (
        <div className="flex flex-col items-center gap-1.5 rounded-lg border border-dashed px-6 py-10 text-center">
          <span className="text-[14px] font-semibold">No sessions yet</span>
          <span className="text-[13px] text-muted-foreground">
            Statistics appear once a student finishes a session.
          </span>
        </div>
      ) : (
        <div className="grid gap-4 lg:grid-cols-3">
          <Card title="Pass rate by step" tip={TIPS.pass}>
            {statistics.pass_rates.map((r) => (
              <Row key={r.step} label={r.step} value={`${r.percent}%`}>
                <span className="block h-1.5 overflow-hidden rounded-full bg-muted">
                  <span
                    className="block h-full rounded-full bg-primary"
                    style={{ width: `${r.percent}%` }}
                  />
                </span>
              </Row>
            ))}
          </Card>

          <Card title="Most-failed criteria" tip={TIPS.criteria}>
            {statistics.failed_criteria.map((c) => (
              <Row key={c.criterion} label={c.criterion} value={String(c.failures)} />
            ))}
          </Card>

          {/* Last in the row, so its bubble opens leftwards rather than off the page. */}
          <Card title="Average attempts to pass" tip={TIPS.attempts} tipAlign="left">
            {statistics.average_attempts.map((a) => (
              <Row key={a.step} label={a.step} value={a.average.toFixed(1)} />
            ))}
          </Card>
        </div>
      )}
    </section>
  );
}

function Card({
  title,
  tip,
  tipAlign = "right",
  children,
}: {
  title: string;
  tip: string;
  tipAlign?: "left" | "right";
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-lg border">
      <div className="flex items-center gap-1.5 border-b px-4 py-3.5 text-[14px] font-semibold">
        {title}
        <InfoTip text={tip} align={tipAlign} />
      </div>
      <div className="flex flex-col gap-2.5 px-4 py-3.5">{children}</div>
    </div>
  );
}

/** A label, an optional bar, and a number on the right. Without a bar the label
 *  takes that column too, since a criterion name needs the width. */
function Row({
  label,
  value,
  children,
}: {
  label: string;
  value: string;
  children?: React.ReactNode;
}) {
  return (
    <div className="grid grid-cols-[74px_1fr_44px] items-center gap-2.5 text-[13px]">
      <span className={`text-[#3f3f46] ${children ? "" : "col-span-2"}`}>{label}</span>
      {children}
      <span className="text-right text-muted-foreground">{value}</span>
    </div>
  );
}
