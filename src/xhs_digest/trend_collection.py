"""Collection helpers for provider-neutral AI trend signals."""

from __future__ import annotations

from datetime import datetime

from xhs_digest.database import create_engine_and_session, create_tables
from xhs_digest.providers.trend_sources import TrendProviderRegistry, build_default_trend_registry
from xhs_digest.providers.base import ProviderNote
from xhs_digest.repository import DigestRepository
from xhs_digest.trend_models import TrendItem
from xhs_digest.trend_service import AI_ENTITIES


def collect_trend_signals(
    *,
    database_url: str,
    registry: TrendProviderRegistry | None = None,
    limit_per_entity: int = 10,
    window_hours: int = 24,
) -> int:
    """Fetch public trend items from enabled providers and persist them as notes."""

    registry = registry or build_default_trend_registry()
    providers = [provider for provider in registry.providers() if provider.status().enabled]
    engine, session_factory = create_engine_and_session(database_url)
    create_tables(engine)
    stored_count = 0

    with session_factory() as session:
        repo = DigestRepository(session)
        for provider in providers:
            for entity in AI_ENTITIES:
                items = provider.fetch_items(entity.label, limit=limit_per_entity, window_hours=window_hours)
                for item in items:
                    repo.upsert_note(_trend_item_to_provider_note(item), tag_names=[entity.label, entity.galaxy_label])
                    stored_count += 1
        session.commit()
    return stored_count


def _trend_item_to_provider_note(item: TrendItem) -> ProviderNote:
    metrics = item.metrics
    raw = dict(item.raw)
    raw.update(
        {
            "trend_entity": item.entity,
            "trend_sentiment": item.sentiment,
            "trend_heat": item.heat,
        }
    )
    return ProviderNote(
        provider=item.platform,
        note_id=item.id,
        title=item.title,
        description=item.summary,
        url=item.url,
        author_name=item.author,
        published_at=item.published_at or datetime.now().astimezone(),
        liked_count=metrics.likes or metrics.stars or metrics.score,
        collected_count=metrics.saves,
        commented_count=metrics.comments,
        shared_count=metrics.shares,
        tags=item.tags,
        raw=raw,
    )
