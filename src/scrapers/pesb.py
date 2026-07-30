"""Parser for the PESB vacancy tables.

Written against column *headings* rather than CSS classes or cell positions,
so a redesign of the site does not silently break the scrape. If the headings
themselves change, the run logs a warning instead of returning empty results.
"""

from __future__ import annotations

import logging
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..models import Item, parse_date

log = logging.getLogger("pesb")

# Heading text -> logical column. Matched as a substring, lowercased.
COLUMN_HINTS = {
    "organisation": ["name of the cpse", "cpse", "organisation", "organization",
                     "company", "enterprise"],
    "post": ["post", "job description", "designation"],
    "schedule": ["sch. of", "schedule"],
    "scale": ["pay scale", "scale"],
    "last_date": ["last date", "closing date", "last dt"],
    "vacancy_date": ["vacancy date", "date of vacancy"],
}

TIME_RE = re.compile(r"\b(\d{1,2}[:.]\d{2}\s*(?:AM|PM))\b", re.I)
NOISE = re.compile(r"\b(job description|apply|download|click here|view)\b", re.I)


def _cell_text(cell) -> str:
    return re.sub(r"\s+", " ", cell.get_text(" ", strip=True)).strip()


def _map_columns(header_cells: list[str]) -> dict[str, int]:
    mapping: dict[str, int] = {}
    for idx, raw in enumerate(header_cells):
        h = raw.lower()
        for logical, hints in COLUMN_HINTS.items():
            if logical in mapping:
                continue
            if any(hint in h for hint in hints):
                mapping[logical] = idx
                break
    return mapping


def _pick_table(soup: BeautifulSoup):
    """Choose the table that actually holds vacancies."""
    best, best_score, best_map = None, 0, {}
    for table in soup.find_all("table"):
        head = table.find("tr")
        if not head:
            continue
        headers = [_cell_text(c) for c in head.find_all(["th", "td"])]
        mapping = _map_columns(headers)
        score = len(mapping) + (2 if "last_date" in mapping else 0)
        if score > best_score:
            best, best_score, best_map = table, score, mapping
    return (best, best_map) if best_score >= 2 else (None, {})


def _split_dates(text: str) -> tuple[str | None, str]:
    """A PESB cell often holds a date plus a cut-off time."""
    d = parse_date(text)
    t = TIME_RE.search(text)
    return (d.isoformat() if d else None), (t.group(1).upper() if t else "")


def parse(html: str, source_id: str, source_name: str, kind: str,
          base_url: str) -> list[Item]:
    soup = BeautifulSoup(html, "html.parser")
    table, cols = _pick_table(soup)
    if table is None:
        log.warning("%s: no vacancy table recognised - check the page layout",
                    source_id)
        return []

    items: list[Item] = []
    rows = table.find_all("tr")[1:]
    for row in rows:
        cells = row.find_all(["td", "th"])
        if len(cells) < 2:
            continue
        texts = [_cell_text(c) for c in cells]

        def col(name: str) -> str:
            i = cols.get(name)
            return texts[i] if i is not None and i < len(texts) else ""

        org = col("organisation")
        post_cell = col("post")
        if not org and not post_cell:
            continue

        # The post cell also carries the issue date and link labels.
        issue = parse_date(post_cell)
        post = NOISE.sub("", post_cell)
        post = re.sub(r"\d{2}[.\-/]\d{2}[.\-/]\d{4}", "", post)
        post = re.sub(r"\s{2,}", " ", post).strip(" .-|")

        # The scale cell on PESB holds the pay scale and the vacancy date.
        scale_cell = col("scale")
        vac_date = parse_date(col("vacancy_date")) or parse_date(scale_cell)
        scale = re.sub(r"\d{2}[.\-/]\d{2}[.\-/]\d{4}", "", scale_cell).strip()

        last_iso, note = _split_dates(col("last_date"))

        link = ""
        for a in row.find_all("a", href=True):
            href = a["href"]
            if href and not href.lower().startswith("javascript"):
                link = urljoin(base_url, href)
                break

        if not post:
            continue

        items.append(Item(
            source_id=source_id,
            source_name=source_name,
            kind=kind,
            organisation=org or "(not stated)",
            post=post,
            issue_date=issue.isoformat() if issue else None,
            vacancy_date=vac_date.isoformat() if vac_date else None,
            last_date=last_iso,
            deadline_note=note,
            scale=scale,
            schedule=col("schedule"),
            url=link or base_url,
            group="Board level (PESB)",
        ))

    log.info("%s: parsed %d rows", source_id, len(items))
    return items
