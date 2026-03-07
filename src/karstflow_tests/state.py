"""Validator state snapshot capture and comparison."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from solana.rpc.async_api import AsyncClient
from solders.pubkey import Pubkey

from karstflow_tests.rpc import RpcClient


@dataclass(frozen=True)
class ValidatorSnapshot:
    """Point-in-time snapshot of validator state."""

    slot: int
    block_height: int
    epoch: int
    transaction_count: int
    balances: dict[str, int] = field(default_factory=dict)
    accounts: dict[str, dict[str, Any] | None] = field(default_factory=dict)
    timestamp: float = 0.0


@dataclass
class StateDiff:
    """Difference between two validator snapshots."""

    slot_delta: int
    block_height_delta: int
    epoch_changed: bool
    tx_count_delta: int
    balance_changes: dict[str, int]  # pubkey -> delta
    accounts_created: list[str]
    accounts_removed: list[str]

    @property
    def has_changes(self) -> bool:
        """Return True if any state changed between snapshots."""
        return (
            self.slot_delta != 0
            or self.tx_count_delta != 0
            or bool(self.balance_changes)
            or bool(self.accounts_created)
            or bool(self.accounts_removed)
        )


class StateCapture:
    """Capture and compare validator state snapshots.

    Usage:
        capture = StateCapture(solana_client, rpc_client)
        capture.track_account("sender", sender_pubkey)
        capture.track_account("recipient", recipient_pubkey)

        before = await capture.snapshot()
        # ... do operations ...
        after = await capture.snapshot()

        diff = capture.diff(before, after)
        assert diff.balance_changes["recipient"] == 1_000_000_000
    """

    def __init__(self, solana: AsyncClient, rpc: RpcClient) -> None:
        self._solana = solana
        self._rpc = rpc
        self._tracked: dict[str, Pubkey] = {}

    def track_account(self, name: str, pubkey: Pubkey | str) -> StateCapture:
        """Track an account by name for inclusion in snapshots."""
        if isinstance(pubkey, str):
            pubkey = Pubkey.from_string(pubkey)
        self._tracked[name] = pubkey
        return self

    def track_accounts(self, accounts: dict[str, Pubkey | str]) -> StateCapture:
        """Track multiple accounts by name for inclusion in snapshots."""
        for name, pubkey in accounts.items():
            self.track_account(name, pubkey)
        return self

    async def snapshot(self) -> ValidatorSnapshot:
        """Capture current validator state."""
        epoch_info = await self._rpc.get_epoch_info()
        tx_count = await self._rpc.get_transaction_count()

        balances: dict[str, int] = {}
        accounts: dict[str, dict[str, Any] | None] = {}

        for name, pubkey in self._tracked.items():
            bal_resp = await self._solana.get_balance(pubkey)
            balances[name] = bal_resp.value

            acc_resp = await self._solana.get_account_info(pubkey)
            if acc_resp.value is not None:
                # Store as dict for serializability
                accounts[name] = {
                    "lamports": acc_resp.value.lamports,
                    "owner": str(acc_resp.value.owner),
                    "executable": acc_resp.value.executable,
                }
            else:
                accounts[name] = None

        return ValidatorSnapshot(
            slot=epoch_info["absoluteSlot"],
            block_height=epoch_info["blockHeight"],
            epoch=epoch_info["epoch"],
            transaction_count=tx_count,
            balances=balances,
            accounts=accounts,
            timestamp=time.monotonic(),
        )

    @staticmethod
    def diff(before: ValidatorSnapshot, after: ValidatorSnapshot) -> StateDiff:
        """Compute difference between two snapshots."""
        balance_changes: dict[str, int] = {}
        for name in set(before.balances) | set(after.balances):
            old = before.balances.get(name, 0)
            new = after.balances.get(name, 0)
            if old != new:
                balance_changes[name] = new - old

        created = [
            name
            for name in after.accounts
            if after.accounts[name] is not None and before.accounts.get(name) is None
        ]
        removed = [
            name
            for name in before.accounts
            if before.accounts[name] is not None and after.accounts.get(name) is None
        ]

        return StateDiff(
            slot_delta=after.slot - before.slot,
            block_height_delta=after.block_height - before.block_height,
            epoch_changed=after.epoch != before.epoch,
            tx_count_delta=after.transaction_count - before.transaction_count,
            balance_changes=balance_changes,
            accounts_created=created,
            accounts_removed=removed,
        )
