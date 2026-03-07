"""Functional tests: commitment level behavior across RPC methods.

Verifies that processed, confirmed, and finalized commitment levels
return appropriate data and maintain expected ordering invariants.
"""

from __future__ import annotations

import pytest
from solana.rpc.async_api import AsyncClient
from solders.keypair import Keypair

from karstflow_tests.config import Commitment, TestConfig
from karstflow_tests.rpc import RpcClient
from karstflow_tests.wait import wait_for_confirmation


@pytest.mark.parametrize(
    "commitment",
    [Commitment.PROCESSED, Commitment.CONFIRMED, Commitment.FINALIZED],
    ids=["processed", "confirmed", "finalized"],
)
async def test_get_slot_all_commitments(rpc_client: RpcClient, commitment: Commitment) -> None:
    """getSlot returns valid slot at every commitment level."""
    slot = await rpc_client.get_slot(commitment)
    assert isinstance(slot, int)
    assert slot > 0


async def test_slot_ordering_across_commitments(rpc_client: RpcClient) -> None:
    """processed >= confirmed >= finalized for slot values."""
    processed = await rpc_client.get_slot(Commitment.PROCESSED)
    confirmed = await rpc_client.get_slot(Commitment.CONFIRMED)
    finalized = await rpc_client.get_slot(Commitment.FINALIZED)
    assert processed >= confirmed >= finalized


@pytest.mark.parametrize(
    "commitment",
    [Commitment.PROCESSED, Commitment.CONFIRMED, Commitment.FINALIZED],
    ids=["processed", "confirmed", "finalized"],
)
async def test_get_block_height_all_commitments(
    rpc_client: RpcClient, commitment: Commitment
) -> None:
    """getBlockHeight returns valid height at every commitment level."""
    height = await rpc_client.get_block_height(commitment)
    assert isinstance(height, int)
    assert height > 0


async def test_block_height_ordering(rpc_client: RpcClient) -> None:
    """Block height ordering: processed >= confirmed >= finalized."""
    processed = await rpc_client.get_block_height(Commitment.PROCESSED)
    confirmed = await rpc_client.get_block_height(Commitment.CONFIRMED)
    finalized = await rpc_client.get_block_height(Commitment.FINALIZED)
    assert processed >= confirmed >= finalized


@pytest.mark.parametrize(
    "commitment",
    [Commitment.PROCESSED, Commitment.CONFIRMED, Commitment.FINALIZED],
    ids=["processed", "confirmed", "finalized"],
)
async def test_get_epoch_info_all_commitments(
    rpc_client: RpcClient, commitment: Commitment
) -> None:
    """getEpochInfo returns valid data at every commitment level."""
    info = await rpc_client.get_epoch_info(commitment)
    assert "epoch" in info
    assert "absoluteSlot" in info
    assert "blockHeight" in info
    assert info["absoluteSlot"] > 0


async def test_get_balance_commitment_levels(
    solana_client: AsyncClient,
    rpc_client: RpcClient,
    test_config: TestConfig,
) -> None:
    """getBalance returns consistent results across commitment levels."""
    kp = Keypair()
    resp = await solana_client.request_airdrop(kp.pubkey(), 1_000_000_000)
    await wait_for_confirmation(test_config.rpc_url, str(resp.value))

    pubkey_str = str(kp.pubkey())
    confirmed_bal = await rpc_client.get_balance(pubkey_str, Commitment.CONFIRMED)
    finalized_bal = await rpc_client.get_balance(pubkey_str, Commitment.FINALIZED)

    assert confirmed_bal["value"] == 1_000_000_000
    # Finalized may lag but should eventually match
    assert finalized_bal["value"] in (0, 1_000_000_000)


@pytest.mark.parametrize(
    "commitment",
    [Commitment.PROCESSED, Commitment.CONFIRMED, Commitment.FINALIZED],
    ids=["processed", "confirmed", "finalized"],
)
async def test_get_transaction_count_all_commitments(
    rpc_client: RpcClient, commitment: Commitment
) -> None:
    """getTransactionCount works at every commitment level."""
    count = await rpc_client.get_transaction_count(commitment)
    assert isinstance(count, int)
    assert count >= 0


async def test_transaction_count_ordering(rpc_client: RpcClient) -> None:
    """Transaction count: processed >= confirmed >= finalized."""
    processed = await rpc_client.get_transaction_count(Commitment.PROCESSED)
    confirmed = await rpc_client.get_transaction_count(Commitment.CONFIRMED)
    finalized = await rpc_client.get_transaction_count(Commitment.FINALIZED)
    assert processed >= confirmed >= finalized
