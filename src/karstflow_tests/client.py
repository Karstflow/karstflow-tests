"""Unified test client facade combining RPC + WS + convenience methods."""

from __future__ import annotations

import asyncio
from typing import Any

from solana.rpc.async_api import AsyncClient
from solders.keypair import Keypair
from solders.pubkey import Pubkey

from karstflow_tests.config import Commitment, TestConfig
from karstflow_tests.factories import KeypairFactory, TransactionFactory
from karstflow_tests.rpc import RpcClient
from karstflow_tests.types import EpochInfo, RpcResponse, SignatureStatus
from karstflow_tests.wait import wait_for_confirmation, wait_for_health
from karstflow_tests.ws import WsClient


class ValidatorClient:
    """High-level test client providing unified access to validator APIs.

    Combines:
    - solana-py AsyncClient (official SDK, primary for standard operations)
    - RpcClient (raw JSON-RPC for edge cases, batch, custom methods)
    - WsClient (WebSocket subscriptions)
    - KeypairFactory (funded test accounts)
    - TransactionFactory (transaction building)
    """

    def __init__(self, config: TestConfig | None = None) -> None:
        self._config = config or TestConfig()
        self.solana = AsyncClient(self._config.rpc_url)
        self.rpc = RpcClient(config=self._config)
        self.ws = WsClient(config=self._config)
        self.keypairs = KeypairFactory(self.solana)
        self.transactions = TransactionFactory(self.solana)

    @property
    def config(self) -> TestConfig:
        return self._config

    async def close(self) -> None:
        await self.ws.close()
        await self.rpc.close()
        await self.solana.close()

    async def __aenter__(self) -> ValidatorClient:
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()

    # ── Health & readiness ───────────────────────────────────────────

    async def wait_ready(self, timeout: float | None = None) -> None:
        """Wait until validator responds to health checks."""
        t = timeout or self._config.health_timeout
        await wait_for_health(self._config.rpc_url, timeout=t)

    async def is_healthy(self) -> bool:
        """Quick health check. Returns False on any error."""
        try:
            result = await self.rpc.get_health()
            return result == "ok"
        except Exception:
            return False

    # ── Account convenience ──────────────────────────────────────────

    async def fund_account(self, pubkey: Pubkey | str, lamports: int | None = None) -> str:
        """Airdrop to an existing account. Returns signature."""
        if isinstance(pubkey, str):
            pubkey = Pubkey.from_string(pubkey)
        amount = lamports or self._config.airdrop_lamports
        resp = await self.solana.request_airdrop(pubkey, amount)
        sig = str(resp.value)
        await wait_for_confirmation(self._config.rpc_url, sig)
        return sig

    async def get_balance(self, pubkey: Pubkey | str) -> int:
        """Get account balance in lamports."""
        if isinstance(pubkey, str):
            pubkey = Pubkey.from_string(pubkey)
        result = await self.solana.get_balance(pubkey)
        return result.value

    # ── Slot & epoch ─────────────────────────────────────────────────

    async def get_slot(self) -> int:
        result = await self.solana.get_slot()
        return result.value

    async def get_epoch_info(self) -> EpochInfo:
        resp = await self.rpc.get_epoch_info()
        return EpochInfo.from_dict(resp)

    async def wait_for_slot(
        self, target_slot: int, timeout: float = 30.0, interval: float = 0.5
    ) -> int:
        """Wait until slot reaches target. Returns actual slot."""
        deadline = asyncio.get_event_loop().time() + timeout
        while asyncio.get_event_loop().time() < deadline:
            current = await self.get_slot()
            if current >= target_slot:
                return current
            await asyncio.sleep(interval)
        raise TimeoutError(f"Slot did not reach {target_slot} within {timeout}s")

    async def wait_slots(self, count: int, timeout: float = 30.0) -> int:
        """Wait for N slots to pass. Returns final slot."""
        start = await self.get_slot()
        return await self.wait_for_slot(start + count, timeout=timeout)

    # ── Transaction convenience ──────────────────────────────────────

    async def transfer(
        self,
        sender: Keypair,
        recipient: Pubkey,
        lamports: int,
        *,
        confirm: bool = True,
    ) -> str:
        """Send SOL transfer. Returns signature."""
        return await self.transactions.send_transfer(sender, recipient, lamports, confirm=confirm)

    async def get_signature_status(self, signature: str) -> SignatureStatus | None:
        """Get parsed signature status."""
        from solders.signature import Signature

        sig = Signature.from_string(signature)
        result = await self.solana.get_signature_statuses([sig])
        statuses = result.value
        if not statuses or statuses[0] is None:
            return None
        raw = statuses[0]
        return SignatureStatus(
            slot=raw.slot,
            confirmations=raw.confirmations,
            err=raw.err,
            confirmation_status=str(raw.confirmation_status) if raw.confirmation_status else None,
        )

    async def confirm_transaction(self, signature: str, timeout: float | None = None) -> None:
        """Wait for transaction confirmation."""
        t = timeout or self._config.confirmation_timeout
        await wait_for_confirmation(self._config.rpc_url, signature, timeout=t)

    # ── Batch & custom RPC ───────────────────────────────────────────

    async def batch_rpc(self, requests: list[tuple[str, list[Any] | None]]) -> list[RpcResponse]:
        """Send batch JSON-RPC request via raw client."""
        return await self.rpc.batch(requests)

    async def custom_rpc(
        self,
        method: str,
        params: list[Any] | None = None,
        *,
        commitment: Commitment | None = None,
    ) -> Any:
        """Call any RPC method with optional commitment override."""
        if commitment and params is not None:
            # Inject commitment into last dict param or append
            if params and isinstance(params[-1], dict):
                params[-1]["commitment"] = commitment.value
            else:
                params.append({"commitment": commitment.value})
        return await self.rpc.request(method, params)

    async def custom_rpc_raw(
        self,
        method: str,
        params: list[Any] | None = None,
    ) -> RpcResponse:
        """Call any RPC method and get full response (no raise on error)."""
        return await self.rpc.request_raw(method, params)
