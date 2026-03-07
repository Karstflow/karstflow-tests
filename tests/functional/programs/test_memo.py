"""Functional tests: Memo program (basic program execution)."""

from __future__ import annotations

from solana.rpc.async_api import AsyncClient

from karstflow_tests.config import TestConfig
from karstflow_tests.programs import send_memo
from karstflow_tests.rpc import RpcClient
from tests.helpers.setup import funded_sender


async def test_memo_basic(
    solana_client: AsyncClient,
    test_config: TestConfig,
) -> None:
    """Sending a memo transaction succeeds."""
    signer = await funded_sender(solana_client, test_config.rpc_url)
    sig = await send_memo(solana_client, signer, "hello karstflow")
    assert len(sig) > 40


async def test_memo_visible_in_logs(
    solana_client: AsyncClient,
    test_config: TestConfig,
    raw_rpc: RpcClient,
) -> None:
    """Memo text appears in transaction logs."""
    signer = await funded_sender(solana_client, test_config.rpc_url)
    memo_text = "test-memo-log-check"
    sig = await send_memo(solana_client, signer, memo_text)

    result = await raw_rpc.get_transaction(sig)
    assert result is not None
    logs = result["meta"].get("logMessages", [])
    assert any(memo_text in log for log in logs)


async def test_memo_empty_text(
    solana_client: AsyncClient,
    test_config: TestConfig,
) -> None:
    """Empty memo text is valid."""
    signer = await funded_sender(solana_client, test_config.rpc_url)
    sig = await send_memo(solana_client, signer, "")
    assert len(sig) > 40


async def test_memo_long_text(
    solana_client: AsyncClient,
    test_config: TestConfig,
) -> None:
    """Long memo text (up to reasonable length) succeeds."""
    signer = await funded_sender(solana_client, test_config.rpc_url)
    long_text = "x" * 500
    sig = await send_memo(solana_client, signer, long_text)
    assert len(sig) > 40


async def test_memo_unicode(
    solana_client: AsyncClient,
    test_config: TestConfig,
) -> None:
    """Unicode memo text is valid."""
    signer = await funded_sender(solana_client, test_config.rpc_url)
    sig = await send_memo(solana_client, signer, "привет мир 🌍")
    assert len(sig) > 40
