from fastapi.testclient import TestClient

from xhs_digest.api import create_app


def test_trends_api_returns_demo_snapshot_when_database_is_empty(tmp_path):
    app = create_app(database_url=f"sqlite+pysqlite:///{tmp_path / 'trends.sqlite3'}")
    client = TestClient(app)

    response = client.get("/api/trends")

    assert response.status_code == 200
    payload = response.json()
    assert payload["window"] == "24h"
    assert payload["galaxies"]
    assert payload["nodes"]
    assert any(node["label"] == "ChatGPT" for node in payload["nodes"])


def test_trend_detail_api_returns_one_entity(tmp_path):
    app = create_app(database_url=f"sqlite+pysqlite:///{tmp_path / 'trends.sqlite3'}")
    client = TestClient(app)

    response = client.get("/api/trends/chatgpt")

    assert response.status_code == 200
    assert response.json()["entity"] == "chatgpt"


def test_provider_status_api_exposes_reserved_sources(tmp_path):
    app = create_app(database_url=f"sqlite+pysqlite:///{tmp_path / 'trends.sqlite3'}")
    client = TestClient(app)

    response = client.get("/api/providers/status")

    assert response.status_code == 200
    platforms = {provider["platform"] for provider in response.json()}
    assert {"github", "hackernews", "weibo", "x"} <= platforms
