"""Shared models for the AI trend visualization API."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol

from pydantic import BaseModel, Field


JsonDict = dict[str, Any]


class EntityRule(BaseModel):
    """Configured AI entity and the keywords that map content to it."""

    id: str
    label: str
    galaxy: str
    galaxy_label: str
    keywords: list[str]
    color: str


class TrendMetric(BaseModel):
    """Normalized engagement metrics for one provider item."""

    likes: int = 0
    comments: int = 0
    saves: int = 0
    shares: int = 0
    views: int = 0
    stars: int = 0
    score: int = 0


class TrendItem(BaseModel):
    """Provider-neutral item consumed by the trend aggregation layer."""

    platform: str
    id: str
    entity: str
    title: str
    summary: str | None = None
    url: str | None = None
    author: str | None = None
    published_at: datetime | None = None
    metrics: TrendMetric = Field(default_factory=TrendMetric)
    tags: list[str] = Field(default_factory=list)
    sentiment: float = 0.0
    heat: float = 0.0
    raw: JsonDict = Field(default_factory=dict)


class TrendPoint(BaseModel):
    label: str
    value: float


class ProviderStatus(BaseModel):
    platform: str
    label: str
    enabled: bool = False
    refresh_minutes: int = 30
    last_success_at: datetime | None = None
    last_error: str | None = None
    notes: str | None = None


class GalaxyInfo(BaseModel):
    id: str
    label: str
    description: str
    color: str


class TrendNode(BaseModel):
    entity: str
    label: str
    galaxy: str
    galaxy_label: str
    color: str
    heat: float
    growth: float
    sentiment: float
    item_count: int
    platform_distribution: dict[str, int]
    heat_breakdown: dict[str, float]
    trend: list[TrendPoint]
    top_items: list[TrendItem]
    summary: str


class TrendSnapshot(BaseModel):
    generated_at: datetime
    window: str
    refresh_minutes: int
    galaxies: list[GalaxyInfo]
    nodes: list[TrendNode]
    providers: list[ProviderStatus]


class TrendProvider(Protocol):
    """Provider-neutral source contract for public trend items."""

    name: str
    label: str

    def fetch_items(self, keyword: str, *, limit: int = 20, window_hours: int = 24) -> list[TrendItem]:
        """Fetch public items related to a keyword."""

    def status(self) -> ProviderStatus:
        """Return the provider configuration and health status."""
