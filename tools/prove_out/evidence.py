"""Canonical bytes for LF-defined evidence and old CRLF-converted checkouts."""

from pathlib import Path


def canonical_lf(data):
    """Normalize CRLF only; preserve lone CR, all other bytes and final newlines."""
    return data.replace(b"\r\n", b"\n")


def evidence_bytes(path):
    """Read an evidence/source snapshot under its documented canonical LF contract."""
    return canonical_lf(Path(path).read_bytes())
