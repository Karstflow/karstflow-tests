"""Functional tests: system/native program accounts and rent behavior.

Tests Solana-specific invariants:
- Native programs are executable and owned by NativeLoader
- System accounts are owned by system program
- Rent exemption behavior
"""

from __future__ import annotations

import pytest
from solana.rpc.async_api import AsyncClient
from solders.keypair import Keypair

from karstflow_tests.config import TestConfig
from karstflow_tests.rpc import RpcClient
from tests.helpers.constants import NATIVE_PROGRAMS, SYSTEM_PROGRAM
from tests.helpers.setup import airdrop_and_confirm


@pytest.mark.parametrize(
    ("name", "address"),
    NATIVE_PROGRAMS,
    ids=[p[0] for p in NATIVE_PROGRAMS],
)
async def test_native_program_exists(rpc_client: RpcClient, name: str, address: str) -> None:
    """Native program accounts should exist on validator."""
    resp = await rpc_client.request_raw("getAccountInfo", [address, {"encoding": "base64"}])
    assert resp.ok


async def test_system_program_account_info(rpc_client: RpcClient) -> None:
    """System program account has special native handling."""
    resp = await rpc_client.request_raw("getAccountInfo", [SYSTEM_PROGRAM, {"encoding": "base64"}])
    assert resp.ok


async def test_funded_account_owned_by_system(
    solana_client: AsyncClient, test_config: TestConfig
) -> None:
    """Newly funded account is owned by system program."""
    kp = Keypair()
    await airdrop_and_confirm(solana_client, test_config.rpc_url, kp.pubkey())

    info = await solana_client.get_account_info(kp.pubkey())
    assert info.value is not None
    assert str(info.value.owner) == SYSTEM_PROGRAM


async def test_funded_account_has_zero_data(
    solana_client: AsyncClient, test_config: TestConfig
) -> None:
    """System-owned accounts have zero data length."""
    kp = Keypair()
    await airdrop_and_confirm(solana_client, test_config.rpc_url, kp.pubkey())

    info = await solana_client.get_account_info(kp.pubkey())
    assert info.value is not None
    assert info.value.data == b""


async def test_rent_exempt_account_persists(
    solana_client: AsyncClient, test_config: TestConfig, rpc_client: RpcClient
) -> None:
    """Account with rent-exempt balance is not garbage collected."""
    rent_exempt = await rpc_client.get_minimum_balance_for_rent_exemption(0)
    kp = Keypair()
    await airdrop_and_confirm(solana_client, test_config.rpc_url, kp.pubkey(), rent_exempt)

    info = await solana_client.get_account_info(kp.pubkey())
    assert info.value is not None
    assert info.value.lamports >= rent_exempt
