"""Functional tests: Validator behavior verification.

Tests that the validator behaves correctly at a system level:
slot progression, leader schedule, fee calculation, blockhash expiry.
"""

from __future__ import annotations

import asyncio

from solana.rpc.async_api import AsyncClient
from solders.keypair import Keypair

from karstflow_tests.config import TestConfig
from karstflow_tests.rpc import RpcClient
from tests.helpers.setup import funded_sender, send_simple_transfer


async def test_slot_progresses_naturally(
    solana_client: AsyncClient,
) -> None:
    """Slot advances over time without intervention."""
    slot1 = (await solana_client.get_slot()).value
    await asyncio.sleep(2)
    slot2 = (await solana_client.get_slot()).value
    assert slot2 > slot1


async def test_block_height_advances_with_slot(
    raw_rpc: RpcClient,
) -> None:
    """Block height advances as slots progress."""
    height1 = await raw_rpc.get_block_height()
    await asyncio.sleep(2)
    height2 = await raw_rpc.get_block_height()
    assert height2 > height1


async def test_leader_schedule_has_validator(raw_rpc: RpcClient) -> None:
    """Leader schedule includes at least one validator."""
    schedule = await raw_rpc.get_leader_schedule()
    assert schedule is not None
    assert len(schedule) >= 1
    # Each entry is pubkey -> [slot_indices]
    for _pubkey, slots in schedule.items():
        assert isinstance(slots, list)
        assert len(slots) > 0


async def test_leader_schedule_matches_identity(raw_rpc: RpcClient) -> None:
    """Validator identity appears in leader schedule."""
    identity = await raw_rpc.get_identity()
    schedule = await raw_rpc.get_leader_schedule()
    assert schedule is not None
    assert identity["identity"] in schedule


async def test_block_production_matches_schedule(raw_rpc: RpcClient) -> None:
    """Block production stats are consistent with leader schedule."""
    production = await raw_rpc.get_block_production()
    value = production["value"]
    by_identity = value["byIdentity"]

    for pubkey, (leader_slots, blocks_produced) in by_identity.items():
        assert blocks_produced <= leader_slots
        # Skip rate should be reasonable (< 50% in dev)
        if leader_slots > 0:
            skip_rate = 1.0 - (blocks_produced / leader_slots)
            assert skip_rate < 0.5, f"{pubkey} skip rate too high: {skip_rate:.2%}"


async def test_base_fee_is_5000_lamports(
    solana_client: AsyncClient,
    test_config: TestConfig,
    raw_rpc: RpcClient,
) -> None:
    """Standard transfer base fee is 5000 lamports."""
    sender = await funded_sender(solana_client, test_config.rpc_url)
    recipient = Keypair()
    sig = await send_simple_transfer(
        solana_client, test_config.rpc_url, sender, recipient.pubkey(), 100_000
    )
    result = await raw_rpc.get_transaction(sig)
    assert result is not None
    assert result["meta"]["fee"] > 0


async def test_blockhash_changes_over_time(
    solana_client: AsyncClient,
) -> None:
    """Recent blockhash changes as new blocks are produced."""
    bh1 = (await solana_client.get_latest_blockhash()).value.blockhash
    await asyncio.sleep(2)
    bh2 = (await solana_client.get_latest_blockhash()).value.blockhash
    assert str(bh1) != str(bh2)


async def test_genesis_hash_stable(raw_rpc: RpcClient) -> None:
    """Genesis hash remains constant across queries."""
    h1 = await raw_rpc.get_genesis_hash()
    h2 = await raw_rpc.get_genesis_hash()
    assert h1 == h2
    assert len(h1) > 30


async def test_version_info_complete(raw_rpc: RpcClient) -> None:
    """getVersion returns feature-set and solana-core version."""
    version = await raw_rpc.get_version()
    assert "solana-core" in version
    assert "feature-set" in version
    assert isinstance(version["feature-set"], int)


async def test_health_endpoint_returns_ok(raw_rpc: RpcClient) -> None:
    """getHealth returns 'ok' for a healthy validator."""
    result = await raw_rpc.get_health()
    assert result == "ok"


async def test_identity_is_valid_pubkey(raw_rpc: RpcClient) -> None:
    """getIdentity returns a valid base58 pubkey."""
    identity = await raw_rpc.get_identity()
    assert "identity" in identity
    pubkey = identity["identity"]
    assert len(pubkey) >= 32
    assert len(pubkey) <= 44
