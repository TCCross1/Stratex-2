#!/usr/bin/env python3
"""Atlas evidence package generator (EF-001).

Writes a redacted evidence package under `.atlas/evidence/evidence-{stamp}/`.
Never dumps environment values, credentials, tokens, or raw secret matches.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

SECRET_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|secret|token|password|passwd|authorization)\s*[=:]\s*\S+"),
    re.compile(r"(?i)bearer\s+[a-z0-9\-._~+/]+=*"),
    re.compile(r"(?i)mongodb(\+srv)?://[^\s\"']+"),
    re.compile(r"(?i)postgres(ql)?://[^\s\"']+"),
    re.compile(r"(?i)mysql://[^\s\"']+"),
    re.compile(r"(?i)AKIA[0-9A-Z]{16}"),
    re.compile(r"(?i)-----BEGIN (RSA |OPENSSH |EC )?PRIVATE KEY-----"),
]

MONGO_URL_RE = re.compile(r"(?i)mongodb(\+srv)?://[^\s\"']+")
ENV_ASSIGN_RE = re.compile(r"(?i)^([A-Z0-9_]+)=(.*)$")


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _run_git(root: Path, *args: str) -> str:
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=str(root),
            capture_output=True,
            text=True,
            check=False,
        )
        return (proc.stdout or "").strip()
    except OSError:
        return ""


def redact_text(text: str) -> str:
    """Redact secrets and Mongo/connection URLs. Never preserve secret values."""
    if not text:
        return text
    out = text
    out = MONGO_URL_RE.sub("mongodb://***REDACTED***", out)
    for pat in SECRET_PATTERNS:
        out = pat.sub("[REDACTED]", out)
    # Redact .env-style assignments without dumping values.
    lines = []
    for line in out.splitlines():
        m = ENV_ASSIGN_RE.match(line.strip())
        if m and any(
            k in m.group(1).upper()
            for k in ("SECRET", "TOKEN", "PASSWORD", "PASSWD", "KEY", "MONGO", "URI", "URL", "CREDENTIAL")
        ):
            lines.append(f"{m.group(1)}=***REDACTED***")
        else:
            lines.append(line)
    return "\n".join(lines)


def _git_summary(root: Path, base: Optional[str]) -> Dict[str, Any]:
    head = _run_git(root, "rev-parse", "HEAD")
    branch = _run_git(root, "rev-parse", "--abbrev-ref", "HEAD")
    status = _run_git(root, "status", "--porcelain")
    changed: List[str] = []
    if base:
        diff = _run_git(root, "diff", "--name-only", f"{base}...HEAD")
        changed = [p for p in diff.splitlines() if p.strip()]
    else:
        staged = _run_git(root, "diff", "--name-only", "--cached")
        unstaged = _run_git(root, "diff", "--name-only")
        untracked = _run_git(root, "ls-files", "--others", "--exclude-standard")
        changed = sorted(
            {
                p
                for p in (staged.splitlines() + unstaged.splitlines() + untracked.splitlines())
                if p.strip()
            }
        )
    return {
        "head": head or None,
        "branch": branch or None,
        "base": base,
        "changed_paths": changed,
        "dirty": bool(status),
        "status_porcelain_redacted": redact_text(status),
    }


def _classify_secret_hits(root: Path, paths: List[str]) -> Dict[str, int]:
    """Count secret-pattern hits only — never store matched secret values."""
    counts = {pat.pattern: 0 for pat in SECRET_PATTERNS}
    total = 0
    for rel in paths:
        path = root / rel
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for pat in SECRET_PATTERNS:
            n = len(pat.findall(text))
            if n:
                counts[pat.pattern] += n
                total += n
    return {"total_hits": total, "by_pattern": counts}


def _safe_env_presence() -> Dict[str, bool]:
    """Record only whether sensitive env keys are present — never values."""
    keys = [
        "MONGO_URL",
        "MONGODB_URI",
        "DATABASE_URL",
        "JWT_SECRET",
        "PASSPORT_SEAL_SECRET",
        "SECRET_KEY",
        "DEV_NO_AUTH",
        "DEMO_MFA_BYPASS",
        "DEMO_SMS_BYPASS",
        "STRATEX_VERIFY_ALLOW_DIRTY",
        "ATLAS_SCOPE_OVERRIDE",
        "ATLAS_ARCHITECTURE_APPROVAL",
        "ATLAS_MERGE_AUTHORIZATION",
    ]
    return {k: (k in os.environ) for k in keys}


def generate_evidence(root: Path | str, base: Optional[str] = None) -> Path:
    """Generate a redacted Atlas evidence package.

    Returns the evidence directory path: `.atlas/evidence/evidence-{stamp}/`.
    """
    root = Path(root).resolve()
    stamp = _stamp()
    out_dir = root / ".atlas" / "evidence" / f"evidence-{stamp}"
    out_dir.mkdir(parents=True, exist_ok=True)

    git_info = _git_summary(root, base)
    secret_counts = _classify_secret_hits(root, git_info.get("changed_paths") or [])

    lanes_path = root / "engineering" / "lanes.yaml"
    contracts_path = root / "engineering" / "contracts" / "registry.yaml"
    constitution = root / "STRATEX_HIGH_VELOCITY_ENGINEERING_SYSTEM.md"

    index: Dict[str, Any] = {
        "schema": "stratex.atlas.evidence.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "stamp": stamp,
        "root": str(root),
        "production_readiness": "NOT_READY",
        "note": (
            "Evidence supports Atlas review but does not authorize merge. "
            "No credentials, tokens, environment values, or raw secret matches "
            "are included."
        ),
        "git": git_info,
        "files_present": {
            "lanes_yaml": lanes_path.is_file(),
            "contracts_registry": contracts_path.is_file(),
            "constitution": constitution.is_file(),
            "stratex_cli": (root / "stratex").is_file(),
        },
        "security": {
            "secret_pattern_hit_counts": secret_counts,
            "env_keys_present": _safe_env_presence(),
            "env_values_included": False,
        },
        "redaction": {
            "mongo_urls": True,
            "secret_patterns": True,
            "env_values": True,
        },
    }

    # Persist only the safe index — never copy .env contents or raw secrets.
    # Do not run line-oriented secret redaction across JSON (would break structure);
    # values were constructed without secrets and git status was pre-redacted.
    index_path = out_dir / "index.json"
    index_path.write_text(
        json.dumps(index, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    summary_path = out_dir / "SUMMARY.md"
    summary_path.write_text(
        "\n".join(
            [
                f"# Atlas evidence {stamp}",
                "",
                f"- Generated: {index['generated_at']}",
                f"- Branch: {git_info.get('branch')}",
                f"- HEAD: {git_info.get('head')}",
                f"- Changed paths: {len(git_info.get('changed_paths') or [])}",
                f"- Secret pattern hits (count only): {secret_counts.get('total_hits', 0)}",
                "- Env values included: false",
                "- Merge authorization: not granted by this package",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return out_dir


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate redacted Atlas evidence")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[2]))
    parser.add_argument("--base", default=None)
    args = parser.parse_args()
    path = generate_evidence(args.root, base=args.base)
    print(path)
