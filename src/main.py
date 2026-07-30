"""Daily run: fetch every source, work out what is new, notify, rebuild the
board.

    python -m src.main                # full run
    python -m src.main --dry-run      # fetch and build, send nothing
    python -m src.main --check-urls   # just test every address in the config
"""

from __future__ import annotations

import argparse
import csv
import logging
import os
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import yaml

from . import fetcher
from .dashboard import render
from .models import Item
from .notify import channels, compose
from .scrapers import pagewatch, pesb
from .store import Store

logging.basicConfig(level=logging.INFO,
                    format="%(levelname)-7s %(name)-9s %(message)s")
log = logging.getLogger("run")

IST = timezone(timedelta(hours=5, minutes=30))
CONFIG = Path("config/sources.yaml")
CSV_OUT = Path("docs/vacancies.csv")


def load_config() -> dict:
    return yaml.safe_load(CONFIG.read_text(encoding="utf-8"))


def keyword_filter(post: str, keywords: list[str]) -> bool:
    text = post.lower()
    for kw in keywords:
        k = kw.lower()
        pattern = r"\b" + re.escape(k) + r"\b"
        if re.search(pattern, text):
            return True
    return False


def is_railway(org: str, matches: list[str]) -> bool:
    o = org.lower()
    return any(m.lower() in o for m in matches)


def check_urls(cfg: dict) -> int:
    bad = 0
    sources = cfg["structured"] + cfg["watched"]
    for s in sources:
        ok, _, note = fetcher.get(s["url"])
        flag = "ok  " if ok else "FAIL"
        if not ok:
            bad += 1
        print(f"{flag}  {s['name']:<38} {s['url']}"
              + (f"\n        {note}" if not ok else ""))
    print(f"\n{len(sources) - bad} of {len(sources)} reachable.")
    return bad


def write_csv(items: list[Item], today) -> None:
    CSV_OUT.parent.mkdir(parents=True, exist_ok=True)
    with CSV_OUT.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["Organisation", "Post", "Type", "Issued", "Vacant from",
                    "Apply by", "Cut-off", "Days left", "Schedule", "Scale",
                    "Source", "Link"])
        for i in sorted(items, key=lambda x: (x.days_left(today) is None,
                                              x.days_left(today) or 0)):
            w.writerow([i.organisation, i.post, i.kind, i.issue_date or "",
                        i.vacancy_date or "", i.last_date or "",
                        i.deadline_note, i.days_left(today) if
                        i.days_left(today) is not None else "",
                        i.schedule, i.scale, i.source_name, i.url])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--check-urls", action="store_true")
    ap.add_argument("--demo", action="store_true",
                    help="mark output as sample data and write to "
                         "docs/preview-demo.html")
    args = ap.parse_args()

    cfg = load_config()
    st = cfg["settings"]

    if args.check_urls:
        return 0 if check_urls(cfg) == 0 else 1

    now = datetime.now(IST)
    today = now.date()
    store = Store()
    failures: list[tuple[str, str]] = []
    found: list[Item] = []

    # --- structured sources ------------------------------------------------
    for src in cfg["structured"]:
        ok, html_text, note = fetcher.get(src["url"])
        if not ok:
            failures.append((src["name"], note))
            continue
        rows = pesb.parse(html_text, src["id"], src["name"], src["kind"],
                          src["url"])
        for item in rows:
            if not keyword_filter(item.post, cfg["post_keywords"]):
                continue
            if st.get("railway_cpse_only") and not is_railway(
                    item.organisation, cfg["railway_cpse_match"]):
                continue
            found.append(item)

    # --- watched pages -----------------------------------------------------
    for src in cfg["watched"]:
        ok, html_text, note = fetcher.get(src["url"])
        if not ok:
            failures.append((src["name"], note))
            continue
        items, fingerprint = pagewatch.scan(html_text, src, store.page(src["id"]))
        store.set_page(src["id"], fingerprint)
        found.extend(items)

    # --- what is new -------------------------------------------------------
    new_items = [i for i in found if store.is_new(i)
                 and i.status(today, st["closing_soon_days"]) != "expired"]
    for item in found:
        store.remember(item)

    removed = store.prune(today, st.get("keep_expired_days", 3))
    all_items = store.all_items()
    live = [i for i in all_items if i.status(today, st["closing_soon_days"])
            != "expired"]

    log.info("found %d · new %d · tracking %d · pruned %d · failures %d",
             len(found), len(new_items), len(live), removed, len(failures))

    # --- outputs -----------------------------------------------------------
    dashboard_url = os.getenv("DASHBOARD_URL", "")
    render(all_items, {i.uid for i in new_items}, today,
           st["closing_soon_days"], failures,
           now.strftime("%d %b %Y, %H:%M IST"),
           demo=args.demo,
           out=Path("docs/preview-demo.html") if args.demo else None)
    write_csv(live, today)

    subject, body = compose.build(new_items, live, today,
                                  st["closing_soon_days"], dashboard_url,
                                  failures)

    quiet_ok = os.getenv("ALWAYS_NOTIFY", "false").lower() == "true"
    has_news = bool(new_items) or any(
        i.status(today, st["closing_soon_days"]) == "closing" for i in live)

    if args.dry_run:
        print("\n" + "-" * 60)
        print(subject)
        print("-" * 60)
        print(channels._plain(body))
    elif has_news or quiet_ok:
        results = channels.send_all(subject, body, quiet=False)
        log.info("sent: %s", {k: v for k, v in results.items()})
    else:
        log.info("nothing to report - no message sent")

    store.save(today)
    return 0


if __name__ == "__main__":
    sys.exit(main())
