"""Render a self-contained HTML report (inline CSS/JS, no external deps to view).

Color coding per example:
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
    --agree:#1a7f37; --agree-bg:#e6f4ea;
    --criteria:#9a6700; --criteria-bg:#fff8e1;
    --verdict:#cf222e; --verdict-bg:#ffebe9;
    --error:#57606a; --error-bg:#eaeef2;
    --line:#d0d7de; --ink:#1f2328; --muted:#57606a; --bg:#ffffff;
  }
  * { box-sizing:border-box; }
  body { font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;
         color:var(--ink); margin:0; padding:24px; background:#f6f8fa; }
  h1 { font-size:20px; margin:0 0 4px; }
  h2 { font-size:15px; margin:28px 0 10px; }
  .sub { color:var(--muted); font-size:13px; margin-bottom:16px; }
  .meta { font-size:12px; color:var(--muted); }
  .meta code { background:#eaeef2; padding:1px 5px; border-radius:4px; }
  .cards { display:flex; flex-wrap:wrap; gap:12px; margin:8px 0 4px; }
  .card { background:var(--bg); border:1px solid var(--line); border-radius:8px;
          padding:12px 16px; min-width:150px; }
  .card .big { font-size:24px; font-weight:600; }
  .card .lbl { font-size:12px; color:var(--muted); }
  table { width:100%; border-collapse:collapse; background:var(--bg);
          border:1px solid var(--line); border-radius:8px; overflow:hidden; font-size:13px; }
  th,td { text-align:left; padding:8px 10px; border-bottom:1px solid var(--line); vertical-align:top; }
  th { background:#f6f8fa; font-weight:600; position:sticky; top:0; }
  tr:last-child td { border-bottom:none; }
  .pill { display:inline-block; padding:1px 8px; border-radius:999px; font-size:11px;
          font-weight:600; white-space:nowrap; }
  .s-agree { background:var(--agree-bg); color:var(--agree); }
  .s-criteria_diff { background:var(--criteria-bg); color:var(--criteria); }
  .s-verdict_diff { background:var(--verdict-bg); color:var(--verdict); }
  .s-error { background:var(--error-bg); color:var(--error); }
  td.status-agree { border-left:4px solid var(--agree); }
  td.status-criteria_diff { border-left:4px solid var(--criteria); }
  td.status-verdict_diff { border-left:4px solid var(--verdict); }
  td.status-error { border-left:4px solid var(--error); }
  .crit { display:inline-block; padding:1px 7px; margin:1px 2px; border-radius:6px;
          font-size:11px; border:1px solid var(--line); }
  .c-match { background:var(--agree-bg); color:var(--agree); border-color:#acd9b8; }
  .c-miss  { background:var(--verdict-bg); color:var(--verdict); border-color:#f3b6ba; }
  .c-extra { background:var(--criteria-bg); color:var(--criteria); border-color:#ecd9a0; }
  .resp { max-width:420px; }
  .muted { color:var(--muted); }
  .bar { background:#eaeef2; border-radius:4px; height:8px; width:80px; display:inline-block; vertical-align:middle; overflow:hidden; }
  .bar > span { display:block; height:100%; background:var(--agree); }
  details { margin-top:6px; }
  summary { cursor:pointer; color:var(--muted); font-size:12px; }
  .warn { color:var(--criteria); font-size:11px; }
  .err { color:var(--verdict); font-size:12px; }
  .toolbar { margin:12px 0; font-size:13px; }
  .legend span { margin-right:14px; font-size:12px; }
  .key { font-family:ui-monospace,Consolas,monospace; font-size:12px; }
</style>
</head>
<body>
  <h1>SENSEEI — Student Assessment Agent</h1>
  <div class="sub">Evaluation report · {{ meta.timestamp }}</div>
  <div class="meta">
    Prompt: <code>{{ meta.prompt_version }}</code> (<code>{{ meta.prompt_hash }}</code>) ·
    Provider: <code>{{ meta.provider }}</code> · Model: <code>{{ meta.model }}</code>{% if meta.thinking_level %} · Thinking: <code>{{ meta.thinking_level }}</code>{% endif %} ·
    Examples: <code>{{ summary.total }}</code> · Source: <code>{{ meta.csv }}</code>
  </div>

  <div class="cards">
    <div class="card"><div class="big">{{ "%.1f"|format(summary.verdict_accuracy*100) }}%</div>
      <div class="lbl">Verdict accuracy ({{ summary.verdict_correct }}/{{ summary.total }})</div></div>
    <div class="card"><div class="big">{{ "%.1f"|format(summary.criteria_exact_rate*100) }}%</div>
      <div class="lbl">Criteria exact-match ({{ summary.criteria_exact }}/{{ summary.fail_n }} FAILs)</div></div>
    <div class="card"><div class="big" style="color:var(--agree)">{{ summary.status_counts.agree }}</div>
      <div class="lbl">Full agreement</div></div>
    <div class="card"><div class="big" style="color:var(--criteria)">{{ summary.status_counts.criteria_diff }}</div>
      <div class="lbl">Criteria differ</div></div>
    <div class="card"><div class="big" style="color:var(--verdict)">{{ summary.status_counts.verdict_diff }}</div>
      <div class="lbl">Verdict mismatch</div></div>
    {% if summary.status_counts.error %}
    <div class="card"><div class="big" style="color:var(--error)">{{ summary.status_counts.error }}</div>
      <div class="lbl">Errors</div></div>
    {% endif %}
    {% if meta.cost and meta.cost.est_cost_usd is not none %}
    <div class="card"><div class="big">${{ "%.4f"|format(meta.cost.est_cost_usd) }}</div>
      <div class="lbl">Est. cost (USD)</div></div>
    <div class="card"><div class="big" style="font-size:14px;line-height:1.5">
        {{ "{:,}".format(meta.cost.input_tokens) }} in<br>
        {{ "{:,}".format(meta.cost.thinking_tokens) }} thinking<br>
        {{ "{:,}".format(meta.cost.output_tokens) }} out</div>
      <div class="lbl">Tokens</div></div>
    {% endif %}
  </div>

  <h2>Accuracy by SEE-I step</h2>
  <table>
    <tr><th>Step</th><th>n</th><th>Verdict correct</th><th>Accuracy</th></tr>
    {% for s in summary.per_step %}
    <tr>
      <td>{{ s.step }}</td><td>{{ s.n }}</td><td>{{ s.correct }}/{{ s.n }}</td>
      <td><span class="bar"><span style="width:{{ (s.accuracy*100)|round(0,'floor') }}%"></span></span>
          {{ "%.1f"|format(s.accuracy*100) }}%</td>
    </tr>
    {% endfor %}
  </table>

  <h2>Per-criterion catch rate <span class="muted">(how often the agent flags a criterion that should fail)</span></h2>
  <table>
    <tr><th>Step</th><th>Criterion</th><th>Expected fails</th><th>Caught (recall)</th><th>False flags</th></tr>
    {% for c in summary.per_criterion %}
    <tr>
      <td>{{ c.step }}</td><td>{{ c.criterion }}</td>
      <td>{{ c.expected }}</td>
      <td>{% if c.recall is none %}<span class="muted">—</span>{% else %}{{ c.caught }}/{{ c.expected }}
          ({{ "%.0f"|format(c.recall*100) }}%){% endif %}</td>
      <td>{% if c.false_flag %}<span class="warn">{{ c.false_flag }}</span>{% else %}0{% endif %}</td>
    </tr>
    {% endfor %}
  </table>

  <h2>Per-example results</h2>
  <div class="toolbar">
    <label><input type="checkbox" id="mmOnly" onchange="toggleMM()"> Show mismatches only</label>
    <span class="legend" style="margin-left:18px;">
      <span class="pill s-agree">agree</span>
      <span class="pill s-criteria_diff">criteria differ</span>
      <span class="pill s-verdict_diff">verdict mismatch</span>
      <span class="pill s-error">error</span>
    </span>
  </div>
  <table id="results">
    <tr>
      <th>ID</th><th>Step</th><th>Response</th>
      <th>Expected</th><th>Agent</th><th>Criteria diff</th><th>Status</th>
    </tr>
    {% for r in records %}
    <tr data-status="{{ r.status }}">
      <td class="status-{{ r.status }} key">{{ r.id }}</td>
      <td>{{ r.step }}</td>
      <td class="resp">
        {{ r.user_response }}
        {% if r.criteria %}
        <details><summary>agent reasoning</summary>
          {% for name, j in r.criteria.items() %}
            <div><b>{{ name }}</b>: {{ "PASS" if j.passed else "FAIL" }} — <span class="muted">{{ j.reason }}</span></div>
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
        {% for c in r.matched %}<span class="crit c-match" title="matched">✓ {{ c }}</span>{% endfor %}
        {% for c in r.missed %}<span class="crit c-miss" title="expected but not flagged">✗ {{ c }}</span>{% endfor %}
        {% for c in r.extra %}<span class="crit c-extra" title="flagged but not expected">+ {{ c }}</span>{% endfor %}
      </td>
      <td><span class="pill s-{{ r.status }}">{{ r.status_label }}</span></td>
    </tr>
    {% endfor %}
  </table>

  <script>
    function toggleMM() {
      var only = document.getElementById('mmOnly').checked;
      document.querySelectorAll('#results tr[data-status]').forEach(function(tr){
        tr.style.display = (only && tr.getAttribute('data-status') === 'agree') ? 'none' : '';
      });
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
