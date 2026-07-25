"""Safe allowlisted acquisition for PX-006A external datasets."""
from __future__ import annotations

import shutil
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from .common import (
    DEFAULT_TIMEOUT_SECONDS,
    LAB_VERSION,
    MAX_ARCHIVE_BYTES,
    MAX_REDIRECTS,
    MAX_REPO_BYTES,
    content_dir,
    dataset_dir,
    get_registry_entry,
    governance_block,
    now_iso,
    quarantine_dir,
    receipt_dir,
    sanitize_dataset_id,
    sha256_file,
    write_json,
)
from .security import (
    AcquisitionSecurityError,
    assert_allowlisted_url,
    assert_https,
    bounded_redirects,
    safe_extract_zip,
)


class RedirectTracker(urllib.request.HTTPRedirectHandler):
    def __init__(self, max_redirects: int = MAX_REDIRECTS) -> None:
        super().__init__()
        self.max_redirects = max_redirects
        self.history: List[str] = []

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        self.history.append(str(newurl))
        bounded_redirects(self.history, max_redirects=self.max_redirects)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _dir_size_bytes(path: Path) -> int:
    total = 0
    for p in path.rglob("*"):
        if p.is_file() and not p.is_symlink():
            try:
                total += p.stat().st_size
            except OSError:
                continue
    return total


def _count_images(path: Path) -> int:
    n = 0
    for p in path.rglob("*"):
        if p.is_file() and p.suffix.lower() in {
            ".jpg",
            ".jpeg",
            ".tif",
            ".tiff",
            ".png",
            ".dng",
        }:
            n += 1
    return n


