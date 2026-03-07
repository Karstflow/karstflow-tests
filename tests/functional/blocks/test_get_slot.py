"""Functional tests: getSlot, getSlotLeader, getSlotLeaders."""

from __future__ import annotations

import asyncio

import pytest
from solana.rpc.async_api import AsyncClient

from karstflow_tests.config import Commitment
from karstflow_tests.rpc import RpcClient


async def test_get_slot_positive(solana_client: AsyncClient) -> None:
    """Current slot is a positive integer."""
    result = await solana_client.get_slot()
    assert isinstance(result.value, int)
    assert result.value > 0


async def test_slot_advances(solana_client: AsyncClient) -> None:
    """Slot number increases over time."""
    s1 = (await solana_client.get_slot()).value
    await asyncio.sleep(1)
    s2 = (await solana_client.get_slot()).value
    assert s2 > s1


@pytest.mark.parametrize(
    "commitment",
    [Commitment.PROCESSED, Commitment.CONFIRMED, Commitment.FINALIZED],
    ids=["processed", "confirmed", "finalized"],
)
async def test_slot_by_commitment(rpc_client: RpcClient, commitment: Commitment) -> None:
    """getSlot works with all commitment levels."""
    slot = await rpc_client.get_slot(commitment=commitment)
    assert isinstance(slot, int)
    assert slot > 0


async def test_slot_ordering_by_commitment(rpc_client: RpcClient) -> None:
    """processed >= confirmed >= finalized slot ordering."""
    processed = await rpc_client.get_slot(commitment=Commitment.PROCESSED)
    confirmed = await rpc_client.get_slot(commitment=Commitment.CONFIRMED)
    finalized = await rpc_client.get_slot(commitment=Commitment.FINALIZED)
    assert processed >= confirmed >= finalized


async def test_get_slot_leader(rpc_client: RpcClient) -> None:
    """getSlotLeader returns a valid pubkey string."""
    result = await rpc_client.request("getSlotLeader")
    assert isinstance(result, str)
    assert len(result) >= 32
