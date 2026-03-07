"""WebSocket subscription helper for karstflow validator."""

from __future__ import annotations

import asyncio
import json
from typing import Any

import websockets
from websockets.asyncio.client import ClientConnection


class WsSubscription:
    """Manages a single WebSocket subscription to the validator."""

    def __init__(self, url: str = "ws://localhost:8900") -> None:
        self.url = url
        self._conn: ClientConnection | None = None
        self._request_id = 0
        self._subscription_id: int | None = None

    async def connect(self) -> None:
        self._conn = await websockets.connect(self.url)

    async def close(self) -> None:
        if self._conn is not None:
            if self._subscription_id is not None:
                await self._unsubscribe()
            await self._conn.close()
            self._conn = None

    async def subscribe(self, method: str, params: list[Any] | None = None) -> int:
        """Subscribe to a notification method. Returns subscription ID."""
        assert self._conn is not None, "Not connected"
        self._request_id += 1
        payload = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": method,
        }
        if params is not None:
            payload["params"] = params

        await self._conn.send(json.dumps(payload))
        response = json.loads(await self._conn.recv())

        if "error" in response:
            raise WsError(response["error"]["code"], response["error"]["message"])

        self._subscription_id = response["result"]
        return self._subscription_id

    async def recv_notification(self, timeout: float = 10.0) -> dict[str, Any]:
        """Wait for the next subscription notification."""
        assert self._conn is not None, "Not connected"
        raw = await asyncio.wait_for(self._conn.recv(), timeout=timeout)
        msg = json.loads(raw)
        return msg["params"]

    async def _unsubscribe(self) -> None:
        """Unsubscribe from current subscription."""
        if self._conn is None or self._subscription_id is None:
            return
        self._request_id += 1
        # Derive unsubscribe method from subscribe context
        payload = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": "unsubscribe",
            "params": [self._subscription_id],
        }
        try:
            await self._conn.send(json.dumps(payload))
            await asyncio.wait_for(self._conn.recv(), timeout=5.0)
        except Exception:
            pass
        self._subscription_id = None


class WsError(Exception):
    """WebSocket RPC error."""

    def __init__(self, code: int, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"WS error {code}: {message}")
