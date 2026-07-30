"""Renders the board to docs/index.html for GitHub Pages.

Visual idea: a signal-box chart. Each vacancy sits on a track rail with a
signal lamp whose aspect carries the only thing that matters at a glance -
how much time is left. Red means days, amber means weeks, green means the
deadline is not the constraint.
"""

from __future__ import annotations

import html
from datetime import date, datetime
from pathlib import Path

from .models import Item

OUT = Path("docs/index.html")

ASPECT = {"closing": "danger", "open": "caution", "distant": "clear",
          "expired": "off", "no-date": "off"}
ASPECT_WORD = {"danger": "Closing", "caution": "Open", "clear": "Open",
               "off": "No date"}


def _fmt(iso: str | None) -> str:
    if not iso:
        return "—"
    try:
        return date.fromisoformat(iso).strftime("%d %b %Y")
    except ValueError:
        return iso


def _counter(n: int, label: str, cls: str) -> str:
    return (f'<button class="count {cls}" data-filter="{cls}">'
            f'<span class="count-n">{n}</span>'
            f'<span class="count-l">{label}</span></button>')


def _row(item: Item, today: date, soon: int, is_new: bool) -> str:
    st = item.status(today, soon)
    aspect = ASPECT[st]
    d = item.days_left(today)

    if item.kind == "upcoming":
        gutter_n, gutter_l = (str(d) if d is not None and d >= 0 else "—"), "days to"
        when = f"Falls vacant {_fmt(item.vacancy_date)}"
    elif d is None:
        gutter_n, gutter_l = "·", ""
        when = _fmt(item.issue_date) if item.issue_date else "Posted recently"
    elif d < 0:
        gutter_n, gutter_l = "0", "closed"
        when = f"Closed {_fmt(item.last_date)}"
    else:
        gutter_n, gutter_l = str(d), "day" if d == 1 else "days"
        note = f" · {item.deadline_note}" if item.deadline_note else ""
        when = f"Apply by {_fmt(item.last_date)}{note}"

    meta = [when]
    if item.vacancy_date and item.kind != "upcoming":
        meta.append(f"Vacant from {_fmt(item.vacancy_date)}")
    if item.schedule:
        meta.append(html.escape(item.schedule))
    if item.scale:
        meta.append(html.escape(item.scale))
    meta.append(html.escape(item.source_name))

    tag = '<span class="tag-new">New</span>' if is_new else ""
    is_new_attr = "1" if is_new else "0"
    search = html.escape(
        f"{item.organisation} {item.post} {item.source_name} {item.group}".lower())

    return f"""
      <li class="row {aspect}" data-search="{search}" data-aspect="{aspect}" data-new="{is_new_attr}">
        <div class="gutter" aria-hidden="true">
          <span class="lamp"></span>
          <span class="g-n">{gutter_n}</span>
          <span class="g-l">{gutter_l}</span>
        </div>
        <div class="body">
          <p class="org">{html.escape(item.organisation)}{tag}</p>
          <h3 class="post"><a href="{html.escape(item.url)}" target="_blank"
             rel="noopener">{html.escape(item.post)}</a></h3>
          <p class="meta">{' <i>·</i> '.join(meta)}</p>
        </div>
        <span class="sr">{ASPECT_WORD[aspect]}</span>
      </li>"""


def _section(title: str, note: str, rows: list[str]) -> str:
    if not rows:
        return ""
    return f"""
    <section class="block">
      <header class="block-h">
        <h2>{title}</h2><span class="block-n">{len(rows)}</span>
        <p class="block-note">{note}</p>
      </header>
      <ul class="rail">{''.join(rows)}</ul>
    </section>"""


