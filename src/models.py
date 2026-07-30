"""Data model for a tracked vacancy or page change."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field, asdict
from datetime import date, datetime
from typing import Optional

DATE_PATTERNS = [
    (re.compile(r"\b(\d{2})[.\-/](\d{2})[.\-/](\d{4})\b"), "dmy"),
    (re.compile(r"\b(\d{4})[.\-/](\d{2})[.\-/](\d{2})\b"), "ymd"),
]

MONTHS = {
    m.lower(): i
    for i, m in enumerate(
        ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
         "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], start=1)
}
TEXT_DATE = re.compile(
    r"\b(\d{1,2})\s*[-\s]\s*([A-Za-z]{3,9})\s*[-,\s]\s*(\d{4})\b")


def parse_date(text: str) -> Optional[date]:
    """Pull the first sensible date out of a blob of text."""
    if not text:
        return None
    for pattern, order in DATE_PATTERNS:
        m = pattern.search(text)
        if not m:
            continue
        a, b, c = (int(x) for x in m.groups())
        try:
            return date(c, b, a) if order == "dmy" else date(a, b, c)
        except ValueError:
            continue
    m = TEXT_DATE.search(text)
    if m:
        day, mon, year = m.groups()
        month = MONTHS.get(mon[:3].lower())
        if month:
            try:
                return date(int(year), month, int(day))
            except ValueError:
                pass
    return None


@dataclass
class Item:
    """One vacancy, or one detected change on a watched page."""

    source_id: str
    source_name: str
    kind: str                      # advertised | upcoming | document | change
    organisation: str
    post: str = ""
    issue_date: Optional[str] = None      # ISO
    vacancy_date: Optional[str] = None    # ISO - date the post falls vacant
    last_date: Optional[str] = None       # ISO - application deadline
    deadline_note: str = ""               # e.g. "3:00 PM"
    scale: str = ""
    schedule: str = ""
    url: str = ""
    group: str = ""
    first_seen: str = field(default_factory=lambda: datetime.now().date().isoformat())

    @property
    def uid(self) -> str:
        raw = "|".join([self.source_id, self.organisation.lower(),
                        self.post.lower(), self.last_date or "",
                        self.vacancy_date or "", self.url])
        return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]

    def days_left(self, today: date) -> Optional[int]:
        target = self.last_date or (self.vacancy_date if self.kind == "upcoming" else None)
        if not target:
            return None
        try:
            return (date.fromisoformat(target) - today).days
        except ValueError:
            return None

    def status(self, today: date, closing_soon_days: int) -> str:
        d = self.days_left(today)
        if d is None:
            return "no-date"
        if d < 0:
            return "expired"
        if d <= closing_soon_days:
            return "closing"
        if d <= 30:
            return "open"
        return "distant"

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> "Item":
        allowed = {f for f in Item.__dataclass_fields__}
        return Item(**{k: v for k, v in d.items() if k in allowed})
