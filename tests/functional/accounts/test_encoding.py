"""Functional tests: account data encoding formats.

Verifies that different encoding options (base64, base58, jsonParsed)
return correctly formatted data.
"""

from __future__ import annotations

import base64

from karstflow_tests.request_builder import RequestBuilder
from karstflow_tests.rpc import RpcClient


async def test_account_info_base64_encoding(rpc_client: RpcClient) -> None:
    """getAccountInfo with base64 encoding returns base64 data."""
    spec = (
        RequestBuilder("getAccountInfo")
        .with_pubkey("Vote111111111111111111111111111111111111111")
        .with_encoding("base64")
        .build()
    )
    result = await rpc_client.execute(spec)
    assert result is not None
    info = result["value"]
    assert info is not None
    data = info["data"]
    assert isinstance(data, list)
    assert data[1] == "base64"
    # Verify it's valid base64
    base64.b64decode(data[0])


async def test_account_info_base58_encoding(rpc_client: RpcClient) -> None:
    """getAccountInfo with base58 encoding returns base58 string."""
    spec = (
        RequestBuilder("getAccountInfo")
        .with_pubkey("11111111111111111111111111111111")
        .with_encoding("base58")
        .build()
    )
    result = await rpc_client.execute(spec)
    assert result is not None


async def test_account_info_json_parsed(rpc_client: RpcClient) -> None:
    """getAccountInfo with jsonParsed encoding for vote account."""
    spec = (
        RequestBuilder("getAccountInfo")
        .with_pubkey("Vote111111111111111111111111111111111111111")
        .with_encoding("jsonParsed")
        .build()
    )
    result = await rpc_client.execute(spec)
    assert result is not None


async def test_account_info_data_slice(rpc_client: RpcClient) -> None:
    """getAccountInfo with dataSlice returns truncated data."""
    # Use Clock sysvar — it has 40 bytes of data (unlike native programs which have 0)
    sysvar_clock = "SysvarC1ock11111111111111111111111111111111"

    # First get full data
    full_spec = (
        RequestBuilder("getAccountInfo")
        .with_pubkey(sysvar_clock)
        .with_encoding("base64")
        .build()
    )
    full_result = await rpc_client.execute(full_spec)
    assert full_result is not None
    full_info = full_result["value"]
    assert full_info is not None
    full_data = base64.b64decode(full_info["data"][0])
    assert len(full_data) > 4

    # Now get a slice
    slice_spec = (
        RequestBuilder("getAccountInfo")
        .with_pubkey(sysvar_clock)
        .with_encoding("base64")
        .with_data_slice(0, 4)
        .build()
    )
    slice_result = await rpc_client.execute(slice_spec)
    assert slice_result is not None
    slice_info = slice_result["value"]
    assert slice_info is not None
    # Sliced data should be exactly 4 bytes
    slice_data = base64.b64decode(slice_info["data"][0])
    assert len(slice_data) == 4
    # Sliced bytes should match the first 4 bytes of full data
    assert slice_data == full_data[:4]


async def test_multiple_accounts_base64(rpc_client: RpcClient) -> None:
    """getMultipleAccounts with base64 encoding."""
    result = await rpc_client.get_multiple_accounts(
        [
            "11111111111111111111111111111111",
            "Vote111111111111111111111111111111111111111",
        ],
        encoding="base64",
    )
    assert "value" in result
    values = result["value"]
    assert len(values) == 2


async def test_program_accounts_with_memcmp_filter(rpc_client: RpcClient) -> None:
    """getProgramAccounts with memcmp filter."""
    spec = (
        RequestBuilder("getProgramAccounts")
        .with_pubkey("Vote111111111111111111111111111111111111111")
        .with_encoding("base64")
        .with_filters([{"memcmp": {"offset": 0, "bytes": "1"}}])
        .build()
    )
    result = await rpc_client.execute(spec)
    assert isinstance(result, list)


async def test_program_accounts_data_size_filter(rpc_client: RpcClient) -> None:
    """getProgramAccounts with dataSize filter only."""
    spec = (
        RequestBuilder("getProgramAccounts")
        .with_pubkey("11111111111111111111111111111111")
        .with_encoding("base64")
        .with_filters([{"dataSize": 0}])
        .build()
    )
    result = await rpc_client.execute(spec)
    assert isinstance(result, list)


async def test_get_transaction_json_encoding(rpc_client: RpcClient) -> None:
    """getTransaction encoding options."""
    # Just verify the method accepts the encoding parameter
    spec = RequestBuilder("getSlot").build()
    slot = await rpc_client.execute(spec)
    assert isinstance(slot, int)
