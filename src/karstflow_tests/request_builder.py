"""Fluent builder for constructing custom JSON-RPC requests."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class RpcRequestSpec:
    """Immutable specification for an RPC request."""

    method: str
    params: list[Any] | None = None
    commitment: str | None = None
    encoding: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


class RequestBuilder:
    """Fluent builder for RPC requests.

    Usage:
        spec = (RequestBuilder("getAccountInfo")
            .with_pubkey("11111111111111111111111111111111")
            .with_encoding("base64")
            .with_commitment("confirmed")
            .with_param("dataSlice", {"offset": 0, "length": 32})
            .build())

        result = await rpc.execute(spec)
    """

    def __init__(self, method: str) -> None:
        self._method = method
        self._positional: list[Any] = []
        self._config: dict[str, Any] = {}
        self._commitment: str | None = None
        self._encoding: str | None = None

    def with_pubkey(self, pubkey: str) -> RequestBuilder:
        """Add a pubkey as the first positional param."""
        self._positional.insert(0, pubkey)
        return self

    def with_pubkeys(self, pubkeys: list[str]) -> RequestBuilder:
        """Add multiple pubkeys as first positional param."""
        self._positional.insert(0, pubkeys)
        return self

    def with_commitment(self, commitment: str) -> RequestBuilder:
        self._commitment = commitment
        return self

    def with_encoding(self, encoding: str) -> RequestBuilder:
        self._encoding = encoding
        return self

    def with_param(self, key: str, value: Any) -> RequestBuilder:
        """Add a named config parameter."""
        self._config[key] = value
        return self

    def with_positional(self, value: Any) -> RequestBuilder:
        """Add a raw positional parameter."""
        self._positional.append(value)
        return self

    def with_data_slice(self, offset: int, length: int) -> RequestBuilder:
        self._config["dataSlice"] = {"offset": offset, "length": length}
        return self

    def with_filters(self, filters: list[dict[str, Any]]) -> RequestBuilder:
        self._config["filters"] = filters
        return self

    def with_limit(self, limit: int) -> RequestBuilder:
        self._config["limit"] = limit
        return self

    def with_min_context_slot(self, slot: int) -> RequestBuilder:
        self._config["minContextSlot"] = slot
        return self

    def with_tx_version(self, version: int = 0) -> RequestBuilder:
        """Set maxSupportedTransactionVersion."""
        self._config["maxSupportedTransactionVersion"] = version
        return self

    def build(self) -> RpcRequestSpec:
        """Build the immutable request spec."""
        config = dict(self._config)
        if self._commitment:
            config["commitment"] = self._commitment
        if self._encoding:
            config["encoding"] = self._encoding

        params: list[Any] | None = None
        if self._positional or config:
            params = list(self._positional)
            if config:
                params.append(config)

        return RpcRequestSpec(
            method=self._method,
            params=params,
            commitment=self._commitment,
            encoding=self._encoding,
            extra=dict(self._config),
        )
