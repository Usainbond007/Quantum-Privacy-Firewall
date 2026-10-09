"""Artifact provenance and fail-closed resume checks. No Qiskit dependency.

A cache can be reused only when its exact experiment fingerprint matches.
Old untagged artifacts are deliberately NOT trusted for automatic reuse.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import tempfile


def digest(value):
    blob = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(blob).hexdigest()


def file_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def provenance(config, source_files, extra=None):
    files = {str(Path(p).name): file_sha256(p) for p in source_files}
    return {"schema": 1, "config_sha256": digest(config), "sources": files, "extra": extra or {}}


def write_json_atomic(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf8", dir=path.parent, suffix=".tmp", delete=False) as handle:
        tmp = Path(handle.name)
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)


def require_matching_cache(manifest_path, expected):
    path = Path(manifest_path)
    if not path.exists():
        raise ValueError(f"Cache manifest missing: {path}; refuse unverified resume")
    with path.open(encoding="utf8") as stream:
        actual = json.load(stream)
    if actual != expected:
        raise ValueError(f"Cache provenance mismatch at {path}; use a new output directory")
    return True


def validate_unique_keys(rows, keys):
    seen = set()
    for row in rows:
        key = tuple(row[k] for k in keys)
        if key in seen:
            raise ValueError(f"Duplicate artifact key: {key}")
        seen.add(key)
    return len(seen)
