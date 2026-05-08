"""Just One API provider client."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import re
from time import sleep
from typing import Any

import httpx
from dateutil import parser as date_parser

from xhs_digest.providers.base import (
    ProviderComment,
    ProviderCommentPage,
    ProviderError,
    ProviderNote,
    ProviderRequestError,
    ProviderRetryableError,
    ProviderSearchPage,
    SuggestedKeyword,
)


JsonDict = dict[str, Any]


class JustOneClient:
    """Thin, retry-friendly httpx client for the Just One API."""

    name = "justone"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        api_token: str | None = None,
        base_url: str = "https://api.justoneapi.com",
        timeout_seconds: float | None = None,
        timeout: float | httpx.Timeout = 15.0,
        max_retries: int = 2,
        client: httpx.Client | None = None,
    ) -> None:
        self.api_key = api_key or api_token or ""
        self.base_url = base_url.rstrip("/")
        self.max_retries = max(0, max_retries)
        self._owns_client = client is None
        self._client = client or httpx.Client(base_url=self.base_url, timeout=timeout_seconds or timeout)

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> "JustOneClient":
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def search_notes(
        self,
        keyword: str,
        *,
        cursor: str | None = None,
        limit: int = 20,
    ) -> ProviderSearchPage:
        payload = {
            "token": self.api_key,
            "keyword": keyword,
            "page": int(cursor or 1),
            "sort": "popularity_descending",
            "noteType": "_0",
        }
        data = self._request_json("GET", "/api/xiaohongshu/search-note/v2", params=_drop_none(payload))
        items = _pick_list(data, "notes", "items", "list", "data")
        return ProviderSearchPage(
            notes=_map_notes(items, provider=self.name, limit=limit),
            next_cursor=_pick_str(data, "next_cursor", "nextCursor", "lastCursor", "cursor", "next"),
            has_more=bool(_pick(data, "has_more", "hasMore", "has_next", "hasNext") or False),
            raw=data,
        )

    def get_note_detail(self, note_id: str) -> ProviderNote:
        data = self._request_json(
            "GET",
            "/api/xiaohongshu/get-note-detail/v2",
            params={"token": self.api_key, "noteId": note_id},
        )
        item = _pick_mapping(data, "note", "item", "data") or data
        return _map_note(item, provider=self.name, fallback_note_id=note_id)

    def get_note_comments(
        self,
        note_id: str,
        *,
        cursor: str | None = None,
        limit: int = 20,
    ) -> ProviderCommentPage:
        payload = {"token": self.api_key, "noteId": note_id, "lastCursor": cursor, "sort": "latest"}
        data = self._request_json("GET", "/api/xiaohongshu/get-note-comment/v2", params=_drop_none(payload))
        items = _pick_list(data, "comments", "items", "list", "data")
        return ProviderCommentPage(
            comments=[
                _map_comment(item, provider=self.name, fallback_note_id=note_id)
                for item in items
                if isinstance(item, Mapping)
            ],
            next_cursor=_pick_str(data, "next_cursor", "nextCursor", "lastCursor", "cursor", "next"),
            has_more=bool(_pick(data, "has_more", "hasMore", "has_next", "hasNext") or False),
            raw=data,
        )

    def suggest_keywords(self, keyword: str, *, limit: int = 10) -> list[SuggestedKeyword]:
        payload = {"token": self.api_key, "keyword": keyword}
        data = self._request_json("GET", "/api/xiaohongshu/search-recommend/v1", params=payload)
        items = _pick_list(data, "keywords", "suggestions", "items", "list", "data")
        suggestions: list[SuggestedKeyword] = []
        for item in items:
            if isinstance(item, str):
                suggestions.append(SuggestedKeyword(keyword=item))
            elif isinstance(item, Mapping):
                value = _pick_str(item, "keyword", "word", "name", "query", "text")
                if value:
                    suggestions.append(
                        SuggestedKeyword(
                            keyword=value,
                            score=_to_float(_pick(item, "score", "heat", "rank", "weight")),
                            raw=dict(item),
                        )
                    )
        return suggestions

    def _request_json(self, method: str, path: str, **kwargs: Any) -> JsonDict:
        headers = kwargs.pop("headers", {})
        headers = {"Authorization": f"Bearer {self.api_key}", **headers}

        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                response = self._client.request(method, path, headers=headers, **kwargs)
                if response.status_code in {408, 409, 425, 429} or response.status_code >= 500:
                    raise ProviderRetryableError(_response_message(response))
                if response.status_code >= 400:
                    raise ProviderRequestError(_response_message(response))
                data = response.json()
                if not isinstance(data, dict):
                    raise ProviderRequestError("Just One API returned a non-object JSON response")
                code = data.get("code")
                if code not in (None, 0, "0"):
                    message = data.get("message") or data.get("msg") or f"business code {code}"
                    if code in (301, 302, 303, 500, "301", "302", "303", "500"):
                        raise ProviderRetryableError(str(message))
                    raise ProviderRequestError(str(message))
                return data
            except ProviderRequestError:
                raise
            except (httpx.TimeoutException, httpx.TransportError, ProviderRetryableError) as exc:
                last_error = exc
                if attempt >= self.max_retries:
                    raise ProviderRetryableError(str(exc)) from exc
                sleep(min(2**attempt, 8))
            except ValueError as exc:
                raise ProviderRequestError("Just One API returned invalid JSON") from exc

        raise ProviderError(str(last_error) if last_error else "Just One API request failed")


def _drop_none(values: Mapping[str, Any]) -> JsonDict:
    return {key: value for key, value in values.items() if value is not None}


def _response_message(response: httpx.Response) -> str:
    retry_after = response.headers.get("retry-after")
    retry_note = ""
    if retry_after:
        retry_note = f"; retry after {_format_retry_after(retry_after)}"
    safe_url = re.sub(r"([?&]token=)[^&]+", r"\1***redacted***", str(response.request.url))
    return f"Just One API {response.status_code} for {response.request.method} {safe_url}{retry_note}"


def _format_retry_after(value: str) -> str:
    try:
        return parsedate_to_datetime(value).isoformat()
    except (TypeError, ValueError):
        return value


def _pick(data: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in data and data[key] not in ("", None):
            return data[key]
    return None


def _pick_mapping(data: Mapping[str, Any], *keys: str) -> Mapping[str, Any] | None:
    value = _pick(data, *keys)
    return value if isinstance(value, Mapping) else None


def _pick_list(data: Mapping[str, Any], *keys: str) -> list[Any]:
    value = _pick(data, *keys)
    if isinstance(value, list):
        return value
    if isinstance(value, Mapping):
        nested = _pick(value, "items", "list", "records", "notes", "comments")
        if isinstance(nested, list):
            return nested
    return []


def _pick_str(data: Mapping[str, Any], *keys: str) -> str | None:
    value = _pick(data, *keys)
    if value is None:
        return None
    return str(value)


def _map_note(item: Mapping[str, Any], *, provider: str, fallback_note_id: str | None = None) -> ProviderNote:
    nested_note = _pick_mapping(item, "note", "note_card", "noteCard", "note_info", "noteInfo")
    if nested_note is not None:
        item = nested_note

    author = _pick_mapping(item, "author", "user", "user_info", "userInfo") or {}
    metrics = _pick_mapping(item, "metrics", "stats", "statistics", "interact_info", "interactInfo") or {}
    raw = dict(item)
    note_id = _pick_str(item, "note_id", "noteId", "id", "noteIdStr", "xsec_token") or fallback_note_id
    if not note_id:
        raise ProviderRequestError("Just One note item did not include a usable note id")

    return ProviderNote(
        provider=provider,
        note_id=note_id,
        title=_pick_str(item, "title", "display_title", "displayTitle", "name"),
        description=_pick_str(item, "description", "desc", "content", "text"),
        url=_pick_str(item, "url", "share_url", "shareUrl", "link"),
        author_id=_pick_str(author, "id", "user_id", "userId", "uid") or _pick_str(item, "author_id", "authorId", "user_id"),
        author_name=_pick_str(author, "name", "nickname", "nick_name", "username")
        or _pick_str(item, "author_name", "authorName", "nickname"),
        published_at=_parse_datetime(_pick(item, "published_at", "publishTime", "publish_time", "created_at", "time")),
        liked_count=_to_int(_pick(metrics, "liked_count", "likedCount", "likes", "like_count", "likeCount") or _pick(item, "liked_count", "likedCount")),
        collected_count=_to_int(_pick(metrics, "collected_count", "collectedCount", "collects", "collect_count", "collectCount") or _pick(item, "collected_count", "collectedCount")),
        commented_count=_to_int(_pick(metrics, "commented_count", "commentedCount", "comments", "comment_count", "commentCount", "comments_count", "commentsCount") or _pick(item, "commented_count", "commentedCount", "comment_count", "commentCount", "comments", "comments_count", "commentsCount")),
        shared_count=_to_int(_pick(metrics, "shared_count", "sharedCount", "shares", "share_count", "shareCount") or _pick(item, "shared_count", "sharedCount", "share_count", "shareCount", "shares")),
        tags=_map_tags(item),
        raw=raw,
    )


def _map_notes(items: list[Any], *, provider: str, limit: int | None = None) -> list[ProviderNote]:
    notes: list[ProviderNote] = []
    for item in items:
        if not isinstance(item, Mapping):
            continue
        try:
            notes.append(_map_note(item, provider=provider))
        except ProviderRequestError:
            continue
        if limit is not None and len(notes) >= limit:
            break
    return notes


def _map_comment(item: Mapping[str, Any], *, provider: str, fallback_note_id: str) -> ProviderComment:
    author = _pick_mapping(item, "author", "user", "user_info", "userInfo") or {}
    comment_id = _pick_str(item, "comment_id", "commentId", "id")
    if not comment_id:
        raise ProviderRequestError("Just One comment item did not include a usable comment id")

    return ProviderComment(
        provider=provider,
        comment_id=comment_id,
        note_id=_pick_str(item, "note_id", "noteId", "target_id", "targetId") or fallback_note_id,
        parent_comment_id=_pick_str(item, "parent_comment_id", "parentCommentId", "parent_id", "parentId"),
        author_id=_pick_str(author, "id", "user_id", "userId", "uid") or _pick_str(item, "author_id", "authorId", "user_id"),
        author_name=_pick_str(author, "name", "nickname", "nick_name", "username")
        or _pick_str(item, "author_name", "authorName", "nickname"),
        content=_pick_str(item, "content", "text", "desc"),
        liked_count=_to_int(_pick(item, "liked_count", "likedCount", "likes", "like_count", "likeCount")),
        created_at=_parse_datetime(_pick(item, "created_at", "createTime", "create_time", "time")),
        raw=dict(item),
    )


def _map_tags(item: Mapping[str, Any]) -> list[str]:
    tags = _pick(item, "tags", "tag_list", "tagList", "hashtags", "topics")
    if isinstance(tags, str):
        return [tags]
    if not isinstance(tags, list):
        return []
    values: list[str] = []
    for tag in tags:
        if isinstance(tag, str):
            values.append(tag)
        elif isinstance(tag, Mapping):
            value = _pick_str(tag, "name", "tag", "keyword", "title")
            if value:
                values.append(value)
    return values


def _parse_datetime(value: Any) -> datetime | None:
    if value in ("", None):
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, (int, float)):
        seconds = value / 1000 if value > 10_000_000_000 else value
        return datetime.fromtimestamp(seconds, tz=timezone.utc)
    if isinstance(value, str):
        try:
            parsed = date_parser.parse(value)
        except (TypeError, ValueError, OverflowError):
            return None
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed
    return None


def _to_int(value: Any) -> int | None:
    if value in ("", None):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _to_float(value: Any) -> float | None:
    if value in ("", None):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def normalize_search_response(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Normalize a Just One search payload into simple public note dictionaries."""

    items = _pick_list(payload, "notes", "items", "list", "data")
    notes = _map_notes(items, provider="justone")
    return [
        {
            "id": note.note_id,
            "note_id": note.note_id,
            "title": note.title,
            "description": note.description,
            "url": note.url,
            "author_name": note.author_name,
            "liked_count": note.liked_count,
            "collected_count": note.collected_count,
            "commented_count": note.commented_count,
            "shared_count": note.shared_count,
            "published_at": note.published_at.isoformat() if note.published_at else None,
        }
        for note in notes
    ]


parse_search_response = normalize_search_response
map_search_response = normalize_search_response
JustOneProvider = JustOneClient
