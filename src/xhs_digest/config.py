from __future__ import annotations

from datetime import time
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class EnvSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "sqlite+pysqlite:///./xhs_digest.sqlite3"
    xhs_provider: str = "justone"
    xhs_api_token: str | None = None
    xhs_api_base_url: str = "https://api.justoneapi.com"
    openai_api_key: str | None = None
    openai_base_url: str | None = None
    openai_model: str = "gpt-4o-mini"
    trend_refresh_minutes: int = 30
    github_token: str | None = None
    producthunt_token: str | None = None
    reddit_client_id: str | None = None
    reddit_client_secret: str | None = None
    x_bearer_token: str | None = None
    weibo_api_token: str | None = None
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_from: str | None = None
    smtp_use_tls: bool = True
    smtp_use_ssl: bool = False
    smtp_timeout_seconds: float = 20.0
    mail_to: str | None = None
    digest_timezone: str = "Asia/Shanghai"
    log_level: str = "INFO"

    @property
    def recipients(self) -> list[str]:
        if not self.mail_to:
            return []
        return [item.strip() for item in self.mail_to.split(",") if item.strip()]

    def require_provider_credentials(self) -> None:
        if self.xhs_provider == "justone" and not self.xhs_api_token:
            raise ValueError("XHS_API_TOKEN is required when XHS_PROVIDER=justone.")

    def require_smtp_credentials(self) -> None:
        if self.smtp_host and self.smtp_host.lower() == "sendmail":
            missing = [
                name
                for name, value in {
                    "SMTP_FROM": self.smtp_from,
                    "MAIL_TO": self.mail_to,
                }.items()
                if not value
            ]
            if missing:
                raise ValueError(f"Missing sendmail settings: {', '.join(missing)}")
            return

        missing = [
            name
            for name, value in {
                "SMTP_HOST": self.smtp_host,
                "SMTP_USER": self.smtp_user,
                "SMTP_PASSWORD": self.smtp_password,
                "SMTP_FROM": self.smtp_from,
                "MAIL_TO": self.mail_to,
            }.items()
            if not value
        ]
        if missing:
            raise ValueError(f"Missing SMTP/email settings: {', '.join(missing)}")


class TagRule(BaseModel):
    name: str
    keywords: list[str] = Field(default_factory=list)
    synonyms: list[str] = Field(default_factory=list)
    exclude_keywords: list[str] = Field(default_factory=list)
    daily_limit: int = 30
    min_heat: int = 0

    @field_validator("keywords", "synonyms", "exclude_keywords", mode="before")
    @classmethod
    def normalize_words(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [value]
        return [str(item).strip() for item in value if str(item).strip()]

    @property
    def search_terms(self) -> list[str]:
        seen: set[str] = set()
        terms: list[str] = []
        for item in [*self.keywords, *self.synonyms]:
            normalized = item.strip()
            if normalized and normalized not in seen:
                seen.add(normalized)
                terms.append(normalized)
        return terms


class TagConfig(BaseModel):
    tags: list[TagRule]


class ScheduleConfig(BaseModel):
    hour: int = 8
    minute: int = 30
    timezone: str = "Asia/Shanghai"

    @property
    def send_time(self) -> time:
        return time(hour=self.hour, minute=self.minute)


class DigestConfig(BaseModel):
    default_notes_per_tag: int = 30
    comments_per_note: int = 20
    top_notes_for_comments: int = 5
    top_topics_per_tag: int = 5
    hot_posts_count: int = 10
    subject_template: str = "小红书 AI 风向雷达日报 - {date}"
    send_failure_notice: bool = True


class ProviderConfig(BaseModel):
    timeout_seconds: int = 20
    max_retries: int = 2


class RuntimeConfig(BaseModel):
    schedule: ScheduleConfig = Field(default_factory=ScheduleConfig)
    digest: DigestConfig = Field(default_factory=DigestConfig)
    provider: ProviderConfig = Field(default_factory=ProviderConfig)


def _read_yaml(path: str | Path) -> dict[str, Any]:
    target = Path(path)
    if not target.exists():
        raise FileNotFoundError(f"Config file not found: {target}")
    with target.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Config file must contain a YAML mapping: {target}")
    return data


def load_tags(path: str | Path = "tags.yaml") -> list[TagRule]:
    return TagConfig.model_validate(_read_yaml(path)).tags


def load_runtime_config(path: str | Path = "settings.yaml") -> RuntimeConfig:
    return RuntimeConfig.model_validate(_read_yaml(path))


def load_env() -> EnvSettings:
    return EnvSettings()
