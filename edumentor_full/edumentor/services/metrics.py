from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict
import time


@dataclass
class Metrics:
    total_requests: int = 0
    total_tutor_requests: int = 0
    total_planner_requests: int = 0
    total_analyzer_requests: int = 0

    total_errors: int = 0

    total_tutor_latency_ms: float = 0.0
    total_requests_with_latency: int = 0

    tool_usage: Dict[str, int] = field(default_factory=dict)

    def inc_tool(self, tool_name: str) -> None:
        self.tool_usage[tool_name] = self.tool_usage.get(tool_name, 0) + 1


metrics = Metrics()


class Timer:
    """Context manager to measure elapsed wall time in milliseconds."""

    def __enter__(self) -> "Timer":
        self._start = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self._end = time.perf_counter()

    @property
    def elapsed_ms(self) -> float:
        return (self._end - self._start) * 1000.0
