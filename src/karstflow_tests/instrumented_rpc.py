"""Instrumented RPC client that wraps RpcClient with middleware chain.

Transparently passes all calls through the middleware interceptors
for timing, recording, and error classification.
"""

from __future__ import annotations

import time
from typing import Any

from karstflow_tests.config import Commitment, RetryPolicy, TestConfig
from karstflow_tests.middleware import MiddlewareChain, default_middleware
from karstflow_tests.request_builder import RpcRequestSpec
from karstflow_tests.rpc import RpcClient
from karstflow_tests.types import RpcResponse


class InstrumentedRpcClient(RpcClient):
    """RpcClient with middleware interception on every call.

    Usage:
        from karstflow_tests.middleware import TimingInterceptor

        client = InstrumentedRpcClient(config=config)
        # ... run tests ...
        timing = client.middleware.get(TimingInterceptor)
        print(timing.report())
    """

    def __init__(
        self,
        url: str | None = None,
        *,
        config: TestConfig | None = None,
        timeout: float | None = None,
        commitment: Commitment | None = None,
        retry: RetryPolicy | None = None,
        middleware: MiddlewareChain | None = None,
    ) -> None:
        super().__init__(url, config=config, timeout=timeout, commitment=commitment, retry=retry)
        self.middleware = middleware or default_middleware()

    async def request(
        self,
        method: str,
        params: list[Any] | None = None,
        *,
        raw: bool = False,
    ) -> Any:
        await self.middleware.run_before(method, params)
        t0 = time.perf_counter()
        error_data: dict[str, Any] | None = None
        result = None
        try:
            resp = await super().request(method, params, raw=raw)
            if raw and isinstance(resp, RpcResponse) and resp.error is not None:
                error_data = {
                    "code": resp.error.code,
                    "message": resp.error.message,
                    "data": resp.error.data,
                }
            result = resp
            return resp
        except Exception as exc:
            error_data = {"code": -1, "message": str(exc)}
            raise
        finally:
            elapsed = (time.perf_counter() - t0) * 1000
            await self.middleware.run_after(method, params, result, error_data, elapsed)

    async def request_raw(
        self,
        method: str,
        params: list[Any] | None = None,
    ) -> RpcResponse:
        await self.middleware.run_before(method, params)
        t0 = time.perf_counter()
        error_data: dict[str, Any] | None = None
        resp: RpcResponse | None = None
        try:
            resp = await super().request_raw(method, params)
            if resp.error is not None:
                error_data = {
                    "code": resp.error.code,
                    "message": resp.error.message,
                    "data": resp.error.data,
                }
            return resp
        except Exception as exc:
            error_data = {"code": -1, "message": str(exc)}
            raise
        finally:
            elapsed = (time.perf_counter() - t0) * 1000
            await self.middleware.run_after(method, params, resp, error_data, elapsed)

    async def execute(self, spec: RpcRequestSpec) -> Any:
        return await self.request(spec.method, spec.params)

    async def execute_raw(self, spec: RpcRequestSpec) -> RpcResponse:
        return await self.request_raw(spec.method, spec.params)
