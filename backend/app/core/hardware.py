"""
STRATEX™ / HYDRA Core™ — Dynamic Hardware Mapping Utility
=========================================================

Single source of truth for the backend's compute-fabric configuration.

Resolution order (first match wins):
    1. Explicit env override:  HYDRA_COMPUTE_DEVICE = cuda | mps | cpu
    2. CUDA available          (NVIDIA GPU + nvidia-container-toolkit, multi-GPU aware)
    3. Apple MPS available     (Metal Performance Shaders on darwin/arm64)
    4. CPU fallback            (always available)

The module is import-safe: it never raises if torch is missing — downstream
inference pipelines simply receive `device.kind == "cpu"` and fall back to
numpy/onnxruntime-cpu paths.

Public surface
--------------
    detect_hardware()  -> HardwareProfile      (cached singleton)
    get_device_string() -> "cuda:0" | "mps" | "cpu"
    HardwareProfile dataclass (immutable; JSON-serializable via .as_dict())
"""

from __future__ import annotations

import logging
import os
import platform
from dataclasses import asdict, dataclass, field
from functools import lru_cache
from typing import List, Literal, Optional

logger = logging.getLogger("hydra.hardware")

DeviceKind = Literal["cuda", "mps", "cpu"]
_VALID_OVERRIDES = {"cuda", "mps", "cpu"}


@dataclass(frozen=True)
class GPUInfo:
    """Single CUDA device descriptor — surfaced for multi-GPU dispatch."""

    index: int
    name: str
    total_memory_mb: int
    compute_capability: Optional[str] = None  # e.g. "8.9" for Ada Lovelace


@dataclass(frozen=True)
class HardwareProfile:
    """Immutable snapshot of the host compute fabric at process start."""

    kind: DeviceKind
    device_string: str                     # "cuda:0" | "mps" | "cpu"
    visible_gpu_count: int                 # 0 if no CUDA
    gpus: List[GPUInfo] = field(default_factory=list)
    cpu_count: int = 0
    platform_arch: str = ""
    platform_system: str = ""
    torch_version: Optional[str] = None
    override_applied: Optional[str] = None  # HYDRA_COMPUTE_DEVICE value, if any

    def as_dict(self) -> dict:
        d = asdict(self)
        d["gpus"] = [asdict(g) for g in self.gpus]
        return d

    @property
    def supports_multi_gpu(self) -> bool:
        return self.kind == "cuda" and self.visible_gpu_count > 1


# --------------------------------------------------------------------------- #
# Probing helpers (each is import-safe + side-effect-free)                    #
# --------------------------------------------------------------------------- #
def _probe_cuda() -> tuple[bool, List[GPUInfo], Optional[str]]:
    """Return (is_available, gpu_list, torch_version)."""
    try:
        import torch  # type: ignore
    except ImportError:
        return False, [], None

    torch_version = getattr(torch, "__version__", None)
    if not torch.cuda.is_available():
        return False, [], torch_version

    gpus: List[GPUInfo] = []
    try:
        count = torch.cuda.device_count()
        for i in range(count):
            props = torch.cuda.get_device_properties(i)
            cc = f"{props.major}.{props.minor}" if hasattr(props, "major") else None
            gpus.append(
                GPUInfo(
                    index=i,
                    name=getattr(props, "name", f"cuda:{i}"),
                    total_memory_mb=int(getattr(props, "total_memory", 0) // (1024 * 1024)),
                    compute_capability=cc,
                )
            )
    except Exception as exc:  # noqa: BLE001 — defensive: never break boot
        logger.warning("CUDA probe partial-fail: %s", exc)

    return True, gpus, torch_version


def _probe_mps() -> bool:
    try:
        import torch  # type: ignore

        return bool(getattr(torch.backends, "mps", None) and torch.backends.mps.is_available())
    except Exception:
        return False


def _read_override() -> Optional[str]:
    raw = os.environ.get("HYDRA_COMPUTE_DEVICE")
    if not raw:
        return None
    val = raw.strip().lower()
    if val in _VALID_OVERRIDES:
        return val
    logger.warning(
        "HYDRA_COMPUTE_DEVICE=%r is not one of %s — ignoring override.",
        raw,
        sorted(_VALID_OVERRIDES),
    )
    return None


# --------------------------------------------------------------------------- #
# Public API                                                                  #
# --------------------------------------------------------------------------- #
@lru_cache(maxsize=1)
def detect_hardware() -> HardwareProfile:
    """Resolve the host compute fabric. Cached for the life of the process."""
    override = _read_override()
    cuda_ok, gpus, torch_version = _probe_cuda()
    mps_ok = _probe_mps()

    if override == "cuda" and not cuda_ok:
        logger.warning("HYDRA_COMPUTE_DEVICE=cuda requested but CUDA unavailable — falling back.")
        override = None
    if override == "mps" and not mps_ok:
        logger.warning("HYDRA_COMPUTE_DEVICE=mps requested but MPS unavailable — falling back.")
        override = None

    if override == "cpu":
        kind: DeviceKind = "cpu"
        device_string = "cpu"
    elif override == "cuda" or (override is None and cuda_ok):
        kind = "cuda"
        device_string = "cuda:0"
    elif override == "mps" or (override is None and mps_ok):
        kind = "mps"
        device_string = "mps"
    else:
        kind = "cpu"
        device_string = "cpu"

    profile = HardwareProfile(
        kind=kind,
        device_string=device_string,
        visible_gpu_count=len(gpus) if kind == "cuda" else 0,
        gpus=gpus if kind == "cuda" else [],
        cpu_count=os.cpu_count() or 0,
        platform_arch=platform.machine(),
        platform_system=platform.system(),
        torch_version=torch_version,
        override_applied=override,
    )

    logger.info(
        "HYDRA hardware resolved: kind=%s device=%s gpus=%d arch=%s system=%s torch=%s override=%s",
        profile.kind,
        profile.device_string,
        profile.visible_gpu_count,
        profile.platform_arch,
        profile.platform_system,
        profile.torch_version,
        profile.override_applied,
    )
    return profile


def get_device_string() -> str:
    """Convenience accessor for inference call-sites: `tensor.to(get_device_string())`."""
    return detect_hardware().device_string


__all__ = ["GPUInfo", "HardwareProfile", "detect_hardware", "get_device_string"]
