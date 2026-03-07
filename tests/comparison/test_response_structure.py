"""Response structure comparison tests.

Validates that RPC response shapes (field names, nesting, types) match
between a reference Solana validator and karstflow, regardless of actual values.

Requires: KARSTFLOW_REFERENCE_URL env var pointing to Solana reference node.
"""

from __future__ import annotations

from typing import Any

import pytest

from karstflow_tests.comparison import ComparisonClient


def _collect_shape(obj: Any, path: str = "") -> dict[str, str]:
    """Recursively collect {path: type_name} for every leaf in a JSON-like value."""
    if isinstance(obj, dict):
        shape: dict[str, str] = {}
        for key, val in sorted(obj.items()):
            child = f"{path}.{key}" if path else key
            shape.update(_collect_shape(val, child))
        if not obj:
            shape[path or "(root)"] = "dict(empty)"
        return shape
    if isinstance(obj, list):
        if not obj:
            return {path or "(root)": "list(empty)"}
        # Sample first element only for shape comparison
        return _collect_shape(obj[0], f"{path}[0]")
    return {path or "(root)": type(obj).__name__}


def _compare_shapes(
    reference: Any,
    target: Any,
    method: str,
) -> list[str]:
    """Compare structural shapes and return list of difference descriptions."""
    ref_shape = _collect_shape(reference)
    tgt_shape = _collect_shape(target)
    diffs: list[str] = []
    all_paths = sorted(set(ref_shape) | set(tgt_shape))
    for p in all_paths:
        ref_type = ref_shape.get(p)
        tgt_type = tgt_shape.get(p)
        if ref_type is None:
            diffs.append(f"{method}: extra field '{p}' in target (type={tgt_type})")
        elif tgt_type is None:
            diffs.append(f"{method}: missing field '{p}' in target (ref type={ref_type})")
        elif ref_type != tgt_type:
            diffs.append(f"{method}: type mismatch at '{p}': ref={ref_type} vs target={tgt_type}")
    return diffs


# Methods whose response structure should be identical
STRUCTURE_METHODS: list[tuple[str, list[Any] | None]] = [
    ("getVersion", None),
    ("getEpochSchedule", None),
    ("getEpochInfo", None),
    ("getGenesisHash", None),
    ("getIdentity", None),
    ("getInflationGovernor", None),
    ("getInflationRate", None),
    ("getSupply", None),
    ("getStakeMinimumDelegation", None),
    ("getHealth", None),
    ("getSlot", None),
    ("getBlockHeight", None),
    ("getMinimumBalanceForRentExemption", [128]),
]


@pytest.mark.parametrize(
    ("method", "params"),
    STRUCTURE_METHODS,
    ids=[c[0] for c in STRUCTURE_METHODS],
)
async def test_response_structure_matches(
    comparison_client: ComparisonClient,
    method: str,
    params: list[Any] | None,
) -> None:
    """Verify response structure (field names and types) matches reference."""
    result = await comparison_client.compare(method, params)
    assert result.reference_error is None, f"Reference error for {method}: {result.reference_error}"
    assert result.target_error is None, f"Target error for {method}: {result.target_error}"

    diffs = _compare_shapes(result.reference_result, result.target_result, method)
    assert not diffs, f"Structure mismatch for {method}:\n" + "\n".join(diffs)


async def test_context_wrapper_present(comparison_client: ComparisonClient) -> None:
    """Verify methods that return context-wrapped results have the wrapper."""
    context_methods = [
        ("getBalance", ["11111111111111111111111111111111"]),
        ("getEpochInfo", None),
        ("getSupply", None),
        ("getStakeMinimumDelegation", None),
    ]
    for method, params in context_methods:
        result = await comparison_client.compare(method, params)
        if result.reference_error or result.target_error:
            continue
        ref = result.reference_result
        tgt = result.target_result
        if isinstance(ref, dict) and "context" in ref:
            assert isinstance(tgt, dict), (
                f"{method}: reference has context wrapper but target is {type(tgt).__name__}"
            )
            assert "context" in tgt, f"{method}: reference has context wrapper but target does not"
            assert "slot" in ref["context"], f"{method}: reference context missing 'slot'"
            assert "slot" in tgt["context"], f"{method}: target context missing 'slot'"


async def test_error_shape_consistency(comparison_client: ComparisonClient) -> None:
    """Verify error responses have consistent structure."""
    error_calls = [
        ("getBalance", ["not-a-valid-pubkey"]),
        ("getAccountInfo", ["not-a-valid-pubkey"]),
    ]
    for method, params in error_calls:
        result = await comparison_client.compare(method, params)
        # Both should return errors for invalid inputs
        if result.reference_error and result.target_error:
            ref_keys = set(result.reference_error.keys())
            tgt_keys = set(result.target_error.keys())
            assert ref_keys == tgt_keys, (
                f"{method}: error shape mismatch: ref keys={ref_keys} vs target keys={tgt_keys}"
            )
