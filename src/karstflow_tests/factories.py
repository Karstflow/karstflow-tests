"""Test data factories for keypairs, transactions, accounts."""

from __future__ import annotations

import struct

from solana.rpc.async_api import AsyncClient
from solders.hash import Hash
from solders.keypair import Keypair
from solders.message import Message
from solders.pubkey import Pubkey
from solders.system_program import TransferParams, transfer
from solders.transaction import Transaction

from karstflow_tests.wait import wait_for_confirmation


class KeypairFactory:
    """Factory for generating test keypairs with optional funding."""

    def __init__(self, client: AsyncClient) -> None:
        self._client = client
        self._funded: list[Keypair] = []

    async def create(self, fund_lamports: int = 0) -> Keypair:
        """Create a new keypair, optionally funded via airdrop."""
        kp = Keypair()
        if fund_lamports > 0:
            resp = await self._client.request_airdrop(kp.pubkey(), fund_lamports)
            endpoint = str(self._client._provider.endpoint_uri)
            await wait_for_confirmation(endpoint, str(resp.value))
            self._funded.append(kp)
        return kp

    async def create_funded(self, lamports: int = 10_000_000_000) -> Keypair:
        """Create and fund a keypair with specified lamports."""
        return await self.create(fund_lamports=lamports)

    async def create_batch(self, count: int, fund_lamports: int = 0) -> list[Keypair]:
        """Create multiple keypairs."""
        return [await self.create(fund_lamports=fund_lamports) for _ in range(count)]


class TransactionFactory:
    """Factory for building common transaction types."""

    def __init__(self, client: AsyncClient) -> None:
        self._client = client

    async def _get_blockhash(self) -> Hash:
        resp = await self._client.get_latest_blockhash()
        return resp.value.blockhash

    async def build_transfer(
        self,
        sender: Keypair,
        recipient: Pubkey,
        lamports: int,
    ) -> Transaction:
        """Build a signed SOL transfer transaction."""
        blockhash = await self._get_blockhash()
        ix = transfer(
            TransferParams(
                from_pubkey=sender.pubkey(),
                to_pubkey=recipient,
                lamports=lamports,
            )
        )
        msg = Message.new_with_blockhash([ix], sender.pubkey(), blockhash)
        tx = Transaction.new_unsigned(msg)
        tx.sign([sender], blockhash)
        return tx

    async def send_transfer(
        self,
        sender: Keypair,
        recipient: Pubkey,
        lamports: int,
        *,
        confirm: bool = True,
    ) -> str:
        """Build, send, and optionally confirm a SOL transfer. Returns signature."""
        tx = await self.build_transfer(sender, recipient, lamports)
        resp = await self._client.send_transaction(tx)
        sig = str(resp.value)
        if confirm:
            endpoint = str(self._client._provider.endpoint_uri)
            await wait_for_confirmation(endpoint, sig)
        return sig

    async def build_transfer_many(
        self,
        sender: Keypair,
        recipients: list[tuple[Pubkey, int]],
    ) -> Transaction:
        """Build a transaction with multiple transfer instructions."""
        blockhash = await self._get_blockhash()
        ixs = [
            transfer(
                TransferParams(
                    from_pubkey=sender.pubkey(),
                    to_pubkey=to,
                    lamports=amount,
                )
            )
            for to, amount in recipients
        ]
        msg = Message.new_with_blockhash(ixs, sender.pubkey(), blockhash)
        tx = Transaction.new_unsigned(msg)
        tx.sign([sender], blockhash)
        return tx


def make_memo_data(text: str) -> bytes:
    """Create memo program instruction data from text."""
    return text.encode("utf-8")


def make_system_account_data(lamports: int, space: int, owner: Pubkey) -> bytes:
    """Build CreateAccount instruction data for system program."""
    # System program CreateAccount layout:
    # u32 instruction index (0) + u64 lamports + u64 space + 32-byte owner
    return struct.pack("<IQQ", 0, lamports, space) + bytes(owner)


# Common test pubkeys for parametrized tests
SYSTEM_PROGRAM = Pubkey.from_string("11111111111111111111111111111111")
TOKEN_PROGRAM = Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")
MEMO_PROGRAM = Pubkey.from_string("MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr")


def known_program_ids() -> list[tuple[str, Pubkey]]:
    """Return list of (name, pubkey) for known programs — useful for parametrization."""
    return [
        ("system", SYSTEM_PROGRAM),
        ("token", TOKEN_PROGRAM),
        ("memo", MEMO_PROGRAM),
    ]


def lamport_amounts() -> list[int]:
    """Common test amounts in lamports for parametrized transfer tests."""
    return [
        1,
        1_000,
        1_000_000,
        100_000_000,
        1_000_000_000,
        5_000_000_000,
    ]


def invalid_pubkey_strings() -> list[str]:
    """Invalid pubkey strings for negative test cases."""
    return [
        "",
        "not-a-key",
        "11111",
        "ZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ",
        "0" * 100,
    ]


def rpc_methods_readonly() -> list[str]:
    """Read-only RPC methods for parametrized method coverage tests."""
    return [
        "getHealth",
        "getVersion",
        "getSlot",
        "getBlockHeight",
        "getGenesisHash",
        "getEpochInfo",
        "getEpochSchedule",
        "getLeaderSchedule",
        "getRecentBlockhash",
        "getMinimumBalanceForRentExemption",
        "getSupply",
        "getStakeMinimumDelegation",
        "getInflationRate",
        "getInflationGovernor",
        "getIdentity",
        "getClusterNodes",
        "getRecentPerformanceSamples",
        "getVoteAccounts",
    ]


def rpc_methods_with_pubkey_param() -> list[str]:
    """RPC methods that require a pubkey parameter."""
    return [
        "getBalance",
        "getAccountInfo",
        "getTokenAccountsByOwner",
        "getSignaturesForAddress",
    ]
