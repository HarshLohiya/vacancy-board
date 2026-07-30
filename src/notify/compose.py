"""Turns the day's findings into the text each channel sends."""

from __future__ import annotations

from datetime import date

from ..models import Item

LAMP = {"closing": "🔴", "open": "🟡", "distant": "🟢",
        "expired": "⚫", "no-date": "⚪"}


def _fmt(iso: str | None) -> str:
    if not iso:
        return "—"
    try:
        return date.fromisoformat(iso).strftime("%d %b %Y")
    except ValueError:
        return iso


def _line(item: Item, today: date, soon: int) -> str:
    st = item.status(today, soon)
    d = item.days_left(today)
    lamp = LAMP[st]
    head = f"{lamp} <b>{item.post}</b>"
    body = [f"    {item.organisation}"]
    if item.kind == "upcoming":
        body.append(f"    Falls vacant {_fmt(item.vacancy_date)}"
                    + (f" · in {d} days" if d is not None and d >= 0 else ""))
    elif item.last_date:
        tail = f" · {item.deadline_note}" if item.deadline_note else ""
        left = (f" · {d} days left" if d is not None and d > 0
                else " · closes today" if d == 0 else " · closed")
        body.append(f"    Apply by {_fmt(item.last_date)}{tail}{left}")
        if item.vacancy_date:
            body.append(f"    Post falls vacant {_fmt(item.vacancy_date)}")
    if item.url:
        body.append(f"    <a href=\"{item.url}\">Open</a>")
    return head + "\n" + "\n".join(body)


def build(new_items: list[Item], live_items: list[Item], today: date,
          soon: int, dashboard_url: str, failures: list[tuple[str, str]]
          ) -> tuple[str, str]:
    """Return (subject, html_body). The body uses the small HTML subset that
    Telegram accepts, which e-mail and WhatsApp then adapt."""

    closing = sorted([i for i in live_items
                      if i.status(today, soon) == "closing"],
                     key=lambda i: i.days_left(today) or 99)
    new_sorted = sorted(new_items, key=lambda i: (i.kind != "advertised",
                                                  i.days_left(today) or 999))

    if closing:
        subject = (f"{len(new_items)} new · {len(closing)} closing within "
                   f"{soon} days")
    elif new_items:
        subject = f"{len(new_items)} new vacancy notification(s)"
    else:
        subject = "No change today"

    parts = [f"<b>Vacancy board · {today.strftime('%d %b %Y')}</b>", ""]

    if new_sorted:
        parts.append(f"<b>NEW SINCE YESTERDAY ({len(new_sorted)})</b>")
        parts += [_line(i, today, soon) for i in new_sorted[:25]]
        if len(new_sorted) > 25:
            parts.append(f"    …and {len(new_sorted) - 25} more on the board.")
        parts.append("")

    if closing:
        remaining = [i for i in closing if i not in new_sorted]
        if remaining:
            parts.append(f"<b>CLOSING SOON ({len(remaining)})</b>")
            parts += [_line(i, today, soon) for i in remaining]
            parts.append("")

    if not new_sorted and not closing:
        parts.append("Nothing new. Nothing closing in the next "
                     f"{soon} days.")
        parts.append("")

    open_count = len([i for i in live_items
                      if i.status(today, soon) in ("open", "distant")])
    parts.append(f"Tracking {open_count} open post(s) and "
                 f"{len([i for i in live_items if i.kind == 'upcoming'])} "
                 "upcoming vacancy date(s).")

    if dashboard_url:
        parts.append(f"<a href=\"{dashboard_url}\">Full board</a>")

    if failures:
        parts.append("")
        parts.append(f"<b>Sources unreachable ({len(failures)})</b>")
        for name, note in failures[:8]:
            parts.append(f"    {name} — {note}")

    return subject, "\n".join(parts)
