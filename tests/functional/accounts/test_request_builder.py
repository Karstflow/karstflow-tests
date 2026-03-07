"""Tests using the RequestBuilder fluent API for custom RPC requests."""

from __future__ import annotations

from karstflow_tests.request_builder import RequestBuilder
from karstflow_tests.rpc import RpcClient


async def test_builder_get_slot(rpc_client: RpcClient) -> None:
    """Build and execute a getSlot request."""
    spec = RequestBuilder("getSlot").with_commitment("confirmed").build()
    result = await rpc_client.execute(spec)
    assert isinstance(result, int)
    assert result > 0


async def test_builder_get_account_info(rpc_client: RpcClient) -> None:
    """Build a getAccountInfo request with encoding and commitment."""
    spec = (
        RequestBuilder("getAccountInfo")
        .with_pubkey("11111111111111111111111111111111")
        .with_encoding("base64")
        .with_commitment("confirmed")
        .build()
    )
    result = await rpc_client.execute(spec)
    assert result is not None
    assert result["executable"]


async def test_builder_get_account_with_data_slice(rpc_client: RpcClient) -> None:
    """Build a getAccountInfo request with dataSlice."""
    spec = (
        RequestBuilder("getAccountInfo")
        .with_pubkey("Vote111111111111111111111111111111111111111")
        .with_encoding("base64")
        .with_data_slice(0, 0)
        .build()
    )
    result = await rpc_client.execute(spec)
    # Vote program exists but is native, should return info
    assert result is not None


async def test_builder_get_program_accounts_with_filter(rpc_client: RpcClient) -> None:
    """Build a getProgramAccounts with dataSize filter."""
    spec = (
        RequestBuilder("getProgramAccounts")
        .with_pubkey("Vote111111111111111111111111111111111111111")
        .with_encoding("base64")
        .with_filters([{"dataSize": 3762}])
        .build()
    )
    result = await rpc_client.execute(spec)
    assert isinstance(result, list)


async def test_builder_batch_execution(rpc_client: RpcClient) -> None:
    """Execute multiple builder specs as a batch."""
    specs = [
        RequestBuilder("getSlot").with_commitment("confirmed").build(),
        RequestBuilder("getBlockHeight").with_commitment("confirmed").build(),
        RequestBuilder("getHealth").build(),
        RequestBuilder("getVersion").build(),
    ]
    responses = await rpc_client.execute_batch(specs)
    assert len(responses) == 4
    assert all(r.ok for r in responses)


async def test_builder_get_balance(rpc_client: RpcClient) -> None:
    """Build a getBalance request."""
    spec = (
        RequestBuilder("getBalance")
        .with_pubkey("11111111111111111111111111111111")
        .with_commitment("finalized")
        .build()
    )
    result = await rpc_client.execute(spec)
    assert isinstance(result, dict)
    assert "value" in result


async def test_builder_with_limit(rpc_client: RpcClient) -> None:
    """Build a getRecentPerformanceSamples with positional limit."""
    spec = RequestBuilder("getRecentPerformanceSamples").with_positional(5).build()
    result = await rpc_client.execute(spec)
    assert isinstance(result, list)
    assert len(result) <= 5


async def test_builder_raw_execution(rpc_client: RpcClient) -> None:
    """Execute builder spec and get full RpcResponse."""
    spec = RequestBuilder("getSlot").build()
    response = await rpc_client.execute_raw(spec)
    assert response.ok
    assert isinstance(response.result, int)


async def test_builder_spec_immutability(rpc_client: RpcClient) -> None:
    """RpcRequestSpec is immutable (frozen dataclass)."""
    spec = RequestBuilder("getSlot").with_commitment("confirmed").build()
    assert spec.method == "getSlot"
    assert spec.commitment == "confirmed"
    # Verify it's actually frozen
    try:
        spec.method = "other"
        msg = "Should have raised FrozenInstanceError"
        raise AssertionError(msg)
    except AttributeError:
        pass
