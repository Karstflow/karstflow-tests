"""RPC middleware/interceptor chain for request/response processing.

Provides composable middleware that wraps RPC calls to add:
- Timing measurement per method
- Request/response logging
- Call recording for replay and analysis
- Error classification and statistics
"""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Protocol


class RpcInterceptor(Protocol):
    """Protocol for RPC call interceptors."""

    async def before(self, method: str, params: list[Any] | None) -> None: ...
    async def after(
        self,
        method: str,
        params: list[Any] | None,
        result: Any,
        error: dict[str, Any] | None,
        elapsed_ms: float,
    ) -> None: ...


@dataclass
class CallRecord:
    """Single recorded RPC call."""

    method: str
    params: list[Any] | None
    result: Any
    error: dict[str, Any] | None
    elapsed_ms: float
    timestamp: float


@dataclass
class MethodStats:
    """Aggregated statistics for a single RPC method."""

    call_count: int = 0
    error_count: int = 0
    total_ms: float = 0.0
    min_ms: float = float("inf")
    max_ms: float = 0.0

    @property
    def avg_ms(self) -> float:
        return self.total_ms / self.call_count if self.call_count else 0.0

    def record(self, elapsed_ms: float, is_error: bool) -> None:
        self.call_count += 1
        if is_error:
            self.error_count += 1
        self.total_ms += elapsed_ms
        self.min_ms = min(self.min_ms, elapsed_ms)
        self.max_ms = max(self.max_ms, elapsed_ms)


class TimingInterceptor:
    """Records per-method timing statistics."""

    def __init__(self) -> None:
        self.stats: dict[str, MethodStats] = defaultdict(MethodStats)

    async def before(self, method: str, params: list[Any] | None) -> None:
        pass

    async def after(
        self,
        method: str,
        params: list[Any] | None,
        result: Any,
        error: dict[str, Any] | None,
        elapsed_ms: float,
    ) -> None:
        self.stats[method].record(elapsed_ms, error is not None)

    def report(self) -> str:
        """Generate a timing report sorted by total time."""
        if not self.stats:
            return "No RPC calls recorded."
        lines = [
            f"{'Method':<40} {'Calls':>6} {'Errs':>5} {'Avg ms':>8} "
            f"{'Min ms':>8} {'Max ms':>8} {'Total ms':>10}",
            "-" * 95,
        ]
        for method, s in sorted(self.stats.items(), key=lambda x: x[1].total_ms, reverse=True):
            lines.append(
                f"{method:<40} {s.call_count:>6} {s.error_count:>5} {s.avg_ms:>8.1f} "
                f"{s.min_ms:>8.1f} {s.max_ms:>8.1f} {s.total_ms:>10.1f}"
            )
        lines.append("-" * 95)
        total_calls = sum(s.call_count for s in self.stats.values())
        total_errors = sum(s.error_count for s in self.stats.values())
        total_time = sum(s.total_ms for s in self.stats.values())
        lines.append(
            f"{'TOTAL':<40} {total_calls:>6} {total_errors:>5}"
            f" {'':>8} {'':>8} {'':>8} {total_time:>10.1f}"
        )
        return "\n".join(lines)

    def reset(self) -> None:
        self.stats.clear()


class RecordingInterceptor:
    """Records all RPC calls for later replay or analysis."""

    def __init__(self, *, max_records: int = 10000) -> None:
        self.records: list[CallRecord] = []
        self._max = max_records

    async def before(self, method: str, params: list[Any] | None) -> None:
        pass

    async def after(
        self,
        method: str,
        params: list[Any] | None,
        result: Any,
        error: dict[str, Any] | None,
        elapsed_ms: float,
    ) -> None:
        if len(self.records) < self._max:
            self.records.append(
                CallRecord(
                    method=method,
                    params=params,
                    result=result,
                    error=error,
                    elapsed_ms=elapsed_ms,
                    timestamp=time.time(),
                )
            )

    def calls_for(self, method: str) -> list[CallRecord]:
        """Return all recorded calls for a specific method."""
        return [r for r in self.records if r.method == method]

    def errors(self) -> list[CallRecord]:
        """Return all recorded calls that resulted in errors."""
        return [r for r in self.records if r.error is not None]

    @property
    def methods_called(self) -> set[str]:
        return {r.method for r in self.records}

    def reset(self) -> None:
        self.records.clear()


class ErrorClassifier:
    """Classifies and counts RPC errors by code and method."""

    def __init__(self) -> None:
        self.by_code: dict[int, int] = defaultdict(int)
        self.by_method: dict[str, dict[int, int]] = defaultdict(lambda: defaultdict(int))

    async def before(self, method: str, params: list[Any] | None) -> None:
        pass

    async def after(
        self,
        method: str,
        params: list[Any] | None,
        result: Any,
        error: dict[str, Any] | None,
        elapsed_ms: float,
    ) -> None:
        if error is not None:
            code = error.get("code", -1)
            self.by_code[code] += 1
            self.by_method[method][code] += 1

    def report(self) -> str:
        if not self.by_code:
            return "No RPC errors recorded."
        lines = ["Error distribution by code:"]
        for code, count in sorted(self.by_code.items()):
            lines.append(f"  {code}: {count} occurrences")
        lines.append("\nError distribution by method:")
        for method, codes in sorted(self.by_method.items()):
            parts = ", ".join(f"{c}:{n}" for c, n in sorted(codes.items()))
            lines.append(f"  {method}: {parts}")
        return "\n".join(lines)


@dataclass
class MiddlewareChain:
    """Composable chain of RPC interceptors."""

    interceptors: list[Any] = field(default_factory=list)

    def add(self, interceptor: Any) -> MiddlewareChain:
        self.interceptors.append(interceptor)
        return self

    async def run_before(self, method: str, params: list[Any] | None) -> None:
        for i in self.interceptors:
            await i.before(method, params)

    async def run_after(
        self,
        method: str,
        params: list[Any] | None,
        result: Any,
        error: dict[str, Any] | None,
        elapsed_ms: float,
    ) -> None:
        for i in self.interceptors:
            await i.after(method, params, result, error, elapsed_ms)

    def get(self, interceptor_type: type) -> Any | None:
        """Find an interceptor by type."""
        for i in self.interceptors:
            if isinstance(i, interceptor_type):
                return i
        return None


def default_middleware() -> MiddlewareChain:
    """Create the default middleware chain with timing + recording."""
    return MiddlewareChain(
        interceptors=[
            TimingInterceptor(),
            RecordingInterceptor(),
            ErrorClassifier(),
        ]
    )
