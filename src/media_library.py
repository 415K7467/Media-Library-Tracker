"""Persistence and collection management for MediaItem records."""

from __future__ import annotations

import csv
import json
import os
from typing import Any, Iterable, Optional

from media_item import MediaItem

SEARCHABLE_FIELDS = ("title", "category", "status", "notes")
SORTABLE_FIELDS = ("title", "category", "status", "rating", "watched")


class MediaLibraryError(Exception):
    """Raised for library-level failures (I/O, corrupt data, bad lookups)."""


class MediaLibrary:
    """In-memory collection of MediaItem objects backed by a JSON file."""

    def __init__(self, storage_path: str) -> None:
        self.storage_path = storage_path
        self._items: list[MediaItem] = []
        self._next_id = 1

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------
    def load(self) -> None:
        if not os.path.exists(self.storage_path):
            self._items = []
            self._next_id = 1
            return

        try:
            with open(self.storage_path, "r", encoding="utf-8") as handle:
                raw = handle.read().strip()
        except OSError as exc:
            raise MediaLibraryError(f"Could not read storage file: {exc}") from exc

        if not raw:
            self._items = []
            self._next_id = 1
            return

        try:
            records = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise MediaLibraryError(f"Storage file is corrupted: {exc}") from exc

        items: list[MediaItem] = []
        for record in records:
            try:
                items.append(MediaItem.from_dict(record))
            except ValueError:
                # Skip corrupt/invalid individual records rather than failing the whole load.
                continue

        self._items = items
        used_ids = [item.item_id for item in self._items if item.item_id is not None]
        self._next_id = max(used_ids, default=0) + 1

    def save(self) -> None:
        directory = os.path.dirname(self.storage_path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        try:
            with open(self.storage_path, "w", encoding="utf-8") as handle:
                json.dump([item.to_dict() for item in self._items], handle, indent=2)
        except OSError as exc:
            raise MediaLibraryError(f"Could not write storage file: {exc}") from exc

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------
    @property
    def items(self) -> list[MediaItem]:
        return list(self._items)

    def add_item(self, item: MediaItem) -> MediaItem:
        item.item_id = self._next_id
        self._next_id += 1
        self._items.append(item)
        self.save()
        return item

    def update_item(self, item_id: int, **changes: Any) -> MediaItem:
        item = self.get_item(item_id)
        for field, value in changes.items():
            setattr(item, field, value)
        self.save()
        return item

    def delete_item(self, item_id: int) -> None:
        item = self.get_item(item_id)
        self._items.remove(item)
        self.save()

    def get_item(self, item_id: int) -> MediaItem:
        for item in self._items:
            if item.item_id == item_id:
                return item
        raise MediaLibraryError(f"No item found with id {item_id}.")

    def toggle_watched(self, item_id: int) -> MediaItem:
        item = self.get_item(item_id)
        item.toggle_watched()
        self.save()
        return item

    # ------------------------------------------------------------------
    # Search / sort
    # ------------------------------------------------------------------
    def search(self, query: str, field: Optional[str] = None) -> list[MediaItem]:
        query = (query or "").strip().lower()
        if not query:
            return self.items

        fields = (field,) if field else SEARCHABLE_FIELDS
        results = []
        for item in self._items:
            for candidate_field in fields:
                value = self._field_value(item, candidate_field)
                if query in str(value).lower():
                    results.append(item)
                    break
        return results

    def sort(self, items: Iterable[MediaItem], field: str, reverse: bool = False) -> list[MediaItem]:
        if field not in SORTABLE_FIELDS:
            raise MediaLibraryError(f"Cannot sort by unknown field {field!r}.")

        def sort_key(item: MediaItem):
            value = self._field_value(item, field)
            # None ratings should sort last regardless of direction.
            if value is None:
                return (1, 0)
            return (0, value)

        return sorted(items, key=sort_key, reverse=reverse)

    @staticmethod
    def _field_value(item: MediaItem, field: str) -> Any:
        value = getattr(item, field)
        if hasattr(value, "value"):  # Enum
            return value.value
        return value

    # ------------------------------------------------------------------
    # Stats & export
    # ------------------------------------------------------------------
    def statistics(self) -> dict[str, Any]:
        by_category: dict[str, int] = {}
        watched_count = 0
        for item in self._items:
            by_category[item.category.value] = by_category.get(item.category.value, 0) + 1
            if item.watched:
                watched_count += 1

        total = len(self._items)
        return {
            "total": total,
            "by_category": by_category,
            "watched": watched_count,
            "unwatched": total - watched_count,
        }

    def export_csv(self, path: str, items: Optional[Iterable[MediaItem]] = None) -> None:
        rows = list(items) if items is not None else self._items
        fieldnames = ["item_id", "title", "category", "status", "rating", "watched", "notes", "image_path"]
        try:
            with open(path, "w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=fieldnames)
                writer.writeheader()
                for item in rows:
                    data = item.to_dict()
                    writer.writerow(data)
        except OSError as exc:
            raise MediaLibraryError(f"Could not write CSV file: {exc}") from exc
