from pathlib import Path
import re

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]


def test_settings_yaml_exposes_runtime_sections():
    settings = yaml.safe_load((ROOT / "settings.yaml").read_text(encoding="utf-8"))

    assert set(settings) >= {"schedule", "digest", "provider"}
    assert 0 <= settings["schedule"]["hour"] <= 23
    assert 0 <= settings["schedule"]["minute"] <= 59
    assert settings["schedule"]["timezone"]
    assert settings["digest"]["default_notes_per_tag"] > 0
    assert settings["provider"]["timeout_seconds"] > 0


def test_tags_yaml_contains_reviewable_topic_configuration():
    tags_config = yaml.safe_load((ROOT / "tags.yaml").read_text(encoding="utf-8"))

    assert isinstance(tags_config["tags"], list)
    assert tags_config["tags"]
    for tag in tags_config["tags"]:
        assert tag["name"]
        assert isinstance(tag["keywords"], list)
        assert tag["keywords"]
        assert tag["daily_limit"] > 0
        assert tag["min_heat"] >= 0


def test_env_example_documents_required_runtime_variables():
    env_text = (ROOT / ".env.example").read_text(encoding="utf-8")
    names = set(re.findall(r"^([A-Z0-9_]+)=", env_text, flags=re.MULTILINE))

    assert {
        "DATABASE_URL",
        "XHS_PROVIDER",
        "XHS_API_TOKEN",
        "XHS_API_BASE_URL",
        "OPENAI_API_KEY",
        "OPENAI_MODEL",
        "SMTP_HOST",
        "SMTP_PORT",
        "SMTP_USER",
        "SMTP_PASSWORD",
        "SMTP_FROM",
        "MAIL_TO",
        "DIGEST_TIMEZONE",
        "LOG_LEVEL",
    } <= names


def test_public_cli_entrypoint_is_declared():
    tomllib = pytest.importorskip("tomllib")
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert pyproject["project"]["scripts"]["daily-digest"] == "xhs_digest.cli:app"
