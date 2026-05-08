"""Provider registry and public trend source clients."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Callable

import httpx

from xhs_digest.trend_models import ProviderStatus, TrendItem, TrendMetric, TrendProvider
from xhs_digest.trend_service import match_entity_from_text


ProviderFactory = Callable[[], TrendProvider]


class TrendProviderRegistry:
    """Small registry that keeps platform integrations behind one boundary."""

    def __init__(self) -> None:
        self._factories: dict[str, ProviderFactory] = {}

    def register(self, name: str, factory: ProviderFactory) -> None:
        self._factories[name] = factory

    def create(self, name: str) -> TrendProvider:
        if name not in self._factories:
            raise KeyError(f"Unknown trend provider: {name}")
        return self._factories[name]()

    def providers(self) -> list[TrendProvider]:
        return [factory() for factory in self._factories.values()]

    def statuses(self) -> list[ProviderStatus]:
        return [provider.status() for provider in self.providers()]


class HackerNewsTrendProvider:
    """Hacker News public Firebase API source."""

    name = "hackernews"
    label = "Hacker News"

    def __init__(self, *, client: httpx.Client | None = None, timeout: float = 12.0) -> None:
        self._owns_client = client is None
        self._client = client or httpx.Client(base_url="https://hacker-news.firebaseio.com/v0", timeout=timeout)
        self._last_error: str | None = None
        self._last_success_at: datetime | None = None

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def fetch_items(self, keyword: str, *, limit: int = 20, window_hours: int = 24) -> list[TrendItem]:
        try:
            story_ids = self._client.get("/topstories.json").raise_for_status().json()
            items: list[TrendItem] = []
            for story_id in story_ids[: max(limit * 8, 40)]:
                payload = self._client.get(f"/item/{story_id}.json").raise_for_status().json()
                title = str(payload.get("title") or "")
                entity = match_entity_from_text(f"{keyword} {title}") or match_entity_from_text(title)
                if not entity:
                    continue
                if keyword.lower() not in title.lower() and entity != keyword.strip().lower():
                    continue
                published_at = datetime.fromtimestamp(int(payload.get("time") or 0), tz=UTC)
                items.append(
                    TrendItem(
                        platform=self.name,
                        id=str(payload.get("id") or story_id),
                        entity=entity,
                        title=title or "Untitled Hacker News story",
                        summary=payload.get("text"),
                        url=payload.get("url") or f"https://news.ycombinator.com/item?id={story_id}",
                        author=payload.get("by"),
                        published_at=published_at,
                        metrics=TrendMetric(score=int(payload.get("score") or 0), comments=int(payload.get("descendants") or 0)),
                        tags=[keyword, "Hacker News"],
                        raw={"type": payload.get("type")},
                    )
                )
                if len(items) >= limit:
                    break
            self._last_success_at = datetime.now(UTC)
            self._last_error = None
            return items
        except Exception as exc:
            self._last_error = str(exc)
            raise

    def status(self) -> ProviderStatus:
        return ProviderStatus(
            platform=self.name,
            label=self.label,
            enabled=True,
            last_success_at=self._last_success_at,
            last_error=self._last_error,
            notes="Public Firebase API, no credentials required.",
        )


class GitHubTrendProvider:
    """GitHub repository search source."""

    name = "github"
    label = "GitHub"

    def __init__(
        self,
        *,
        token: str | None = None,
        client: httpx.Client | None = None,
        timeout: float = 12.0,
    ) -> None:
        headers = {"Accept": "application/vnd.github+json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        self._owns_client = client is None
        self._client = client or httpx.Client(base_url="https://api.github.com", headers=headers, timeout=timeout)
        self._last_error: str | None = None
        self._last_success_at: datetime | None = None

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def fetch_items(self, keyword: str, *, limit: int = 20, window_hours: int = 24) -> list[TrendItem]:
        try:
            response = self._client.get(
                "/search/repositories",
                params={
                    "q": f"{keyword} AI in:name,description",
                    "sort": "updated",
                    "order": "desc",
                    "per_page": min(limit, 50),
                },
            )
            response.raise_for_status()
            items: list[TrendItem] = []
            for repo in response.json().get("items", []):
                text = " ".join([keyword, str(repo.get("name") or ""), str(repo.get("description") or "")])
                entity = match_entity_from_text(text)
                if not entity:
                    continue
                published_at = _parse_datetime(repo.get("pushed_at") or repo.get("updated_at") or repo.get("created_at"))
                items.append(
                    TrendItem(
                        platform=self.name,
                        id=str(repo.get("id") or repo.get("full_name")),
                        entity=entity,
                        title=str(repo.get("full_name") or repo.get("name") or "GitHub repository"),
                        summary=repo.get("description"),
                        url=repo.get("html_url"),
                        author=(repo.get("owner") or {}).get("login"),
                        published_at=published_at,
                        metrics=TrendMetric(
                            stars=int(repo.get("stargazers_count") or 0),
                            score=int(repo.get("forks_count") or 0),
                        ),
                        tags=[keyword, "GitHub"],
                        raw={"language": repo.get("language")},
                    )
                )
            self._last_success_at = datetime.now(UTC)
            self._last_error = None
            return items
        except Exception as exc:
            self._last_error = str(exc)
            raise

    def status(self) -> ProviderStatus:
        return ProviderStatus(
            platform=self.name,
            label=self.label,
            enabled=True,
            last_success_at=self._last_success_at,
            last_error=self._last_error,
            notes="Public repository search; token optional for higher rate limits.",
        )


class ReservedTrendProvider:
    """Provider slot reserved for sources that need credentials or compliance review."""

    def __init__(self, *, name: str, label: str, notes: str) -> None:
        self.name = name
        self.label = label
        self._notes = notes

    def fetch_items(self, keyword: str, *, limit: int = 20, window_hours: int = 24) -> list[TrendItem]:
        return []

    def status(self) -> ProviderStatus:
        return ProviderStatus(platform=self.name, label=self.label, enabled=False, notes=self._notes)


def build_default_trend_registry(*, github_token: str | None = None) -> TrendProviderRegistry:
    registry = TrendProviderRegistry()
    registry.register("hackernews", lambda: HackerNewsTrendProvider())
    registry.register("github", lambda: GitHubTrendProvider(token=github_token))
    registry.register(
        "producthunt",
        lambda: ReservedTrendProvider(
            name="producthunt",
            label="Product Hunt",
            notes="Requires Product Hunt API token before live collection.",
        ),
    )
    registry.register(
        "reddit",
        lambda: ReservedTrendProvider(
            name="reddit",
            label="Reddit",
            notes="Requires OAuth credentials for compliant live collection.",
        ),
    )
    registry.register(
        "weibo",
        lambda: ReservedTrendProvider(
            name="weibo",
            label="Weibo",
            notes="Reserved for a compliant third-party provider.",
        ),
    )
    registry.register(
        "x",
        lambda: ReservedTrendProvider(
            name="x",
            label="X",
            notes="Requires official X API access.",
        ),
    )
    return registry


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
