import pytest


def _load_render_callable():
    renderer = pytest.importorskip(
        "xhs_digest.renderer",
        reason="renderer module is not implemented yet",
    )
    for name in ("render_digest", "render_html_digest", "render_email"):
        candidate = getattr(renderer, name, None)
        if callable(candidate):
            return candidate
    pytest.skip("no public renderer callable is implemented yet")


def test_renderer_includes_subject_tags_and_notes():
    render = _load_render_callable()
    digest = {
        "date": "2026-05-08",
        "subject": "XHS AI Digest",
        "tags": [
            {
                "name": "AI tools",
                "topics": ["agent workflows"],
                "notes": [
                    {
                        "title": "Agent workflow launch",
                        "url": "https://example.com/note/1",
                        "heat": 123,
                    }
                ],
            }
        ],
    }

    output = render(digest)

    assert "XHS AI Digest" in output
    assert "AI tools" in output
    assert "Agent workflow launch" in output


def test_renderer_returns_text_for_empty_digest():
    render = _load_render_callable()

    output = render({"date": "2026-05-08", "subject": "Empty digest", "tags": []})

    assert isinstance(output, str)
    assert "Empty digest" in output
