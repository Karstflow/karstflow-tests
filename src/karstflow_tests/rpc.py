"""Typed JSON-RPC client wrapper for karstflow validator."""

from __future__ import annotations

from typing import Any

import httpx


class RpcClient:
    """Async JSON-RPC client for karstflow validator RPC endpoint."""

    def __init__(self, url: str = "http://localhost:8899") -> None:
        self.url = url
        self._client = httpx.AsyncClient(base_url=url, timeout=30.0)
        self._request_id = 0

    async def close(self) -> None:
        await self._client.aclose()

    async def request(self, method: str, params: list[Any] | None = None) -> Any:
        """Send a JSON-RPC 2.0 request and return the result."""
        self._request_id += 1
        payload = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": method,
        }
        if params is not None:
            payload["params"] = params

        response = await self._client.post("/", json=payload)
        response.raise_for_status()
        data = response.json()

        if "error" in data:
            raise RpcError(data["error"]["code"], data["error"]["message"])

        return data.get("result")

    async def get_health(self) -> str:
        return await self.request("getHealth")

    async def get_version(self) -> dict[str, Any]:
        return await self.request("getVersion")

    async def get_genesis_hash(self) -> str:
        return await self.request("getGenesisHash")

    async def get_slot(self) -> int:
        return await self.request("getSlot")

    async def get_block_height(self) -> int:
        return await self.request("getBlockHeight")

    async def get_epoch_info(self) -> dict[str, Any]:
        return await self.request("getEpochInfo")

    async def get_balance(self, pubkey: str) -> dict[str, Any]:
        return await self.request("getBalance", [pubkey])

    async def get_account_info(
        self, pubkey: str, encoding: str = "base64"
    ) -> dict[str, Any] | None:
        return await self.request("getAccountInfo", [pubkey, {"encoding": encoding}])

    async def get_multiple_accounts(
        self, pubkeys: list[str], encoding: str = "base64"
    ) -> dict[str, Any]:
        return await self.request("getMultipleAccounts", [pubkeys, {"encoding": encoding}])

    async def send_transaction(self, tx_base64: str) -> str:
        return await self.request("sendTransaction", [tx_base64, {"encoding": "base64"}])

    async def get_transaction(
        self, signature: str, encoding: str = "json"
    ) -> dict[str, Any] | None:
        return await self.request(
            "getTransaction",
            [signature, {"encoding": encoding, "maxSupportedTransactionVersion": 0}],
        )

    async def simulate_transaction(self, tx_base64: str) -> dict[str, Any]:
        return await self.request("simulateTransaction", [tx_base64, {"encoding": "base64"}])

    async def get_signatures_for_address(
        self, address: str, limit: int = 10
    ) -> list[dict[str, Any]]:
        return await self.request("getSignaturesForAddress", [address, {"limit": limit}])

    async def get_signature_statuses(
        self,
        signatures: list[str],
    ) -> dict[str, Any]:
        return await self.request(
            "getSignatureStatuses", [signatures, {"searchTransactionHistory": True}]
        )

    async def get_block(self, slot: int) -> dict[str, Any] | None:
        return await self.request(
            "getBlock",
            [slot, {"encoding": "json", "maxSupportedTransactionVersion": 0}],
        )

    async def get_block_time(self, slot: int) -> int | None:
        return await self.request("getBlockTime", [slot])

    async def request_airdrop(self, pubkey: str, lamports: int) -> str:
        return await self.request("requestAirdrop", [pubkey, lamports])

    async def get_leader_schedule(self) -> dict[str, Any] | None:
        return await self.request("getLeaderSchedule")

    async def get_epoch_schedule(self) -> dict[str, Any]:
        return await self.request("getEpochSchedule")


class RpcError(Exception):
    """JSON-RPC error response."""

    def __init__(self, code: int, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"RPC error {code}: {message}")
