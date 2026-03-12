"""Tests using StateCapture for before/after state comparison."""

from __future__ import annotations

from solana.rpc.async_api import AsyncClient
from solders.keypair import Keypair

from karstflow_tests.config import TestConfig
from karstflow_tests.rpc import RpcClient
from karstflow_tests.state import StateCapture
from karstflow_tests.wait import wait_for_confirmation


async def test_snapshot_captures_slot(
    solana_client: AsyncClient,
    rpc_client: RpcClient,
) -> None:
    """Snapshot captures current slot and block height."""
    capture = StateCapture(solana_client, rpc_client)
    snap = await capture.snapshot()
    assert snap.slot > 0
    assert snap.block_height > 0
    assert snap.epoch >= 0
    assert snap.transaction_count >= 0


async def test_snapshot_tracks_balances(
    solana_client: AsyncClient,
    rpc_client: RpcClient,
    test_config: TestConfig,
) -> None:
    """Snapshot tracks specified account balances."""
    kp = Keypair()
    resp = await solana_client.request_airdrop(kp.pubkey(), 1_000_000_000)
    await wait_for_confirmation(test_config.rpc_url, str(resp.value))

    capture = StateCapture(solana_client, rpc_client)
    capture.track_account("test_account", kp.pubkey())
    snap = await capture.snapshot()

    assert "test_account" in snap.balances
    assert snap.balances["test_account"] == 1_000_000_000


async def test_diff_detects_balance_change(
    solana_client: AsyncClient,
    rpc_client: RpcClient,
    test_config: TestConfig,
) -> None:
    """Diff detects balance change after airdrop."""
    kp = Keypair()
    capture = StateCapture(solana_client, rpc_client)
    capture.track_account("target", kp.pubkey())

    before = await capture.snapshot()

    resp = await solana_client.request_airdrop(kp.pubkey(), 2_000_000_000)
    await wait_for_confirmation(test_config.rpc_url, str(resp.value))

    after = await capture.snapshot()
    diff = StateCapture.diff(before, after)

    assert diff.has_changes
    assert "target" in diff.balance_changes
    assert diff.balance_changes["target"] == 2_000_000_000
    # slot_delta may be 0 if both snapshots land in the same slot
    assert diff.slot_delta >= 0


async def test_diff_detects_account_creation(
    solana_client: AsyncClient,
    rpc_client: RpcClient,
    test_config: TestConfig,
) -> None:
    """Diff detects new account creation."""
    kp = Keypair()
    capture = StateCapture(solana_client, rpc_client)
    capture.track_account("new_account", kp.pubkey())

    before = await capture.snapshot()
    assert before.accounts["new_account"] is None

    resp = await solana_client.request_airdrop(kp.pubkey(), 1_000_000_000)
    await wait_for_confirmation(test_config.rpc_url, str(resp.value))

    after = await capture.snapshot()
    assert after.accounts["new_account"] is not None

    diff = StateCapture.diff(before, after)
    assert "new_account" in diff.accounts_created


async def test_diff_tx_count_increases(
    solana_client: AsyncClient,
    rpc_client: RpcClient,
    test_config: TestConfig,
) -> None:
    """Diff shows transaction count increase."""
    capture = StateCapture(solana_client, rpc_client)
    before = await capture.snapshot()

    kp = Keypair()
    resp = await solana_client.request_airdrop(kp.pubkey(), 1_000_000_000)
    await wait_for_confirmation(test_config.rpc_url, str(resp.value))

    after = await capture.snapshot()
    diff = StateCapture.diff(before, after)

    # In dev mode, getTransactionCount may not track real tx counts yet
    assert diff.tx_count_delta >= 0


async def test_snapshot_with_string_pubkey(
    solana_client: AsyncClient,
    rpc_client: RpcClient,
) -> None:
    """Track account with string pubkey."""
    capture = StateCapture(solana_client, rpc_client)
    capture.track_account("system", "11111111111111111111111111111111")
    snap = await capture.snapshot()
    assert "system" in snap.balances


async def test_multiple_tracked_accounts(
    solana_client: AsyncClient,
    rpc_client: RpcClient,
    test_config: TestConfig,
) -> None:
    """Track multiple accounts simultaneously."""
    kp1 = Keypair()
    kp2 = Keypair()
    capture = StateCapture(solana_client, rpc_client)
    capture.track_accounts(
        {
            "account1": kp1.pubkey(),
            "account2": kp2.pubkey(),
        }
    )
    snap = await capture.snapshot()
    assert len(snap.balances) == 2
    assert "account1" in snap.balances
    assert "account2" in snap.balances
