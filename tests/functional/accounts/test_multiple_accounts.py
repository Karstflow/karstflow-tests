"""Functional tests: getMultipleAccounts RPC method."""

from __future__ import annotations

from solana.rpc.async_api import AsyncClient
from solders.keypair import Keypair
from solders.pubkey import Pubkey

from karstflow_tests.config import TestConfig
from karstflow_tests.rpc import RpcClient
from karstflow_tests.wait import wait_for_confirmation


async def test_multiple_accounts_mixed(solana_client: AsyncClient, test_config: TestConfig) -> None:
    """Batch query returns funded and unfunded accounts correctly."""
    funded = Keypair()
    unfunded = Keypair()
    resp = await solana_client.request_airdrop(funded.pubkey(), 1_000_000_000)
    await wait_for_confirmation(test_config.rpc_url, str(resp.value))

    result = await solana_client.get_multiple_accounts([funded.pubkey(), unfunded.pubkey()])
    accounts = result.value
    assert len(accounts) == 2
    assert accounts[0] is not None
    assert accounts[0].lamports == 1_000_000_000
    assert accounts[1] is None


async def test_multiple_accounts_all_nonexistent(solana_client: AsyncClient) -> None:
    """All non-existent accounts return None."""
    keys = [Keypair().pubkey() for _ in range(3)]
    result = await solana_client.get_multiple_accounts(keys)
    assert all(acc is None for acc in result.value)


async def test_multiple_accounts_empty_list(rpc_client: RpcClient) -> None:
    """Empty pubkey list returns empty result."""
    result = await rpc_client.get_multiple_accounts([])
    assert isinstance(result, dict)
    assert "value" in result


async def test_multiple_accounts_system_program(solana_client: AsyncClient) -> None:
    """Can query system program via getMultipleAccounts."""
    system = Pubkey.from_string("11111111111111111111111111111111")
    result = await solana_client.get_multiple_accounts([system])
    assert len(result.value) == 1
