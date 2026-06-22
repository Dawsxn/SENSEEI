"""Render a self-contained HTML report (inline CSS/JS, no external deps to view).

Dark-themed, presentation-oriented. Every metric / legend / marker carries a
plain-language explanation shown on hover (the small ⓘ). Color coding per example:
  green  = verdict AND criteria set both agree
  amber  = verdict agrees but the criteria set differs
  red    = verdict mismatch
  gray   = parse / provider error (no usable verdict)
"""

from __future__ import annotations

from jinja2 import Template

_TEMPLATE = Template(
    r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SENSEEI Assessment Agent — {{ meta.prompt_version }} — {{ meta.timestamp }}</title>
<style>
  :root {
    --bg:#0d1117; --panel:#161b22; --panel2:#1c2128; --line:#30363d;
    --ink:#e6edf3; --muted:#8b949e; --accent:#58a6ff;
    --agree:#3fb950; --agree-bg:rgba(63,185,80,.15); --agree-bd:rgba(63,185,80,.4);
    --criteria:#d29922; --criteria-bg:rgba(210,153,34,.15); --criteria-bd:rgba(210,153,34,.4);
    --verdict:#f85149; --verdict-bg:rgba(248,81,73,.15); --verdict-bd:rgba(248,81,73,.4);
    --error:#8b949e; --error-bg:rgba(139,148,158,.15); --error-bd:rgba(139,148,158,.4);
  }
  * { box-sizing:border-box; }
  body { font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;
         color:var(--ink); margin:0; padding:24px; background:var(--bg); }
  h1 { font-size:20px; margin:0 0 4px; }
  h2 { font-size:15px; margin:30px 0 6px; font-weight:600; }
  a { color:var(--accent); }
  .sub { color:var(--muted); font-size:13px; margin-bottom:4px; }
  .hint { color:var(--muted); font-size:12px; margin:10px 0 0; font-style:italic; }
  .meta { font-size:12px; color:var(--muted); margin-top:10px; line-height:1.7; }
  .meta code { background:var(--panel2); padding:1px 6px; border-radius:5px; color:var(--ink); }
  .secdesc { color:var(--muted); font-size:12.5px; margin:0 0 10px; max-width:760px; }

  .cards { display:flex; flex-wrap:wrap; gap:12px; margin:14px 0 4px; }
  .card { background:var(--panel); border:1px solid var(--line); border-radius:10px;
          padding:14px 16px; min-width:160px; }
  .card .big { font-size:26px; font-weight:600; }
  .card .lbl { font-size:12px; color:var(--muted); margin-top:2px; }
  .card .sub2 { font-size:11px; color:var(--muted); margin-top:3px; }

  .chips { display:flex; flex-wrap:wrap; gap:10px; margin:6px 0 2px; }
  .chip { display:inline-flex; align-items:center; gap:8px; padding:8px 13px;
          border-radius:999px; font-size:13px; font-weight:600; border:1px solid var(--line); }
  .chip .n { font-size:15px; }
  .c-agree { background:var(--agree-bg); color:var(--agree); border-color:var(--agree-bd); }
  .c-criteria_diff { background:var(--criteria-bg); color:var(--criteria); border-color:var(--criteria-bd); }
  .c-verdict_diff { background:var(--verdict-bg); color:var(--verdict); border-color:var(--verdict-bd); }
  .c-error { background:var(--error-bg); color:var(--error); border-color:var(--error-bd); }

  table { width:100%; border-collapse:collapse; background:var(--panel);
          border:1px solid var(--line); border-radius:10px; overflow:hidden; font-size:13px; }
  th,td { text-align:left; padding:9px 11px; border-bottom:1px solid var(--line); vertical-align:top; }
  th { background:var(--panel2); font-weight:600; color:var(--ink); }
  tbody tr:last-child td { border-bottom:none; }
  tbody tr:hover { background:var(--panel2); }

  .pill { display:inline-block; padding:2px 9px; border-radius:999px; font-size:11px;
          font-weight:600; white-space:nowrap; }
  .s-agree { background:var(--agree-bg); color:var(--agree); }
  .s-criteria_diff { background:var(--criteria-bg); color:var(--criteria); }
  .s-verdict_diff { background:var(--verdict-bg); color:var(--verdict); }
  .s-error { background:var(--error-bg); color:var(--error); }
  td.status-agree { border-left:3px solid var(--agree); }
  td.status-criteria_diff { border-left:3px solid var(--criteria); }
  td.status-verdict_diff { border-left:3px solid var(--verdict); }
  td.status-error { border-left:3px solid var(--error); }

  .crit { display:inline-block; padding:1px 7px; margin:1px 2px; border-radius:6px;
          font-size:11px; border:1px solid var(--line); color:var(--ink); }
  .c-match { background:var(--agree-bg); color:var(--agree); border-color:var(--agree-bd); }
  .c-miss  { background:var(--verdict-bg); color:var(--verdict); border-color:var(--verdict-bd); }
  .c-extra { background:var(--criteria-bg); color:var(--criteria); border-color:var(--criteria-bd); }
  .resp { max-width:430px; }
  .muted { color:var(--muted); }
  .bar { background:var(--panel2); border-radius:4px; height:8px; width:90px; display:inline-block;
         vertical-align:middle; overflow:hidden; border:1px solid var(--line); }
  .bar > span { display:block; height:100%; background:var(--agree); }
  details { margin-top:6px; }
  summary { cursor:pointer; color:var(--accent); font-size:12px; }
  details .reason { margin-top:4px; }
  .warn { color:var(--criteria); font-size:11px; }
  .err { color:var(--verdict); font-size:12px; }
  .key { font-family:ui-monospace,Consolas,monospace; font-size:12px; }

  /* filter bar */
  .toolbar { display:flex; flex-wrap:wrap; align-items:center; gap:16px; margin:10px 0; font-size:13px; }
  .toolbar label { color:var(--muted); display:inline-flex; align-items:center; gap:6px; }
  .toolbar select { background:var(--panel2); color:var(--ink); border:1px solid var(--line);
                    border-radius:6px; padding:5px 8px; font-size:13px; }
  #counter { margin-left:auto; }

  /* hover tooltip (the ⓘ) */
  .info { display:inline-block; width:14px; height:14px; line-height:13px; text-align:center;
          border:1px solid var(--line); border-radius:50%; font-size:9px; font-style:normal;
          color:var(--muted); background:var(--panel2); cursor:help; vertical-align:middle; }
  .tip { position:relative; }
  .tip:hover::after {
    content:attr(data-tip); position:absolute; left:0; top:140%; z-index:20;
    width:max-content; max-width:300px; white-space:normal;
    background:#000; color:#fff; border:1px solid var(--line); border-radius:8px;
    padding:8px 10px; font-size:12px; font-weight:400; line-height:1.45;
    box-shadow:0 6px 20px rgba(0,0,0,.5);
  }
  th.tip:hover::after { font-weight:400; }
</style>
</head>
<body>
  <h1>SENSEEI — Student Assessment Agent</h1>
  <div class="sub">Evaluation report · {{ meta.timestamp }}</div>
  <div class="meta">
    Prompt: <code>{{ meta.prompt_version }}</code> (<code>{{ meta.prompt_hash }}</code>){% if meta.rubric_version %} ·
    Rubric: <code>{{ meta.rubric_version }}</code>{% endif %}{% if meta.example_set_version %} ·
    Example set: <code>{{ meta.example_set_version }}</code>{% endif %} ·
    Provider: <code>{{ meta.provider }}</code> · Model: <code>{{ meta.model }}</code>{% if meta.thinking_level %} · Thinking: <code>{{ meta.thinking_level }}</code>{% endif %} ·
    Examples: <code>{{ summary.total }}</code> · Source: <code>{{ meta.csv }}</code>
  </div>
  <p class="hint">Hover any ⓘ for a plain-language explanation of the metric.</p>

  <div class="cards">
    <div class="card">
      <div class="big">{{ "%.1f"|format(summary.verdict_accuracy*100) }}%</div>
      <div class="lbl tip" data-tip="Share of responses where the agent's overall PASS/FAIL verdict matched the human label. This is the headline number.">Verdict accuracy <span class="info">i</span></div>
      <div class="sub2">{{ summary.verdict_correct }}/{{ summary.total }} responses correct</div>
    </div>
    {% if meta.cost and meta.cost.est_cost_usd is not none %}
    <div class="card">
      <div class="big">${{ "%.4f"|format(meta.cost.est_cost_usd) }}</div>
      <div class="lbl tip" data-tip="Estimated cost of this run in USD, from token usage at the configured prices (thinking + output are billed at the output rate).">Est. cost <span class="info">i</span></div>
      <div class="sub2">this run</div>
    </div>
    <div class="card">
      <div class="big" style="font-size:15px;line-height:1.6">
        {{ "{:,}".format(meta.cost.input_tokens) }} in<br>
        {{ "{:,}".format(meta.cost.thinking_tokens) }} thinking<br>
        {{ "{:,}".format(meta.cost.output_tokens) }} out</div>
      <div class="lbl tip" data-tip="Tokens consumed this run: prompt input sent to the model, the model's internal thinking, and its visible output.">Tokens <span class="info">i</span></div>
    </div>
    {% endif %}
  </div>

  <h2 class="tip" data-tip="Every response falls into exactly one of these outcomes. The colors match the left border of each row in the per-example table below.">Outcome breakdown <span class="info">i</span></h2>
  <div class="chips">
    <span class="chip c-agree tip" data-tip="Verdict AND the exact set of failing criteria both match the label. A full, clean agreement.">agree <span class="n">{{ summary.status_counts.agree }}</span></span>
    <span class="chip c-criteria_diff tip" data-tip="The PASS/FAIL verdict matches, but the agent flagged a different set of criteria than expected.">criteria differ <span class="n">{{ summary.status_counts.criteria_diff }}</span></span>
    <span class="chip c-verdict_diff tip" data-tip="The agent's PASS/FAIL disagrees with the label. This is the most serious kind of error.">verdict mismatch <span class="n">{{ summary.status_counts.verdict_diff }}</span></span>
    <span class="chip c-error tip" data-tip="No usable verdict was produced (a JSON-parse or provider error, e.g. a truncated response).">error <span class="n">{{ summary.status_counts.error }}</span></span>
  </div>

  <h2 class="tip" data-tip="Verdict accuracy split by SEE-I step, so you can see which step the agent judges best and worst.">Accuracy by SEE-I step <span class="info">i</span></h2>
  <table>
    <thead><tr><th>Step</th><th>Examples</th><th>Correct</th><th>Accuracy</th></tr></thead>
    <tbody>
    {% for s in summary.per_step %}
    <tr>
      <td>{{ s.step }}</td><td>{{ s.n }}</td><td>{{ s.correct }}/{{ s.n }}</td>
      <td><span class="bar"><span style="width:{{ (s.accuracy*100)|round(0,'floor') }}%"></span></span>
          {{ "%.1f"|format(s.accuracy*100) }}%</td>
    </tr>
    {% endfor %}
    </tbody>
  </table>

  <h2 class="tip" data-tip="Per rubric criterion: of the examples that SHOULD fail it, how many the agent caught — and how often it flagged the criterion when it shouldn't have. Your guide to which criterion to tune next.">Per-criterion catch rate <span class="info">i</span></h2>
  <table>
    <thead><tr>
      <th>Step</th><th>Criterion</th>
      <th class="tip" data-tip="Of the examples expected to fail this criterion, how many the agent flagged. (— means no example targets it.)">Caught <span class="info">i</span></th>
      <th class="tip" data-tip="Times the agent flagged this criterion on an example that was NOT expected to fail it (over-flagging).">False flags <span class="info">i</span></th>
    </tr></thead>
    <tbody>
    {% for c in summary.per_criterion %}
    <tr>
      <td>{{ c.step }}</td><td>{{ c.criterion }}</td>
      <td>{% if c.recall is none %}<span class="muted">—</span>{% else %}{{ c.caught }}/{{ c.expected }}
          <span class="muted">({{ "%.0f"|format(c.recall*100) }}%)</span>{% endif %}</td>
      <td>{% if c.false_flag %}<span class="warn">{{ c.false_flag }}</span>{% else %}<span class="muted">0</span>{% endif %}</td>
    </tr>
    {% endfor %}
    </tbody>
  </table>

  <h2>Per-example results</h2>
  <p class="secdesc">One row per labeled response. The colored left border and the Status pill show the
    outcome (see the breakdown above). Use the agent reasoning toggle to see why each criterion was judged.</p>
  <div class="toolbar">
    <label>Status
      <select id="f-status" onchange="applyFilters()">
        <option value="all">All</option>
        <option value="agree">Agree</option>
        <option value="criteria_diff">Criteria differ</option>
        <option value="verdict_diff">Verdict mismatch</option>
        <option value="error">Error</option>
      </select>
    </label>
    <label>SEE-I step
      <select id="f-step" onchange="applyFilters()">
        <option value="all">All</option>
        {% for s in summary.per_step %}<option value="{{ s.step }}">{{ s.step }}</option>{% endfor %}
      </select>
    </label>
    <span class="muted" id="counter">Showing {{ summary.total }} of {{ summary.total }}</span>
  </div>
  <table id="results">
    <thead><tr>
      <th>ID</th><th>Step</th><th>Response</th>
      <th>Expected</th><th>Agent</th>
      <th class="tip" data-tip="How the agent's failing criteria compare to the expected ones. ✓ matched = expected to fail and flagged; ✗ missed = expected to fail but not flagged; + extra = flagged but not expected.">Criteria diff <span class="info">i</span></th>
      <th>Status</th>
    </tr></thead>
    <tbody>
    {% for r in records %}
    <tr data-status="{{ r.status }}" data-step="{{ r.step }}">
      <td class="status-{{ r.status }} key">{{ r.id }}</td>
      <td>{{ r.step }}</td>
      <td class="resp">
        {{ r.user_response }}
        {% if r.criteria %}
        <details><summary>agent reasoning</summary>
          {% for name, j in r.criteria.items() %}
            <div class="reason"><b>{{ name }}</b>: {{ "PASS" if j.passed else "FAIL" }} — <span class="muted">{{ j.reason }}</span></div>
          {% endfor %}
        </details>
        {% endif %}
        {% if r.warnings %}<div class="warn">⚠ {{ r.warnings|join("; ") }}</div>{% endif %}
        {% if r.error %}<div class="err">⚠ {{ r.error }}</div>{% endif %}
        {% if r.finish_reason and r.finish_reason != "STOP" %}<div class="err">⚠ finish_reason: {{ r.finish_reason }}</div>{% endif %}
      </td>
      <td>
        <b>{{ r.expected_verdict }}</b>
        {% for c in r.expected_criteria %}<span class="crit">{{ c }}</span>{% endfor %}
      </td>
      <td>
        <b>{{ r.actual_verdict or "—" }}</b>
        {% for c in r.actual_criteria %}<span class="crit">{{ c }}</span>{% endfor %}
      </td>
      <td>
        {% for c in r.matched %}<span class="crit c-match" title="matched: expected to fail and flagged">✓ {{ c }}</span>{% endfor %}
        {% for c in r.missed %}<span class="crit c-miss" title="missed: expected to fail but not flagged">✗ {{ c }}</span>{% endfor %}
        {% for c in r.extra %}<span class="crit c-extra" title="extra: flagged but not expected">+ {{ c }}</span>{% endfor %}
      </td>
      <td><span class="pill s-{{ r.status }}">{{ r.status_label }}</span></td>
    </tr>
    {% endfor %}
    </tbody>
  </table>

  <script>
    function applyFilters() {
      var st = document.getElementById('f-status').value;
      var sp = document.getElementById('f-step').value;
      var rows = document.querySelectorAll('#results tbody tr');
      var shown = 0;
      rows.forEach(function(tr){
        var ok = (st === 'all' || tr.dataset.status === st) &&
                 (sp === 'all' || tr.dataset.step === sp);
        tr.style.display = ok ? '' : 'none';
        if (ok) shown++;
      });
      document.getElementById('counter').textContent = 'Showing ' + shown + ' of ' + rows.length;
    }
  </script>
</body>
</html>
"""
)

_STATUS_LABELS = {
    "agree": "✓ agree",
    "criteria_diff": "≈ criteria differ",
    "verdict_diff": "✗ verdict",
    "error": "⚠ error",
}


def render_report(meta: dict, summary: dict, records: list[dict]) -> str:
    for r in records:
        r.setdefault("status_label", _STATUS_LABELS.get(r["status"], r["status"]))
    return _TEMPLATE.render(meta=meta, summary=summary, records=records)
