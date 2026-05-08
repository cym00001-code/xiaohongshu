from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import typer
from rich.console import Console

from .config import load_env, load_runtime_config, load_tags
from .digest import parse_digest_date, run_daily_digest
from .logging import configure_logging
from .scheduler import run_scheduler

app = typer.Typer(help="小红书风向雷达日报")
console = Console()


def _load_common(tags_path: Path, settings_path: Path):
    env = load_env()
    configure_logging(env.log_level)
    runtime = load_runtime_config(settings_path)
    tags = load_tags(tags_path)
    return env, runtime, tags


@app.command("init-db")
def init_db() -> None:
    """Create database tables."""
    from .database import create_engine_and_session, create_tables

    env = load_env()
    configure_logging(env.log_level)
    engine, _ = create_engine_and_session(env.database_url)
    create_tables(engine)
    console.print("[green]Database tables are ready.[/green]")


@app.command("run")
def run(
    date_value: str = typer.Option("today", "--date", help="today, yesterday, or YYYY-MM-DD"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Generate the digest without sending email."),
    tags_path: Path = typer.Option(Path("tags.yaml"), "--tags", help="Path to tag config."),
    settings_path: Path = typer.Option(Path("settings.yaml"), "--settings", help="Path to runtime config."),
) -> None:
    """Generate the daily digest."""
    env, runtime, tags = _load_common(tags_path, settings_path)
    target_date = parse_digest_date(date_value, timezone=runtime.schedule.timezone)
    result = run_daily_digest(target_date=target_date, env=env, runtime=runtime, tags=tags, dry_run=dry_run)
    console.print(f"[green]Digest ready:[/green] {result.subject}")
    console.print(f"Notes: {result.note_count} | Hot posts: {result.hot_note_count} | Topics: {result.topic_count} | Sent: {result.sent}")


@app.command("test-email")
def test_email() -> None:
    """Send a small SMTP test email."""
    from .mailer import SmtpMailer

    env = load_env()
    configure_logging(env.log_level)
    env.require_smtp_credentials()
    mailer = SmtpMailer.from_env(env)
    mailer.send_html(
        subject="小红书风向雷达测试邮件",
        html="<p>测试成功：邮件服务已经可以发送日报。</p>",
        recipients=env.recipients,
    )
    console.print("[green]Test email sent.[/green]")


@app.command("backfill")
def backfill(
    days: int = typer.Option(7, "--days", min=1, max=30, help="How many past days to generate as dry-run baselines."),
    tags_path: Path = typer.Option(Path("tags.yaml"), "--tags", help="Path to tag config."),
    settings_path: Path = typer.Option(Path("settings.yaml"), "--settings", help="Path to runtime config."),
) -> None:
    """Backfill recent daily baselines without sending emails."""
    env, runtime, tags = _load_common(tags_path, settings_path)
    today = parse_digest_date("today", timezone=runtime.schedule.timezone)
    for offset in range(days, 0, -1):
        target_date = today - timedelta(days=offset)
        result = run_daily_digest(target_date=target_date, env=env, runtime=runtime, tags=tags, dry_run=True)
        console.print(f"[green]Backfilled[/green] {target_date.isoformat()} notes={result.note_count} topics={result.topic_count}")


@app.command("schedule")
def schedule(
    tags_path: Path = typer.Option(Path("tags.yaml"), "--tags", help="Path to tag config."),
    settings_path: Path = typer.Option(Path("settings.yaml"), "--settings", help="Path to runtime config."),
) -> None:
    """Run the daily scheduler process."""
    env, runtime, tags = _load_common(tags_path, settings_path)
    run_scheduler(env, runtime, tags)


@app.command("serve")
def serve(
    host: str = typer.Option("127.0.0.1", "--host", help="Web server host."),
    port: int = typer.Option(8000, "--port", help="Web server port."),
    reload: bool = typer.Option(False, "--reload", help="Reload the API server during local development."),
) -> None:
    """Run the AI Trend Galaxy API and bundled frontend."""
    import uvicorn

    uvicorn.run("xhs_digest.api:app", host=host, port=port, reload=reload)


@app.command("collect-trends")
def collect_trends(
    limit_per_entity: int = typer.Option(10, "--limit-per-entity", min=1, max=50, help="Items per AI entity and provider."),
    window_hours: int = typer.Option(24, "--window-hours", min=1, max=168, help="Collection time window."),
) -> None:
    """Collect public AI trend signals from enabled providers."""
    from .providers.trend_sources import build_default_trend_registry
    from .trend_collection import collect_trend_signals

    env = load_env()
    configure_logging(env.log_level)
    registry = build_default_trend_registry(github_token=env.github_token)
    count = collect_trend_signals(
        database_url=env.database_url,
        registry=registry,
        limit_per_entity=limit_per_entity,
        window_hours=window_hours,
    )
    console.print(f"[green]AI 趋势信号采集完成：[/green]{count} 条")


if __name__ == "__main__":
    app()
