"""Typed JSON-RPC client wrapper for karstflow validator.

Provides raw JSON-RPC access for edge cases not covered by solana-py,
batch requests, custom method calls, and detailed response inspection.
"""

from __future__ import annotations

import asyncio
from typing import Any

import httpx

from karstflow_tests.config import Commitment, RetryPolicy, TestConfig
from karstflow_tests.request_builder import RpcRequestSpec
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

    # ── RequestBuilder integration ───────────────────────────────────

    async def execute(self, spec: RpcRequestSpec) -> Any:
        """Execute a request built with RequestBuilder."""
        return await self.request(spec.method, spec.params)

    async def execute_raw(self, spec: RpcRequestSpec) -> RpcResponse:
        """Execute a request built with RequestBuilder, return full response."""
        return await self.request_raw(spec.method, spec.params)

    async def execute_batch(self, specs: list[RpcRequestSpec]) -> list[RpcResponse]:
        """Execute multiple RequestBuilder specs as a batch."""
        requests = [(s.method, s.params) for s in specs]
        return await self.batch(requests)

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

    async def get_block_production(self, identity: str | None = None) -> dict[str, Any]:
        params: dict[str, Any] = {}
        if identity:
            params["identity"] = identity
        return await self.request("getBlockProduction", [params] if params else None)

    async def get_block_commitment(self, slot: int) -> dict[str, Any]:
        return await self.request("getBlockCommitment", [slot])

    async def get_first_available_block(self) -> int:
        return await self.request("getFirstAvailableBlock")

    async def get_highest_snapshot_slot(self) -> dict[str, Any]:
        return await self.request("getHighestSnapshotSlot")

    async def get_largest_accounts(self, *, filter_type: str | None = None) -> dict[str, Any]:
        params: list[Any] = []
        if filter_type:
            params.append({"filter": filter_type})
        return await self.request("getLargestAccounts", params or None)

    async def get_program_accounts(
        self,
        program_id: str,
        *,
        encoding: str = "base64",
        filters: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        config: dict[str, Any] = {"encoding": encoding}
        if filters:
            config["filters"] = filters
        return await self.request("getProgramAccounts", [program_id, config])

    async def get_token_account_balance(self, pubkey: str) -> dict[str, Any]:
        return await self.request("getTokenAccountBalance", [pubkey])

    async def get_token_accounts_by_owner(
        self,
        owner: str,
        *,
        mint: str | None = None,
        program_id: str | None = None,
        encoding: str = "base64",
    ) -> dict[str, Any]:
        filter_param: dict[str, str] = {}
        if mint:
            filter_param["mint"] = mint
        elif program_id:
            filter_param["programId"] = program_id
        return await self.request(
            "getTokenAccountsByOwner",
            [owner, filter_param, {"encoding": encoding}],
        )

    async def get_token_supply(self, mint: str) -> dict[str, Any]:
        return await self.request("getTokenSupply", [mint])

    async def get_transaction_count(self, commitment: Commitment | None = None) -> int:
        c = commitment or self.commitment
        return await self.request("getTransactionCount", [{"commitment": c.value}])

    async def get_stake_activation(
        self, pubkey: str, *, epoch: int | None = None
    ) -> dict[str, Any]:
        config: dict[str, Any] = {}
        if epoch is not None:
            config["epoch"] = epoch
        return await self.request("getStakeActivation", [pubkey, config] if config else [pubkey])

    async def get_stake_minimum_delegation(self) -> dict[str, Any]:
        return await self.request("getStakeMinimumDelegation")

    async def get_inflation_governor(self) -> dict[str, Any]:
        return await self.request("getInflationGovernor")

    async def get_inflation_reward(
        self, addresses: list[str], *, epoch: int | None = None
    ) -> list[dict[str, Any] | None]:
        config: dict[str, Any] = {}
        if epoch is not None:
            config["epoch"] = epoch
        return await self.request(
            "getInflationReward", [addresses, config] if config else [addresses]
        )

    async def get_fees(self) -> dict[str, Any]:
        return await self.request("getFees")

    async def get_fee_for_message(self, message_b64: str) -> int | None:
        return await self.request("getFeeForMessage", [message_b64])

    async def get_blocks(self, start_slot: int, end_slot: int | None = None) -> list[int]:
        params: list[Any] = [start_slot]
        if end_slot is not None:
            params.append(end_slot)
        return await self.request("getBlocks", params)

    async def get_blocks_with_limit(self, start_slot: int, limit: int) -> list[int]:
        return await self.request("getBlocksWithLimit", [start_slot, limit])

    async def get_recent_prioritization_fees(
        self, addresses: list[str] | None = None
    ) -> list[dict[str, Any]]:
        return await self.request("getRecentPrioritizationFees", [addresses] if addresses else None)

    async def get_max_retransmit_slot(self) -> int:
        return await self.request("getMaxRetransmitSlot")

    async def get_max_shred_insert_slot(self) -> int:
        return await self.request("getMaxShredInsertSlot")

    async def minimum_ledger_slot(self) -> int:
        return await self.request("minimumLedgerSlot")

    async def get_slot_leader(self, commitment: Commitment | None = None) -> str:
        c = commitment or self.commitment
        return await self.request("getSlotLeader", [{"commitment": c.value}])

    async def get_slot_leaders(self, start_slot: int, limit: int) -> list[str]:
        return await self.request("getSlotLeaders", [start_slot, limit])
