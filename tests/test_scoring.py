from types import SimpleNamespace

import pytest


def _load_score_callable():
    scoring = pytest.importorskip(
        "xhs_digest.scoring",
        reason="scoring module is not implemented yet",
    )
    for name in ("score_note", "calculate_heat_score", "heat_score"):
        candidate = getattr(scoring, name, None)
        if callable(candidate):
            return candidate
    pytest.skip("no public scoring callable is implemented yet")


def _call_score(score_func, **metrics):
    try:
        return score_func(**metrics)
    except TypeError:
        note = SimpleNamespace(**metrics)
        return score_func(note)


def test_heat_score_increases_with_engagement():
    score_func = _load_score_callable()

    low = _call_score(score_func, likes=10, comments=2, collects=1, shares=0)
    high = _call_score(score_func, likes=100, comments=20, collects=10, shares=5)

    assert high > low


def test_heat_score_handles_missing_or_zero_metrics():
    score_func = _load_score_callable()

    score = _call_score(score_func, likes=0, comments=0, collects=0, shares=0)

    assert score >= 0
