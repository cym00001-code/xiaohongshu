"""Simple deterministic topic clustering for ranked notes."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence


@dataclass(slots=True)
class TopicCluster:
    """A group of notes that share topic keywords."""

    topic: str
    keywords: list[str]
    notes: list[dict[str, Any]]
    score: float
    summary: str | None = None


TOKEN_RE = re.compile(r"#[^#\s]+|[A-Za-z][A-Za-z0-9_+-]{1,}|[\u4e00-\u9fff]{2,}")
STOPWORDS = {
    "this",
    "that",
    "with",
    "from",
    "小红书",
    "分享",
    "推荐",
    "真的",
    "一个",
}


def cluster_notes(
    notes: Iterable[Any],
    *,
    max_clusters: int = 5,
    min_cluster_size: int = 1,
    max_notes_per_cluster: int = 8,
) -> list[TopicCluster]:
    """Cluster notes by overlapping title/content tokens."""

    normalized = [_normalize_note(note) for note in notes]
    normalized.sort(key=lambda item: (-_score(item), _stable_id(item)))

    clusters: list[TopicCluster] = []
    for note in normalized:
        tokens = set(_tokens(note))
        best_cluster: TopicCluster | None = None
        best_overlap = 0
        for cluster in clusters:
            overlap = len(tokens.intersection(cluster.keywords))
            if overlap > best_overlap:
                best_overlap = overlap
                best_cluster = cluster
        if best_cluster is not None and best_overlap > 0:
            best_cluster.notes.append(note)
            _refresh_cluster(best_cluster, max_notes_per_cluster)
        else:
            clusters.append(_make_cluster([note], max_notes_per_cluster))

    clusters = [cluster for cluster in clusters if len(cluster.notes) >= min_cluster_size]
    clusters.sort(key=lambda cluster: (-cluster.score, cluster.topic))
    return clusters[:max_clusters]


def cluster_notes_by_tag(notes: Iterable[Any], *, top_topics_per_tag: int = 5) -> list[TopicCluster]:
    """Cluster notes inside each tag and return a flat topic list."""

    grouped: dict[str, list[Any]] = {}
    for note in notes:
        tag_name = _get(note, "tag_name") or _get(note, "tag") or "未分类"
        grouped.setdefault(str(tag_name), []).append(note)

    all_clusters: list[TopicCluster] = []
    for tag_name, tag_notes in grouped.items():
        clusters = cluster_notes(tag_notes, max_clusters=top_topics_per_tag, max_notes_per_cluster=6)
        for cluster in clusters:
            cluster.topic = f"{tag_name}：{cluster.topic}"
            all_clusters.append(cluster)
    all_clusters.sort(key=lambda cluster: (-cluster.score, cluster.topic))
    return all_clusters


def _make_cluster(notes: list[dict[str, Any]], max_notes: int) -> TopicCluster:
    keywords = _top_keywords(notes)
    topic = keywords[0] if keywords else "General"
    cluster_notes = sorted(notes, key=lambda item: (-_score(item), _stable_id(item)))[:max_notes]
    return TopicCluster(topic=topic, keywords=keywords, notes=cluster_notes, score=_cluster_score(notes))


def _refresh_cluster(cluster: TopicCluster, max_notes: int) -> None:
    cluster.keywords = _top_keywords(cluster.notes)
    cluster.topic = cluster.keywords[0] if cluster.keywords else cluster.topic
    cluster.notes.sort(key=lambda item: (-_score(item), _stable_id(item)))
    del cluster.notes[max_notes:]
    cluster.score = _cluster_score(cluster.notes)


def _top_keywords(notes: Sequence[dict[str, Any]], limit: int = 6) -> list[str]:
    counter: Counter[str] = Counter()
    for note in notes:
        counter.update(_tokens(note))
    return [token for token, _ in sorted(counter.items(), key=lambda item: (-item[1], item[0]))[:limit]]


def _cluster_score(notes: Sequence[dict[str, Any]]) -> float:
    if not notes:
        return 0.0
    return round(sum(_score(note) for note in notes) / len(notes) + min(len(notes), 5), 6)


def _tokens(note: Mapping[str, Any]) -> list[str]:
    text = " ".join(str(note.get(field) or "") for field in ("title", "content", "desc", "description"))
    tags = " ".join(str(tag) for tag in (note.get("tags") or []))
    raw_tokens = TOKEN_RE.findall(f"{text} {tags}")
    return [token.strip("#").lower() for token in raw_tokens if token.strip("#").lower() not in STOPWORDS]


def _normalize_note(note: Any) -> dict[str, Any]:
    if isinstance(note, Mapping):
        return dict(note)
    return {
        "id": getattr(note, "id", None),
        "note_id": getattr(note, "note_id", None),
        "title": getattr(note, "title", ""),
        "content": getattr(note, "content", "") or getattr(note, "description", ""),
        "url": getattr(note, "url", None),
        "score": getattr(note, "score", 0),
        "tag_name": getattr(note, "tag_name", None),
    }


def _score(note: Mapping[str, Any]) -> float:
    try:
        return float(note.get("score") or 0)
    except (TypeError, ValueError):
        return 0.0


def _stable_id(note: Mapping[str, Any]) -> str:
    return str(note.get("id") or note.get("note_id") or note.get("url") or note.get("title") or "")


def _get(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, Mapping):
        return obj.get(key, default)
    return getattr(obj, key, default)

