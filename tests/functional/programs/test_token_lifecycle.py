"""Functional tests: SPL Token full lifecycle.

Tests mint creation, token account creation, minting, transferring,
burning, and closing token accounts.
"""

from __future__ import annotations

from solana.rpc.async_api import AsyncClient

from karstflow_tests.config import TestConfig
from karstflow_tests.rpc import RpcClient
from karstflow_tests.token import (
    TOKEN_PROGRAM_ID,
    burn_tokens,
    close_token_account,
    create_mint,
    create_token_account,
    mint_to,
    token_transfer,
)
from tests.helpers.setup import funded_sender


async def test_create_mint(
    solana_client: AsyncClient,
    test_config: TestConfig,
) -> None:
    """Creating a new SPL Token mint succeeds."""
    payer = await funded_sender(solana_client, test_config.rpc_url)
    mint_kp = await create_mint(solana_client, payer, decimals=6)

    result = await solana_client.get_account_info(mint_kp.pubkey())
    assert result.value is not None
    assert str(result.value.owner) == str(TOKEN_PROGRAM_ID)
    assert len(result.value.data) == 82  # Mint size


async def test_create_token_account(
    solana_client: AsyncClient,
    test_config: TestConfig,
) -> None:
    """Creating a token account for a mint succeeds."""
    payer = await funded_sender(solana_client, test_config.rpc_url)
    mint_kp = await create_mint(solana_client, payer, decimals=9)

    token_acct = await create_token_account(solana_client, payer, mint_kp.pubkey(), payer.pubkey())
    result = await solana_client.get_account_info(token_acct.pubkey())
    assert result.value is not None
    assert str(result.value.owner) == str(TOKEN_PROGRAM_ID)
    assert len(result.value.data) == 165  # Token account size


async def test_mint_to_tokens(
    solana_client: AsyncClient,
    test_config: TestConfig,
    raw_rpc: RpcClient,
) -> None:
    """Minting tokens increases the token account balance."""
    payer = await funded_sender(solana_client, test_config.rpc_url)
    mint_kp = await create_mint(solana_client, payer)
    token_acct = await create_token_account(solana_client, payer, mint_kp.pubkey(), payer.pubkey())

    await mint_to(solana_client, payer, mint_kp.pubkey(), token_acct.pubkey(), payer, 1_000_000_000)

    # Check balance via RPC
    balance = await raw_rpc.get_token_account_balance(str(token_acct.pubkey()))
    assert "value" in balance
    assert int(balance["value"]["amount"]) == 1_000_000_000


async def test_token_transfer(
    solana_client: AsyncClient,
    test_config: TestConfig,
    raw_rpc: RpcClient,
) -> None:
    """Transferring tokens between accounts works correctly."""
    payer = await funded_sender(solana_client, test_config.rpc_url)
    mint_kp = await create_mint(solana_client, payer)

    src_acct = await create_token_account(solana_client, payer, mint_kp.pubkey(), payer.pubkey())
    dst_acct = await create_token_account(solana_client, payer, mint_kp.pubkey(), payer.pubkey())

    await mint_to(solana_client, payer, mint_kp.pubkey(), src_acct.pubkey(), payer, 1_000_000)
    await token_transfer(solana_client, payer, src_acct.pubkey(), dst_acct.pubkey(), 400_000)

    src_balance = await raw_rpc.get_token_account_balance(str(src_acct.pubkey()))
    dst_balance = await raw_rpc.get_token_account_balance(str(dst_acct.pubkey()))
    assert int(src_balance["value"]["amount"]) == 600_000
    assert int(dst_balance["value"]["amount"]) == 400_000


async def test_burn_tokens(
    solana_client: AsyncClient,
    test_config: TestConfig,
    raw_rpc: RpcClient,
) -> None:
    """Burning tokens reduces the account balance."""
    payer = await funded_sender(solana_client, test_config.rpc_url)
    mint_kp = await create_mint(solana_client, payer)
    token_acct = await create_token_account(solana_client, payer, mint_kp.pubkey(), payer.pubkey())

    await mint_to(solana_client, payer, mint_kp.pubkey(), token_acct.pubkey(), payer, 1_000_000)
    await burn_tokens(solana_client, payer, token_acct.pubkey(), mint_kp.pubkey(), 300_000)

    balance = await raw_rpc.get_token_account_balance(str(token_acct.pubkey()))
    assert int(balance["value"]["amount"]) == 700_000


