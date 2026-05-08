"""Repository helpers for digest persistence."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from datetime import date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from xhs_digest.models import Comment, DailyTopic, DigestRun, Note, RawApiEvent, Tag
from xhs_digest.providers.base import ProviderComment, ProviderNote


JsonDict = dict[str, Any]


def _drop_none(values: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in values.items() if value is not None}


class DigestRepository:
    """Small persistence facade around a SQLAlchemy session."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self._tag_cache: dict[str, Tag] = {}

    def upsert_tag(self, name: str, *, category: str | None = None) -> Tag:
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("tag name cannot be empty")

        cached = self._tag_cache.get(clean_name)
        if cached is not None:
            if category is not None:
                cached.category = category
            return cached

        tag = self.session.scalar(select(Tag).where(Tag.name == clean_name))
        if tag is None:
            tag = Tag(name=clean_name, category=category)
            self.session.add(tag)
        elif category is not None:
            tag.category = category
        self._tag_cache[clean_name] = tag
        return tag

    def upsert_note(self, note: ProviderNote, *, tag_names: Sequence[str] = ()) -> Note:
        stored = self.session.scalar(
            select(Note).where(
                Note.provider == note.provider,
                Note.provider_note_id == note.note_id,
            )
        )
        values = _drop_none(
            {
                "url": note.url,
                "title": note.title,
                "description": note.description,
                "author_id": note.author_id,
                "author_name": note.author_name,
                "published_at": note.published_at,
                "liked_count": note.liked_count,
                "collected_count": note.collected_count,
                "commented_count": note.commented_count,
                "shared_count": note.shared_count,
                "raw": note.raw,
            }
        )
        if stored is None:
            stored = Note(provider=note.provider, provider_note_id=note.note_id, **values)
            self.session.add(stored)
        else:
            for key, value in values.items():
                setattr(stored, key, value)

        self._attach_tags(stored, [*note.tags, *tag_names])
        return stored

    def upsert_notes(self, notes: Iterable[ProviderNote], *, tag_names: Sequence[str] = ()) -> list[Note]:
        return [self.upsert_note(note, tag_names=tag_names) for note in notes]

    def upsert_comment(self, comment: ProviderComment, *, note: Note | None = None) -> Comment:
        if note is None:
            self.session.flush()
        stored_note = note or self.session.scalar(
            select(Note).where(
                Note.provider == comment.provider,
                Note.provider_note_id == comment.note_id,
            )
        )
        if stored_note is None:
            raise ValueError(f"note {comment.provider}:{comment.note_id} must exist before comments are stored")

        stored = self.session.scalar(
            select(Comment).where(
                Comment.provider == comment.provider,
                Comment.provider_comment_id == comment.comment_id,
            )
        )
        values = _drop_none(
            {
                "parent_comment_id": comment.parent_comment_id,
                "author_id": comment.author_id,
                "author_name": comment.author_name,
                "content": comment.content,
                "liked_count": comment.liked_count,
                "created_at": comment.created_at,
                "raw": comment.raw,
            }
        )
        if stored is None:
            stored = Comment(
                provider=comment.provider,
                provider_comment_id=comment.comment_id,
                **values,
            )
            stored.note = stored_note
            self.session.add(stored)
        else:
            stored.note = stored_note
            for key, value in values.items():
                setattr(stored, key, value)
        return stored

    def upsert_comments(self, comments: Iterable[ProviderComment]) -> list[Comment]:
        return [self.upsert_comment(comment) for comment in comments]

    def upsert_daily_topic(
        self,
        topic_date: date,
        keyword: str,
        *,
        provider: str | None = None,
        score: float | None = None,
        metadata: JsonDict | None = None,
    ) -> DailyTopic:
        clean_keyword = keyword.strip()
        if not clean_keyword:
            raise ValueError("topic keyword cannot be empty")

        topic = self.session.scalar(
            select(DailyTopic).where(
                DailyTopic.topic_date == topic_date,
                DailyTopic.keyword == clean_keyword,
            )
        )
        values = _drop_none({"provider": provider, "score": score, "metadata_": metadata})
        if topic is None:
            topic = DailyTopic(topic_date=topic_date, keyword=clean_keyword, **values)
            self.session.add(topic)
        else:
            for key, value in values.items():
                setattr(topic, key, value)
        return topic

    def create_digest_run(
        self,
        run_date: date,
        *,
        provider: str | None = None,
        metadata: JsonDict | None = None,
    ) -> DigestRun:
        run = DigestRun(run_date=run_date, provider=provider, metadata_=metadata or {})
        self.session.add(run)
        return run

    def finish_digest_run(
        self,
        run: DigestRun,
        *,
        status: str,
        notes_seen: int | None = None,
        comments_seen: int | None = None,
        error: str | None = None,
        finished_at: datetime | None = None,
    ) -> DigestRun:
        run.status = status
        run.finished_at = finished_at or datetime.now().astimezone()
        if notes_seen is not None:
            run.notes_seen = notes_seen
        if comments_seen is not None:
            run.comments_seen = comments_seen
        run.error = error
        return run

    def add_raw_api_event(
        self,
        *,
        provider: str,
        endpoint: str,
        request: JsonDict | None = None,
        response: JsonDict | list[Any] | None = None,
        status_code: int | None = None,
        error: str | None = None,
    ) -> RawApiEvent:
        event = RawApiEvent(
            provider=provider,
            endpoint=endpoint,
            request=request or {},
            response=response,
            status_code=status_code,
            error=error,
        )
        self.session.add(event)
        return event

    def _attach_tags(self, note: Note, tag_names: Sequence[str]) -> None:
        seen = {tag.name for tag in note.tags}
        for tag_name in tag_names:
            clean_name = tag_name.strip()
            if clean_name and clean_name not in seen:
                note.tags.append(self.upsert_tag(clean_name))
                seen.add(clean_name)
