"""Validator lifecycle management for test sessions.

Provides automatic Docker-based validator start/stop with health polling,
log capture, and configurable startup options.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from karstflow_tests.wait import wait_for_health


@dataclass
class ValidatorConfig:
    """Configuration for starting a validator node."""

    image: str = "karstflow:latest"
    rpc_port: int = 8899
    ws_port: int = 8900
    gossip_port: int = 8001
    config_path: str | None = None
    extra_args: list[str] = field(default_factory=list)
    health_timeout: float = 60.0
    env: dict[str, str] = field(default_factory=dict)

    @property
    def rpc_url(self) -> str:
        return f"http://localhost:{self.rpc_port}"

    @property
    def ws_url(self) -> str:
        return f"ws://localhost:{self.ws_port}"


@dataclass
class ValidatorProcess:
    """Running validator process handle with log access."""

    container_id: str
    config: ValidatorConfig
    _stopped: bool = False

    @property
    def rpc_url(self) -> str:
        return self.config.rpc_url

    @property
    def ws_url(self) -> str:
        return self.config.ws_url

    async def wait_ready(self) -> None:
        """Wait until the validator is responding to RPC requests."""
        await wait_for_health(self.rpc_url, timeout=self.config.health_timeout)

    async def stop(self) -> None:
        """Stop and remove the container."""
        if self._stopped:
            return
        proc = await asyncio.create_subprocess_exec(
            "docker",
            "stop",
            self.container_id,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.wait()
        proc = await asyncio.create_subprocess_exec(
            "docker",
            "rm",
            "-f",
            self.container_id,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.wait()
        self._stopped = True

    async def logs(self, tail: int = 100) -> str:
        """Get recent container logs."""
        proc = await asyncio.create_subprocess_exec(
            "docker",
            "logs",
            "--tail",
            str(tail),
            self.container_id,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        stdout, _ = await proc.communicate()
        return stdout.decode()

    async def is_running(self) -> bool:
        """Check if the container is still running."""
        proc = await asyncio.create_subprocess_exec(
            "docker",
            "inspect",
            "-f",
            "{{.State.Running}}",
            self.container_id,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        stdout, _ = await proc.communicate()
        return stdout.decode().strip() == "true"


class ValidatorLifecycle:
    """Manages validator container lifecycle for test sessions.

    Usage:
        lifecycle = ValidatorLifecycle()
        validator = await lifecycle.start()
        await validator.wait_ready()
        # ... run tests ...
        await lifecycle.stop()

    As context manager:
        async with ValidatorLifecycle() as validator:
            # validator is started and ready
            ...
    """

    def __init__(self, config: ValidatorConfig | None = None) -> None:
        self.config = config or ValidatorConfig()
        self._process: ValidatorProcess | None = None

    async def start(self) -> ValidatorProcess:
        """Start the validator in a Docker container."""
        cmd = [
            "docker",
            "run",
            "-d",
            "--name",
            f"karstflow-test-{self.config.rpc_port}",
            "-p",
            f"{self.config.rpc_port}:8899",
            "-p",
            f"{self.config.ws_port}:8900",
        ]

        for key, value in self.config.env.items():
            cmd.extend(["-e", f"{key}={value}"])

        cmd.append(self.config.image)

        if self.config.config_path:
            cmd.extend(["--config", self.config.config_path])

        cmd.extend(self.config.extra_args)

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            raise RuntimeError(f"Failed to start validator: {stderr.decode()}")

        container_id = stdout.decode().strip()
        self._process = ValidatorProcess(container_id, self.config)
        return self._process

    async def stop(self) -> None:
        """Stop the validator container."""
        if self._process:
            await self._process.stop()
            self._process = None

    async def restart(self) -> ValidatorProcess:
        """Stop and start the validator."""
        await self.stop()
        return await self.start()

    async def __aenter__(self) -> ValidatorProcess:
        validator = await self.start()
        await validator.wait_ready()
        return validator

    async def __aexit__(self, *args: object) -> None:
        await self.stop()


class ComposeLifecycle:
    """Manages a docker-compose based cluster for integration tests.

    Usage:
        async with ComposeLifecycle("docker-compose.yml", nodes=3) as cluster:
            for node in cluster:
                print(node.rpc_url)
    """

    def __init__(
        self,
        compose_file: str = "docker-compose.yml",
        *,
        nodes: int = 3,
        health_timeout: float = 90.0,
        project_name: str = "karstflow-test",
    ) -> None:
        self.compose_file = compose_file
        self.nodes = nodes
        self.health_timeout = health_timeout
        self.project_name = project_name
        self._started = False

    async def start(self) -> list[ValidatorConfig]:
        """Start the cluster via docker-compose."""
        proc = await asyncio.create_subprocess_exec(
            "docker",
            "compose",
            "-f",
            self.compose_file,
            "-p",
            self.project_name,
            "up",
            "-d",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(f"docker-compose up failed: {stderr.decode()}")

        self._started = True
        configs = []
        for i in range(self.nodes):
            configs.append(
                ValidatorConfig(
                    rpc_port=8899 + (i * 10),
                    ws_port=8900 + (i * 10),
                )
            )

        # Wait for all nodes
        await asyncio.gather(
            *(wait_for_health(c.rpc_url, timeout=self.health_timeout) for c in configs)
        )
        return configs

    async def stop(self) -> None:
        """Stop the cluster."""
        if not self._started:
            return
        proc = await asyncio.create_subprocess_exec(
            "docker",
            "compose",
            "-f",
            self.compose_file,
            "-p",
            self.project_name,
            "down",
            "-v",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.wait()
        self._started = False

    async def __aenter__(self) -> list[ValidatorConfig]:
        return await self.start()

    async def __aexit__(self, *args: object) -> None:
        await self.stop()
