"""HTML email rendering for digest output."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import date
from pathlib import Path
from typing import Any, Mapping

from jinja2 import Environment, FileSystemLoader, PackageLoader, select_autoescape


DEFAULT_TEMPLATE = "digest_email.html.j2"


def render_digest_email(
    *,
    topics: list[Any],
    digest_date: date | str | None = None,
    target_date: date | str | None = None,
    subject: str | None = None,
    summary: str | None = None,
    hot_notes: list[Any] | None = None,
    notes: list[Any] | None = None,
    metadata: Mapping[str, Any] | None = None,
    template_name: str = DEFAULT_TEMPLATE,
    template_dir: str | Path | None = None,
) -> str:
    """Render the digest HTML email."""

    env = _environment(template_dir)
    template = env.get_template(template_name)
    normalized_topics = [_normalize(topic) for topic in topics]
    return template.render(
        subject=subject or "Xiaohongshu trend digest",
        digest_date=digest_date or target_date or date.today().isoformat(),
        summary=summary,
        hot_notes=[_normalize_note(note) for note in (hot_notes or [])],
        topics=normalized_topics,
        notes=[_normalize_note(note) for note in (notes or [])],
        metadata=dict(metadata or {}),
    )


def render_digest(digest: Mapping[str, Any]) -> str:
    """Render a dict-shaped digest used by tests and simple integrations."""

    topics: list[dict[str, Any]] = []
    for tag in digest.get("tags", []):
        notes = tag.get("notes", [])
        topic_names = tag.get("topics", []) or [tag.get("name", "General")]
        for topic_name in topic_names:
            topics.append(
                {
                    "topic": f"{tag.get('name', '未分类')}：{topic_name}",
                    "keywords": [tag.get("name", "")],
                    "summary": None,
                    "notes": notes,
                    "score": 0,
                }
            )
    return render_digest_email(topics=topics, digest_date=digest.get("date"), subject=digest.get("subject"))


render_html_digest = render_digest
render_email = render_digest


def _environment(template_dir: str | Path | None = None) -> Environment:
    loader = FileSystemLoader(str(template_dir)) if template_dir else PackageLoader("xhs_digest", "templates")
    return Environment(loader=loader, autoescape=select_autoescape(["html", "xml"]), trim_blocks=True, lstrip_blocks=True)


def _normalize(value: Any) -> dict[str, Any]:
    if is_dataclass(value):
        data = asdict(value)
    elif isinstance(value, Mapping):
        data = dict(value)
    else:
        data = vars(value)
    data["notes"] = [_normalize_note(note) for note in data.get("notes", [])]
    return data


def _normalize_note(note: Any) -> dict[str, Any]:
    if is_dataclass(note):
        return asdict(note)
    if isinstance(note, Mapping):
        return dict(note)
    return vars(note)
