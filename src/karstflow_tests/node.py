"""Node process/container manager for karstflow validator."""

from __future__ import annotations

import asyncio
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from karstflow_tests.wait import wait_for_health


@dataclass
class NodeHandle:
    """Handle to a running karstflow validator node."""

    rpc_url: str = "http://localhost:8899"
    ws_url: str = "ws://localhost:8900"
    process: subprocess.Popen[bytes] | None = None
    container_id: str | None = None

    async def wait_ready(self, timeout: float = 30.0) -> None:
        """Wait until the node responds to health checks."""
        await wait_for_health(self.rpc_url, timeout=timeout)

    async def stop(self) -> None:
        """Stop the node process or container."""
        if self.process is not None:
            self.process.terminate()
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.process = None
        elif self.container_id is not None:
            proc = await asyncio.create_subprocess_exec(
                "docker",
                "stop",
                self.container_id,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await proc.wait()
            self.container_id = None


@dataclass
class ClusterHandle:
    """Handle to a multi-node karstflow cluster."""

    nodes: list[NodeHandle] = field(default_factory=list)
    compose_file: str | None = None

    @classmethod
    def from_urls(cls, urls: list[str]) -> ClusterHandle:
        """Create a handle from pre-running node URLs."""
        nodes = []
        for url in urls:
            ws_url = (
                url.replace("http://", "ws://")
                .replace(":8899", ":8900")
                .replace(":8909", ":8910")
            )
            nodes.append(NodeHandle(rpc_url=url, ws_url=ws_url))
        return cls(nodes=nodes)

    async def wait_all_ready(self, timeout: float = 60.0) -> None:
        """Wait until all nodes respond to health checks."""
        await asyncio.gather(*(node.wait_ready(timeout=timeout) for node in self.nodes))

    async def stop(self) -> None:
        """Stop all cluster nodes via docker-compose."""
        if self.compose_file:
            proc = await asyncio.create_subprocess_exec(
                "docker",
                "compose",
                "-f",
                self.compose_file,
                "down",
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await proc.wait()
        else:
            await asyncio.gather(*(node.stop() for node in self.nodes))


class NodeManager:
    """Manages karstflow node lifecycle for testing."""

    def start_local(
        self,
        binary_path: str | Path,
        config: dict[str, Any] | None = None,
        rpc_port: int = 8899,
        ws_port: int = 8900,
    ) -> NodeHandle:
        """Start a validator node via local binary subprocess."""
        cmd = [str(binary_path), "--dev"]
        if config:
            for key, value in config.items():
                cmd.extend([f"--{key}", str(value)])

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        return NodeHandle(
            rpc_url=f"http://localhost:{rpc_port}",
            ws_url=f"ws://localhost:{ws_port}",
            process=process,
        )

    async def start_docker(
        self,
        image: str = "karstflow:latest",
        rpc_port: int = 8899,
        ws_port: int = 8900,
        extra_args: list[str] | None = None,
    ) -> NodeHandle:
        """Start a validator node via Docker container."""
        cmd = [
            "docker",
            "run",
            "-d",
            "-p",
            f"{rpc_port}:8899",
            "-p",
            f"{ws_port}:8900",
            image,
            "--dev",
        ]
        if extra_args:
            cmd.extend(extra_args)

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        container_id = stdout.decode().strip()

        return NodeHandle(
            rpc_url=f"http://localhost:{rpc_port}",
            ws_url=f"ws://localhost:{ws_port}",
            container_id=container_id,
        )

    async def start_cluster(
        self,
        compose_file: str = "docker-compose.yml",
        nodes: int = 3,
    ) -> ClusterHandle:
        """Start a multi-node cluster via docker-compose."""
        proc = await asyncio.create_subprocess_exec(
            "docker",
            "compose",
            "-f",
            compose_file,
            "up",
            "-d",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.wait()

        # Build node handles for each validator service
        node_handles = []
        for i in range(nodes):
            rpc_port = 8899 + (i * 100)
            ws_port = 8900 + (i * 100)
            node_handles.append(
                NodeHandle(
                    rpc_url=f"http://localhost:{rpc_port}",
                    ws_url=f"ws://localhost:{ws_port}",
                )
            )

        return ClusterHandle(nodes=node_handles, compose_file=compose_file)
