/** Overlapping bell curves, one per group, for one measure of the trial.
 *
 * Each curve is the normal distribution with the group's mean and SD, drawn
 * from the figures the server sends. With a handful of people per group the
 * curve is a summary, not the data, so the actual values sit under it as dots:
 * read the dots first. A group with fewer than two values, or no spread, has no
 * curve, only its dots.
 *
 * Three groups at most: the three colours are a validated set that stays
 * distinguishable for colour-blind readers wherever the curves overlap (the
 * dataviz palette's first three slots). The aqua sits below 3:1 against white,
 * so every curve is also labelled by name, and the table below holds every
 * figure the chart shows. */

import { useMemo, useState } from "react";

import type { AnalysisDistribution, AnalysisFormat } from "./types";

export const SERIES: { key: string; label: string; color: string }[] = [
  { key: "chatbot", label: "Chatbot", color: "#2a78d6" },
  { key: "reading_only", label: "Reading only", color: "#eb6834" },
  { key: "seei", label: "SEE-I", color: "#1baf7a" },
];

// Drawn at about the width the card gives it on a desktop, so the text inside
// the SVG stays near its stated size instead of scaling up with the chart.
const W = 1180;
const H = 300;
// The right gutter holds the dot rows' names, clear of any dot.
const PAD = { left: 16, right: 104, top: 28, bottom: 74 };
const PLOT_H = H - PAD.top - PAD.bottom;
const RUG_Y = H - PAD.bottom + 24; // the first row of dots, under the axis line
const RUG_GAP = 14;

function pdf(x: number, mean: number, sd: number): number {
  const z = (x - mean) / sd;
  return Math.exp(-0.5 * z * z) / (sd * Math.sqrt(2 * Math.PI));
}

/** The normal CDF, by the Abramowitz–Stegun approximation of erf (error < 1.5e-7). */
function cdf(x: number, mean: number, sd: number): number {
  const z = (x - mean) / (sd * Math.SQRT2);
  const t = 1 / (1 + 0.3275911 * Math.abs(z));
  const poly = t * (0.254829592 + t * (-0.284496736 + t * (1.421413741 + t * (-1.453152027 + t * 1.061405429))));
  const erf = 1 - poly * Math.exp(-z * z);
  return 0.5 * (1 + (z >= 0 ? erf : -erf));
}

/** About six round ticks across [lo, hi]. */
function ticks(lo: number, hi: number): number[] {
  const span = hi - lo || 1;
  const raw = span / 6;
  const mag = 10 ** Math.floor(Math.log10(raw));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => s >= raw) ?? raw;
  const out = [];
  for (let v = Math.ceil(lo / step) * step; v <= hi + 1e-9; v += step) out.push(Math.round(v * 1000) / 1000);
  return out;
}

export function formatValue(v: number, format: AnalysisFormat): string {
  if (format === "share") return `${Math.round(v * 100)}%`;
  if (format === "minutes") return `${v.toFixed(1)} min`;
  return String(Math.round(v * 100) / 100);
}

