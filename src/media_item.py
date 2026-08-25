"""Domain model for a single media entry in the library."""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional


class Category(Enum):
    BOOK = "Book"
    MOVIE = "Movie"
    GAME = "Game"
    SHOW = "Show"
    OTHER = "Other"

    @classmethod
    def values(cls) -> list[str]:
        return [member.value for member in cls]

    @classmethod
    def from_value(cls, value: str) -> "Category":
        for member in cls:
            if member.value == value:
                return member
        raise ValueError(f"Unknown category: {value!r}")


class Status(Enum):
    PLANNED = "Planned"
    IN_PROGRESS = "In Progress"
    COMPLETED = "Completed"
    DROPPED = "Dropped"

    @classmethod
    def values(cls) -> list[str]:
        return [member.value for member in cls]

    @classmethod
    def from_value(cls, value: str) -> "Status":
        for member in cls:
            if member.value == value:
                return member
        raise ValueError(f"Unknown status: {value!r}")


MIN_RATING = 0
MAX_RATING = 5


class MediaItem:
    """A single catalog entry (book, movie, game, ...)."""

    def __init__(
        self,
        title: str,
        category: str | Category,
        status: str | Status = Status.PLANNED,
        rating: Optional[int] = None,
        notes: str = "",
        watched: bool = False,
        image_path: str = "",
        item_id: Optional[int] = None,
    ) -> None:
        self.item_id = item_id
        self.title = title
        self.category = category
        self.status = status
        self.rating = rating
        self.notes = notes
        self.watched = watched
        self.image_path = image_path

    # ------------------------------------------------------------------
    # Validated properties
    # ------------------------------------------------------------------
    @property
    def title(self) -> str:
        return self._title

    @title.setter
    def title(self, value: str) -> None:
        value = (value or "").strip()
        if not value:
            raise ValueError("Title cannot be empty.")
        self._title = value

    @property
    def category(self) -> Category:
        return self._category

    @category.setter
    def category(self, value: str | Category) -> None:
        self._category = value if isinstance(value, Category) else Category.from_value(value)

    @property
    def status(self) -> Status:
        return self._status

    @status.setter
    def status(self, value: str | Status) -> None:
        self._status = value if isinstance(value, Status) else Status.from_value(value)

    @property
    def rating(self) -> Optional[int]:
        return self._rating

    @rating.setter
    def rating(self, value: Optional[int]) -> None:
        if value in (None, ""):
            self._rating = None
            return
        try:
            value = int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError("Rating must be an integer.") from exc
        if not MIN_RATING <= value <= MAX_RATING:
            raise ValueError(f"Rating must be between {MIN_RATING} and {MAX_RATING}.")
        self._rating = value

    @property
    def watched(self) -> bool:
        return self._watched

    @watched.setter
    def watched(self, value: bool) -> None:
        self._watched = bool(value)

    # ------------------------------------------------------------------
    # Behaviour
    # ------------------------------------------------------------------
    def toggle_watched(self) -> None:
        self.watched = not self.watched

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "title": self.title,
            "category": self.category.value,
            "status": self.status.value,
            "rating": self.rating,
            "notes": self.notes,
            "watched": self.watched,
            "image_path": self.image_path,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MediaItem":
        return cls(
            title=data.get("title", ""),
            category=data.get("category", Category.OTHER.value),
            status=data.get("status", Status.PLANNED.value),
            rating=data.get("rating"),
            notes=data.get("notes", ""),
            watched=data.get("watched", False),
            image_path=data.get("image_path", ""),
            item_id=data.get("item_id"),
        )

    def __repr__(self) -> str:
        return f"MediaItem(id={self.item_id}, title={self.title!r}, category={self.category.value})"
