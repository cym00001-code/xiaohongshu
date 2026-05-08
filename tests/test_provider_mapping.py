from pathlib import Path
import json

import pytest


FIXTURE = Path(__file__).resolve().parent / "fixtures" / "justone_search.json"


def test_justone_fixture_documents_expected_provider_shape():
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))

    assert payload["code"] == 0
    assert isinstance(payload["data"]["items"], list)
    first = payload["data"]["items"][0]
    assert {
        "note_id",
        "title",
        "desc",
        "liked_count",
        "comment_count",
        "collected_count",
        "share_count",
        "user",
        "url",
        "time",
    } <= set(first)


def test_justone_provider_maps_fixture_to_public_note_fields():
    provider_module = pytest.importorskip(
        "xhs_digest.providers.justone",
        reason="justone provider is not implemented yet",
    )
    mapper = None
    for name in ("map_search_response", "parse_search_response", "normalize_search_response"):
        candidate = getattr(provider_module, name, None)
        if callable(candidate):
            mapper = candidate
            break
    if mapper is None:
        pytest.skip("no public JustOne mapping callable is implemented yet")

    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    notes = mapper(payload)

    assert notes
    first = notes[0]
    if isinstance(first, dict):
        assert {"id", "title", "url"} <= set(first)
        assert first["title"]
    else:
        assert first.id
        assert first.title
        assert first.url
