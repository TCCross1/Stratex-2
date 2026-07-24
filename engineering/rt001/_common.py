"""Shared RT-001 helpers — Docker detection and honest status reporting.

Never claims production readiness. When Docker (or a dependency) is missing,
callers must surface INTEGRATION_ENVIRONMENT_UNAVAILABLE rather than PASS.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

STATUS_UNAVAILABLE = "INTEGRATION_ENVIRONMENT_UNAVAILABLE"
STATUS_OK = "OK"
STATUS_SKIP = "SKIP"

RT001_DIR = Path(__file__).resolve().parent
REPO_ROOT = RT001_DIR.parents[1]
RUNTIME_DIR = REPO_ROOT / ".rt001"
SECRETS_FILE = RUNTIME_DIR / "secrets.env"
COMPOSE_FILE = RT001_DIR / "docker-compose.yml"
ENV_EXAMPLE = RT001_DIR / ".env.example"


@dataclass
class ProbeResult:
    name: str
    status: str
    messages: List[str] = field(default_factory=list)
    available: bool = False

    def extend(self, msg: str) -> None:
        self.messages.append(msg)

    def as_lines(self) -> List[str]:
        lines = [f"[{self.status}] {self.name}"]
        for m in self.messages:
            lines.append(f"  - {m}")
        return lines


def docker_available() -> ProbeResult:
    """Return whether the Docker CLI and daemon are usable."""
    result = ProbeResult(name="docker", status=STATUS_OK, available=True)
    docker = shutil.which("docker")
    if not docker:
        result.status = STATUS_UNAVAILABLE
        result.available = False
        result.extend(f"{STATUS_UNAVAILABLE}: docker CLI not found on PATH")
        return result

    try:
        proc = subprocess.run(
            [docker, "info"],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        result.status = STATUS_UNAVAILABLE
        result.available = False
        result.extend(f"{STATUS_UNAVAILABLE}: docker info failed: {exc}")
        return result

    if proc.returncode != 0:
        result.status = STATUS_UNAVAILABLE
        result.available = False
        err = (proc.stderr or proc.stdout or "").strip().splitlines()
        detail = err[0] if err else f"exit {proc.returncode}"
        result.extend(f"{STATUS_UNAVAILABLE}: docker daemon unreachable ({detail})")
        return result

    result.extend(f"docker available at {docker}")
    return result


def compose_cmd() -> Optional[List[str]]:
    """Prefer `docker compose`, fall back to `docker-compose`."""
    docker = shutil.which("docker")
    if docker:
        probe = subprocess.run(
            [docker, "compose", "version"],
            capture_output=True,
            text=True,
        )
        if probe.returncode == 0:
            return [docker, "compose"]
    legacy = shutil.which("docker-compose")
    if legacy:
        return [legacy]
    return None


def load_dotenv_file(path: Path) -> None:
    """Load KEY=VALUE lines into os.environ without overriding existing keys."""
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key and key not in os.environ:
            os.environ[key] = value


def ensure_runtime_dir() -> Path:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    return RUNTIME_DIR


def print_result(result: ProbeResult) -> int:
    """Print probe result. Unavailable → exit 0 (does not fail repo verify)."""
    for line in result.as_lines():
        print(line)
    # Honest unavailable must not fail the whole repo verify pipeline.
    if result.status == STATUS_UNAVAILABLE:
        return 0
    if result.status == STATUS_SKIP:
        return 0
    return 0 if result.available or result.status == STATUS_OK else 1
