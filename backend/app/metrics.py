"""Tiny in-memory metrics in Prometheus text format — no extra dependency.

Banks scrape /metrics into their existing monitoring. We expose verdict mix,
error count and analyze latency. ponytail: hand-rolled exposition format; swap
for prometheus_client only if we need histograms/labels it doesn't cover.
"""
from __future__ import annotations

import threading

_lock = threading.Lock()
_verdicts: dict[tuple[str, str], int] = {}   # (source, alert_level) -> count
_actions: dict[str, int] = {}                # action -> count
_errors: dict[str, int] = {}                 # source -> count
_lat_count = 0
_lat_sum = 0.0


def record_verdict(source: str, alert_level: str, action: str | None = None) -> None:
    with _lock:
        _verdicts[(source, alert_level)] = _verdicts.get((source, alert_level), 0) + 1
        if action:
            _actions[action] = _actions.get(action, 0) + 1


def record_error(source: str) -> None:
    with _lock:
        _errors[source] = _errors.get(source, 0) + 1


def observe_latency(seconds: float) -> None:
    global _lat_count, _lat_sum
    with _lock:
        _lat_count += 1
        _lat_sum += seconds


def render() -> str:
    with _lock:
        lines = [
            "# HELP dhwani_analyze_total Verdicts emitted, by source and alert level",
            "# TYPE dhwani_analyze_total counter",
        ]
        for (src, lvl), n in sorted(_verdicts.items()):
            lines.append(f'dhwani_analyze_total{{source="{src}",alert_level="{lvl}"}} {n}')
        lines += ["# HELP dhwani_action_total Fused decisions, by action",
                  "# TYPE dhwani_action_total counter"]
        for act, n in sorted(_actions.items()):
            lines.append(f'dhwani_action_total{{action="{act}"}} {n}')
        lines += ["# HELP dhwani_errors_total Analyze errors, by source",
                  "# TYPE dhwani_errors_total counter"]
        for src, n in sorted(_errors.items()):
            lines.append(f'dhwani_errors_total{{source="{src}"}} {n}')
        lines += ["# HELP dhwani_analyze_latency_seconds Analyze latency (REST)",
                  "# TYPE dhwani_analyze_latency_seconds summary",
                  f"dhwani_analyze_latency_seconds_count {_lat_count}",
                  f"dhwani_analyze_latency_seconds_sum {_lat_sum:.4f}"]
    return "\n".join(lines) + "\n"
