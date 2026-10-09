"""The Modeling Rules page: the registry as one self-contained HTML page, for reading and review.

Grouped by stage, each rule shows its value and units, grade, jurisdiction, reasoning, sources
with links and quotes, status and ruling. A filter by grade and status makes placeholders and
judgment calls easy to find. The page is outside the identity check but deterministic: no
timestamps, rules in registry order.

Spec: Work Order 5, A4; decision 0009.
"""

import html
import json
from typing import Any

from swm.rules.registry import Registry, Rule, Source, Stage

STAGE_TITLES = {
    Stage.DEPENDENCIES: "Dependencies",
    Stage.REQUIREMENTS: "Requirements",
    Stage.RESERVES: "Reserves",
    Stage.STRENGTH: "Coupling strength",
    Stage.TOLERANCE: "Tolerance",
    Stage.FAILURE_MODES: "Failure modes",
    Stage.REPAIR: "Repair",
    Stage.CREWS: "Crews",
    Stage.STORM: "Storm",
    Stage.SIZING: "Sizing",
    Stage.LAYERS: "Layers",
    Stage.DRAWS: "Draws",
}
"""Stages in page order, with their headings."""

STYLE = """
:root { --ink:#1d2330; --muted:#5b6475; --line:#d9dde5; --card:#ffffff; --page:#f4f5f7;
  --accent:#2f5da8; --S:#1f7a4d; --L:#2f5da8; --J:#a15c00; --open:#b3261e; --placeholder:#8a6d00;
  --ruled:#1f7a4d; }
@media (prefers-color-scheme: dark) { :root { --ink:#e6e8ee; --muted:#a3aaba; --line:#353b47;
  --card:#1c2029; --page:#12151b; --accent:#8fb3ff; --S:#5cc98f; --L:#8fb3ff; --J:#f0b35a;
  --open:#ff8a80; --placeholder:#e6c95c; --ruled:#5cc98f; } }
* { box-sizing: border-box; }
body { margin:0; font:15px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif; color:var(--ink);
  background:var(--page); }
header { padding:20px 16px 12px; border-bottom:1px solid var(--line); background:var(--card); }
header h1 { margin:0 0 4px; font-size:22px; }
header p { margin:2px 0; color:var(--muted); font-size:13px; word-break:break-all; }
.filters { position:sticky; top:0; z-index:1; padding:10px 16px; background:var(--card);
  border-bottom:1px solid var(--line); display:flex; flex-wrap:wrap; gap:6px 18px; font-size:13px; }
.filters fieldset { border:0; margin:0; padding:0; display:flex; gap:10px; flex-wrap:wrap; }
.filters legend { float:left; margin-right:6px; font-weight:600; }
main { max-width:1100px; margin:0 auto; padding:8px 16px 40px; }
h2 { margin:28px 0 8px; font-size:18px; }
h2 small { color:var(--muted); font-weight:400; }
.rule { background:var(--card); border:1px solid var(--line); border-radius:8px; padding:12px 14px;
  margin:10px 0; }
.rule h3 { margin:0; font-size:15px; }
.id { font:12px ui-monospace, SFMono-Regular, Consolas, monospace; color:var(--muted);
  word-break:break-all; }
.badges { display:flex; flex-wrap:wrap; gap:6px; margin:6px 0; }
.badge { font-size:12px; border:1px solid currentColor; border-radius:10px; padding:0 8px; }
.grade-S { color:var(--S); } .grade-L { color:var(--L); } .grade-J { color:var(--J); }
.status-open { color:var(--open); } .status-placeholder { color:var(--placeholder); }
.status-ruled { color:var(--ruled); } .plain { color:var(--muted); }
.value { font:13px ui-monospace, SFMono-Regular, Consolas, monospace; background:var(--page);
  border-radius:6px; padding:6px 8px; overflow-x:auto; white-space:pre-wrap;
  word-break:break-word; }
.value strong { font-size:15px; }
details summary { cursor:pointer; color:var(--accent); font-size:13px; }
.sources { margin:6px 0 0; padding-left:18px; font-size:13px; }
.sources blockquote { margin:2px 0 4px; padding-left:8px; border-left:3px solid var(--line);
  color:var(--muted); }
.meta { font-size:13px; color:var(--muted); margin-top:4px; }
a { color:var(--accent); }
.hidden { display:none; }
"""

SCRIPT = """
const boxes = Array.from(document.querySelectorAll('.filters input'));
function apply() {
  const on = new Set(boxes.filter(b => b.checked).map(b => b.value));
  document.querySelectorAll('.rule').forEach(r => {
    const show = on.has('grade-' + r.dataset.grade) && on.has('status-' + r.dataset.status);
    r.classList.toggle('hidden', !show);
  });
  document.querySelectorAll('section').forEach(s => {
    const shown = s.querySelectorAll('.rule:not(.hidden)').length;
    s.classList.toggle('hidden', shown === 0);
    s.querySelector('.count').textContent = shown;
  });
}
boxes.forEach(b => b.addEventListener('change', apply));
apply();
"""


