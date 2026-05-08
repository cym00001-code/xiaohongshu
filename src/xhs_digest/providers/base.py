"""Provider contracts and shared provider value objects."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol


JsonDict = dict[str, Any]


class ProviderError(RuntimeError):
    """Base provider error."""


class ProviderRetryableError(ProviderError):
    """A provider request may succeed if retried later."""


class ProviderRequestError(ProviderError):
    """A provider request failed and should not be retried as-is."""


@dataclass(slots=True)
class ProviderNote:
    provider: str
    note_id: str
    title: str | None = None
    description: str | None = None
    url: str | None = None
    author_id: str | None = None
    author_name: str | None = None
    published_at: datetime | None = None
    liked_count: int | None = None
    collected_count: int | None = None
    commented_count: int | None = None
    shared_count: int | None = None
    tags: list[str] = field(default_factory=list)
    raw: JsonDict = field(default_factory=dict)


@dataclass(slots=True)
class ProviderComment:
    provider: str
    comment_id: str
    note_id: str
    parent_comment_id: str | None = None
    author_id: str | None = None
    author_name: str | None = None
    content: str | None = None
    liked_count: int | None = None
    created_at: datetime | None = None
    raw: JsonDict = field(default_factory=dict)


@dataclass(slots=True)
class ProviderSearchPage:
    notes: list[ProviderNote]
    next_cursor: str | None = None
    has_more: bool = False
    raw: JsonDict = field(default_factory=dict)


@dataclass(slots=True)
class ProviderCommentPage:
    comments: list[ProviderComment]
    next_cursor: str | None = None
    has_more: bool = False
    raw: JsonDict = field(default_factory=dict)


@dataclass(slots=True)
class SuggestedKeyword:
    keyword: str
    score: float | None = None
    raw: JsonDict = field(default_factory=dict)


class XhsProvider(Protocol):
    name: str

    def search_notes(
        self,
        keyword: str,
        *,
        cursor: str | None = None,
        limit: int = 20,
    ) -> ProviderSearchPage:
        """Search notes for a keyword."""

    def get_note_detail(self, note_id: str) -> ProviderNote:
        """Fetch one note by provider note id."""

    def get_note_comments(
        self,
        note_id: str,
        *,
        cursor: str | None = None,
        limit: int = 20,
    ) -> ProviderCommentPage:
        """Fetch public comments for a note."""

    def suggest_keywords(self, keyword: str, *, limit: int = 10) -> list[SuggestedKeyword]:
        """Return keyword suggestions related to a seed keyword."""
