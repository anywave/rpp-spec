"""Deterministic tables for the provisional rpp-control fixed-frame codec.

This is an independent stdlib layout/fixture model for the new local codec, not
cryptography or an implementation of an existing Python control codec. Verifier
fixtures recognize literal expected bytes only. Nothing here signs a message.
"""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path


FRAME_LEN = 112
HEADER_LEN = 48
SENDER = bytes(range(16))
RECIPIENT = bytes(range(128, 144))
SIGNATURE = bytes(range(64))
SEQUENCES = (0, 1, 127, 128, 255, 256, 65535, 65536,
             (1 << 24) - 1, 1 << 24, (1 << 32) - 1, 1 << 32,
             (1 << 40) - 1, 1 << 40, (1 << 48) - 1, 1 << 48,
             (1 << 56) - 1, 1 << 56, (1 << 63) - 1, 1 << 63, (1 << 64) - 1)


def frame(kind=1, sequence=0, sender=SENDER, recipient=RECIPIENT, signature=SIGNATURE):
    return b"RPPC" + bytes((1, kind, 0, 0)) + sequence.to_bytes(8, "big") + sender + recipient + signature


def verdict(data, recipient, header, signature, mode):
    if len(data) < FRAME_LEN:
        return "Truncated", 0
    if len(data) > FRAME_LEN:
        return "Oversize", 0
    if data[:4] != b"RPPC":
        return "BadMagic", 0
    if data[4] != 1:
        return "UnsupportedVersion", 0
    if data[5] not in range(1, 7):
        return "UnknownKind", 0
    if data[6:8] != b"\0\0":
        return "NonzeroReserved", 0
    if data[32:48] != recipient:
        return "WrongRecipient", 0
    accepted = data[48:] == signature
    if mode == "bound":
        accepted = accepted and data[:HEADER_LEN] == header and data[16:32] == header[16:32]
    if mode == "reject":
        accepted = False
    return ("OK" if accepted else "InvalidSignature"), 1


def cases():
    rows = []

    def add(family, case, data, *, recipient=RECIPIENT, header=None, signature=SIGNATURE, mode="bound"):
        if header is None:
            header = data[:HEADER_LEN] if len(data) >= HEADER_LEN else frame()[:HEADER_LEN]
        result, calls = verdict(data, recipient, header, signature, mode)
        rows.append([family, str(case), result, str(calls), mode, recipient.hex(), header.hex(),
                     signature.hex(), data.hex() or "-"])

    for kind in range(1, 7):
        for index, sequence in enumerate(SEQUENCES):
            add("roundtrip", f"kind-{kind}-sequence-{index}", frame(kind, sequence))
        for label, identity, signature in (("zero", bytes(16), bytes(64)),
                                           ("ones", bytes([255]) * 16, bytes([255]) * 64)):
            add("opaque-fields", f"kind-{kind}-{label}", frame(kind, 0, identity, identity, signature),
                recipient=identity, signature=signature)

    baseline = frame()
    baseline_header = baseline[:HEADER_LEN]
    for length in range(145):
        data = baseline[:length] if length <= FRAME_LEN else baseline + b"X" * (length - FRAME_LEN)
        add("length", length, data, header=baseline_header, mode="signature-only")
    for kind in range(256):
        data = bytearray(baseline)
        data[5] = kind
        add("kind", kind, bytes(data), mode="signature-only")
    for version in range(256):
        data = bytearray(baseline)
        data[4] = version
        add("version", version, bytes(data), mode="signature-only")
    for value in (0, 1, 2, 255, 256, 32768, 65535):
        data = bytearray(baseline)
        data[6:8] = value.to_bytes(2, "big")
        add("reserved", value, bytes(data), mode="signature-only")
    for index, magic in enumerate((b"XXXX", b"rppc", bytes(4))):
        add("magic", index, magic + baseline[4:], mode="signature-only")
    for offset in range(FRAME_LEN):
        for value in (0, 1, 127, 128, 255):
            if baseline[offset] == value:
                continue
            data = bytearray(baseline)
            data[offset] = value
            add("byte-substitution", f"offset-{offset}-value-{value}", bytes(data), header=baseline_header)

    for index, content in enumerate((b"START", b"GRANT", b"CONSENT", b"KEY", b"MODEL", b"PROMPT:fixture", b"ANSWER:fixture")):
        add("forbidden-raw", index, content.ljust(FRAME_LEN, b"\0"), header=baseline_header, mode="signature-only")
        add("forbidden-extension", index, baseline + content, header=baseline_header, mode="signature-only")

    for index, offset in enumerate((5, 8, 15, 16, 31, 32, 47, 48, 111)):
        data = bytearray(baseline)
        data[offset] = 3 if offset == 5 else data[offset] ^ 1
        # Recipient edits reach the verifier under their changed expected target,
        # so this checks binding of the whole header instead of being masked by
        # the separate wrong-recipient guard.
        recipient = bytes(data[32:48]) if 32 <= offset < 48 else RECIPIENT
        add("verification-binding", index, bytes(data), recipient=recipient, header=baseline_header)
    add("verifier-refusal", 0, baseline, header=baseline_header, mode="reject")
    add("wrong-recipient", 0, baseline, recipient=bytes(16), header=baseline_header, mode="signature-only")
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("rust/rpp-control/tests/data"))
    args = parser.parse_args()
    rows = cases()
    header = ["family", "case", "expected", "verifier_calls", "verifier_fixture", "recipient_hex",
              "verified_header_hex", "verified_signature_hex", "frame_hex"]
    payload = ("\t".join(header) + "\n" + "".join("\t".join(row) + "\n" for row in rows)).encode("ascii")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "control-corpus.tsv").write_bytes(payload)
    manifest = {
        "frame_bytes": FRAME_LEN, "header_bytes": HEADER_LEN, "signature_bytes": 64,
        "rows": len(rows), "bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest(),
        "family_counts": dict(sorted(Counter(row[0] for row in rows).items())),
        "verdict_counts": dict(sorted(Counter(row[2] for row in rows).items())),
        "evidence": "new provisional local layout; stdlib table oracle and literal-byte verifier fixtures, not cryptography",
        "choices": ["RPPC magic, version1, six kinds1..6, reserved-zero, big-endian sequence and 16-byte recipient binding",
                    "strict112-byte/no-payload model; 64-byte signature is opaque",
                    "signature-only fixtures isolate structural guards; bound fixtures isolate whole-header verification"],
    }
    (args.output_dir / "control-manifest.json").write_bytes((json.dumps(manifest, sort_keys=True, indent=2) + "\n").encode("utf-8"))
    print(json.dumps(manifest, sort_keys=True))


if __name__ == "__main__":
    main()