def rules_page_html(registry: Registry) -> bytes:
    """Render the registry as one self-contained HTML page.

    Parameters
    ----------
    registry : Registry
        The modeling rules to show.

    Returns
    -------
    bytes
        The page, UTF-8, with LF line endings.

    Spec: Work Order 5, A4.
    """
    sections = []
    for stage, title in STAGE_TITLES.items():
        rules = [rule for rule in registry.rules if rule.stage == stage]
        if not rules:
            continue
        cards = "\n".join(_card(rule) for rule in rules)
        sections.append(
            f'<section id="{stage.value}"><h2>{title} <small>(<span class="count">'
            f"{len(rules)}</span> rules)</small></h2>\n{cards}\n</section>"
        )
    grades = "".join(
        f'<label><input type="checkbox" value="grade-{g}" checked> {label}</label>'
        for g, label in (("S", "S standard"), ("L", "L literature"), ("J", "J judgment"),
                         ("none", "no grade"))
    )  # fmt: skip
    statuses = "".join(
        f'<label><input type="checkbox" value="status-{s}" checked> {s}</label>'
        for s in ("ruled", "calibrated", "placeholder", "open")
    )
    counts = {s: sum(1 for r in registry.rules if r.status.value == s) for s in
              ("ruled", "calibrated", "placeholder", "open")}  # fmt: skip
    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Modeling Rules</title>
<style>{STYLE}</style>
</head>
<body>
<header>
<h1>Modeling Rules</h1>
<p>Every rule and number that shapes a SyntheticWorldModel world, with its source and reasoning.
Rules change only by a reviewed edit to the registry; a recipe may override any rule
for a sensitivity run, and its overrides are stamped on the world.</p>
<p>Registry version {html.escape(registry.version)} · SHA-256 {registry.sha256} ·
{len(registry.rules)} rules: {counts["ruled"]} ruled, {counts["calibrated"]} calibrated,
{counts["placeholder"]} placeholder, {counts["open"]} open</p>
</header>
<div class="filters">
<fieldset><legend>Grade</legend>{grades}</fieldset>
<fieldset><legend>Status</legend>{statuses}</fieldset>
</div>
<main>
{chr(10).join(sections)}
</main>
<script>{SCRIPT}</script>
</body>
</html>
"""
    return page.encode("utf-8")


def _card(rule: Rule) -> str:
    grade = rule.grade.value if rule.grade else "none"
    badges = [
        f'<span class="badge grade-{grade}">grade {grade if rule.grade else "none"}</span>',
        f'<span class="badge status-{rule.status.value}">{rule.status.value}</span>',
    ]
    if rule.jurisdiction:
        badges.append(f'<span class="badge plain">{rule.jurisdiction.value}</span>')
    if rule.theta_role:
        badges.append(f'<span class="badge plain">θ*-{rule.theta_role.value}</span>')
    if rule.open_decision:
        badges.append(
            f'<span class="badge plain">open decision: {html.escape(rule.open_decision)}</span>'
        )
    applies = ", ".join(
        f"{name.replace('_', ' ')} {html.escape(value)}"
        for name, value in (
            ("layer", rule.applies_to.layer),
            ("class", rule.applies_to.node_class),
            ("where", rule.applies_to.condition),
        )
        if value
    )
    ruling = ""
    if rule.ruling:
        ruling = (
            f"Ruled by {html.escape(rule.ruling.by)}, {html.escape(rule.ruling.date)}, "
            f"decision {html.escape(rule.ruling.decision)}."
        )
    history = ""
    if rule.history:
        items = "".join(
            f"<li>{html.escape(_text(h.value))} {html.escape(h.units or '')} until "
            f"{html.escape(h.date)} (decision {html.escape(h.decision)})</li>"
            for h in rule.history
        )
        history = f"<div class='meta'>History:<ul>{items}</ul></div>"
    sources = "".join(_source(s) for s in rule.sources) or "<li>No source: see the reasoning.</li>"
    return f"""<article class="rule" data-grade="{grade}" data-status="{rule.status.value}">
<h3>{html.escape(rule.title)}</h3>
<div class="id">{rule.id}</div>
<div class="badges">{"".join(badges)}</div>
{_value(rule)}
<p>{html.escape(rule.reasoning)}</p>
<div class="meta">{"Applies to " + applies + ". " if applies else ""}{ruling}</div>
<ul class="sources">{sources}</ul>
{history}
</article>"""


def _value(rule: Rule) -> str:
    units = f" {html.escape(rule.units)}" if rule.units else ""
    if rule.value is None:
        return '<div class="value">no value yet</div>'
    if isinstance(rule.value, dict | list):
        text = html.escape(_text(rule.value))
        if len(text) > 600:
            return (
                f"<details><summary>Value ({len(text)} characters){units}</summary>"
                f'<div class="value">{text}</div></details>'
            )
        return f'<div class="value">{text}{units}</div>'
    return f'<div class="value"><strong>{html.escape(_text(rule.value))}</strong>{units}</div>'


def _source(source: Source) -> str:
    citation = html.escape(source.citation)
    if source.url and source.url.startswith("http"):
        citation = f'<a href="{html.escape(source.url)}">{citation}</a>'
    elif source.url:
        citation += f" ({html.escape(source.url)})"
    verified = {True: " · read at the source", False: " · not checked at the source", None: ""}[
        source.verified
    ]
    quote = f"<blockquote>{html.escape(source.quote)}</blockquote>" if source.quote else ""
    return f"<li>{citation}<span class='plain'>{verified}</span>{quote}</li>"


def _text(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, indent=1)