def _git_clone(
    url: str,
    dest: Path,
    *,
    timeout: int,
    dry_run: bool,
) -> Dict[str, Any]:
    assert_https(url)
    if dry_run:
        return {
            "status": "dry_run",
            "url": url,
            "destination": str(dest),
            "method": "git_clone",
        }
    parent = dest.parent
    parent.mkdir(parents=True, exist_ok=True)
    git_dir = dest / ".git"
    # content_dir() may pre-create an empty destination — treat non-git dirs as fresh.
    if dest.exists() and not git_dir.is_dir():
        if any(dest.iterdir()):
            raise AcquisitionSecurityError(
                f"destination exists but is not a git clone: {dest}"
            )
        dest.rmdir()
    if dest.exists() and git_dir.is_dir():
        # Idempotent: reuse existing clone; fetch latest commit tip for recording.
        subprocess.run(
            ["git", "-C", str(dest), "fetch", "--prune", "origin"],
            check=False,
            timeout=timeout,
            capture_output=True,
            text=True,
        )
    else:
        # No credentials; no submodule recursion.
        result = subprocess.run(
            [
                "git",
                "clone",
                "--depth",
                "1",
                "--single-branch",
                "--no-recurse-submodules",
                url,
                str(dest),
            ],
            check=False,
            timeout=timeout,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise AcquisitionSecurityError(
                f"git clone failed for {url}: {result.stderr.strip()[:500]}"
            )
    # Refuse to init/execute submodules.
    commit = subprocess.run(
        ["git", "-C", str(dest), "rev-parse", "HEAD"],
        check=True,
        timeout=30,
        capture_output=True,
        text=True,
    ).stdout.strip()
    # Detect LFS pointers without downloading automatically.
    lfs_required = False
    sample = list(dest.rglob("*"))[:200]
    for p in sample:
        if not p.is_file():
            continue
        try:
            head = p.read_bytes()[:120]
        except OSError:
            continue
        if head.startswith(b"version https://git-lfs.github.com/spec/v1"):
            lfs_required = True
            break
    size = _dir_size_bytes(dest)
    if size > MAX_REPO_BYTES:
        raise AcquisitionSecurityError(
            f"repository exceeds max size: {size} > {MAX_REPO_BYTES}"
        )
    return {
        "status": "acquired",
        "url": url,
        "destination": str(dest),
        "method": "git_clone",
        "repository_commit": commit,
        "size_bytes": size,
        "image_count": _count_images(dest),
        "lfs_required": lfs_required,
        "lfs_content_available": (not lfs_required),
        "submodules_initialized": False,
    }


def _download_archive(
    url: str,
    dest_archive: Path,
    *,
    timeout: int,
    dry_run: bool,
) -> Dict[str, Any]:
    assert_https(url)
    if dry_run:
        return {
            "status": "dry_run",
            "url": url,
            "destination": str(dest_archive),
            "method": "https_archive",
        }
    dest_archive.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest_archive.with_suffix(dest_archive.suffix + ".partial")
    if tmp.exists():
        tmp.unlink()
    tracker = RedirectTracker(max_redirects=MAX_REDIRECTS)
    opener = urllib.request.build_opener(tracker)
    http_meta: Dict[str, Any] = {"redirects": list(tracker.history)}
    # HEAD preflight for Content-Length when supported.
    try:
        head_req = urllib.request.Request(
            url,
            headers={"User-Agent": f"Stratex-DatasetLab/{LAB_VERSION}"},
            method="HEAD",
        )
        with opener.open(head_req, timeout=min(60, timeout)) as head_resp:
            cl = head_resp.headers.get("Content-Length")
            http_meta["preflight_content_length"] = int(cl) if cl else None
            if cl and int(cl) > MAX_ARCHIVE_BYTES:
                raise AcquisitionSecurityError(
                    f"archive Content-Length exceeds max size: {cl} > {MAX_ARCHIVE_BYTES}"
                )
    except AcquisitionSecurityError:
        raise
    except Exception as exc:  # noqa: BLE001
        http_meta["preflight_warning"] = f"{type(exc).__name__}: {exc}"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": f"Stratex-DatasetLab/{LAB_VERSION}"},
        method="GET",
    )
    try:
        with opener.open(req, timeout=timeout) as resp:
            http_meta["final_url"] = resp.geturl()
            http_meta["status"] = getattr(resp, "status", None) or resp.getcode()
            http_meta["headers"] = {
                k.lower(): v
                for k, v in resp.headers.items()
                if k.lower()
                in {
                    "content-type",
                    "content-length",
                    "etag",
                    "last-modified",
                    "content-disposition",
                }
            }
            # Redirect history after response
            http_meta["redirects"] = list(tracker.history)
            bounded_redirects(tracker.history, max_redirects=MAX_REDIRECTS)
            written = 0
            with tmp.open("wb") as out:
                while True:
                    chunk = resp.read(1024 * 1024)
                    if not chunk:
                        break
                    written += len(chunk)
                    if written > MAX_ARCHIVE_BYTES:
                        out.close()
                        tmp.unlink(missing_ok=True)
                        raise AcquisitionSecurityError(
                            f"archive exceeds max size: {written} > {MAX_ARCHIVE_BYTES}"
                        )
                    out.write(chunk)
    except urllib.error.HTTPError as exc:
        tmp.unlink(missing_ok=True)
        raise AcquisitionSecurityError(f"HTTP error acquiring {url}: {exc.code}") from exc
    except urllib.error.URLError as exc:
        tmp.unlink(missing_ok=True)
        raise AcquisitionSecurityError(f"URL error acquiring {url}: {exc}") from exc
    except Exception:
        tmp.unlink(missing_ok=True)
        raise
    tmp.replace(dest_archive)
    checksum = sha256_file(dest_archive)
    return {
        "status": "downloaded",
        "url": url,
        "destination": str(dest_archive),
        "method": "https_archive",
        "size_bytes": dest_archive.stat().st_size,
        "archive_checksum": checksum,
        "http_metadata": http_meta,
    }


