"""Persistent state, kept as JSON in the repository so the workflow remembers
what it has already sent."""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

from .models import Item

STATE_PATH = Path("data/state.json")


class Store:
    def __init__(self, path: Path = STATE_PATH):
        self.path = path
        self.data = {"items": {}, "pages": {}, "last_run": None}
        if path.exists():
            try:
                self.data = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                pass
        self.data.setdefault("items", {})
        self.data.setdefault("pages", {})

    # -- vacancies ---------------------------------------------------------
    def is_new(self, item: Item) -> bool:
        return item.uid not in self.data["items"]

    def remember(self, item: Item) -> None:
        existing = self.data["items"].get(item.uid)
        if existing:
            item.first_seen = existing.get("first_seen", item.first_seen)
        self.data["items"][item.uid] = item.to_dict()

    def all_items(self) -> list[Item]:
        return [Item.from_dict(d) for d in self.data["items"].values()]

    # -- watched pages -----------------------------------------------------
    def page(self, source_id: str) -> dict:
        return self.data["pages"].get(source_id, {})

    def set_page(self, source_id: str, fingerprint: dict) -> None:
        self.data["pages"][source_id] = fingerprint

    # -- housekeeping ------------------------------------------------------
    def prune(self, today: date, keep_expired_days: int) -> int:
        """Drop items whose deadline passed a while ago, and stale one-off
        notices, so the file does not grow without limit."""
        cutoff = today - timedelta(days=max(keep_expired_days, 60))
        hard_cutoff = today - timedelta(days=120)
        removed = 0
        for uid, raw in list(self.data["items"].items()):
            item = Item.from_dict(raw)
            drop = False
            if item.last_date:
                try:
                    drop = date.fromisoformat(item.last_date) < cutoff
                except ValueError:
                    drop = False
            elif item.kind in ("document", "change"):
                try:
                    drop = date.fromisoformat(item.first_seen) < hard_cutoff
                except ValueError:
                    drop = True
            if drop:
                del self.data["items"][uid]
                removed += 1
        return removed

    def save(self, today: date) -> None:
        self.data["last_run"] = today.isoformat()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(self.data, indent=1, sort_keys=True), encoding="utf-8")
