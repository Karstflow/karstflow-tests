"""Typed response models for RPC results."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RpcResponse:
    """Raw JSON-RPC response wrapper."""

    id: int
    result: Any
    error: RpcErrorData | None = None

    @property
    def ok(self) -> bool:
        return self.error is None

    def unwrap(self) -> Any:
        """Return result or raise on error."""
        if self.error is not None:
            raise RpcCallError(self.error.code, self.error.message, self.error.data)
        return self.result


@dataclass(frozen=True)
class RpcErrorData:
    """Structured RPC error."""

    code: int
    message: str
    data: Any = None


@dataclass(frozen=True)
class EpochInfo:
    """Parsed getEpochInfo result."""

    epoch: int
    slot_index: int
    slots_in_epoch: int
    absolute_slot: int
    block_height: int
    transaction_count: int | None

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> EpochInfo:
        return cls(
            epoch=d["epoch"],
            slot_index=d["slotIndex"],
            slots_in_epoch=d["slotsInEpoch"],
            absolute_slot=d["absoluteSlot"],
            block_height=d["blockHeight"],
            transaction_count=d.get("transactionCount"),
        )


@dataclass(frozen=True)
class BlockProduction:
    """Parsed block production stats for a validator."""

    leader_slots: int
    blocks_produced: int

    @property
    def skip_rate(self) -> float:
        if self.leader_slots == 0:
            return 0.0
        return 1.0 - (self.blocks_produced / self.leader_slots)


@dataclass(frozen=True)
class AccountInfo:
    """Parsed account info."""

    lamports: int
    owner: str
    executable: bool
    rent_epoch: int
    data: Any
    space: int

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> AccountInfo:
        data = d.get("data", [])
        space = d.get("space", 0)
        if isinstance(data, list) and len(data) >= 1 and isinstance(data[0], str):
            space = space or len(data[0]) // 2  # base64 rough estimate
        return cls(
            lamports=d["lamports"],
            owner=d["owner"],
            executable=d["executable"],
            rent_epoch=d["rentEpoch"],
            data=data,
            space=space,
        )


@dataclass(frozen=True)
class SignatureStatus:
    """Parsed signature status."""

    slot: int
    confirmations: int | None
    err: Any
    confirmation_status: str | None

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> SignatureStatus:
        return cls(
            slot=d["slot"],
            confirmations=d.get("confirmations"),
            err=d.get("err"),
            confirmation_status=d.get("confirmationStatus"),
        )

    @property
    def confirmed(self) -> bool:
        return self.confirmation_status in ("confirmed", "finalized")

    @property
    def finalized(self) -> bool:
        return self.confirmation_status == "finalized"

    @property
    def failed(self) -> bool:
        return self.err is not None


class RpcCallError(Exception):
    """Raised when an RPC call returns an error."""

    def __init__(self, code: int, message: str, data: Any = None) -> None:
        self.code = code
        self.message = message
        self.data = data
        super().__init__(f"RPC error {code}: {message}")