CSS = """
:root{
  --paper:#e6eaed; --card:#fff; --ink:#171b1f; --muted:#5c6670;
  --rule:#ccd3d8; --brand:#6e1a22; --brand-ink:#f3e7e4;
  --danger:#c0272d; --caution:#c07c00; --clear:#157f4c; --off:#8b959c;
  --shadow:0 1px 0 rgba(23,27,31,.06), 0 6px 22px -14px rgba(23,27,31,.5);
}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--paper);color:var(--ink);
  font:15px/1.5 "IBM Plex Sans",-apple-system,Segoe UI,Roboto,sans-serif;}
a{color:inherit}
.sr{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)}
.wrap{max-width:900px;margin:0 auto;padding:0 18px 72px}

/* masthead */
.mast{background:var(--brand);color:var(--brand-ink);
  border-bottom:3px solid #4a1016}
.mast .wrap{padding-top:24px;padding-bottom:22px}
.mast h1{margin:0;font-family:"IBM Plex Sans Condensed",sans-serif;
  font-weight:600;font-size:clamp(26px,5vw,40px);letter-spacing:.055em;
  text-transform:uppercase;line-height:1.05}
.mast p{margin:8px 0 0;font-size:13.5px;opacity:.82;max-width:52ch}
.stamp{margin-top:14px;font-family:"IBM Plex Mono",monospace;font-size:11.5px;
  letter-spacing:.09em;text-transform:uppercase;opacity:.72}

/* counters */
.counts{display:flex;gap:8px;flex-wrap:wrap;margin:-20px 0 26px}
.count{flex:1 1 150px;background:var(--card);border:1px solid var(--rule);
  border-radius:2px;border-top:3px solid var(--off);padding:12px 14px;
  text-align:left;cursor:pointer;font:inherit;box-shadow:var(--shadow);
  transition:transform .12s ease, border-color .12s ease}
.count:hover{transform:translateY(-2px)}
.count[aria-pressed="true"]{outline:2px solid var(--ink);outline-offset:-2px}
.count.danger{border-top-color:var(--danger)}
.count.caution{border-top-color:var(--caution)}
.count.clear{border-top-color:var(--clear)}
.count.fresh{border-top-color:var(--brand)}
.count-n{display:block;font-family:"IBM Plex Mono",monospace;font-size:26px;
  font-weight:600;line-height:1}
.count-l{display:block;margin-top:5px;font-size:11px;letter-spacing:.1em;
  text-transform:uppercase;color:var(--muted)}

.tools{display:flex;gap:10px;align-items:center;margin:0 0 22px}
.tools input{flex:1;padding:11px 13px;border:1px solid var(--rule);
  border-radius:2px;background:var(--card);font:inherit}
.tools input:focus-visible{outline:2px solid var(--brand);outline-offset:-1px}

/* sections */
.block{margin:0 0 34px}
.block-h{display:grid;grid-template-columns:auto auto 1fr;align-items:baseline;
  gap:10px;padding-bottom:9px;border-bottom:1px solid var(--rule);margin-bottom:2px}
.block-h h2{margin:0;font-family:"IBM Plex Sans Condensed",sans-serif;
  font-size:15px;letter-spacing:.13em;text-transform:uppercase;font-weight:600}
.block-n{font-family:"IBM Plex Mono",monospace;font-size:12px;color:var(--muted)}
.block-note{grid-column:1/-1;margin:2px 0 0;font-size:12.5px;color:var(--muted)}

/* the rail */
.rail{list-style:none;margin:0;padding:0}
.row{display:grid;grid-template-columns:66px 1fr;background:var(--card);
  border:1px solid var(--rule);border-top:none;position:relative}
.rail .row:first-child{border-top:1px solid var(--rule)}
.gutter{position:relative;display:flex;flex-direction:column;
  align-items:center;justify-content:center;padding:15px 4px;
  border-right:1px solid var(--rule);background:#f4f6f7}
/* the track: a continuous line the lamps sit on */
.gutter::before{content:"";position:absolute;left:50%;top:0;bottom:0;width:2px;
  margin-left:-1px;background:repeating-linear-gradient(to bottom,
    var(--rule) 0 6px, transparent 6px 10px)}
.lamp{position:relative;z-index:1;width:11px;height:11px;border-radius:50%;
  background:var(--off);box-shadow:0 0 0 4px #f4f6f7;margin-bottom:7px}
.row.danger .lamp{background:var(--danger);
  box-shadow:0 0 0 4px #f4f6f7, 0 0 0 7px rgba(192,39,45,.22)}
.row.caution .lamp{background:var(--caution);box-shadow:0 0 0 4px #f4f6f7}
.row.clear .lamp{background:var(--clear);box-shadow:0 0 0 4px #f4f6f7}
.g-n{position:relative;z-index:1;font-family:"IBM Plex Mono",monospace;
  font-size:21px;font-weight:600;line-height:1;background:#f4f6f7;padding:1px 3px}
.g-l{position:relative;z-index:1;font-size:9.5px;letter-spacing:.09em;
  text-transform:uppercase;color:var(--muted);background:#f4f6f7;padding:0 3px}
.row.danger .g-n{color:var(--danger)}

.body{padding:14px 16px 15px;min-width:0}
.org{margin:0;font-size:11px;letter-spacing:.11em;text-transform:uppercase;
  color:var(--muted);display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.tag-new{background:var(--brand);color:#fff;border-radius:2px;
  padding:1px 6px;font-size:9.5px;letter-spacing:.1em}
.post{margin:5px 0 6px;font-size:17px;font-weight:600;line-height:1.28}
.post a{text-decoration:none;background-image:linear-gradient(var(--rule),var(--rule));
  background-size:100% 1px;background-repeat:no-repeat;background-position:0 100%;
  padding-bottom:1px}
.post a:hover{background-image:linear-gradient(var(--brand),var(--brand))}
.meta{margin:0;font-family:"IBM Plex Mono",monospace;font-size:11.5px;
  color:var(--muted);line-height:1.65}
.meta i{font-style:normal;opacity:.45;padding:0 2px}

.empty{background:var(--card);border:1px dashed var(--rule);padding:26px;
  text-align:center;color:var(--muted);font-size:14px}
.foot{margin-top:40px;padding-top:16px;border-top:1px solid var(--rule);
  font-size:12px;color:var(--muted);line-height:1.7}
.foot code{font-family:"IBM Plex Mono",monospace;background:#dde3e6;padding:1px 5px}
.fail{color:var(--danger)}
.demo{background:#3a0d11;color:#ffd9d9;padding:11px 18px;font-size:13px;
  text-align:center;font-weight:600;letter-spacing:.01em}

@media (max-width:560px){
  .row{grid-template-columns:52px 1fr}
  .g-n{font-size:18px}
  .post{font-size:15.5px}
  .count{flex:1 1 calc(50% - 8px)}
}
@media (prefers-reduced-motion:reduce){*{transition:none!important}}
"""

