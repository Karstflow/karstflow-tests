"""Dual-target comparison testing: run same RPC calls against two endpoints.

Enables running the identical test scenario against a reference Solana
validator and karstflow, then automatically comparing results.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from enum import Enum
from typing import Any

from karstflow_tests.config import TestConfig
from karstflow_tests.rpc import RpcClient


class DiffKind(Enum):
    """Classification of a comparison difference."""

    MATCH = "match"
    VALUE_MISMATCH = "value_mismatch"
    TYPE_MISMATCH = "type_mismatch"
    MISSING_FIELD = "missing_field"
    EXTRA_FIELD = "extra_field"
    ERROR_MISMATCH = "error_mismatch"
    BOTH_ERROR = "both_error"
    REFERENCE_ERROR = "reference_error"
    TARGET_ERROR = "target_error"


@dataclass(frozen=True)
class ComparisonResult:
    """Result of comparing a single RPC call against two endpoints."""

    method: str
    params: list[Any] | None
    reference_result: Any
    target_result: Any
    reference_error: dict[str, Any] | None
    target_error: dict[str, Any] | None
    diffs: list[FieldDiff]

    @property
    def matches(self) -> bool:
        return len(self.diffs) == 0

    @property
    def kind(self) -> DiffKind:
        if self.reference_error and self.target_error:
            if self.reference_error.get("code") == self.target_error.get("code"):
                return DiffKind.BOTH_ERROR
            return DiffKind.ERROR_MISMATCH
        if self.reference_error:
            return DiffKind.REFERENCE_ERROR
        if self.target_error:
            return DiffKind.TARGET_ERROR
        return DiffKind.MATCH if self.matches else DiffKind.VALUE_MISMATCH


@dataclass(frozen=True)
class FieldDiff:
    """A single field-level difference between reference and target."""

    path: str
    kind: DiffKind
    reference_value: Any = None
    target_value: Any = None

    def __str__(self) -> str:
        if self.kind == DiffKind.MISSING_FIELD:
            return f"  {self.path}: missing in target (ref={self.reference_value!r})"
        if self.kind == DiffKind.EXTRA_FIELD:
            return f"  {self.path}: extra in target (target={self.target_value!r})"
        return f"  {self.path}: ref={self.reference_value!r} vs target={self.target_value!r}"


# Fields that are inherently different between nodes (slots, hashes, timestamps)
DEFAULT_IGNORE_FIELDS: frozenset[str] = frozenset(
    {
        "context.slot",
        "context.apiVersion",
        "absoluteSlot",
        "blockHeight",
        "slotIndex",
        "transactionCount",
        "slot",
        "blockTime",
        "blockhash",
        "lastValidBlockHeight",
        "feeCalculator",
        "full",
        "incremental",
    }
)


def deep_compare(
    reference: Any,
    target: Any,
    path: str = "",
    ignore_fields: frozenset[str] = DEFAULT_IGNORE_FIELDS,
) -> list[FieldDiff]:
    """Deep compare two JSON-like values, collecting field-level diffs."""
    field_name = path.rsplit(".", 1)[-1] if path else ""
    if field_name in ignore_fields or path in ignore_fields:
        return []

    if isinstance(reference, dict) and isinstance(target, dict):
        diffs: list[FieldDiff] = []
        all_keys = set(reference) | set(target)
        for key in sorted(all_keys):
            child_path = f"{path}.{key}" if path else key
            if key in ignore_fields or child_path in ignore_fields:
                continue
            if key not in target:
                diffs.append(
                    FieldDiff(child_path, DiffKind.MISSING_FIELD, reference_value=reference[key])
                )
            elif key not in reference:
                diffs.append(FieldDiff(child_path, DiffKind.EXTRA_FIELD, target_value=target[key]))
            else:
                diffs.extend(deep_compare(reference[key], target[key], child_path, ignore_fields))
        return diffs

    if isinstance(reference, list) and isinstance(target, list):
        diffs = []
        for i in range(max(len(reference), len(target))):
            child_path = f"{path}[{i}]"
            if i >= len(target):
                diffs.append(
                    FieldDiff(child_path, DiffKind.MISSING_FIELD, reference_value=reference[i])
                )
            elif i >= len(reference):
                diffs.append(FieldDiff(child_path, DiffKind.EXTRA_FIELD, target_value=target[i]))
            else:
                diffs.extend(deep_compare(reference[i], target[i], child_path, ignore_fields))
        return diffs

    if not isinstance(reference, type(target)):
        return [FieldDiff(path, DiffKind.TYPE_MISMATCH, reference, target)]

    if reference != target:
        return [FieldDiff(path, DiffKind.VALUE_MISMATCH, reference, target)]

    return []


class ComparisonClient:
    """Run same RPC calls against reference and target, compare results.

    Usage:
        async with ComparisonClient(
            reference_url="http://localhost:8899",    # Solana reference
            target_url="http://localhost:9899",        # karstflow
        ) as cmp:
            result = await cmp.compare("getVersion")
            assert result.matches

            results = await cmp.compare_many([
                ("getEpochSchedule", None),
                ("getMinimumBalanceForRentExemption", [128]),
                ("getStakeMinimumDelegation", None),
            ])
            for r in results:
                if not r.matches:
                    print(f"{r.method}: {len(r.diffs)} diffs")
    """

    def __init__(
        self,
        reference_url: str,
        target_url: str,
        *,
        ignore_fields: frozenset[str] | None = None,
        timeout: float = 30.0,
    ) -> None:
        ref_config = TestConfig(rpc_url=reference_url)
        tgt_config = TestConfig(rpc_url=target_url)
        self._reference = RpcClient(config=ref_config, timeout=timeout)
        self._target = RpcClient(config=tgt_config, timeout=timeout)
        self._ignore = ignore_fields or DEFAULT_IGNORE_FIELDS
        self.results: list[ComparisonResult] = []

    async def __aenter__(self) -> ComparisonClient:
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()

    async def close(self) -> None:
        await self._reference.close()
        await self._target.close()

    async def compare(
        self,
        method: str,
        params: list[Any] | None = None,
        *,
        ignore_fields: frozenset[str] | None = None,
    ) -> ComparisonResult:
        """Run a single RPC call against both endpoints and compare."""
        ignore = ignore_fields or self._ignore

        ref_resp, tgt_resp = await asyncio.gather(
            self._reference.request_raw(method, params),
            self._target.request_raw(method, params),
            return_exceptions=True,
        )

        ref_error: dict[str, Any] | None = None
        tgt_error: dict[str, Any] | None = None
        ref_result: Any = None
        tgt_result: Any = None

        if isinstance(ref_resp, BaseException):
            ref_error = {"code": -1, "message": str(ref_resp)}
        else:
            ref_result = ref_resp.result
            if ref_resp.error:
                ref_error = {"code": ref_resp.error.code, "message": ref_resp.error.message}

        if isinstance(tgt_resp, BaseException):
            tgt_error = {"code": -1, "message": str(tgt_resp)}
        else:
            tgt_result = tgt_resp.result
            if tgt_resp.error:
                tgt_error = {"code": tgt_resp.error.code, "message": tgt_resp.error.message}

        if ref_error and tgt_error:
            diffs = []
            if ref_error.get("code") != tgt_error.get("code"):
                diffs.append(
                    FieldDiff(
                        "error.code",
                        DiffKind.VALUE_MISMATCH,
                        ref_error.get("code"),
                        tgt_error.get("code"),
                    )
                )
        elif ref_error or tgt_error:
            diffs = [
                FieldDiff(
                    "error",
                    DiffKind.ERROR_MISMATCH,
                    ref_error,
                    tgt_error,
                )
            ]
        else:
            diffs = deep_compare(ref_result, tgt_result, ignore_fields=ignore)

        result = ComparisonResult(
            method=method,
            params=params,
            reference_result=ref_result,
            target_result=tgt_result,
            reference_error=ref_error,
            target_error=tgt_error,
            diffs=diffs,
        )
        self.results.append(result)
        return result

    async def compare_many(
        self,
        calls: list[tuple[str, list[Any] | None]],
    ) -> list[ComparisonResult]:
        """Run multiple comparisons in parallel."""
        tasks = [self.compare(method, params) for method, params in calls]
        return await asyncio.gather(*tasks)

    def report(self) -> str:
        """Generate a human-readable comparison report."""
        if not self.results:
            return "No comparison results."
        matched = sum(1 for r in self.results if r.matches)
        total = len(self.results)
        lines = [
            f"Comparison Report: {matched}/{total} methods match",
            "=" * 60,
        ]
        for r in self.results:
            status = "OK" if r.matches else "DIFF"
            lines.append(f"  [{status}] {r.method}")
            if not r.matches:
                for d in r.diffs[:5]:  # Limit to first 5 diffs per method
                    lines.append(f"    {d}")
                if len(r.diffs) > 5:
                    lines.append(f"    ... and {len(r.diffs) - 5} more diffs")
        return "\n".join(lines)


# Pre-built comparison call lists for common use cases

BASIC_COMPARISON_CALLS: list[tuple[str, list[Any] | None]] = [
    ("getVersion", None),
    ("getGenesisHash", None),
    ("getEpochSchedule", None),
    ("getStakeMinimumDelegation", None),
    ("getMinimumBalanceForRentExemption", [0]),
    ("getMinimumBalanceForRentExemption", [128]),
    ("getMinimumBalanceForRentExemption", [165]),
    ("getMinimumBalanceForRentExemption", [82]),
]

CLUSTER_COMPARISON_CALLS: list[tuple[str, list[Any] | None]] = [
    ("getHealth", None),
    ("getIdentity", None),
    ("getClusterNodes", None),
    ("getVoteAccounts", None),
    ("getLeaderSchedule", None),
    ("getSlot", None),
    ("getBlockHeight", None),
    ("getEpochInfo", None),
    ("getSupply", None),
    ("getInflationRate", None),
    ("getInflationGovernor", None),
]
