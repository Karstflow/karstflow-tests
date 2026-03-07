"""Functional tests: token account query methods.

Covers getTokenAccountsByDelegate, getTokenLargestAccounts, and
related token query edge cases.
"""

from __future__ import annotations

from solana.rpc.async_api import AsyncClient
from solders.keypair import Keypair

from karstflow_tests.config import TestConfig
from karstflow_tests.rpc import RpcClient
from karstflow_tests.token import create_mint, create_token_account, mint_to
from tests.helpers.setup import funded_sender


async def test_token_largest_accounts(
    solana_client: AsyncClient,
    rpc_client: RpcClient,
    test_config: TestConfig,
) -> None:
    """getTokenLargestAccounts returns accounts sorted by balance."""
    authority = await funded_sender(solana_client, test_config.rpc_url, 10_000_000_000)
    mint_kp = await create_mint(solana_client, authority, decimals=6)

    acc1 = await create_token_account(
        solana_client, authority, mint_kp.pubkey(), authority.pubkey()
    )
    await mint_to(solana_client, authority, mint_kp.pubkey(), acc1.pubkey(), authority, 5000)

    result = await rpc_client.get_token_largest_accounts(str(mint_kp.pubkey()))
    assert "value" in result
    accounts = result["value"]
    assert len(accounts) >= 1
    assert accounts[0]["amount"] == "5000"


async def test_token_largest_accounts_empty_mint(
    solana_client: AsyncClient,
    rpc_client: RpcClient,
    test_config: TestConfig,
) -> None:
    """getTokenLargestAccounts for mint with no token accounts."""
    authority = await funded_sender(solana_client, test_config.rpc_url)
    mint_kp = await create_mint(solana_client, authority, decimals=6)

    result = await rpc_client.get_token_largest_accounts(str(mint_kp.pubkey()))
    assert "value" in result
    # May be empty or have zero-balance accounts
    assert isinstance(result["value"], list)


async def test_token_largest_accounts_multiple(
    solana_client: AsyncClient,
    rpc_client: RpcClient,
    test_config: TestConfig,
) -> None:
    """getTokenLargestAccounts with multiple holders is sorted descending."""
    authority = await funded_sender(solana_client, test_config.rpc_url, 10_000_000_000)
    holder2 = await funded_sender(solana_client, test_config.rpc_url)
    mint_kp = await create_mint(solana_client, authority, decimals=6)

    acc1 = await create_token_account(
        solana_client, authority, mint_kp.pubkey(), authority.pubkey()
    )
    acc2 = await create_token_account(solana_client, holder2, mint_kp.pubkey(), holder2.pubkey())

    await mint_to(solana_client, authority, mint_kp.pubkey(), acc1.pubkey(), authority, 3000)
    await mint_to(solana_client, authority, mint_kp.pubkey(), acc2.pubkey(), authority, 7000)

    result = await rpc_client.get_token_largest_accounts(str(mint_kp.pubkey()))
    accounts = result["value"]
    assert len(accounts) >= 2
    # Should be sorted descending
    amounts = [int(a["amount"]) for a in accounts]
    assert amounts == sorted(amounts, reverse=True)


async def test_token_accounts_by_delegate_empty(
    rpc_client: RpcClient,
) -> None:
    """getTokenAccountsByDelegate for random key returns empty."""
    kp = Keypair()
    result = await rpc_client.get_token_accounts_by_delegate(
        str(kp.pubkey()),
        program_id="TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
    )
    assert "value" in result
    assert isinstance(result["value"], list)
    assert len(result["value"]) == 0


async def test_is_blockhash_valid_via_wrapper(
    solana_client: AsyncClient,
    rpc_client: RpcClient,
) -> None:
    """isBlockhashValid wrapper returns valid for fresh blockhash."""
    resp = await solana_client.get_latest_blockhash()
    blockhash = str(resp.value.blockhash)

    result = await rpc_client.is_blockhash_valid(blockhash)
    assert "value" in result
    assert result["value"] is True
    assert "context" in result
