from datetime import UTC, datetime, timedelta

from xhs_digest.trend_models import TrendItem, TrendMetric
from xhs_digest.trend_service import build_trend_snapshot, get_trend_node, match_entity_from_text


def test_trend_snapshot_groups_items_into_chinese_galaxies():
    now = datetime(2026, 5, 8, tzinfo=UTC)
    snapshot = build_trend_snapshot(
        [
            TrendItem(
                platform="github",
                id="repo-1",
                entity="chatgpt",
                title="ChatGPT agent workflow",
                published_at=now - timedelta(hours=2),
                metrics=TrendMetric(likes=100, comments=20, stars=50),
                sentiment=0.6,
            ),
            TrendItem(
                platform="weibo",
                id="weibo-1",
                entity="kimi",
                title="Kimi 长文档分析",
                published_at=now - timedelta(hours=4),
                metrics=TrendMetric(likes=80, comments=10, shares=4),
                sentiment=0.4,
            ),
        ],
        generated_at=now,
        include_demo_when_empty=False,
    )

    assert {galaxy.label for galaxy in snapshot.galaxies} >= {"全球大模型星系", "中国国内 AI 星系"}
    chatgpt = get_trend_node(snapshot, "chatgpt")
    kimi = get_trend_node(snapshot, "Kimi")
    assert chatgpt is not None
    assert kimi is not None
    assert chatgpt.galaxy_label == "全球大模型星系"
    assert kimi.galaxy_label == "中国国内 AI 星系"
    assert chatgpt.heat > 0


def test_match_entity_from_text_covers_domestic_and_frontier_terms():
    assert match_entity_from_text("通义千问 开源模型适配") == "qwen"
    assert match_entity_from_text("Sora 视频生成案例") == "sora"
    assert match_entity_from_text("Cursor AI 编程工作流") == "cursor"
