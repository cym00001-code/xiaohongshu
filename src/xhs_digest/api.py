"""FastAPI application for the AI Trend Galaxy frontend."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from xhs_digest.config import load_env
from xhs_digest.trend_models import ProviderStatus, TrendItem, TrendNode, TrendSnapshot
from xhs_digest.trend_service import get_trend_node, trend_snapshot_from_database


def create_app(*, database_url: str | None = None, refresh_minutes: int | None = None) -> FastAPI:
    """Create the API app used by Uvicorn and tests."""

    app = FastAPI(title="AI Trend Galaxy", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET"],
        allow_headers=["*"],
    )

    def snapshot(window: str) -> TrendSnapshot:
        env = load_env()
        return trend_snapshot_from_database(
            database_url or env.database_url,
            window=window,
            refresh_minutes=refresh_minutes or env.trend_refresh_minutes,
        )

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/trends", response_model=TrendSnapshot)
    def trends(window: str = Query("24h", pattern="^(24h|7d)$")) -> TrendSnapshot:
        return snapshot(window)

    @app.get("/api/trends/{entity}", response_model=TrendNode)
    def trend_detail(entity: str, window: str = Query("24h", pattern="^(24h|7d)$")) -> TrendNode:
        node = get_trend_node(snapshot(window), entity)
        if node is None:
            raise HTTPException(status_code=404, detail="Trend entity not found")
        return node

    @app.get("/api/items/{platform}/{item_id}", response_model=TrendItem)
    def item_detail(platform: str, item_id: str, window: str = Query("24h", pattern="^(24h|7d)$")) -> TrendItem:
        for node in snapshot(window).nodes:
            for item in node.top_items:
                if item.platform == platform and item.id == item_id:
                    return item
        raise HTTPException(status_code=404, detail="Trend item not found")

    @app.get("/api/providers/status", response_model=list[ProviderStatus])
    def provider_status(window: str = Query("24h", pattern="^(24h|7d)$")) -> list[ProviderStatus]:
        return snapshot(window).providers

    static_dir = Path(__file__).resolve().parents[2] / "web" / "dist"
    if static_dir.exists():
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="frontend")

    return app


app = create_app()
