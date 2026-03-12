"""Functional tests: nonce account deep coverage.

Tests nonce account lifecycle, advance, authority, and durable tx usage.
"""

from __future__ import annotations

import base64 as b64

from solana.rpc.async_api import AsyncClient
from solders.pubkey import Pubkey

from karstflow_tests.config import TestConfig
from karstflow_tests.programs import create_nonce_account
from karstflow_tests.rpc import RpcClient
from tests.helpers.setup import funded_sender


async def test_nonce_account_data_80_bytes(
    solana_client: AsyncClient,
    rpc_client: RpcClient,
    test_config: TestConfig,
) -> None:
    """Nonce account data is exactly 80 bytes."""
    payer = await funded_sender(solana_client, test_config.rpc_url, 10_000_000_000)
    nonce_kp = await create_nonce_account(solana_client, payer)

    resp = await rpc_client.get_account_info(str(nonce_kp.pubkey()), encoding="base64")
    assert resp is not None
    info = resp["value"]
    assert info is not None
    data = b64.b64decode(info["data"][0])
    assert len(data) == 80


async def test_nonce_account_owned_by_system(
    solana_client: AsyncClient,
    rpc_client: RpcClient,
    test_config: TestConfig,
) -> None:
    """Nonce account is owned by system program."""
    payer = await funded_sender(solana_client, test_config.rpc_url, 10_000_000_000)
    nonce_kp = await create_nonce_account(solana_client, payer)

    resp = await rpc_client.get_account_info(str(nonce_kp.pubkey()))
    assert resp is not None
    info = resp["value"]
    assert info is not None
    assert info["owner"] == "11111111111111111111111111111111"


async def test_nonce_account_is_rent_exempt(
    solana_client: AsyncClient,
    rpc_client: RpcClient,
    test_config: TestConfig,
) -> None:
    """Nonce account balance meets rent exemption."""
    payer = await funded_sender(solana_client, test_config.rpc_url, 10_000_000_000)
    nonce_kp = await create_nonce_account(solana_client, payer)

    min_rent = await rpc_client.get_minimum_balance_for_rent_exemption(80)
    resp = await rpc_client.get_account_info(str(nonce_kp.pubkey()))
    assert resp is not None
    info = resp["value"]
    assert info is not None
    assert info["lamports"] >= min_rent


async def test_nonce_authority_matches_creator(
    solana_client: AsyncClient,
    rpc_client: RpcClient,
    test_config: TestConfig,
) -> None:
    """Nonce authority field matches the payer (creator)."""
    payer = await funded_sender(solana_client, test_config.rpc_url, 10_000_000_000)
    nonce_kp = await create_nonce_account(solana_client, payer)

    resp = await rpc_client.get_account_info(str(nonce_kp.pubkey()), encoding="base64")
    assert resp is not None
    info = resp["value"]
    assert info is not None
    data = b64.b64decode(info["data"][0])
    # Nonce layout: 4B version + 4B state + 32B authority + 32B blockhash
    # Authority is at offset 8
    authority_bytes = data[8:40]
    authority = Pubkey.from_bytes(authority_bytes)
    assert authority == payer.pubkey()


async def test_nonce_has_stored_blockhash(
    solana_client: AsyncClient,
    rpc_client: RpcClient,
    test_config: TestConfig,
) -> None:
    """Nonce account stores a blockhash value."""
    payer = await funded_sender(solana_client, test_config.rpc_url, 10_000_000_000)
    nonce_kp = await create_nonce_account(solana_client, payer)

    resp = await rpc_client.get_account_info(str(nonce_kp.pubkey()), encoding="base64")
    assert resp is not None
    info = resp["value"]
    assert info is not None
    data = b64.b64decode(info["data"][0])
    # Blockhash is at offset 40, 32 bytes
    blockhash_bytes = data[40:72]
    # Should not be all zeros
    assert blockhash_bytes != b"\x00" * 32
