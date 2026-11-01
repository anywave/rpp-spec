"""Portable snapshot bytes; every test names its concrete failing mutation."""

import hashlib
import os
from pathlib import Path
import subprocess

import pytest

from tools.prove_out import evidence


REPO = Path(__file__).resolve().parents[3]
RESULTS = REPO / "tools/prove_out/results"
ATTRIBUTES = (REPO / ".gitattributes").read_text(encoding="utf-8")
SNAPSHOT_SHA256 = {
    "completion/consent-derivation.csv": "2bb94d866f88d11e419158617b6673ada91351b8aac920b76e80eec1635006e9",
    "completion/fallback-counterexamples.csv": "ae052177cc650a8b76307f3abca8e88b58b9f8a47b3795f0d8f3845b64628b7f",
    "completion/policy.csv": "82f95cee2ac0c03d19666ea2665aa6ce152b26af1b74457b31033fe40c4bbb52",
    "completion/sector-access.csv": "1305727a7666950df026eb7bd6ce1946ea2c63c03a445d5dd374b2d1137ea136",
    "completion/sector-projection.md": "50ba1a6fd1bd5a0627d8f0e34aa1de5967e0948b5251f6f82ee327e0ca3d6745",
    "completion/summary.json": "1e9919da3496ebef956ecb65ed40810e629d65cd642c1a590c87b132c43c62a3",
    "foreign/clash-reference.csv": "ee8ca076425e1cc4a1d97a483dfc2b27dbe6d926ddfa1a8c2d72aea2a7f73d98",
    "foreign/rust-native-summary.json": "6c0cb755fd0a9f6d03cefa6545a7d320cfc8a23ba6647d30fd58c477ebeeeaca",
    "foreign/rust-native.csv": "8ad8786406cc1f24625dda28fb2f6eb1432a94c196541389bd93d67304d8f9ff",
    "foreign/rust-reference.csv": "8ad8786406cc1f24625dda28fb2f6eb1432a94c196541389bd93d67304d8f9ff",
    "foreign/summary.json": "94bd3451b6ea7f87e1b95b43c8b9705732ad9a348892aa83f69d1758bb018ef1",
}


@pytest.fixture(autouse=True)
def selected_mutation(monkeypatch):
    mutation = os.environ.get("PROVE_OUT_MUTATION")
    if mutation == "evidence_crlf_missing":
        monkeypatch.setattr(evidence, "canonical_lf", lambda data: data)
    elif mutation == "evidence_attributes_missing":
        monkeypatch.setattr(__import__(__name__, fromlist=["ATTRIBUTES"]), "ATTRIBUTES", "# protection removed\n")


def test_crlf_normalization_preserves_other_bytes_and_content_changes():
    """Mutation: strip lone CR/whitespace or normalize away a real content edit."""
    original = b"caf\xc3\xa9\r\nkeep\rcarriage\ntrailing \r\n"
    expected = b"caf\xc3\xa9\nkeep\rcarriage\ntrailing \n"
    assert evidence.canonical_lf(original) == expected
    assert evidence.canonical_lf(expected) == expected
    assert evidence.canonical_lf(original.replace(b"keep", b"edit")) != expected
    assert evidence.canonical_lf(b"no-final-newline") == b"no-final-newline"


def test_all_completion_and_foreign_snapshot_hashes_accept_crlf_only():
    """Snapshot check; executed mutation evidence_crlf_missing leaves CRLF hashed raw.

    Additional named unexecuted mutation: alter one committed evidence byte.
    These saved digests verify integrity, not independent binding execution.
    """
    actual_paths = {str(path.relative_to(RESULTS)).replace("\\", "/")
                    for folder in ("completion", "foreign")
                    for path in (RESULTS / folder).iterdir() if path.is_file()}
    assert actual_paths == set(SNAPSHOT_SHA256)
    for relative, digest in SNAPSHOT_SHA256.items():
        canonical = evidence.evidence_bytes(RESULTS / relative)
        assert hashlib.sha256(canonical).hexdigest() == digest
        converted = canonical.replace(b"\n", b"\r\n")
        assert hashlib.sha256(evidence.canonical_lf(converted)).hexdigest() == digest
        assert evidence.canonical_lf(converted + b"changed") != canonical


def test_autocrlf_checkout_preserves_all_evidence_paths_and_overlay_rules(tmp_path):
    """Executed mutation evidence_attributes_missing removes both -text rules.

    The ordinary text control must become CRLF, proving autocrlf is active.
    """
    checkout = tmp_path / "checkout"
    checkout.mkdir()

    def git(*args):
        return subprocess.run(["git", "-C", str(checkout), *args], check=True,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout

    git("init", "-b", "evidence-regression")
    git("config", "user.name", "Evidence Regression")
    git("config", "user.email", "evidence@example.invalid")
    git("config", "core.autocrlf", "true")
    git("config", "core.safecrlf", "false")
    (checkout / ".gitattributes").write_text(ATTRIBUTES, encoding="utf-8", newline="\n")
    protected = {"tools/prove_out/results/" + name: evidence.evidence_bytes(RESULTS / name)
                 for name in SNAPSHOT_SHA256}
    protected.update({"tools/overlay_sim/results/scenarios.csv": b"name,value\nrelay,1\n",
                      "tools/overlay_sim/results/summary.json": b'{"rows":1}\n'})
    for relative, payload in protected.items():
        path = checkout / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
    control = checkout / "ordinary.txt"
    control.write_bytes(b"ordinary control\n")
    git("add", ".")
    git("commit", "-m", "Exercise real autocrlf checkout")
    for relative in protected:
        (checkout / relative).unlink()
    control.unlink()
    git("checkout-index", "--force", "--all")
    assert control.read_bytes() == b"ordinary control\r\n"
    for relative, payload in protected.items():
        assert (checkout / relative).read_bytes() == payload
        assert git("show", "HEAD:" + relative) == payload
    attrs = git("check-attr", "text", "--", *protected).decode("utf-8")
    assert len(attrs.splitlines()) == len(protected)
    assert all(line.endswith(": text: unset") for line in attrs.splitlines())