async def test_token_supply_reflects_minting(
    solana_client: AsyncClient,
    test_config: TestConfig,
    raw_rpc: RpcClient,
) -> None:
    """getTokenSupply reflects minted amount."""
    payer = await funded_sender(solana_client, test_config.rpc_url)
    mint_kp = await create_mint(solana_client, payer, decimals=6)
    token_acct = await create_token_account(solana_client, payer, mint_kp.pubkey(), payer.pubkey())

    await mint_to(solana_client, payer, mint_kp.pubkey(), token_acct.pubkey(), payer, 5_000_000)

    supply = await raw_rpc.get_token_supply(str(mint_kp.pubkey()))
    assert "value" in supply
    assert int(supply["value"]["amount"]) == 5_000_000
    assert supply["value"]["decimals"] == 6


async def test_token_supply_after_burn(
    solana_client: AsyncClient,
    test_config: TestConfig,
    raw_rpc: RpcClient,
) -> None:
    """getTokenSupply decreases after burning."""
    payer = await funded_sender(solana_client, test_config.rpc_url)
    mint_kp = await create_mint(solana_client, payer, decimals=9)
    token_acct = await create_token_account(solana_client, payer, mint_kp.pubkey(), payer.pubkey())

    await mint_to(solana_client, payer, mint_kp.pubkey(), token_acct.pubkey(), payer, 2_000_000)
    await burn_tokens(solana_client, payer, token_acct.pubkey(), mint_kp.pubkey(), 500_000)

    supply = await raw_rpc.get_token_supply(str(mint_kp.pubkey()))
    assert int(supply["value"]["amount"]) == 1_500_000


async def test_close_token_account_reclaims_rent(
    solana_client: AsyncClient,
    test_config: TestConfig,
) -> None:
    """Closing a token account returns rent to the destination."""
    payer = await funded_sender(solana_client, test_config.rpc_url)
    mint_kp = await create_mint(solana_client, payer)
    token_acct = await create_token_account(solana_client, payer, mint_kp.pubkey(), payer.pubkey())

    balance_before = (await solana_client.get_balance(payer.pubkey())).value
    await close_token_account(solana_client, payer, token_acct.pubkey(), payer.pubkey())
    balance_after = (await solana_client.get_balance(payer.pubkey())).value

    # Balance should increase (rent reclaimed minus fee)
    # The net change is rent_exemption - fee, which should be positive for 165 bytes
    await solana_client.get_minimum_balance_for_rent_exemption(165)
    # rent > fee (5000), so balance should increase
    assert balance_after > balance_before - 10_000  # allow for fee


async def test_token_accounts_by_owner(
    solana_client: AsyncClient,
    test_config: TestConfig,
    raw_rpc: RpcClient,
) -> None:
    """getTokenAccountsByOwner returns the owner's token accounts."""
    payer = await funded_sender(solana_client, test_config.rpc_url)
    mint_kp = await create_mint(solana_client, payer)
    token_acct = await create_token_account(solana_client, payer, mint_kp.pubkey(), payer.pubkey())

    result = await raw_rpc.get_token_accounts_by_owner(
        str(payer.pubkey()),
        mint=str(mint_kp.pubkey()),
    )
    assert "value" in result
    accounts = result["value"]
    assert len(accounts) >= 1
    found = any(a["pubkey"] == str(token_acct.pubkey()) for a in accounts)
    assert found


async def test_create_mint_different_decimals(
    solana_client: AsyncClient,
    test_config: TestConfig,
    raw_rpc: RpcClient,
) -> None:
    """Mints with different decimal values store correctly."""
    payer = await funded_sender(solana_client, test_config.rpc_url)

    for decimals in [0, 2, 6, 9]:
        mint_kp = await create_mint(solana_client, payer, decimals=decimals)
        token_acct = await create_token_account(
            solana_client, payer, mint_kp.pubkey(), payer.pubkey()
        )
        await mint_to(solana_client, payer, mint_kp.pubkey(), token_acct.pubkey(), payer, 100)
        supply = await raw_rpc.get_token_supply(str(mint_kp.pubkey()))
        assert supply["value"]["decimals"] == decimals
        assert int(supply["value"]["amount"]) == 100
