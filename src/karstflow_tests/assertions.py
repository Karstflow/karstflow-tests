"""Domain-specific assertion helpers for validator testing."""

from __future__ import annotations

from typing import Any

from solana.rpc.async_api import AsyncClient
from solders.pubkey import Pubkey


async def assert_balance(
    client: AsyncClient,
    pubkey: Pubkey | str,
    expected_lamports: int,
    *,
    tolerance: int = 0,
    msg: str = "",
) -> None:
    """Assert account balance within tolerance."""
    if isinstance(pubkey, str):
        pubkey = Pubkey.from_string(pubkey)
    result = await client.get_balance(pubkey)
    actual = result.value
    diff = abs(actual - expected_lamports)
    assert diff <= tolerance, (
        f"Balance mismatch for {pubkey}: expected {expected_lamports} "
        f"(±{tolerance}), got {actual} (diff={diff})" + (f" — {msg}" if msg else "")
    )


async def assert_balance_decreased(
    client: AsyncClient,
    pubkey: Pubkey | str,
    previous_balance: int,
    *,
    min_decrease: int = 1,
    msg: str = "",
) -> int:
    """Assert balance decreased by at least min_decrease. Returns new balance."""
    if isinstance(pubkey, str):
        pubkey = Pubkey.from_string(pubkey)
    result = await client.get_balance(pubkey)
    actual = result.value
    decrease = previous_balance - actual
    assert decrease >= min_decrease, (
        f"Expected balance decrease >= {min_decrease} for {pubkey}, "
        f"but got decrease={decrease} (was {previous_balance}, now {actual})"
        + (f" — {msg}" if msg else "")
    )
    return actual


async def assert_balance_increased(
    client: AsyncClient,
    pubkey: Pubkey | str,
    previous_balance: int,
    *,
    min_increase: int = 1,
    msg: str = "",
) -> int:
    """Assert balance increased by at least min_increase. Returns new balance."""
    if isinstance(pubkey, str):
        pubkey = Pubkey.from_string(pubkey)
    result = await client.get_balance(pubkey)
    actual = result.value
    increase = actual - previous_balance
    assert increase >= min_increase, (
        f"Expected balance increase >= {min_increase} for {pubkey}, "
        f"but got increase={increase} (was {previous_balance}, now {actual})"
        + (f" — {msg}" if msg else "")
    )
    return actual


async def assert_slot_advances(
    client: AsyncClient,
    previous_slot: int,
    *,
    min_advance: int = 1,
    msg: str = "",
) -> int:
    """Assert slot advanced. Returns new slot."""
    result = await client.get_slot()
    current = result.value
    advance = current - previous_slot
    assert advance >= min_advance, (
        f"Slot did not advance enough: expected >= {min_advance}, "
        f"got advance={advance} (was {previous_slot}, now {current})" + (f" — {msg}" if msg else "")
    )
    return current


async def assert_account_exists(
    client: AsyncClient,
    pubkey: Pubkey | str,
    *,
    msg: str = "",
) -> dict[str, Any]:
    """Assert account exists and return account info value dict."""
    if isinstance(pubkey, str):
        pubkey = Pubkey.from_string(pubkey)
    result = await client.get_account_info(pubkey)
    assert result.value is not None, f"Account {pubkey} does not exist" + (
        f" — {msg}" if msg else ""
    )
    return result.value  # type: ignore[return-value]


async def assert_account_not_exists(
    client: AsyncClient,
    pubkey: Pubkey | str,
    *,
    msg: str = "",
) -> None:
    """Assert account does not exist."""
    if isinstance(pubkey, str):
        pubkey = Pubkey.from_string(pubkey)
    result = await client.get_account_info(pubkey)
    assert result.value is None, f"Account {pubkey} exists but should not" + (
        f" — {msg}" if msg else ""
    )


async def assert_transaction_confirmed(
    client: AsyncClient,
    signature: str,
    *,
    msg: str = "",
) -> None:
    """Assert transaction reached confirmed status."""
    from solders.signature import Signature

    sig = Signature.from_string(signature)
    result = await client.get_signature_statuses([sig])
    statuses = result.value
    assert statuses, f"Transaction {signature} statuses empty" + (f" — {msg}" if msg else "")
    assert statuses[0] is not None, f"Transaction {signature} status not found" + (
        f" — {msg}" if msg else ""
    )
    status = statuses[0]
    assert status.confirmation_status in (
        "confirmed",
        "finalized",
    ), f"Transaction {signature} not confirmed: {status}" + (f" — {msg}" if msg else "")


def assert_rpc_error(response: dict[str, Any], *, code: int | None = None) -> dict[str, Any]:
    """Assert RPC response contains an error. Returns the error dict."""
    assert "error" in response, f"Expected RPC error but got success: {response}"
    error = response["error"]
    if code is not None:
        assert error["code"] == code, (
            f"Expected error code {code}, got {error['code']}: {error['message']}"
        )
    return error