def acquire_dataset(
    dataset_id: str,
    *,
    dry_run: bool = False,
    verify_only: bool = False,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> Dict[str, Any]:
    """Acquire an allowlisted dataset into STRATEX_DATASET_ROOT."""
    started = time.perf_counter()
    safe = sanitize_dataset_id(dataset_id)
    entry = get_registry_entry(safe)
    url = str(entry["acquisition_url"])
    method = str(entry["acquisition_method"])
    allowlisted = [str(entry["acquisition_url"])]
    assert_allowlisted_url(url, allowlisted)
    assert_https(url)

    root = dataset_dir(safe)
    content = content_dir(safe)
    receipts = receipt_dir(safe)
    qdir = quarantine_dir(safe)

    receipt: Dict[str, Any] = {
        "dataset_id": safe,
        "lab_version": LAB_VERSION,
        "started_at": now_iso(),
        "dry_run": dry_run,
        "verify_only": verify_only,
        "governance": governance_block(),
        "source_page": entry.get("source_page"),
        "acquisition_url": url,
        "acquisition_method": method,
        "status": "started",
        "errors": [],
        "warnings": [],
    }

    if verify_only:
        existing = content if content.exists() else root
        receipt.update(
            {
                "status": "verify_only",
                "content_path": str(content),
                "size_bytes": _dir_size_bytes(existing) if existing.exists() else 0,
                "image_count": _count_images(existing) if existing.exists() else 0,
                "completed_at": now_iso(),
                "duration_seconds": round(time.perf_counter() - started, 3),
            }
        )
        write_json(receipts / f"acquire-verify-{int(time.time())}.json", receipt)
        return receipt

    try:
        if method == "git_clone":
            result = _git_clone(url, content, timeout=timeout, dry_run=dry_run)
            receipt.update(result)
            if not dry_run:
                # File manifest checksum over relative paths + sizes (not raw GPS).
                manifest = []
                for p in sorted(content.rglob("*")):
                    if p.is_file() and not p.is_symlink():
                        rel = str(p.relative_to(content))
                        manifest.append(
                            {
                                "path": rel,
                                "size": p.stat().st_size,
                                "sha256": sha256_file(p),
                            }
                        )
                write_json(root / "file_manifest.json", manifest)
                receipt["file_manifest_checksum"] = sha256_file(root / "file_manifest.json")
                receipt["observed_file_count"] = len(manifest)
        elif method == "https_archive":
            archive_path = root / "source.zip"
            # Idempotent reuse when a complete archive is already present.
            if (
                not dry_run
                and archive_path.is_file()
                and archive_path.stat().st_size > 0
                and archive_path.stat().st_size <= MAX_ARCHIVE_BYTES
            ):
                dl = {
                    "status": "downloaded",
                    "url": url,
                    "destination": str(archive_path),
                    "method": "https_archive",
                    "size_bytes": archive_path.stat().st_size,
                    "archive_checksum": sha256_file(archive_path),
                    "http_metadata": {"reused_local_archive": True},
                }
            else:
                dl = _download_archive(
                    url, archive_path, timeout=timeout, dry_run=dry_run
                )
            receipt.update(dl)
            if not dry_run:
                # Extract to quarantine then promote.
                if qdir.exists():
                    shutil.rmtree(qdir)
                qdir.mkdir(parents=True, exist_ok=True)
                warnings = safe_extract_zip(archive_path, qdir)
                receipt["warnings"].extend(warnings)
                if content.exists():
                    shutil.rmtree(content)
                qdir.rename(content)
                receipt["image_count"] = _count_images(content)
                receipt["extracted_size_bytes"] = _dir_size_bytes(content)
                # Record DJI-specific license honesty markers.
                receipt["redistribution_allowed"] = False
                receipt["license_status"] = entry.get("license_status", "REVIEW_REQUIRED")
                receipt["license_terms_references"] = [
                    entry.get("source_page"),
                    "DJI website terms / product download page — LICENSE_REVIEW_REQUIRED",
                ]
        else:
            raise AcquisitionSecurityError(f"unsupported acquisition_method: {method}")
        receipt["status"] = receipt.get("status") or "acquired"
        if receipt["status"] == "downloaded":
            receipt["status"] = "acquired"
    except Exception as exc:  # noqa: BLE001 — acquisition boundary
        receipt["status"] = "failed"
        receipt["errors"].append(
            {"type": type(exc).__name__, "message": str(exc)[:800]}
        )
        # Cleanup interrupted partials.
        for partial in root.glob("*.partial"):
            partial.unlink(missing_ok=True)

    receipt["completed_at"] = now_iso()
    receipt["duration_seconds"] = round(time.perf_counter() - started, 3)
    receipt["local_storage_path"] = str(root)
    write_json(receipts / f"acquire-{int(time.time())}.json", receipt)
    write_json(root / "latest_acquisition.json", receipt)
    return receipt


def list_allowlisted_urls() -> List[str]:
    from .common import load_registry

    reg = load_registry()
    return [str(e["acquisition_url"]) for e in reg.get("datasets") or []]
