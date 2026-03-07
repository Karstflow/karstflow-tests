"""Locust load tests for karstflow validator.

Run with:
    uv run locust -f tests/load/locustfile.py --host http://localhost:8899

Or headless:
    uv run locust -f tests/load/locustfile.py --host http://localhost:8899 \
        --headless -u 10 -r 2 -t 60s
"""

from __future__ import annotations

from locust import HttpUser, between, task


class RpcReadUser(HttpUser):
    """Simulates read-heavy RPC traffic."""

    wait_time = between(0.1, 0.5)
    _request_id = 0

    def _rpc(self, method: str, params: list | None = None) -> dict:
        self._request_id += 1
        payload = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": method,
        }
        if params is not None:
            payload["params"] = params

        with self.client.post(
            "/",
            json=payload,
            catch_response=True,
            name=method,
        ) as response:
            if response.status_code != 200:
                response.failure(f"HTTP {response.status_code}")
                return {}
            data = response.json()
            if "error" in data:
                response.failure(f"RPC error: {data['error']['message']}")
                return {}
            response.success()
            return data.get("result", {})

    @task(10)
    def get_slot(self) -> None:
        self._rpc("getSlot")

    @task(5)
    def get_block_height(self) -> None:
        self._rpc("getBlockHeight")

    @task(3)
    def get_health(self) -> None:
        self._rpc("getHealth")

    @task(3)
    def get_epoch_info(self) -> None:
        self._rpc("getEpochInfo")

    @task(2)
    def get_version(self) -> None:
        self._rpc("getVersion")

    @task(2)
    def get_supply(self) -> None:
        self._rpc("getSupply")

    @task(1)
    def get_leader_schedule(self) -> None:
        self._rpc("getLeaderSchedule")

    @task(1)
    def get_cluster_nodes(self) -> None:
        self._rpc("getClusterNodes")

    @task(5)
    def get_latest_blockhash(self) -> None:
        self._rpc("getLatestBlockhash")

    @task(3)
    def batch_read(self) -> None:
        """Send a batch of 5 read-only calls."""
        self._request_id += 1
        methods = ["getSlot", "getBlockHeight", "getHealth", "getVersion", "getEpochInfo"]
        payloads = [
            {"jsonrpc": "2.0", "id": self._request_id + i, "method": m}
            for i, m in enumerate(methods)
        ]
        self._request_id += 5

        with self.client.post(
            "/",
            json=payloads,
            catch_response=True,
            name="batch_5_reads",
        ) as response:
            if response.status_code != 200:
                response.failure(f"HTTP {response.status_code}")
                return
            data = response.json()
            if isinstance(data, list) and len(data) == 5:
                response.success()
            else:
                response.failure("Unexpected batch response")


class MixedWorkloadUser(HttpUser):
    """Simulates mixed read/write RPC traffic."""

    wait_time = between(0.2, 1.0)
    _request_id = 0

    def _rpc(self, method: str, params: list | None = None, name: str | None = None) -> dict:
        self._request_id += 1
        payload = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": method,
        }
        if params is not None:
            payload["params"] = params

        with self.client.post(
            "/",
            json=payload,
            catch_response=True,
            name=name or method,
        ) as response:
            if response.status_code != 200:
                response.failure(f"HTTP {response.status_code}")
                return {}
            data = response.json()
            if "error" in data:
                # Some errors are expected for write operations
                response.failure(f"RPC error: {data['error']['message']}")
                return {}
            response.success()
            return data.get("result", {})

    @task(10)
    def get_slot(self) -> None:
        self._rpc("getSlot")

    @task(5)
    def get_balance_random(self) -> None:
        """Check balance of a random (non-existent) account."""
        from solders.keypair import Keypair

        kp = Keypair()
        self._rpc(
            "getBalance",
            [str(kp.pubkey()), {"commitment": "confirmed"}],
            name="getBalance_random",
        )

    @task(3)
    def get_account_info(self) -> None:
        """Check account info of system program."""
        self._rpc(
            "getAccountInfo",
            ["11111111111111111111111111111111", {"encoding": "base64"}],
            name="getAccountInfo_system",
        )

    @task(2)
    def simulate_transfer(self) -> None:
        """Simulate a transfer (no actual state change)."""
        # Just checking the endpoint responds
        self._rpc("getRecentPerformanceSamples", [1])

    @task(1)
    def get_inflation_rate(self) -> None:
        self._rpc("getInflationRate")
