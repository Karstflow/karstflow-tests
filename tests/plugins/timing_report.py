"""Pytest plugin: per-test timing report and session-level statistics.

Activated with --timing-report flag. Produces a timing summary after the session
showing slowest tests and timing distribution.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

import pytest


@dataclass
class TestTiming:
    """Timing data for a single test."""

    nodeid: str
    duration: float
    outcome: str  # "passed", "failed", "skipped"
    markers: list[str] = field(default_factory=list)


class TimingCollector:
    """Collects timing data across the test session."""

    def __init__(self) -> None:
        self.tests: list[TestTiming] = []
        self.by_marker: dict[str, list[TestTiming]] = defaultdict(list)

    def record(self, timing: TestTiming) -> None:
        self.tests.append(timing)
        for m in timing.markers:
            self.by_marker[m].append(timing)

    def slowest(self, n: int = 20) -> list[TestTiming]:
        return sorted(self.tests, key=lambda t: t.duration, reverse=True)[:n]

    def by_outcome(self, outcome: str) -> list[TestTiming]:
        return [t for t in self.tests if t.outcome == outcome]

    def total_duration(self) -> float:
        return sum(t.duration for t in self.tests)

    def marker_summary(self) -> dict[str, tuple[int, float]]:
        """Return {marker: (count, total_seconds)} for each marker."""
        result: dict[str, tuple[int, float]] = {}
        for marker, timings in self.by_marker.items():
            total = sum(t.duration for t in timings)
            result[marker] = (len(timings), total)
        return result

    def report(self, top_n: int = 20) -> str:
        lines = [
            f"Test Timing Report ({len(self.tests)} tests, {self.total_duration():.1f}s total)",
            "=" * 80,
            "",
        ]

        # Summary by marker
        marker_data = self.marker_summary()
        if marker_data:
            lines.append("By marker:")
            for marker, (count, total) in sorted(
                marker_data.items(), key=lambda x: x[1][1], reverse=True
            ):
                avg = total / count if count else 0
                lines.append(
                    f"  {marker:<20} {count:>4} tests  {total:>7.1f}s total  {avg:>5.1f}s avg"
                )
            lines.append("")

        # Outcome summary
        passed = len(self.by_outcome("passed"))
        failed = len(self.by_outcome("failed"))
        skipped = len(self.by_outcome("skipped"))
        lines.append(f"Outcomes: {passed} passed, {failed} failed, {skipped} skipped")
        lines.append("")

        # Slowest tests
        slowest = self.slowest(top_n)
        if slowest:
            lines.append(f"Top {min(top_n, len(slowest))} slowest tests:")
            for t in slowest:
                status = "PASS" if t.outcome == "passed" else t.outcome.upper()[:4]
                lines.append(f"  [{status}] {t.duration:>6.2f}s  {t.nodeid}")

        return "\n".join(lines)


_collector = TimingCollector()


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--timing-report",
        action="store_true",
        default=False,
        help="Print per-test timing report after session.",
    )


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo) -> None:  # type: ignore[type-arg]
    if call.when != "call":
        return
    markers = [m.name for m in item.iter_markers()]
    _collector.record(
        TestTiming(
            nodeid=item.nodeid,
            duration=call.duration,
            outcome="passed" if call.excinfo is None else "failed",
            markers=markers,
        )
    )


def pytest_runtest_logreport(report: pytest.TestReport) -> None:
    if report.when == "call" and report.skipped:
        # Update last recorded test outcome to skipped
        for t in reversed(_collector.tests):
            if t.nodeid == report.nodeid:
                # Create a new timing with skipped outcome
                _collector.tests.remove(t)
                _collector.record(
                    TestTiming(
                        nodeid=t.nodeid,
                        duration=t.duration,
                        outcome="skipped",
                        markers=t.markers,
                    )
                )
                break


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    if not session.config.getoption("timing_report", default=False):
        return
    if not _collector.tests:
        return
    report = _collector.report()
    print("\n" + report)
