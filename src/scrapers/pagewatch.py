"""Change detection for career pages that publish vacancies as loose PDFs.

Two signals are produced, in order of usefulness:

  1. A document link that was not on the page yesterday. This is the signal
     that matters - it is almost always the notification itself.
  2. The page's visible text changed but no new document appeared. Reported
     once, quietly, so a redesigned or reworded page does not shout.
"""

from __future__ import annotations

import hashlib
import re
from datetime import date
from urllib.parse import urljoin, urldefrag

from bs4 import BeautifulSoup

from ..models import Item, parse_date

DOC_EXT = (".pdf", ".doc", ".docx", ".xls", ".xlsx")
STRIP_TAGS = ["script", "style", "nav", "footer", "noscript", "svg"]

# Words that suggest a link is actually a vacancy notice.
RELEVANT = re.compile(
    r"(vacanc|recruit|appointment|engagement|deputation|career|"
    r"advertis|notice|circular|post|hiring|empanel|contract basis)", re.I)


def _clean_text(soup: BeautifulSoup) -> str:
    for t in soup(STRIP_TAGS):
        t.decompose()
    return re.sub(r"\s+", " ", soup.get_text(" ", strip=True))


def _documents(soup: BeautifulSoup, base_url: str) -> dict[str, str]:
    """url -> link text, for anything that looks like a downloadable notice."""
    out: dict[str, str] = {}
    for a in soup.find_all("a", href=True):
        href = urldefrag(urljoin(base_url, a["href"]))[0]
        label = re.sub(r"\s+", " ", a.get_text(" ", strip=True))[:220]
        low = href.lower()
        if low.endswith(DOC_EXT) or RELEVANT.search(label):
            if len(label) >= 8 or low.endswith(DOC_EXT):
                out[href] = label or href.rsplit("/", 1)[-1]
    return out


def scan(html: str, source: dict, previous: dict) -> tuple[list[Item], dict]:
    """Compare this fetch against the stored fingerprint for the page."""
    base_url = source["url"]
    soup = BeautifulSoup(html, "html.parser")

    docs = _documents(soup, base_url)
    text = _clean_text(BeautifulSoup(html, "html.parser"))
    text_hash = hashlib.sha1(text.encode("utf-8")).hexdigest()

    prev_docs = set(previous.get("docs", []))
    prev_hash = previous.get("text_hash")
    first_run = not previous

    items: list[Item] = []

    if not first_run:
        for url, label in docs.items():
            if url in prev_docs:
                continue
            if not RELEVANT.search(label) and not url.lower().endswith(DOC_EXT):
                continue
            d = parse_date(label)
            future = d and d >= date.today()
            items.append(Item(
                source_id=source["id"],
                source_name=source["name"],
                kind="document",
                organisation=source["name"],
                post=label,
                issue_date=d.isoformat() if d and not future else None,
                last_date=d.isoformat() if future else None,
                deadline_note="date read from the notice title" if future else "",
                url=url,
                group=source.get("group", "Watched page"),
            ))

        if not items and prev_hash and prev_hash != text_hash:
            items.append(Item(
                source_id=source["id"],
                source_name=source["name"],
                kind="change",
                organisation=source["name"],
                post="Page content changed - no new document link found",
                url=base_url,
                group=source.get("group", "Watched page"),
            ))

    fingerprint = {"docs": sorted(docs.keys()), "text_hash": text_hash,
                   "doc_count": len(docs)}
    return items, fingerprint
