from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Iterable
from zoneinfo import ZoneInfo

from .config import EnvSettings, RuntimeConfig, TagRule

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class DigestResult:
    run_id: int | None
    subject: str
    html: str
    note_count: int
    topic_count: int
    hot_note_count: int
    sent: bool


def parse_digest_date(value: str | None, timezone: str = "Asia/Shanghai") -> date:
    if value in (None, "", "today"):
        return datetime.now(ZoneInfo(timezone)).date()
    if value == "yesterday":
        return datetime.now(ZoneInfo(timezone)).date() - timedelta(days=1)
    return date.fromisoformat(value)


def _build_provider(env: EnvSettings, runtime: RuntimeConfig):
    from .providers.justone import JustOneProvider

    if env.xhs_provider != "justone":
        raise ValueError(f"Unsupported provider: {env.xhs_provider}")
    env.require_provider_credentials()
    return JustOneProvider(
        api_token=env.xhs_api_token or "",
        base_url=env.xhs_api_base_url,
        timeout_seconds=runtime.provider.timeout_seconds,
        max_retries=runtime.provider.max_retries,
    )


def _contains_excluded_text(text: str, excluded: Iterable[str]) -> bool:
    lowered = text.lower()
    return any(word.lower() in lowered for word in excluded)


def run_daily_digest(
    *,
    target_date: date,
    env: EnvSettings,
    runtime: RuntimeConfig,
    tags: list[TagRule],
    dry_run: bool = False,
) -> DigestResult:
    from .cluster import cluster_notes_by_tag
    from .database import create_engine_and_session, create_tables
    from .mailer import SmtpMailer
    from .renderer import render_digest_email
    from .repository import DigestRepository
    from .scoring import score_note
    from .summarizer import summarize_digest
    from .providers.base import ProviderError

    engine, session_factory = create_engine_and_session(env.database_url)
    create_tables(engine)
    provider = _build_provider(env, runtime)

    with session_factory() as session:
        repo = DigestRepository(session)
        run = repo.create_digest_run(run_date=target_date, provider=env.xhs_provider, metadata={"dry_run": dry_run})
        session.flush()
        run_id = getattr(run, "id", None)
        digest_notes: list[dict[str, object]] = []
        stored_by_external_id = {}
        comments_seen = 0

        try:
            for tag in tags:
                seen_external_ids: set[str] = set()
                per_tag_limit = max(1, tag.daily_limit or runtime.digest.default_notes_per_tag)
                for term in tag.search_terms:
                    try:
                        page = provider.search_notes(keyword=term, limit=per_tag_limit)
                    except ProviderError as exc:
                        logger.warning("Skipping keyword %s for tag %s: %s", term, tag.name, exc)
                        repo.add_raw_api_event(
                            provider=env.xhs_provider,
                            endpoint="search_notes",
                            request={"keyword": term, "limit": per_tag_limit},
                            error=str(exc),
                        )
                        continue
                    repo.add_raw_api_event(
                        provider=env.xhs_provider,
                        endpoint="search_notes",
                        request={"keyword": term, "limit": per_tag_limit},
                        response={"count": len(page.notes), "has_more": page.has_more, "next_cursor": page.next_cursor},
                    )
                    for note in page.notes:
                        searchable = " ".join([note.title or "", note.description or "", note.author_name or ""])
                        if _contains_excluded_text(searchable, tag.exclude_keywords):
                            continue
                        score = score_note(note, keywords=tag.search_terms, as_of=datetime.combine(target_date, time.max))
                        heat_score = float(score)
                        if heat_score < tag.min_heat:
                            continue
                        external_id = note.note_id or note.url or note.title or ""
                        if external_id in seen_external_ids:
                            continue
                        seen_external_ids.add(external_id)
                        stored_note = repo.upsert_note(note, tag_names=[tag.name])
                        stored_by_external_id[external_id] = stored_note
                        digest_notes.append(
                            {
                                "id": stored_note.id,
                                "note_id": note.note_id,
                                "provider": note.provider,
                                "title": note.title,
                                "description": note.description,
                                "content": note.description,
                                "url": note.url,
                                "author_name": note.author_name,
                                "published_at": note.published_at.isoformat() if note.published_at else None,
                                "liked_count": note.liked_count or 0,
                                "collected_count": note.collected_count or 0,
                                "commented_count": note.commented_count or 0,
                                "shared_count": note.shared_count or 0,
                                "tag_name": tag.name,
                                "keyword": term,
                                "score": heat_score,
                                "score_breakdown": {
                                    "engagement": score.engagement,
                                    "relevance": score.relevance,
                                    "freshness": score.freshness,
                                    "quality": score.quality,
                                },
                            }
                        )

                top_notes = sorted(
                    [note for note in digest_notes if note.get("tag_name") == tag.name],
                    key=lambda item: float(item.get("score") or 0),
                    reverse=True,
                )[: runtime.digest.top_notes_for_comments]
                for note_data in top_notes:
                    external_id = str(note_data.get("note_id") or "")
                    if not external_id:
                        continue
                    try:
                        comment_page = provider.get_note_comments(external_id, limit=runtime.digest.comments_per_note)
                    except ProviderError as exc:
                        logger.warning("Skipping comments for note %s: %s", external_id, exc)
                        repo.add_raw_api_event(
                            provider=env.xhs_provider,
                            endpoint="note_comments",
                            request={"note_id": external_id, "limit": runtime.digest.comments_per_note},
                            error=str(exc),
                        )
                        continue
                    repo.add_raw_api_event(
                        provider=env.xhs_provider,
                        endpoint="note_comments",
                        request={"note_id": external_id, "limit": runtime.digest.comments_per_note},
                        response={"count": len(comment_page.comments), "has_more": comment_page.has_more},
                    )
                    stored_note = stored_by_external_id.get(external_id)
                    for comment in comment_page.comments:
                        repo.upsert_comment(comment, note=stored_note)
                        comments_seen += 1

            topics = cluster_notes_by_tag(digest_notes, top_topics_per_tag=runtime.digest.top_topics_per_tag)
            hot_notes = sorted(
                digest_notes,
                key=lambda item: float(item.get("score") or 0),
                reverse=True,
            )[: max(0, runtime.digest.hot_posts_count)]
            summary = summarize_digest(
                topics=topics,
                notes=digest_notes,
                openai_api_key=env.openai_api_key,
                openai_base_url=env.openai_base_url,
                model=env.openai_model,
            )
            for topic in topics:
                repo.upsert_daily_topic(
                    topic_date=target_date,
                    keyword=topic.topic,
                    provider=env.xhs_provider,
                    score=topic.score,
                    metadata={
                        "keywords": topic.keywords,
                        "summary": topic.summary,
                        "note_count": len(topic.notes),
                    },
                )

            subject = runtime.digest.subject_template.format(date=target_date.isoformat())
            html = render_digest_email(
                target_date=target_date,
                subject=subject,
                summary=summary,
                topics=topics,
                hot_notes=hot_notes,
                notes=digest_notes,
            )

            sent = False
            if not dry_run:
                env.require_smtp_credentials()
                mailer = SmtpMailer.from_env(env)
                mailer.send_html(subject=subject, html=html, recipients=env.recipients)
                sent = True

            repo.finish_digest_run(run, status="sent" if sent else "generated", notes_seen=len(digest_notes), comments_seen=comments_seen)
            session.commit()
            return DigestResult(
                run_id=run_id,
                subject=subject,
                html=html,
                note_count=len(digest_notes),
                topic_count=len(topics),
                hot_note_count=len(hot_notes),
                sent=sent,
            )
        except Exception as exc:
            logger.exception("Daily digest failed")
            repo.finish_digest_run(run, status="failed", error=str(exc), notes_seen=len(digest_notes), comments_seen=comments_seen)
            session.commit()
            raise
