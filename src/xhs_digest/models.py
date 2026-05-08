"""SQLAlchemy models for the digest storage layer."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import Date, DateTime, ForeignKey, Index, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import JSON


JsonDict = dict[str, Any]


class Base(DeclarativeBase):
    """Base class for all ORM models."""


def json_column() -> type[JSON]:
    """Use JSONB on Postgres and regular JSON elsewhere."""

    return JSON().with_variant(JSONB, "postgresql")


class NoteTag(Base):
    """Association table for notes and normalized topic tags."""

    __tablename__ = "note_tags"
    __table_args__ = (
        UniqueConstraint("note_id", "tag_id", name="uq_note_tags_note_id_tag_id"),
    )

    note_id: Mapped[int] = mapped_column(ForeignKey("notes.id", ondelete="CASCADE"), primary_key=True)
    tag_id: Mapped[int] = mapped_column(ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Note(Base):
    """A Xiaohongshu note returned by a provider."""

    __tablename__ = "notes"
    __table_args__ = (
        UniqueConstraint("provider", "provider_note_id", name="uq_notes_provider_provider_note_id"),
        Index("ix_notes_provider_published_at", "provider", "published_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_note_id: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str | None] = mapped_column(Text)
    title: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    author_id: Mapped[str | None] = mapped_column(String(255))
    author_name: Mapped[str | None] = mapped_column(String(255))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    liked_count: Mapped[int | None]
    collected_count: Mapped[int | None]
    commented_count: Mapped[int | None]
    shared_count: Mapped[int | None]
    raw: Mapped[JsonDict] = mapped_column(json_column(), default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    comments: Mapped[list["Comment"]] = relationship(
        back_populates="note",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    tags: Mapped[list["Tag"]] = relationship(
        secondary="note_tags",
        back_populates="notes",
    )


class Comment(Base):
    """A public comment attached to a note."""

    __tablename__ = "comments"
    __table_args__ = (
        UniqueConstraint("provider", "provider_comment_id", name="uq_comments_provider_provider_comment_id"),
        Index("ix_comments_note_id_created_at", "note_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    note_id: Mapped[int] = mapped_column(ForeignKey("notes.id", ondelete="CASCADE"), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_comment_id: Mapped[str] = mapped_column(String(255), nullable=False)
    parent_comment_id: Mapped[str | None] = mapped_column(String(255))
    author_id: Mapped[str | None] = mapped_column(String(255))
    author_name: Mapped[str | None] = mapped_column(String(255))
    content: Mapped[str | None] = mapped_column(Text)
    liked_count: Mapped[int | None]
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    raw: Mapped[JsonDict] = mapped_column(json_column(), default=dict)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    note: Mapped[Note] = relationship(back_populates="comments")


class Tag(Base):
    """A configured or provider-suggested topic tag."""

    __tablename__ = "tags"
    __table_args__ = (UniqueConstraint("name", name="uq_tags_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    category: Mapped[str | None] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    notes: Mapped[list[Note]] = relationship(
        secondary="note_tags",
        back_populates="tags",
    )


class DailyTopic(Base):
    """A daily keyword/topic tracked for digest generation."""

    __tablename__ = "daily_topics"
    __table_args__ = (
        UniqueConstraint("topic_date", "keyword", name="uq_daily_topics_topic_date_keyword"),
        Index("ix_daily_topics_topic_date", "topic_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    topic_date: Mapped[date] = mapped_column(Date, nullable=False)
    keyword: Mapped[str] = mapped_column(String(255), nullable=False)
    provider: Mapped[str | None] = mapped_column(String(64))
    score: Mapped[float | None]
    metadata_: Mapped[JsonDict] = mapped_column("metadata", json_column(), default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class DigestRun(Base):
    """One digest orchestration run."""

    __tablename__ = "digest_runs"
    __table_args__ = (Index("ix_digest_runs_run_date_started_at", "run_date", "started_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    run_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="started")
    provider: Mapped[str | None] = mapped_column(String(64))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes_seen: Mapped[int] = mapped_column(default=0)
    comments_seen: Mapped[int] = mapped_column(default=0)
    error: Mapped[str | None] = mapped_column(Text)
    metadata_: Mapped[JsonDict] = mapped_column("metadata", json_column(), default=dict)


class RawApiEvent(Base):
    """A raw provider request/response event for traceability."""

    __tablename__ = "raw_api_events"
    __table_args__ = (
        Index("ix_raw_api_events_provider_endpoint_created_at", "provider", "endpoint", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    endpoint: Mapped[str] = mapped_column(String(255), nullable=False)
    request: Mapped[JsonDict] = mapped_column(json_column(), default=dict)
    response: Mapped[JsonDict | list[Any] | None] = mapped_column(json_column())
    status_code: Mapped[int | None]
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
