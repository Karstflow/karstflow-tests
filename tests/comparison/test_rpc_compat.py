"""RPC compatibility comparison tests.

Runs the same RPC calls against both a reference Solana validator
and karstflow, then compares results for compatibility.

Requires: KARSTFLOW_REFERENCE_URL env var pointing to Solana reference node.
"""

import pytest

from karstflow_tests.comparison import (
    BASIC_COMPARISON_CALLS,
    CLUSTER_COMPARISON_CALLS,
    ComparisonClient,
)


async def test_basic_rpc_compatibility(comparison_client: ComparisonClient) -> None:
    """Verify basic RPC methods return compatible results."""
    results = await comparison_client.compare_many(BASIC_COMPARISON_CALLS)
    failures = [r for r in results if not r.matches]
    if failures:
        lines = [f"{len(failures)}/{len(results)} methods differ:"]
        for r in failures:
            lines.append(f"  {r.method}: {len(r.diffs)} diffs")
            for d in r.diffs[:3]:
                lines.append(f"    {d}")
        pytest.fail("\n".join(lines))


async def test_version_format(comparison_client: ComparisonClient) -> None:
    """Verify getVersion response has the same fields."""
    result = await comparison_client.compare("getVersion")
    # We expect solana-core and feature-set fields to exist in both
    assert result.reference_result is not None
    assert result.target_result is not None
    assert "solana-core" in result.reference_result
    assert "solana-core" in result.target_result
    assert "feature-set" in result.reference_result
    assert "feature-set" in result.target_result


async def test_epoch_schedule_match(comparison_client: ComparisonClient) -> None:
    """Verify epoch schedule matches reference."""
    result = await comparison_client.compare("getEpochSchedule")
    assert result.matches, f"Epoch schedule differs:\n{comparison_client.report()}"


async def test_rent_exemption_amounts(comparison_client: ComparisonClient) -> None:
    """Verify rent exemption calculation matches for common sizes."""
    sizes = [0, 32, 82, 128, 165, 200, 1024, 10240]
    calls = [("getMinimumBalanceForRentExemption", [s]) for s in sizes]
    results = await comparison_client.compare_many(calls)
    for r in results:
        assert r.matches, (
            f"Rent exemption differs for size {r.params}: "
            f"ref={r.reference_result} vs target={r.target_result}"
        )


async def test_stake_minimum_delegation(comparison_client: ComparisonClient) -> None:
    """Verify stake minimum delegation matches reference."""
    result = await comparison_client.compare("getStakeMinimumDelegation")
    # Compare the value inside the context wrapper
    ref_val = (
        result.reference_result.get("value")
        if isinstance(result.reference_result, dict)
        else result.reference_result
    )
    tgt_val = (
        result.target_result.get("value")
        if isinstance(result.target_result, dict)
        else result.target_result
    )
    assert ref_val == tgt_val, f"Stake min delegation: ref={ref_val} vs target={tgt_val}"


@pytest.mark.parametrize(
    ("method", "params"), CLUSTER_COMPARISON_CALLS, ids=[c[0] for c in CLUSTER_COMPARISON_CALLS]
)
async def test_cluster_methods_no_error(
    comparison_client: ComparisonClient,
    method: str,
    params: list | None,
) -> None:
    """Verify cluster methods don't return errors on either side."""
    result = await comparison_client.compare(method, params)
    assert result.reference_error is None, f"Reference error for {method}: {result.reference_error}"
    assert result.target_error is None, f"Target error for {method}: {result.target_error}"
