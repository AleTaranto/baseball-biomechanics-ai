from __future__ import annotations

import json

import pytest
from app.services.profiling_service import PerformanceProfiler

from run_pipeline import _resolve_sampling_interval


def test_sampling_interval_resolves_expected_processing_modes() -> None:
    assert _resolve_sampling_interval(processing_mode="full", sampling_interval=None) == 1
    assert _resolve_sampling_interval(processing_mode="two_pass", sampling_interval=None) == 1
    assert _resolve_sampling_interval(processing_mode="half_rate", sampling_interval=None) == 2
    assert _resolve_sampling_interval(processing_mode="custom", sampling_interval=4) == 4

    with pytest.raises(ValueError):
        _resolve_sampling_interval(processing_mode="custom", sampling_interval=0)

    with pytest.raises(ValueError):
        _resolve_sampling_interval(processing_mode="unsupported", sampling_interval=None)


def test_profiler_tracks_stage_timings(tmp_path) -> None:
    profiler = PerformanceProfiler(source_fps=120.0, source_resolution=(1920, 1080))
    profiler.profile_stage(
        "synthetic_stage",
        frames_processed=12,
        input_fps=120.0,
        input_resolution=(1920, 1080),
        action=lambda: {"ok": True},
    )

    report_path = tmp_path / "performance.json"
    profiler.write_report(report_path)
    payload = json.loads(report_path.read_text(encoding="utf-8"))

    assert payload["source_fps"] == 120.0
    assert payload["stages"]["synthetic_stage"]["frames_processed"] == 12
    assert payload["stages"]["synthetic_stage"]["frames_per_second"] is not None
    assert payload["stages"]["synthetic_stage"]["input_resolution"] == [1920, 1080]
