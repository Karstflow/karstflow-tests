"""Functional tests: advanced SPL Token operations.

Tests token operations beyond basic lifecycle: multiple mints,
cross-account transfers, decimal precision, error conditions.
"""

from __future__ import annotations

from solana.rpc.async_api import AsyncClient

from karstflow_tests.config import TestConfig
from karstflow_tests.rpc import RpcClient
from karstflow_tests.token import (
    burn_tokens,
    create_mint,
    create_token_account,
    mint_to,
    token_transfer,
)
from tests.helpers.setup import funded_sender


async def test_mint_zero_decimals(
    solana_client: AsyncClient,
    raw_rpc: RpcClient,
    test_config: TestConfig,
) -> None:
    """Mint with 0 decimals (NFT-like) works correctly."""
    authority = await funded_sender(solana_client, test_config.rpc_url)
    mint_kp = await create_mint(solana_client, authority, decimals=0)
    account = await create_token_account(
        solana_client, authority, mint_kp.pubkey(), authority.pubkey()
    )

    await mint_to(solana_client, authority, mint_kp.pubkey(), account.pubkey(), authority, 1)

    balance = await raw_rpc.get_token_account_balance(str(account.pubkey()))
    assert balance["value"]["amount"] == "1"
    assert balance["value"]["decimals"] == 0
    assert balance["value"]["uiAmount"] == 1.0


async def test_mint_max_decimals(
    solana_client: AsyncClient,
    raw_rpc: RpcClient,
    test_config: TestConfig,
) -> None:
    """Mint with 9 decimals works correctly."""
    authority = await funded_sender(solana_client, test_config.rpc_url)
    mint_kp = await create_mint(solana_client, authority, decimals=9)
    account = await create_token_account(
        solana_client, authority, mint_kp.pubkey(), authority.pubkey()
    )

    await mint_to(
        solana_client, authority, mint_kp.pubkey(), account.pubkey(), authority, 1_000_000_000
    )

    balance = await raw_rpc.get_token_account_balance(str(account.pubkey()))
    assert balance["value"]["amount"] == "1000000000"
    assert balance["value"]["decimals"] == 9
    assert balance["value"]["uiAmount"] == 1.0


async def test_transfer_partial_balance(
    solana_client: AsyncClient,
    raw_rpc: RpcClient,
    test_config: TestConfig,
) -> None:
    """Transfer a portion of token balance."""
    authority = await funded_sender(solana_client, test_config.rpc_url, 10_000_000_000)
    mint_kp = await create_mint(solana_client, authority, decimals=6)
    src = await create_token_account(solana_client, authority, mint_kp.pubkey(), authority.pubkey())

    receiver = await funded_sender(solana_client, test_config.rpc_url)
    dst = await create_token_account(solana_client, receiver, mint_kp.pubkey(), receiver.pubkey())

    await mint_to(solana_client, authority, mint_kp.pubkey(), src.pubkey(), authority, 1_000_000)
    await token_transfer(solana_client, authority, src.pubkey(), dst.pubkey(), 400_000)

    src_bal = await raw_rpc.get_token_account_balance(str(src.pubkey()))
    dst_bal = await raw_rpc.get_token_account_balance(str(dst.pubkey()))
    assert src_bal["value"]["amount"] == "600000"
    assert dst_bal["value"]["amount"] == "400000"


async def test_multiple_mints_independent(
    solana_client: AsyncClient,
    raw_rpc: RpcClient,
    test_config: TestConfig,
) -> None:
    """Two independent mints don't interfere with each other."""
    authority = await funded_sender(solana_client, test_config.rpc_url, 10_000_000_000)

    mint_a = await create_mint(solana_client, authority, decimals=6)
    mint_b = await create_mint(solana_client, authority, decimals=6)

    acc_a = await create_token_account(
        solana_client, authority, mint_a.pubkey(), authority.pubkey()
    )
    acc_b = await create_token_account(
        solana_client, authority, mint_b.pubkey(), authority.pubkey()
    )

    await mint_to(solana_client, authority, mint_a.pubkey(), acc_a.pubkey(), authority, 1000)
    await mint_to(solana_client, authority, mint_b.pubkey(), acc_b.pubkey(), authority, 2000)

    supply_a = await raw_rpc.get_token_supply(str(mint_a.pubkey()))
    supply_b = await raw_rpc.get_token_supply(str(mint_b.pubkey()))
    assert supply_a["value"]["amount"] == "1000"
    assert supply_b["value"]["amount"] == "2000"


async def test_burn_entire_balance(
    solana_client: AsyncClient,
    raw_rpc: RpcClient,
    test_config: TestConfig,
) -> None:
    """Burning entire balance leaves zero."""
    authority = await funded_sender(solana_client, test_config.rpc_url)
    mint_kp = await create_mint(solana_client, authority, decimals=6)
    account = await create_token_account(
        solana_client, authority, mint_kp.pubkey(), authority.pubkey()
    )

    await mint_to(solana_client, authority, mint_kp.pubkey(), account.pubkey(), authority, 5000)
    await burn_tokens(solana_client, authority, account.pubkey(), mint_kp.pubkey(), 5000)

    balance = await raw_rpc.get_token_account_balance(str(account.pubkey()))
    assert balance["value"]["amount"] == "0"


async def test_supply_tracks_mint_and_burn(
    solana_client: AsyncClient,
    raw_rpc: RpcClient,
    test_config: TestConfig,
) -> None:
    """Token supply correctly reflects minting and burning."""
    authority = await funded_sender(solana_client, test_config.rpc_url)
    mint_kp = await create_mint(solana_client, authority, decimals=6)
    account = await create_token_account(
        solana_client, authority, mint_kp.pubkey(), authority.pubkey()
    )

    # After mint
    await mint_to(solana_client, authority, mint_kp.pubkey(), account.pubkey(), authority, 10000)
    supply1 = await raw_rpc.get_token_supply(str(mint_kp.pubkey()))
    assert supply1["value"]["amount"] == "10000"

    # After burn
    await burn_tokens(solana_client, authority, account.pubkey(), mint_kp.pubkey(), 3000)
    supply2 = await raw_rpc.get_token_supply(str(mint_kp.pubkey()))
    assert supply2["value"]["amount"] == "7000"


async def test_token_accounts_by_owner(
    solana_client: AsyncClient,
    raw_rpc: RpcClient,
    test_config: TestConfig,
) -> None:
    """getTokenAccountsByOwner returns correct accounts for a mint."""
    authority = await funded_sender(solana_client, test_config.rpc_url, 10_000_000_000)
    mint_kp = await create_mint(solana_client, authority, decimals=6)
    acc1 = await create_token_account(
        solana_client, authority, mint_kp.pubkey(), authority.pubkey()
    )

    result = await raw_rpc.get_token_accounts_by_owner(
        str(authority.pubkey()), mint=str(mint_kp.pubkey())
    )
    assert "value" in result
    accounts = result["value"]
    assert len(accounts) >= 1
    # Verify our account is in the results
    account_keys = [a["pubkey"] for a in accounts]
    assert str(acc1.pubkey()) in account_keys