export function DistributionChart({ dist }: { dist: AnalysisDistribution }) {
  const [hoverX, setHoverX] = useState<number | null>(null);
  const [dot, setDot] = useState<{ x: number; y: number; text: string } | null>(null);

  const series = SERIES.map((s) => ({ ...s, ...dist.series[s.key] })).filter((s) => s.values);
  const fitted = series.filter((s) => s.mean !== null && s.sd !== null && s.sd > 0);

  const { lo, hi } = useMemo(() => {
    const all = series.flatMap((s) => s.values);
    const tails = fitted.flatMap((s) => [s.mean! - 3 * s.sd!, s.mean! + 3 * s.sd!]);
    let lo = dist.low ?? Math.min(...all, ...tails);
    let hi = dist.high ?? Math.max(...all, ...tails);
    if (!Number.isFinite(lo) || !Number.isFinite(hi)) [lo, hi] = [0, 1];
    if (hi === lo) hi = lo + 1;
    return { lo, hi };
  }, [dist, series, fitted]);

  const x = (v: number) => PAD.left + ((v - lo) / (hi - lo)) * (W - PAD.left - PAD.right);
  const fromX = (px: number) => lo + ((px - PAD.left) / (W - PAD.left - PAD.right)) * (hi - lo);

  const curves = useMemo(() => {
    const steps = 160;
    const pts = fitted.map((s) =>
      Array.from({ length: steps + 1 }, (_, i) => {
        const v = lo + ((hi - lo) * i) / steps;
        return [v, pdf(v, s.mean!, s.sd!)] as const;
      }),
    );
    const top = Math.max(...pts.flat().map(([, d]) => d), 1e-9);
    return fitted.map((s, i) => {
      const y = (d: number) => PAD.top + PLOT_H - (d / top) * PLOT_H;
      const line = pts[i].map(([v, d], j) => `${j ? "L" : "M"}${x(v).toFixed(1)},${y(d).toFixed(1)}`).join("");
      const base = PAD.top + PLOT_H;
      const area = `${line}L${x(hi).toFixed(1)},${base}L${x(lo).toFixed(1)},${base}Z`;
      const peak = { px: x(s.mean!), py: y(pdf(s.mean!, s.mean!, s.sd!)) };
      return { ...s, line, area, peak };
    });
    // x depends on lo and hi, which are already in the list
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fitted, lo, hi]);

  // Direct labels at each peak, nudged up when two would collide.
  const labels = useMemo(() => {
    const placed: { key: string; label: string; color: string; lx: number; ly: number }[] = [];
    for (const c of [...curves].sort((a, b) => a.peak.py - b.peak.py)) {
      let ly = c.peak.py - 8;
      while (placed.some((p) => Math.abs(p.lx - c.peak.px) < 90 && Math.abs(p.ly - ly) < 14)) ly -= 14;
      placed.push({ key: c.key, label: c.label, color: c.color, lx: c.peak.px, ly: Math.max(ly, 12) });
    }
    return placed;
  }, [curves]);

  const base = PAD.top + PLOT_H;
  const hoverValue = hoverX === null ? null : fromX(hoverX);

  return (
    <div className="relative">
      <ul className="mb-2 flex flex-wrap gap-x-5 gap-y-1 text-[12px] text-[#3f3f46]" aria-label="Legend">
        {series.map((s) => (
          <li key={s.key} className="flex items-center gap-1.5">
            <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ background: s.color }} />
            <span className="font-medium text-foreground">{s.label}</span>
            <span className="text-muted-foreground">
              n = {s.values.length}
              {s.mean !== null && <> · mean {formatValue(s.mean, dist.format)}</>}
              {s.sd !== null && s.sd > 0 ? <> · SD {formatValue(s.sd, dist.format)}</> : s.values.length > 0 && <> · too few to fit a curve</>}
            </span>
          </li>
        ))}
      </ul>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="h-auto w-full overflow-visible"
        role="img"
        aria-label={`${dist.label}: fitted normal curves by group, with each value as a dot`}
        onMouseMove={(e) => {
          const r = e.currentTarget.getBoundingClientRect();
          const px = ((e.clientX - r.left) / r.width) * W;
          setHoverX(px >= PAD.left && px <= W - PAD.right ? px : null);
        }}
        onMouseLeave={() => setHoverX(null)}
      >
        {/* baseline and ticks: recessive */}
        <line x1={PAD.left} x2={W - PAD.right} y1={base} y2={base} stroke="#e4e4e7" />
        {ticks(lo, hi).map((t) => (
          <g key={t}>
            <line x1={x(t)} x2={x(t)} y1={base} y2={base + 4} stroke="#d4d4d8" />
            <text x={x(t)} y={base + 16} textAnchor="middle" fontSize="11" fill="#71717a">
              {formatValue(t, dist.format)}
            </text>
          </g>
        ))}

        {curves.map((c) => (
          <path key={`${c.key}-area`} d={c.area} fill={c.color} fillOpacity={0.1} />
        ))}
        {curves.map((c) => (
          <g key={c.key}>
            <path d={c.line} fill="none" stroke={c.color} strokeWidth={2} strokeLinejoin="round" />
            <line x1={c.peak.px} x2={c.peak.px} y1={c.peak.py} y2={base} stroke={c.color} strokeWidth={1.5} strokeDasharray="3 3" />
          </g>
        ))}
        {labels.map((l) => (
          <text key={l.key} x={l.lx} y={l.ly} textAnchor="middle" fontSize="12" fontWeight={500} fill="#09090b">
            {l.label}
          </text>
        ))}

        {/* the actual values, one row of dots per group; repeats stack upward */}
        {series.map((s, row) => {
          const seen = new Map<number, number>();
          return s.values.map((v, i) => {
            const k = seen.get(v) ?? 0;
            seen.set(v, k + 1);
            const cx = x(v) + k * 5;
            const cy = RUG_Y + row * RUG_GAP;
            return (
              <circle
                key={`${s.key}-${i}`}
                cx={cx}
                cy={cy}
                r={4}
                fill={s.color}
                stroke="#ffffff"
                strokeWidth={2}
                onMouseEnter={() => setDot({ x: cx, y: cy, text: `${s.label}: ${formatValue(v, dist.format)}` })}
                onMouseLeave={() => setDot(null)}
              >
                <title>{`${s.label}: ${formatValue(v, dist.format)}`}</title>
              </circle>
            );
          });
        })}
        {series.map((s, row) => (
          <text key={`${s.key}-row`} x={W - 8} y={RUG_Y + row * RUG_GAP + 4} textAnchor="end" fontSize="11" fill="#71717a">
            {s.label}
          </text>
        ))}

        {hoverX !== null && !dot && (
          <line x1={hoverX} x2={hoverX} y1={PAD.top} y2={base} stroke="#a1a1aa" strokeDasharray="2 3" />
        )}
      </svg>

      {hoverValue !== null && !dot && fitted.length > 0 && (
        <div
          className="pointer-events-none absolute top-8 z-10 rounded-md border bg-background px-3 py-2 text-[12px] shadow-raised"
          style={{ left: `min(calc(${(hoverX! / W) * 100}% + 12px), calc(100% - 220px))` }}
        >
          <div className="mb-1 font-medium">{formatValue(hoverValue, dist.format)}</div>
          {fitted.map((s) => (
            <div key={s.key} className="flex items-center gap-1.5 text-[#3f3f46]">
              <span className="inline-block h-2 w-2 rounded-full" style={{ background: s.color }} />
              {s.label}: above {Math.round(cdf(hoverValue, s.mean!, s.sd!) * 100)}% of its curve
            </div>
          ))}
        </div>
      )}
      {dot && (
        <div
          className="pointer-events-none absolute z-10 rounded-md border bg-background px-2 py-1 text-[12px] shadow-raised"
          style={{ left: `calc(${(dot.x / W) * 100}% + 8px)`, top: `calc(${(dot.y / H) * 100}% - 32px)` }}
        >
          {dot.text}
        </div>
      )}
    </div>
  );
}
