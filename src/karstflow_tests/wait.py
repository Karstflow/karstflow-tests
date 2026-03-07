"""Polling, retry, and readiness utilities."""

from __future__ import annotations

import asyncio

import httpx


async def wait_for_health(
    rpc_url: str,
    timeout: float = 30.0,
    interval: float = 0.5,
) -> None:
    """Poll the node health endpoint until it responds or timeout."""
    deadline = asyncio.get_event_loop().time() + timeout
    last_error: Exception | None = None

    async with httpx.AsyncClient(timeout=5.0) as client:
        while asyncio.get_event_loop().time() < deadline:
            try:
                response = await client.post(
                    rpc_url,
                    json={
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "getHealth",
                    },
                )
                if response.status_code == 200:
                    return
            except (httpx.ConnectError, httpx.ReadError, httpx.TimeoutException) as e:
                last_error = e
            await asyncio.sleep(interval)

    msg = f"Node at {rpc_url} not ready after {timeout}s"
    if last_error:
        msg += f": {last_error}"
    raise TimeoutError(msg)


async def wait_for_confirmation(
    rpc_url: str,
    signature: str,
    timeout: float = 30.0,
    interval: float = 0.5,
) -> None:
    """Poll until a transaction signature is confirmed."""
    deadline = asyncio.get_event_loop().time() + timeout

    async with httpx.AsyncClient(timeout=5.0) as client:
        while asyncio.get_event_loop().time() < deadline:
            response = await client.post(
                rpc_url,
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "getSignatureStatuses",
                    "params": [[signature], {"searchTransactionHistory": True}],
                },
            )
            data = response.json()
            result = data.get("result", {})
            statuses = result.get("value", [])

            if statuses and statuses[0] is not None:
                status = statuses[0]
                if status.get("confirmationStatus") in ("confirmed", "finalized"):
                    return
                if status.get("err") is not None:
                    raise TransactionError(f"Transaction {signature} failed: {status['err']}")

            await asyncio.sleep(interval)

    raise TimeoutError(f"Transaction {signature} not confirmed after {timeout}s")


class TransactionError(Exception):
    """Transaction execution failed on-chain."""
