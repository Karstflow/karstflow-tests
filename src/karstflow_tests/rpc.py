"""Typed JSON-RPC client wrapper for karstflow validator.

Provides raw JSON-RPC access for edge cases not covered by solana-py,
batch requests, custom method calls, and detailed response inspection.
"""

from __future__ import annotations

import asyncio
from typing import Any

import httpx

from karstflow_tests.config import Commitment, RetryPolicy, TestConfig
from karstflow_tests.types import RpcErrorData, RpcResponse


class RpcClient:
    """Async JSON-RPC client with batch support, retries, and commitment config."""

    def __init__(
        self,
        url: str | None = None,
        *,
        config: TestConfig | None = None,
        timeout: float | None = None,
        commitment: Commitment | None = None,
        retry: RetryPolicy | None = None,
    ) -> None:
        cfg = config or TestConfig()
        self.url = url or cfg.rpc_url
        self.commitment = commitment or cfg.default_commitment
        self._retry = retry or cfg.retry
        self._timeout = timeout or cfg.request_timeout
        self._client = httpx.AsyncClient(base_url=self.url, timeout=self._timeout)
        self._request_id = 0

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> RpcClient:
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()

    def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id

    def _build_payload(
        self,
        method: str,
        params: list[Any] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": method,
        }
        if params is not None:
            payload["params"] = params
        return payload

    async def request(
        self,
        method: str,
        params: list[Any] | None = None,
        *,
        raw: bool = False,
    ) -> Any:
        """Send a JSON-RPC request. Returns result or full RpcResponse if raw=True."""
        payload = self._build_payload(method, params)
        data = await self._send_with_retry(payload)
        resp = self._parse_response(data)
        if raw:
            return resp
        return resp.unwrap()

    async def request_raw(
        self,
        method: str,
        params: list[Any] | None = None,
    ) -> RpcResponse:
        """Send a request and return full typed response (never raises on RPC error)."""
        payload = self._build_payload(method, params)
        data = await self._send_with_retry(payload)
        return self._parse_response(data)

    async def batch(
        self,
        requests: list[tuple[str, list[Any] | None]],
    ) -> list[RpcResponse]:
        """Send a batch of JSON-RPC requests. Returns responses in order."""
        payloads = [self._build_payload(method, params) for method, params in requests]
        response = await self._client.post("/", json=payloads)
        response.raise_for_status()
        results = response.json()
        # Sort by id to match request order
        if isinstance(results, list):
            results.sort(key=lambda r: r.get("id", 0))
        else:
            results = [results]
        return [self._parse_response(r) for r in results]

    async def _send_with_retry(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Send with exponential backoff retry on retryable errors."""
        last_error: Exception | None = None
        for attempt in range(self._retry.max_retries + 1):
            try:
                response = await self._client.post("/", json=payload)
                response.raise_for_status()
                data = response.json()
                # Check for retryable RPC error codes
                if "error" in data and attempt < self._retry.max_retries:
                    code = data["error"].get("code", 0)
                    if code in self._retry.retryable_codes:
                        delay = min(
                            self._retry.backoff_base * (2**attempt),
                            self._retry.backoff_max,
                        )
                        await asyncio.sleep(delay)
                        continue
                return data
            except (httpx.ConnectError, httpx.ReadError, httpx.TimeoutException) as e:
                last_error = e
                if attempt < self._retry.max_retries:
                    delay = min(
                        self._retry.backoff_base * (2**attempt),
                        self._retry.backoff_max,
                    )
                    await asyncio.sleep(delay)
        raise ConnectionError(
            f"RPC request failed after {self._retry.max_retries + 1} attempts"
        ) from last_error

    @staticmethod
    def _parse_response(data: dict[str, Any]) -> RpcResponse:
        error = None
        if "error" in data:
            err = data["error"]
            error = RpcErrorData(
                code=err.get("code", -1),
                message=err.get("message", "unknown"),
                data=err.get("data"),
            )
        return RpcResponse(
            id=data.get("id", 0),
            result=data.get("result"),
            error=error,
        )

    # ── Convenience wrappers ─────────────────────────────────────────

    async def get_health(self) -> str:
        return await self.request("getHealth")

    async def get_version(self) -> dict[str, Any]:
        return await self.request("getVersion")

    async def get_genesis_hash(self) -> str:
        return await self.request("getGenesisHash")

    async def get_slot(self, commitment: Commitment | None = None) -> int:
        c = commitment or self.commitment
        return await self.request("getSlot", [{"commitment": c.value}])

    async def get_block_height(self, commitment: Commitment | None = None) -> int:
        c = commitment or self.commitment
        return await self.request("getBlockHeight", [{"commitment": c.value}])

    async def get_epoch_info(self, commitment: Commitment | None = None) -> dict[str, Any]:
        c = commitment or self.commitment
        return await self.request("getEpochInfo", [{"commitment": c.value}])

    async def get_balance(
        self, pubkey: str, commitment: Commitment | None = None
    ) -> dict[str, Any]:
        c = commitment or self.commitment
        return await self.request("getBalance", [pubkey, {"commitment": c.value}])

    async def get_account_info(
        self,
        pubkey: str,
        *,
        encoding: str = "base64",
        commitment: Commitment | None = None,
    ) -> dict[str, Any] | None:
        c = commitment or self.commitment
        return await self.request(
            "getAccountInfo", [pubkey, {"encoding": encoding, "commitment": c.value}]
        )

    async def get_multiple_accounts(
        self,
        pubkeys: list[str],
        *,
        encoding: str = "base64",
        commitment: Commitment | None = None,
    ) -> dict[str, Any]:
        c = commitment or self.commitment
        return await self.request(
            "getMultipleAccounts", [pubkeys, {"encoding": encoding, "commitment": c.value}]
        )

    async def send_transaction(self, tx_base64: str) -> str:
        return await self.request("sendTransaction", [tx_base64, {"encoding": "base64"}])

    async def simulate_transaction(self, tx_base64: str) -> dict[str, Any]:
        return await self.request("simulateTransaction", [tx_base64, {"encoding": "base64"}])

    async def get_transaction(
        self,
        signature: str,
        *,
        encoding: str = "json",
        commitment: Commitment | None = None,
    ) -> dict[str, Any] | None:
        c = commitment or self.commitment
        return await self.request(
            "getTransaction",
            [
                signature,
                {"encoding": encoding, "commitment": c.value, "maxSupportedTransactionVersion": 0},
            ],
        )

    async def get_signatures_for_address(
        self, address: str, *, limit: int = 10
    ) -> list[dict[str, Any]]:
        return await self.request("getSignaturesForAddress", [address, {"limit": limit}])

    async def get_signature_statuses(
        self, signatures: list[str], *, search_history: bool = True
    ) -> dict[str, Any]:
        return await self.request(
            "getSignatureStatuses",
            [signatures, {"searchTransactionHistory": search_history}],
        )

    async def get_block(self, slot: int, *, encoding: str = "json") -> dict[str, Any] | None:
        return await self.request(
            "getBlock",
            [slot, {"encoding": encoding, "maxSupportedTransactionVersion": 0}],
        )

    async def get_block_time(self, slot: int) -> int | None:
        return await self.request("getBlockTime", [slot])

    async def request_airdrop(self, pubkey: str, lamports: int) -> str:
        return await self.request("requestAirdrop", [pubkey, lamports])

    async def get_leader_schedule(self) -> dict[str, Any] | None:
        return await self.request("getLeaderSchedule")

    async def get_epoch_schedule(self) -> dict[str, Any]:
        return await self.request("getEpochSchedule")

    async def get_minimum_balance_for_rent_exemption(self, data_len: int) -> int:
        return await self.request("getMinimumBalanceForRentExemption", [data_len])

    async def get_supply(self) -> dict[str, Any]:
        return await self.request("getSupply")

    async def get_cluster_nodes(self) -> list[dict[str, Any]]:
        return await self.request("getClusterNodes")

    async def get_vote_accounts(self) -> dict[str, Any]:
        return await self.request("getVoteAccounts")

    async def get_identity(self) -> dict[str, Any]:
        return await self.request("getIdentity")

    async def get_inflation_rate(self) -> dict[str, Any]:
        return await self.request("getInflationRate")

    async def get_recent_performance_samples(self, limit: int = 10) -> list[dict[str, Any]]:
        return await self.request("getRecentPerformanceSamples", [limit])
