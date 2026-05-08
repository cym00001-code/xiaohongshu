"""Trend aggregation for the interactive AI galaxy."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta
from math import log1p
from typing import Iterable

from sqlalchemy import select

from xhs_digest.database import create_engine_and_session, create_tables
from xhs_digest.models import Note
from xhs_digest.trend_models import (
    EntityRule,
    GalaxyInfo,
    ProviderStatus,
    TrendItem,
    TrendMetric,
    TrendNode,
    TrendPoint,
    TrendSnapshot,
)


DEFAULT_REFRESH_MINUTES = 30

GALAXIES: tuple[GalaxyInfo, ...] = (
    GalaxyInfo(
        id="global_models",
        label="全球大模型星系",
        description="ChatGPT、Claude、Gemini、Grok、DeepSeek 等全球主流模型的热度变化。",
        color="#31b7ff",
    ),
    GalaxyInfo(
        id="china_ai",
        label="中国国内 AI 星系",
        description="Kimi、通义千问、豆包、文心一言、智谱清言等国内 AI 产品信号。",
        color="#ffb44a",
    ),
    GalaxyInfo(
        id="frontier_ai",
        label="AI 前沿星系",
        description="视频生成、多模态、Agent、AI 搜索等前沿方向的讨论动能。",
        color="#65e28b",
    ),
    GalaxyInfo(
        id="tooling",
        label="AI 工具生态星系",
        description="Cursor、Perplexity、Notion AI、Copilot 等工作流工具的口碑和采用。",
        color="#b886ff",
    ),
)

GALAXY_BY_ID = {galaxy.id: galaxy for galaxy in GALAXIES}

AI_ENTITIES: tuple[EntityRule, ...] = (
    EntityRule(
        id="chatgpt",
        label="ChatGPT",
        galaxy="global_models",
        galaxy_label="全球大模型星系",
        keywords=["chatgpt", "openai", "gpt", "gpt-4", "gpt-4o", "gpt-5", "custom gpts"],
        color="#31b7ff",
    ),
    EntityRule(
        id="claude",
        label="Claude",
        galaxy="global_models",
        galaxy_label="全球大模型星系",
        keywords=["claude", "anthropic", "sonnet", "opus", "haiku", "claude code"],
        color="#f6a841",
    ),
    EntityRule(
        id="gemini",
        label="Gemini",
        galaxy="global_models",
        galaxy_label="全球大模型星系",
        keywords=["gemini", "google ai", "deepmind", "veo", "imagen"],
        color="#65e28b",
    ),
    EntityRule(
        id="grok",
        label="Grok",
        galaxy="global_models",
        galaxy_label="全球大模型星系",
        keywords=["grok", "xai", "x.ai"],
        color="#ff5264",
    ),
    EntityRule(
        id="deepseek",
        label="DeepSeek",
        galaxy="global_models",
        galaxy_label="全球大模型星系",
        keywords=["deepseek", "deepseek-r1", "deepseek v3", "deepseek v2"],
        color="#2c8dff",
    ),
    EntityRule(
        id="kimi",
        label="Kimi",
        galaxy="china_ai",
        galaxy_label="中国国内 AI 星系",
        keywords=["kimi", "moonshot", "月之暗面", "长文本"],
        color="#ffcf5f",
    ),
    EntityRule(
        id="qwen",
        label="通义千问",
        galaxy="china_ai",
        galaxy_label="中国国内 AI 星系",
        keywords=["qwen", "通义千问", "通义", "阿里云百炼"],
        color="#ff8b3d",
    ),
    EntityRule(
        id="doubao",
        label="豆包",
        galaxy="china_ai",
        galaxy_label="中国国内 AI 星系",
        keywords=["豆包", "doubao", "字节", "火山方舟"],
        color="#ff6f91",
    ),
    EntityRule(
        id="ernie",
        label="文心一言",
        galaxy="china_ai",
        galaxy_label="中国国内 AI 星系",
        keywords=["文心一言", "ernie", "百度智能云", "文心"],
        color="#4fa3ff",
    ),
    EntityRule(
        id="glm",
        label="智谱清言",
        galaxy="china_ai",
        galaxy_label="中国国内 AI 星系",
        keywords=["智谱", "智谱清言", "glm", "chatglm"],
        color="#8cc6ff",
    ),
    EntityRule(
        id="sora",
        label="Sora",
        galaxy="frontier_ai",
        galaxy_label="AI 前沿星系",
        keywords=["sora", "视频生成", "文生视频", "video generation"],
        color="#52ffd1",
    ),
    EntityRule(
        id="agent",
        label="Agent",
        galaxy="frontier_ai",
        galaxy_label="AI 前沿星系",
        keywords=["agent", "智能体", "ai agent", "multi-agent", "manus"],
        color="#79f26f",
    ),
    EntityRule(
        id="multimodal",
        label="多模态",
        galaxy="frontier_ai",
        galaxy_label="AI 前沿星系",
        keywords=["多模态", "multimodal", "语音模型", "图像理解", "视频理解"],
        color="#36d4ff",
    ),
    EntityRule(
        id="cursor",
        label="Cursor",
        galaxy="tooling",
        galaxy_label="AI 工具生态星系",
        keywords=["cursor", "ai 编程", "代码助手", "vibe coding"],
        color="#b886ff",
    ),
    EntityRule(
        id="perplexity",
        label="Perplexity",
        galaxy="tooling",
        galaxy_label="AI 工具生态星系",
        keywords=["perplexity", "ai 搜索", "answer engine"],
        color="#48dfd8",
    ),
    EntityRule(
        id="copilot",
        label="Copilot",
        galaxy="tooling",
        galaxy_label="AI 工具生态星系",
        keywords=["copilot", "github copilot", "microsoft copilot"],
        color="#89b7ff",
    ),
)

ENTITY_BY_ID = {entity.id: entity for entity in AI_ENTITIES}

PLATFORM_LABELS = {
    "justone": "小红书",
    "xhs": "小红书",
    "hackernews": "Hacker News",
    "github": "GitHub",
    "producthunt": "Product Hunt",
    "reddit": "Reddit",
    "weibo": "微博",
    "x": "X",
    "demo": "演示数据",
}


def build_trend_snapshot(
    items: Iterable[TrendItem],
    *,
    window: str = "24h",
    refresh_minutes: int = DEFAULT_REFRESH_MINUTES,
    generated_at: datetime | None = None,
    provider_statuses: list[ProviderStatus] | None = None,
    include_demo_when_empty: bool = True,
) -> TrendSnapshot:
    """Aggregate provider-neutral items into nodes for the 3D visualization."""

    generated_at = generated_at or datetime.now(UTC)
    normalized_items = [_with_heat(item) for item in items if item.entity in ENTITY_BY_ID]
    if not normalized_items and include_demo_when_empty:
        normalized_items = demo_trend_items(generated_at=generated_at)

    grouped: dict[str, list[TrendItem]] = defaultdict(list)
    for item in normalized_items:
        grouped[item.entity].append(item)

    nodes = [
        _build_node(entity, grouped.get(entity.id, []), generated_at=generated_at, window=window)
        for entity in AI_ENTITIES
    ]
    nodes.sort(key=lambda node: (-node.heat, node.label))

    statuses = provider_statuses or default_provider_statuses()
    return TrendSnapshot(
        generated_at=generated_at,
        window=window,
        refresh_minutes=refresh_minutes,
        galaxies=list(GALAXIES),
        nodes=nodes,
        providers=statuses,
    )


def load_trend_items_from_database(
    database_url: str,
    *,
    window_hours: int = 24,
    limit: int = 500,
    now: datetime | None = None,
) -> list[TrendItem]:
    """Load recent stored notes and map them to trend items."""

    now = now or datetime.now(UTC)
    since = now - timedelta(hours=window_hours)
    engine, session_factory = create_engine_and_session(database_url)
    create_tables(engine)
    with session_factory() as session:
        statement = (
            select(Note)
            .where((Note.published_at.is_(None)) | (Note.published_at >= since))
            .order_by(Note.updated_at.desc())
            .limit(limit)
        )
        return [_note_to_trend_item(note) for note in session.scalars(statement) if _match_entity(note)]


def trend_snapshot_from_database(
    database_url: str,
    *,
    window: str = "24h",
    refresh_minutes: int = DEFAULT_REFRESH_MINUTES,
) -> TrendSnapshot:
    """Build a trend snapshot from persisted notes, falling back to demo data."""

    window_hours = 168 if window == "7d" else 24
    items = load_trend_items_from_database(database_url, window_hours=window_hours)
    return build_trend_snapshot(items, window=window, refresh_minutes=refresh_minutes)


def get_trend_node(snapshot: TrendSnapshot, entity: str) -> TrendNode | None:
    """Return one trend node by id or label."""

    normalized = entity.strip().lower()
    for node in snapshot.nodes:
        if node.entity == normalized or node.label.lower() == normalized:
            return node
    return None


def default_provider_statuses() -> list[ProviderStatus]:
    """Return provider status rows for the configured roadmap."""

    return [
        ProviderStatus(
            platform="justone",
            label="小红书",
            enabled=True,
            refresh_minutes=DEFAULT_REFRESH_MINUTES,
            notes="沿用当前项目已有的 Just One 小红书 provider。",
        ),
        ProviderStatus(
            platform="hackernews",
            label="Hacker News",
            enabled=True,
            refresh_minutes=DEFAULT_REFRESH_MINUTES,
            notes="公开 Firebase API，不需要账号。",
        ),
        ProviderStatus(
            platform="github",
            label="GitHub",
            enabled=True,
            refresh_minutes=DEFAULT_REFRESH_MINUTES,
            notes="公开搜索 API；配置 token 后可获得更高限额。",
        ),
        ProviderStatus(
            platform="producthunt",
            label="Product Hunt",
            enabled=False,
            refresh_minutes=DEFAULT_REFRESH_MINUTES,
            notes="需要 Product Hunt API token 后才能实时采集。",
        ),
        ProviderStatus(
            platform="reddit",
            label="Reddit",
            enabled=False,
            refresh_minutes=DEFAULT_REFRESH_MINUTES,
            notes="需要 OAuth 凭据后才能合规实时采集。",
        ),
        ProviderStatus(
            platform="weibo",
            label="微博",
            enabled=False,
            refresh_minutes=DEFAULT_REFRESH_MINUTES,
            notes="预留平台位；建议优先接合规第三方 provider。",
        ),
        ProviderStatus(
            platform="x",
            label="X",
            enabled=False,
            refresh_minutes=DEFAULT_REFRESH_MINUTES,
            notes="预留平台位；需要官方 API 权限。",
        ),
    ]


def demo_trend_items(*, generated_at: datetime | None = None) -> list[TrendItem]:
    """Deterministic sample data so the UI is usable before credentials exist."""

    now = generated_at or datetime.now(UTC)
    rows = [
        ("chatgpt", "github", "GPT-4o Agent 更新引发开发者讨论", 520, 74, 180, 55, 0.72, 2),
        ("chatgpt", "reddit", "企业团队开始批量使用自定义 GPT", 430, 96, 120, 42, 0.61, 5),
        ("chatgpt", "justone", "ChatGPT 写作工作流在小红书爆火", 760, 88, 240, 72, 0.66, 7),
        ("claude", "hackernews", "Claude Code 工作流讨论升温", 360, 118, 92, 35, 0.48, 4),
        ("claude", "github", "Anthropic 提示词工具仓库热度上升", 310, 43, 80, 21, 0.57, 8),
        ("gemini", "github", "Gemini 多模态演示项目获关注", 290, 38, 68, 19, 0.61, 3),
        ("gemini", "producthunt", "Google AI 视频工作流上新", 330, 52, 91, 27, 0.58, 10),
        ("grok", "x", "Grok API 限额讨论分化明显", 210, 126, 34, 66, -0.28, 1),
        ("grok", "reddit", "Grok 对比帖带来持续争议", 180, 88, 21, 31, -0.15, 9),
        ("deepseek", "hackernews", "DeepSeek R1 本地部署笔记热度回升", 410, 77, 130, 48, 0.55, 6),
        ("deepseek", "justone", "DeepSeek 自动化办公教程被大量收藏", 650, 54, 210, 63, 0.59, 11),
        ("kimi", "justone", "Kimi 长文档分析场景继续升温", 520, 62, 190, 35, 0.58, 3),
        ("qwen", "github", "通义千问开源模型适配项目增长", 470, 41, 120, 29, 0.52, 9),
        ("doubao", "weibo", "豆包视频生成能力引发国内讨论", 610, 104, 160, 68, 0.44, 6),
        ("ernie", "weibo", "文心一言企业应用案例传播", 340, 32, 82, 18, 0.39, 12),
        ("glm", "justone", "智谱清言 Agent 模板被推荐", 380, 46, 95, 24, 0.47, 14),
        ("sora", "x", "Sora 短片案例推动视频生成关注", 450, 87, 100, 61, 0.51, 4),
        ("agent", "producthunt", "Agent 工作流产品集中上新", 390, 63, 115, 44, 0.57, 5),
        ("multimodal", "hackernews", "多模态实时语音交互讨论升温", 280, 93, 65, 37, 0.49, 8),
        ("cursor", "github", "Cursor 插件与规则仓库快速增长", 720, 58, 220, 73, 0.62, 2),
        ("perplexity", "reddit", "AI 搜索替代传统搜索的体验讨论", 260, 78, 58, 28, 0.36, 13),
        ("copilot", "github", "Copilot 企业代码审查场景热度稳定", 510, 37, 140, 33, 0.5, 15),
    ]
    items: list[TrendItem] = []
    for entity, platform, title, likes, comments, saves, shares, sentiment, age_hours in rows:
        items.append(
            TrendItem(
                platform=platform,
                id=f"{platform}-{entity}-{age_hours}",
                entity=entity,
                title=title,
                summary=f"{title}，正在 {PLATFORM_LABELS.get(platform, platform)} 形成可见讨论。",
                url=f"https://example.com/{platform}/{entity}/{age_hours}",
                author=f"{PLATFORM_LABELS.get(platform, platform)} 信号源",
                published_at=now - timedelta(hours=age_hours),
                metrics=TrendMetric(likes=likes, comments=comments, saves=saves, shares=shares, score=likes + comments),
                        tags=[ENTITY_BY_ID[entity].label, PLATFORM_LABELS.get(platform, platform)],
                sentiment=sentiment,
            )
        )
    return [_with_heat(item) for item in items]


def _build_node(entity: EntityRule, items: list[TrendItem], *, generated_at: datetime, window: str) -> TrendNode:
    if not items:
        return TrendNode(
            entity=entity.id,
            label=entity.label,
            galaxy=entity.galaxy,
            galaxy_label=entity.galaxy_label,
            color=entity.color,
            heat=0.0,
            growth=0.0,
            sentiment=0.0,
            item_count=0,
            platform_distribution={},
            heat_breakdown={"mentions": 0.0, "engagement": 0.0, "freshness": 0.0},
            trend=_empty_trend(window),
            top_items=[],
            summary=f"{entity.label} 在当前时间窗口内还没有明显信号。",
        )

    item_count = len(items)
    heat = round(sum(item.heat for item in items), 2)
    platform_counts = dict(Counter(item.platform for item in items))
    sentiment = round(sum(item.sentiment for item in items) / item_count, 3)
    trend = _trend_points(items, generated_at=generated_at, window=window)
    growth = _growth_from_trend(trend)
    heat_breakdown = _heat_breakdown(items)
    top_items = sorted(items, key=lambda item: (-item.heat, item.published_at or datetime.min.replace(tzinfo=UTC)))[:5]
    top_platform = PLATFORM_LABELS.get(max(platform_counts, key=platform_counts.get), "多平台")

    return TrendNode(
        entity=entity.id,
        label=entity.label,
        galaxy=entity.galaxy,
        galaxy_label=entity.galaxy_label,
        color=entity.color,
        heat=heat,
        growth=growth,
        sentiment=sentiment,
        item_count=item_count,
        platform_distribution=platform_counts,
        heat_breakdown=heat_breakdown,
        trend=trend,
        top_items=top_items,
        summary=(
            f"{entity.label} 当前在 {top_platform} 最活跃，捕捉到 {item_count} 条公开信号，"
            f"窗口内动能变化为 {growth:+.0f}%。"
        ),
    )


def _note_to_trend_item(note: Note) -> TrendItem:
    entity = _match_entity(note) or "chatgpt"
    return _with_heat(
        TrendItem(
            platform=note.provider,
            id=note.provider_note_id,
            entity=entity,
            title=note.title or note.description or "未命名信号",
            summary=note.description,
            url=note.url,
            author=note.author_name,
            published_at=note.published_at,
            metrics=TrendMetric(
                likes=note.liked_count or 0,
                comments=note.commented_count or 0,
                saves=note.collected_count or 0,
                shares=note.shared_count or 0,
            ),
            tags=[tag.name for tag in note.tags],
            sentiment=_rough_sentiment(" ".join([note.title or "", note.description or ""])),
            raw={"stored_note_id": note.id},
        )
    )


def _match_entity(note: Note) -> str | None:
    text = " ".join(
        [
            note.title or "",
            note.description or "",
            note.author_name or "",
            " ".join(tag.name for tag in note.tags),
        ]
    ).lower()
    return match_entity_from_text(text)


def match_entity_from_text(text: str) -> str | None:
    """Map free text to a tracked AI entity."""

    lowered = text.lower()
    for entity in AI_ENTITIES:
        if any(keyword.lower() in lowered for keyword in entity.keywords):
            return entity.id
    return None


def _with_heat(item: TrendItem) -> TrendItem:
    metrics = item.metrics
    engagement = (
        log1p(metrics.likes) * 1.0
        + log1p(metrics.comments) * 2.0
        + log1p(metrics.saves) * 1.8
        + log1p(metrics.shares) * 2.4
        + log1p(metrics.stars) * 1.5
        + log1p(metrics.score) * 1.0
        + log1p(metrics.views) * 0.2
    )
    freshness = 0.0
    if item.published_at:
        published_at = item.published_at
        if published_at.tzinfo is None:
            published_at = published_at.replace(tzinfo=UTC)
        age_hours = max((datetime.now(UTC) - published_at).total_seconds() / 3600, 0.0)
        freshness = max(0.0, 10.0 - min(age_hours / 4, 10.0))
    item.heat = round((engagement * 8.0) + freshness + (abs(item.sentiment) * 8.0), 3)
    return item


def _trend_points(items: list[TrendItem], *, generated_at: datetime, window: str) -> list[TrendPoint]:
    buckets = 7
    total_hours = 168 if window == "7d" else 24
    bucket_hours = total_hours / buckets
    values = [0.0 for _ in range(buckets)]

    for item in items:
        if item.published_at is None:
            values[-1] += item.heat
            continue
        published_at = item.published_at if item.published_at.tzinfo else item.published_at.replace(tzinfo=UTC)
        age_hours = max((generated_at - published_at).total_seconds() / 3600, 0.0)
        index = buckets - 1 - min(int(age_hours // bucket_hours), buckets - 1)
        values[index] += item.heat

    unit = "天" if window == "7d" else "小时"
    if window == "7d":
        labels = [f"{7 - index}天前" for index in range(buckets - 1)] + ["现在"]
    else:
        labels = [f"{int(total_hours - (index * bucket_hours))}{unit}前" for index in range(buckets - 1)] + ["现在"]
    return [TrendPoint(label=label, value=round(value, 2)) for label, value in zip(labels, values)]


def _growth_from_trend(points: list[TrendPoint]) -> float:
    if len(points) < 2:
        return 0.0
    earlier = sum(point.value for point in points[: len(points) // 2])
    recent = sum(point.value for point in points[len(points) // 2 :])
    if earlier <= 0 and recent > 0:
        return 100.0
    if earlier <= 0:
        return 0.0
    return round(((recent - earlier) / earlier) * 100, 1)


def _heat_breakdown(items: list[TrendItem]) -> dict[str, float]:
    mentions = float(len(items) * 10)
    engagement = sum(item.heat for item in items)
    freshness = sum(1 for item in items if item.published_at) * 8.0
    total = max(mentions + engagement + freshness, 1.0)
    return {
        "mentions": round((mentions / total) * 100, 1),
        "engagement": round((engagement / total) * 100, 1),
        "freshness": round((freshness / total) * 100, 1),
    }


def _empty_trend(window: str) -> list[TrendPoint]:
    labels = ["24小时前", "20小时前", "16小时前", "12小时前", "8小时前", "4小时前", "现在"] if window == "24h" else [
        "7天前",
        "6天前",
        "5天前",
        "4天前",
        "3天前",
        "2天前",
        "现在",
    ]
    return [TrendPoint(label=label, value=0.0) for label in labels]


def _rough_sentiment(text: str) -> float:
    lowered = text.lower()
    positive = ["好用", "推荐", "增长", "launch", "update", "adoption", "workflow", "viral", "strong"]
    negative = ["不好用", "避雷", "限制", "debate", "limit", "issue", "risk", "down"]
    score = sum(word in lowered for word in positive) - sum(word in lowered for word in negative)
    return max(-1.0, min(1.0, score / 3))
