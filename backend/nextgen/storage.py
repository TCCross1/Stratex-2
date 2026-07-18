"""NextGen evidence storage adapter.

Directive 006 §8: replaceable storage adapter. Default implementation is a
local-disk backend rooted at `NEXTGEN_STORAGE_ROOT` (see .env), organized as:

    <root>/<tenant_id>/<mission_id>/<sha256>

Tenant isolation is enforced by path segments; the adapter never accepts a
tenant/mission id that is not URL-safe. Public URL exposure is disallowed
(§9). All downloads flow through an authenticated backend endpoint.

The adapter interface is intentionally minimal so a cloud object-storage
implementation (S3/GCS/etc.) can replace this one without touching route or
model code.
"""
from __future__ import annotations

import hashlib
import os
import re
import shutil
from pathlib import Path
from typing import BinaryIO, Optional, Tuple

_SAFE_ID_RE = re.compile(r"^[A-Za-z0-9_\-]{6,64}$")


def _validate(seg: str) -> str:
    if not _SAFE_ID_RE.match(seg):
        raise ValueError(f"Unsafe storage segment: {seg!r}")
    return seg


class LocalDiskAdapter:
    """Content-addressed local-disk adapter."""

    def __init__(self, root: Optional[str] = None):
        self.root = Path(
            root or os.environ.get("NEXTGEN_STORAGE_ROOT")
            or "/app/backend/nextgen_storage"
        ).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, tenant_id: str, mission_id: str, digest_hex: str) -> Path:
        return self.root / _validate(tenant_id) / _validate(mission_id) / _validate(digest_hex)

    def object_key(self, tenant_id: str, mission_id: str, digest_hex: str) -> str:
        """Opaque storage key used inside evidence records."""
        return f"nextgen://{_validate(tenant_id)}/{_validate(mission_id)}/{_validate(digest_hex)}"

    def put(
        self,
        tenant_id: str,
        mission_id: str,
        source: BinaryIO,
        max_bytes: int = 512 * 1024 * 1024,
    ) -> Tuple[str, int, str]:
        """Stream `source` to disk while computing SHA-256.

        Returns (sha256_hex, size_bytes, object_key).
        Enforces `max_bytes` — raises ValueError if exceeded.
        The write is temp-file → fsync → rename so the on-disk state is
        never a partial file under its final key.
        """
        h = hashlib.sha256()
        size = 0
        tenant_dir = self.root / _validate(tenant_id) / _validate(mission_id)
        tenant_dir.mkdir(parents=True, exist_ok=True)
        tmp = tenant_dir / f".upload-{os.getpid()}-{os.urandom(6).hex()}.part"
        with tmp.open("wb") as f:
            while True:
                chunk = source.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > max_bytes:
                    f.close()
                    tmp.unlink(missing_ok=True)
                    raise ValueError(f"File exceeds max size ({max_bytes} bytes)")
                h.update(chunk)
                f.write(chunk)
            f.flush()
            os.fsync(f.fileno())
        digest = h.hexdigest()
        final = tenant_dir / digest
        if final.exists():
            # Content already present (idempotent write). Discard the temp file
            # and reuse the existing object.
            tmp.unlink(missing_ok=True)
        else:
            tmp.rename(final)
        return digest, size, self.object_key(tenant_id, mission_id, digest)

    def exists(self, tenant_id: str, mission_id: str, digest_hex: str) -> bool:
        return self._path(tenant_id, mission_id, digest_hex).exists()

    def open_read(self, tenant_id: str, mission_id: str, digest_hex: str):
        path = self._path(tenant_id, mission_id, digest_hex)
        if not path.exists():
            raise FileNotFoundError(str(path))
        return path.open("rb")

    def size(self, tenant_id: str, mission_id: str, digest_hex: str) -> int:
        return self._path(tenant_id, mission_id, digest_hex).stat().st_size

    def delete_pending(self, tenant_id: str, mission_id: str, digest_hex: str) -> bool:
        """Delete an object referenced only by a pending (unfinalized) upload."""
        p = self._path(tenant_id, mission_id, digest_hex)
        if p.exists():
            p.unlink()
            return True
        return False


storage = LocalDiskAdapter()
