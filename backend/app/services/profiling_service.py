from __future__ import annotations

import json
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any


class PerformanceProfiler:
    """Record stage-by-stage timings for the pipeline without polluting domain schemas."""

    def __init__(
        self,
        *,
        source_fps: float | None = None,
        source_resolution: tuple[int, int] | None = None,
    ) -> None:
        self.report: dict[str, Any] = {
            "source_fps": source_fps,
            "source_resolution": list(source_resolution) if source_resolution is not None else None,
            "stages": {},
        }

    @staticmethod
    def _frames_per_second(elapsed_seconds: float, frames_processed: int) -> float | None:
        if elapsed_seconds <= 0.0 or frames_processed <= 0:
            return None
        return frames_processed / elapsed_seconds

    def profile_stage(
        self,
        stage_name: str,
        *,
        action: Callable[[], Any],
        frames_processed: int = 0,
        input_fps: float | None = None,
        input_resolution: tuple[int, int] | tuple[int, int, int] | None = None,
    ) -> Any:
        start = time.perf_counter()
        result = action()
        elapsed_seconds = time.perf_counter() - start
        self.report["stages"][stage_name] = {
            "elapsed_seconds": elapsed_seconds,
            "frames_processed": frames_processed,
            "frames_per_second": self._frames_per_second(elapsed_seconds, frames_processed),
            "input_fps": input_fps if input_fps is not None else self.report.get("source_fps"),
            "input_resolution": (
                list(input_resolution)
                if input_resolution is not None
                else self.report.get("source_resolution")
            ),
        }
        return result

    def write_report(self, output_path: str | Path) -> Path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.report, indent=2), encoding="utf-8")
        return path
