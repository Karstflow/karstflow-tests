"""WebSocket subscription helper for karstflow validator."""

from __future__ import annotations

import asyncio
import json
from typing import Any

import websockets
from websockets.asyncio.client import ClientConnection

from karstflow_tests.config import TestConfig

# Map subscribe methods to their unsubscribe counterparts
_UNSUBSCRIBE_MAP: dict[str, str] = {
    "accountSubscribe": "accountUnsubscribe",
    "logsSubscribe": "logsUnsubscribe",
    "programSubscribe": "programUnsubscribe",
    "rootSubscribe": "rootUnsubscribe",
    "signatureSubscribe": "signatureUnsubscribe",
    "slotSubscribe": "slotUnsubscribe",
    "slotsUpdatesSubscribe": "slotsUpdatesUnsubscribe",
    "voteSubscribe": "voteUnsubscribe",
    "blockSubscribe": "blockUnsubscribe",
}


class WsClient:
    """WebSocket client with multi-subscription support and proper unsubscribe dispatch."""

    def __init__(
        self,
        url: str | None = None,
        *,
        config: TestConfig | None = None,
        recv_timeout: float | None = None,
    ) -> None:
        cfg = config or TestConfig()
        self.url = url or cfg.ws_url
        self._recv_timeout = recv_timeout or cfg.ws_recv_timeout
        self._conn: ClientConnection | None = None
        self._request_id = 0
        self._subscriptions: dict[int, str] = {}  # sub_id -> subscribe method

    async def connect(self) -> WsClient:
        self._conn = await websockets.connect(self.url)
        return self

    async def close(self) -> None:
        if self._conn is not None:
            for sub_id, method in list(self._subscriptions.items()):
                await self._unsubscribe(sub_id, method)
            await self._conn.close()
            self._conn = None

    async def __aenter__(self) -> WsClient:
        return await self.connect()

    async def __aexit__(self, *args: object) -> None:
        await self.close()

    def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id

    async def subscribe(
        self,
        method: str,
        params: list[Any] | None = None,
    ) -> int:
        """Subscribe to a notification method. Returns subscription ID."""
        assert self._conn is not None, "Not connected — call connect() first"
        req_id = self._next_id()
        payload: dict[str, Any] = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
        }
        if params is not None:
            payload["params"] = params

        await self._conn.send(json.dumps(payload))
        response = json.loads(await self._conn.recv())

        if "error" in response:
            raise WsError(response["error"]["code"], response["error"]["message"])

        sub_id: int = response["result"]
        self._subscriptions[sub_id] = method
        return sub_id

    async def recv_notification(self, timeout: float | None = None) -> dict[str, Any]:
        """Wait for the next subscription notification."""
        assert self._conn is not None, "Not connected"
        t = timeout or self._recv_timeout
        raw = await asyncio.wait_for(self._conn.recv(), timeout=t)
        msg = json.loads(raw)
        return msg["params"]

    async def recv_notifications(
        self,
        count: int,
        timeout: float | None = None,
    ) -> list[dict[str, Any]]:
        """Receive exactly `count` notifications."""
        results = []
        for _ in range(count):
            results.append(await self.recv_notification(timeout=timeout))
        return results

    async def unsubscribe(self, subscription_id: int) -> bool:
        """Explicitly unsubscribe. Returns True if server acknowledged."""
        method = self._subscriptions.get(subscription_id)
        if method is None:
            return False
        return await self._unsubscribe(subscription_id, method)

    async def _unsubscribe(self, sub_id: int, subscribe_method: str) -> bool:
        if self._conn is None:
            return False
        unsub_method = _UNSUBSCRIBE_MAP.get(subscribe_method)
        if unsub_method is None:
            # Fallback: derive by replacing Subscribe -> Unsubscribe
            unsub_method = subscribe_method.replace("Subscribe", "Unsubscribe")
        req_id = self._next_id()
        payload = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": unsub_method,
            "params": [sub_id],
        }
        try:
            await self._conn.send(json.dumps(payload))
            raw = await asyncio.wait_for(self._conn.recv(), timeout=5.0)
            result = json.loads(raw).get("result", False)
        except Exception:
            result = False
        self._subscriptions.pop(sub_id, None)
        return bool(result)

    # ── Typed subscribe shortcuts ────────────────────────────────────

    async def slot_subscribe(self) -> int:
        """Subscribe to slot notifications."""
        return await self.subscribe("slotSubscribe")

    async def root_subscribe(self) -> int:
        """Subscribe to root notifications."""
        return await self.subscribe("rootSubscribe")

    async def logs_subscribe(
        self,
        mention: str | None = None,
        commitment: str = "confirmed",
    ) -> int:
        """Subscribe to transaction log notifications."""
        if mention:
            filter_param: Any = {"mentions": [mention]}
        else:
            filter_param = "all"
        return await self.subscribe("logsSubscribe", [filter_param, {"commitment": commitment}])

    async def account_subscribe(
        self,
        pubkey: str,
        *,
        encoding: str = "base64",
        commitment: str = "confirmed",
    ) -> int:
        """Subscribe to account change notifications."""
        return await self.subscribe(
            "accountSubscribe",
            [pubkey, {"encoding": encoding, "commitment": commitment}],
        )

    async def program_subscribe(
        self,
        program_id: str,
        *,
        encoding: str = "base64",
        commitment: str = "confirmed",
    ) -> int:
        """Subscribe to program account change notifications."""
        return await self.subscribe(
            "programSubscribe",
            [program_id, {"encoding": encoding, "commitment": commitment}],
        )

    async def signature_subscribe(
        self,
        signature: str,
        *,
        commitment: str = "confirmed",
    ) -> int:
        """Subscribe to signature confirmation notifications."""
        return await self.subscribe(
            "signatureSubscribe",
            [signature, {"commitment": commitment}],
        )


# Keep backward compatibility alias
WsSubscription = WsClient


class WsError(Exception):
    """WebSocket RPC error."""

    def __init__(self, code: int, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"WS error {code}: {message}")
