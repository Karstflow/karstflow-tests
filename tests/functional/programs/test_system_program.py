"""Functional tests: System program operations (create account, allocate)."""

from __future__ import annotations

from solana.rpc.async_api import AsyncClient

from karstflow_tests.config import TestConfig
from karstflow_tests.programs import SYSTEM_PROGRAM, create_program_owned_account
from tests.helpers.setup import funded_sender


async def test_create_system_owned_account(
    solana_client: AsyncClient,
    test_config: TestConfig,
) -> None:
    """CreateAccount instruction creates an account with specified owner."""
    payer = await funded_sender(solana_client, test_config.rpc_url)
    new_acct = await create_program_owned_account(solana_client, payer, SYSTEM_PROGRAM, space=64)
    result = await solana_client.get_account_info(new_acct.pubkey())
    assert result.value is not None
    assert str(result.value.owner) == str(SYSTEM_PROGRAM)


async def test_create_account_with_data_space(
    solana_client: AsyncClient,
    test_config: TestConfig,
) -> None:
    """Created account has the specified data space."""
    payer = await funded_sender(solana_client, test_config.rpc_url)
    space = 256
    new_acct = await create_program_owned_account(solana_client, payer, SYSTEM_PROGRAM, space=space)
    result = await solana_client.get_account_info(new_acct.pubkey())
    assert result.value is not None
    assert len(result.value.data) == space


async def test_create_account_is_rent_exempt(
    solana_client: AsyncClient,
    test_config: TestConfig,
) -> None:
    """Created account should be rent-exempt."""
    payer = await funded_sender(solana_client, test_config.rpc_url)
    space = 128
    new_acct = await create_program_owned_account(solana_client, payer, SYSTEM_PROGRAM, space=space)
    result = await solana_client.get_account_info(new_acct.pubkey())
    assert result.value is not None

    rent_resp = await solana_client.get_minimum_balance_for_rent_exemption(space)
    min_balance = rent_resp.value
    assert result.value.lamports >= min_balance


async def test_create_account_deducts_payer(
    solana_client: AsyncClient,
    test_config: TestConfig,
) -> None:
    """Creating an account reduces payer's balance."""
    payer = await funded_sender(solana_client, test_config.rpc_url)
    balance_before = (await solana_client.get_balance(payer.pubkey())).value

    await create_program_owned_account(solana_client, payer, SYSTEM_PROGRAM, space=64)

    balance_after = (await solana_client.get_balance(payer.pubkey())).value
    assert balance_after < balance_before
