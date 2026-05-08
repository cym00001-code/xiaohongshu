"""Topic summarization with an OpenAI-compatible optional backend."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Protocol

from .cluster import TopicCluster


class ChatClient(Protocol):
    """Minimal protocol implemented by OpenAI-compatible clients."""

    chat: Any


@dataclass(frozen=True, slots=True)
class SummaryConfig:
    """Configuration for optional model-backed summarization."""

    model: str = "gpt-4o-mini"
    base_url: str | None = None
    api_key: str | None = None
    timeout_seconds: float = 20.0


def summarize_clusters(
    clusters: Iterable[TopicCluster],
    *,
    config: SummaryConfig | None = None,
    client: ChatClient | None = None,
) -> list[TopicCluster]:
    """Attach summaries to clusters and return them."""

    config = config or SummaryConfig()
    llm_client = client or _build_client(config)
    summarized: list[TopicCluster] = []
    for cluster in clusters:
        cluster.summary = summarize_cluster(cluster, config=config, client=llm_client)
        summarized.append(cluster)
    return summarized


def summarize_digest(
    *,
    topics: Iterable[TopicCluster],
    notes: Iterable[Any],
    openai_api_key: str | None = None,
    openai_base_url: str | None = None,
    model: str = "gpt-4o-mini",
) -> str:
    """Summarize the overall digest and attach per-topic summaries."""

    topic_list = list(topics)
    note_list = list(notes)
    config = SummaryConfig(model=model, base_url=openai_base_url, api_key=openai_api_key)
    summarize_clusters(topic_list, config=config)
    if not topic_list:
        return "今天没有抓取到满足筛选条件的热点。"
    top_topics = "、".join(cluster.topic for cluster in topic_list[:5])
    return f"今日共识别 {len(topic_list)} 个讨论风向，覆盖 {len(note_list)} 条代表笔记。重点关注：{top_topics}。"


def summarize_cluster(
    cluster: TopicCluster | Mapping[str, Any],
    *,
    config: SummaryConfig | None = None,
    client: ChatClient | None = None,
) -> str:
    """Summarize one topic, falling back to a deterministic extract."""

    config = config or SummaryConfig()
    notes = _cluster_notes(cluster)
    if client is not None:
        summary = _summarize_with_client(client, config.model, _prompt_for(cluster, notes))
        if summary:
            return summary

    built_client = _build_client(config)
    if built_client is not None:
        summary = _summarize_with_client(built_client, config.model, _prompt_for(cluster, notes))
        if summary:
            return summary

    return fallback_summary(cluster)


def fallback_summary(cluster: TopicCluster | Mapping[str, Any], *, max_items: int = 3) -> str:
    """Return a deterministic summary from top note titles."""

    topic = _cluster_topic(cluster)
    notes = _cluster_notes(cluster)
    titles = [str(note.get("title") or note.get("content") or "").strip() for note in notes]
    titles = [title for title in titles if title][:max_items]
    if not titles:
        return f"{topic}: no notes available for summary."
    return f"{topic}: " + " | ".join(titles)


def _build_client(config: SummaryConfig) -> ChatClient | None:
    api_key = config.api_key or os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    try:
        from openai import OpenAI
    except ImportError:
        return None
    kwargs: dict[str, Any] = {"api_key": api_key, "timeout": config.timeout_seconds}
    base_url = config.base_url or os.getenv("OPENAI_BASE_URL")
    if base_url:
        kwargs["base_url"] = base_url
    return OpenAI(**kwargs)


def _summarize_with_client(client: ChatClient, model: str, prompt: str) -> str | None:
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Write concise trend digest summaries. Avoid speculation."},
                {"role": "user", "content": prompt},
            ],
            temperature=0,
        )
    except Exception:
        return None
    content = response.choices[0].message.content if response.choices else None
    return content.strip() if content else None


def _prompt_for(cluster: TopicCluster | Mapping[str, Any], notes: list[Mapping[str, Any]]) -> str:
    lines = [f"Topic: {_cluster_topic(cluster)}", "Summarize these Xiaohongshu notes in 2-3 bullet points:"]
    for note in notes[:8]:
        title = str(note.get("title") or "").strip()
        content = str(note.get("content") or note.get("desc") or note.get("description") or "").strip()
        lines.append(f"- {title}: {content[:240]}")
    return "\n".join(lines)


def _cluster_notes(cluster: TopicCluster | Mapping[str, Any]) -> list[Mapping[str, Any]]:
    notes = cluster.notes if isinstance(cluster, TopicCluster) else cluster.get("notes", [])
    return [note if isinstance(note, Mapping) else vars(note) for note in notes]


def _cluster_topic(cluster: TopicCluster | Mapping[str, Any]) -> str:
    if isinstance(cluster, TopicCluster):
        return cluster.topic
    return str(cluster.get("topic") or "General")