JS = """
const rows=[...document.querySelectorAll('.row')];
const q=document.getElementById('q');
let aspect=null;
function apply(){
  const t=(q.value||'').trim().toLowerCase();
  rows.forEach(r=>{
    const okT=!t||r.dataset.search.includes(t);
    const okA=!aspect||(aspect==='fresh'?r.dataset.new==='1'
                        :r.dataset.aspect===aspect);
    r.style.display=(okT&&okA)?'':'none';
  });
  document.querySelectorAll('.block').forEach(b=>{
    const any=[...b.querySelectorAll('.row')].some(r=>r.style.display!=='none');
    b.style.display=any?'':'none';
  });
}
q.addEventListener('input',apply);
document.querySelectorAll('.count').forEach(c=>c.addEventListener('click',()=>{
  const f=c.dataset.filter;
  aspect=(aspect===f)?null:f;
  document.querySelectorAll('.count').forEach(x=>
    x.setAttribute('aria-pressed', x.dataset.filter===aspect));
  apply();
}));
"""


def render(items: list[Item], new_uids: set[str], today: date, soon: int,
           failures: list[tuple[str, str]], run_at: str,
           demo: bool = False, out: Path | None = None) -> Path:
    live = [i for i in items if i.status(today, soon) != "expired"]

    closing, open_now, upcoming, notices = [], [], [], []
    for i in sorted(live, key=lambda x: (x.days_left(today) is None,
                                         x.days_left(today) or 0)):
        st = i.status(today, soon)
        if i.kind == "upcoming":
            upcoming.append(i)
        elif i.kind in ("document", "change"):
            notices.append(i)
        elif st == "closing":
            closing.append(i)
        else:
            open_now.append(i)

    notices.sort(key=lambda x: x.first_seen, reverse=True)

    def rows(group):
        return [_row(i, today, soon, i.uid in new_uids) for i in group]

    body = "".join([
        _section("Closing soon", f"Deadline within {soon} days.", rows(closing)),
        _section("Open", "Applications still being received.", rows(open_now)),
        _section("Upcoming vacancies",
                 "Posts falling vacant. Not yet advertised — this is the "
                 "early warning list.", rows(upcoming)),
        _section("Recent notices", "New documents found on watched career "
                 "pages. Deadline not machine-readable — open to check.",
                 rows(notices[:40])),
    ])
    if not body:
        body = ('<p class="empty">Nothing on the board. Either it is a quiet '
                'week, or a source needs checking — see the log at the '
                'bottom.</p>')

    fail_html = ""
    if failures:
        rows_ = "".join(f"<div class=\"fail\">{html.escape(n)} — "
                        f"{html.escape(m)}</div>" for n, m in failures)
        fail_html = ("<p style=\"margin:18px 0 6px\"><strong>Sources "
                     f"unreachable ({len(failures)})</strong></p>" + rows_ +
                     "<p>Correct the address in <code>config/sources.yaml</code>"
                     " and the next run will pick it up.</p>")

    counts = "".join([
        _counter(len(closing), "Closing soon", "danger"),
        _counter(len(open_now), "Open", "caution"),
        _counter(len(upcoming), "Upcoming", "clear"),
        _counter(len(new_uids), "New today", "fresh"),
    ])

    demo_banner = ("<div class=\"demo\">Sample data — these rows are "
                   "invented to demonstrate the layout. No vacancy shown "
                   "here is real. The first live run replaces this "
                   "page.</div>") if demo else ""

    page = f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="theme-color" content="#6e1a22">
<title>Vacancy board — Railway PSUs &amp; Metros</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans+Condensed:wght@600&family=IBM+Plex+Sans:wght@400;600&display=swap" rel="stylesheet">
<style>{CSS}</style>
</head><body>

{demo_banner}
<div class="mast"><div class="wrap">
  <h1>Vacancy Board</h1>
  <p>Board-level and senior posts across Railway public sector undertakings,
     metro rail corporations and the Railway Board.</p>
  <p class="stamp">Checked {run_at}</p>
</div></div>

<div class="wrap">
  <div class="counts">{counts}</div>
  <div class="tools">
    <input id="q" type="search" placeholder="Filter by organisation or post"
           aria-label="Filter by organisation or post">
  </div>
  {body}
  <div class="foot">
    {fail_html}
    <p>Rebuilt automatically each morning. Deadlines are shown as published by
       the source — confirm on the source page before acting on one.</p>
  </div>
</div>
<script>{JS}</script>
</body></html>"""

    target = out or OUT
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(page, encoding="utf-8")
    return target
