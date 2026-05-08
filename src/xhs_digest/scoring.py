"""Deterministic note scoring for digest ranking."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from math import log1p
from typing import Any, Iterable, Mapping, Sequence


@dataclass(frozen=True, slots=True)
class ScoreBreakdown:
    """Score components for a note."""

    total: float
    engagement: float
    relevance: float
    freshness: float
    quality: float

    def __float__(self) -> float:
        return self.total

    def __lt__(self, other: object) -> bool:
        return self.total < _coerce_score(other)

    def __le__(self, other: object) -> bool:
        return self.total <= _coerce_score(other)

    def __gt__(self, other: object) -> bool:
        return self.total > _coerce_score(other)

    def __ge__(self, other: object) -> bool:
        return self.total >= _coerce_score(other)


REACTION_FIELDS = {
    "like_count": 1.0,
    "likes": 1.0,
    "liked_count": 1.0,
    "comment_count": 2.0,
    "comments": 2.0,
    "commented_count": 2.0,
    "collect_count": 1.8,
    "collects": 1.8,
    "collected_count": 1.8,
    "favorite_count": 1.8,
    "favorites": 1.8,
    "share_count": 2.4,
    "shares": 2.4,
    "shared_count": 2.4,
    "view_count": 0.2,
    "views": 0.2,
}


def score_note(
    note: Any,
    *,
    keywords: Sequence[str] | None = None,
    as_of: datetime | None = None,
) -> ScoreBreakdown:
    """Return a deterministic weighted score for one note.

    ``as_of`` is optional. When omitted, the score never depends on the
    current clock, which keeps ranking stable in tests and repeated runs.
    """

    engagement = _engagement_score(note)
    relevance = _relevance_score(note, keywords or ())
    freshness = _freshness_score(note, as_of)
    quality = _quality_score(note)
    total = round((engagement * 0.62) + (relevance * 0.2) + (freshness * 0.1) + (quality * 0.08), 6)
    return ScoreBreakdown(
        total=total,
        engagement=round(engagement, 6),
        relevance=round(relevance, 6),
        freshness=round(freshness, 6),
        quality=round(quality, 6),
    )


def rank_notes(
    notes: Iterable[Any],
    *,
    keywords: Sequence[str] | None = None,
    limit: int | None = None,
    as_of: datetime | None = None,
) -> list[dict[str, Any]]:
    """Return notes sorted by score descending with ``score`` metadata added."""

    ranked: list[dict[str, Any]] = []
    for note in notes:
        item = dict(note) if isinstance(note, Mapping) else {"note": note}
        breakdown = score_note(note, keywords=keywords, as_of=as_of)
        item["score"] = breakdown.total
        item["score_breakdown"] = {
            "engagement": breakdown.engagement,
            "relevance": breakdown.relevance,
            "freshness": breakdown.freshness,
            "quality": breakdown.quality,
        }
        ranked.append(item)

    ranked.sort(key=lambda item: (-float(item["score"]), _stable_id(item)))
    return ranked[:limit] if limit is not None else ranked


def _engagement_score(note: Any) -> float:
    total = 0.0
    seen_values: set[tuple[float, float]] = set()
    for field, weight in REACTION_FIELDS.items():
        value = max(_number(_get(note, field)), 0.0)
        marker = (value, weight)
        if value and marker not in seen_values:
            total += log1p(value) * weight
            seen_values.add(marker)
    heat = max(_number(_get(note, "heat")), _number(_get(note, "hot_score")), 0.0)
    if heat:
        total += log1p(heat) * 1.4
    return total


def _relevance_score(note: Any, keywords: Sequence[str]) -> float:
    if not keywords:
        return 0.0
    text = _search_text(note).lower()
    if not text:
        return 0.0
    matches = sum(1 for keyword in keywords if keyword and keyword.lower() in text)
    return min(10.0, matches * 2.5)


def _freshness_score(note: Any, as_of: datetime | None) -> float:
    if as_of is None:
        return 0.0
    created_at = _parse_datetime(_get(note, "created_at") or _get(note, "publish_time") or _get(note, "published_at"))
    if created_at is None:
        return 0.0
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    if as_of.tzinfo is None:
        as_of = as_of.replace(tzinfo=timezone.utc)
    age_hours = max((as_of - created_at).total_seconds() / 3600, 0.0)
    return max(0.0, 10.0 - min(age_hours / 4, 10.0))


def _quality_score(note: Any) -> float:
    title = str(_get(note, "title") or "")
    body = str(_get(note, "content") or _get(note, "desc") or _get(note, "description") or "")
    text_len = len((title + body).strip())
    image_count = max(_number(_get(note, "image_count")), len(_get(note, "images") or []))
    title_bonus = 2.0 if 6 <= len(title) <= 80 else 0.0
    body_bonus = min(4.0, text_len / 120)
    media_bonus = min(2.0, image_count * 0.5)
    return title_bonus + body_bonus + media_bonus


def _search_text(note: Any) -> str:
    pieces = [
        _get(note, "title"),
        _get(note, "content"),
        _get(note, "desc"),
        _get(note, "description"),
        " ".join(str(tag) for tag in (_get(note, "tags") or [])),
    ]
    return " ".join(str(piece) for piece in pieces if piece)


def _stable_id(note: Any) -> str:
    return str(_get(note, "id") or _get(note, "note_id") or _get(note, "url") or _get(note, "title") or "")


def _get(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, Mapping):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _number(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _parse_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if not value:
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(float(value), tz=timezone.utc)
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _coerce_score(value: object) -> float:
    if isinstance(value, ScoreBreakdown):
        return value.total
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0.0
