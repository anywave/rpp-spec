"""Stdlib oracle for the provisional billboard layout; no signing or cryptography.

Structural failures use exact raw-prefix/signature fixtures so refusal cannot
mask an omitted codec guard. Binding failures instead retain a valid reference.
All text below is escaped or encoded as hex in the generated ASCII table.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path


HEADER_LEN = 29
SIGNATURE_LEN = 64
MAX_FRAME_LEN = 925
SIGNATURE = bytes(range(SIGNATURE_LEN))
RECEIPT = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_."


def frame(kind=1, issuer=b"A", machine=b"B", fact=b"A", since=0, until=1,
          receipt=b"r", signature=SIGNATURE):
    header = (b"RPPB" + bytes((1, kind)) + len(issuer).to_bytes(2, "big")
              + len(machine).to_bytes(2, "big") + len(fact).to_bytes(2, "big")
              + bytes((len(receipt),)) + since.to_bytes(8, "big") + until.to_bytes(8, "big"))
    return header + issuer + machine + fact + receipt + signature


def verdict(data, signing, signature, mode):
    if len(data) < HEADER_LEN + SIGNATURE_LEN:
        return "Truncated", 0
    if len(data) > MAX_FRAME_LEN:
        return "Oversize", 0
    if data[:4] != b"RPPB":
        return "BadMagic", 0
    if data[4] != 1:
        return "UnsupportedVersion", 0
    if data[5] not in (1, 2):
        return "UnknownKind", 0
    lengths = [int.from_bytes(data[offset:offset + 2], "big") for offset in (6, 8, 10)] + [data[12]]
    issuer_len, machine_len, fact_len, receipt_len = lengths
    since, until = (int.from_bytes(data[offset:offset + 8], "big") for offset in (13, 21))
    expected = HEADER_LEN + sum(lengths) + SIGNATURE_LEN
    if len(data) < expected:
        return "Truncated", 0
    if len(data) > expected:
        return "TrailingBytes", 0
    offset = HEADER_LEN
    fields = []
    for length in lengths:
        fields.append(data[offset:offset + length])
        offset += length
    issuer, machine, fact, receipt = fields
    try:
        identifiers_valid = all(1 <= len(value.decode("utf-8")) <= 64 for value in (issuer, machine))
    except UnicodeDecodeError:
        identifiers_valid = False
    if not identifiers_valid:
        return "InvalidIdentifier", 0
    if not 1 <= fact_len <= 256 or any(not 0x20 <= value <= 0x7e for value in fact):
        return "InvalidFact", 0
    if not 1 <= receipt_len <= 64 or any(value not in RECEIPT for value in receipt):
        return "InvalidReceipt", 0
    if since >= until:
        return "InvalidInterval", 0
    accepted = mode == "bound" and data[:-SIGNATURE_LEN] == signing and data[-SIGNATURE_LEN:] == signature
    return ("OK" if accepted else "InvalidSignature"), 1


def cases():
    rows = []
    baseline = frame()

    def add(family, name, data, *, canonical=None, bound_to=None, mode="bound"):
        canonical = baseline if canonical is None else canonical
        fixture = data if bound_to is None else bound_to
        signing = fixture[:-SIGNATURE_LEN] if len(fixture) >= SIGNATURE_LEN else b""
        signature = fixture[-SIGNATURE_LEN:] if len(fixture) >= SIGNATURE_LEN else SIGNATURE
        expected, calls = verdict(data, signing, signature, mode)
        rows.append([family, name, expected, str(calls), mode, signing.hex() or "-",
                     signature.hex(), data.hex() or "-", canonical.hex()])

    def valid(name, data):
        add("valid", name, data, canonical=data)

    valid("minimum-fact", baseline)
    valid("minimum-rule", frame(kind=2))
    valid("ascii-max-fields", frame(issuer=b"I" * 64, machine=b"M" * 64, fact=b"~" * 256, receipt=b"r" * 64))
    valid("utf8-max-frame", frame(issuer=("\U0001f642" * 64).encode(), machine=("\U0001f600" * 64).encode(), fact=b"x" * 256, receipt=b"r" * 64))
    valid("unicode-identifiers", frame(issuer="\u00e9".encode(), machine="\u4e2d".encode(), fact=b"Identifier text is opaque."))
    valid("identifier-controls-not-fact", frame(issuer=b"\0", machine="\u202e".encode()))
    valid("zero-signature-last-tick", frame(since=2**64 - 2, until=2**64 - 1, signature=bytes(64)))
    valid("ones-signature", frame(kind=2, since=1, until=65536, signature=bytes([255]) * 64))
    valid("u64-until-max", frame(until=2**64 - 1))
    valid("u32-boundary", frame(since=2**32 - 1, until=2**32))
    valid("overlay-rule", frame(kind=2, fact=b"Pause this application while its owner is away.", since=8, until=10, receipt=b"rule-1"))
    valid("overlay-fact", frame(fact=b"Maintenance window starts at tick nine.", since=9, until=11, receipt=b"fact-1"))
    valid("all-printable-fact", frame(fact=bytes(range(0x20, 0x7f)), receipt=b"AZaz09-_."))
    for length in (0, 28, 96):
        add("truncation", f"prefix-{length}", baseline[:length])
    add("length", "trailing-byte", baseline + b"X")
    add("magic", "wrong-magic", b"X" + baseline[1:])
    for version in (0, 2):
        add("version", f"version-{version}", baseline[:4] + bytes((version,)) + baseline[5:])
    for kind in (0, 3):
        add("kind", f"kind-{kind}", baseline[:5] + bytes((kind,)) + baseline[6:])
    for field in ("issuer", "machine"):
        for name, value in (("empty", b""), ("257-bytes", b"x" * 257),
                            ("65-scalars", b"x" * 65), ("invalid-utf8", b"\xff")):
            add("identifier", field + "-" + name, frame(**{field: value}))
    for name, value in (("empty", b""), ("257-bytes", b"x" * 257), ("escape", b"\x1b"),
                        ("bidi", "\u202e".encode()), ("c1", b"\x85"), ("del", b"\x7f"),
                        ("tab", b"\t"), ("zero-width", "\u200b".encode()), ("tag", "\U000e0061".encode())):
        add("fact", name, frame(fact=value))
    for name, value in (("empty", b""), ("65-bytes", b"r" * 65), ("slash", b"a/b"), ("space", b"a b")):
        add("receipt", name, frame(receipt=value))
    add("interval", "equal", frame(since=1, until=1))
    add("interval", "reversed", frame(since=2, until=1))
    add("verification", "refused", baseline, mode="reject")
    add("verification", "issuer-binding", frame(issuer=b"B"), bound_to=baseline)
    add("verification", "fact-binding", frame(fact=b"B"), bound_to=baseline)
    add("verification", "signature-binding", baseline[:-1] + bytes((baseline[-1] ^ 1,)), bound_to=baseline)
    add("length", "oversize", baseline + b"X" * (MAX_FRAME_LEN + 1 - len(baseline)))
    return rows


def fields_snapshot(rows):
    header = "case\tissuer_hex\tmachine_hex\tkind\tfact_hex\tsince\tuntil\treceipt_hex\tsignature_hex\n"
    lines = []
    for row in rows:
        if row[2] != "OK":
            continue
        data = bytes.fromhex(row[7])
        lengths = [int.from_bytes(data[i:i + 2], "big") for i in (6, 8, 10)] + [data[12]]
        values, offset = [], HEADER_LEN
        for length in lengths:
            values.append(data[offset:offset + length].decode("utf-8"))
            offset += length
        issuer, machine, fact, receipt = (value.encode("utf-8").hex() for value in values)
        since, until = (str(int.from_bytes(data[i:i + 8], "big")) for i in (13, 21))
        lines.append("\t".join((row[1], issuer, machine, str(data[5]), fact, since, until,
                                receipt, data[offset:].hex())) + "\n")
    return (header + "".join(lines)).encode("ascii")


def artifacts():
    rows = cases()
    header = ("family", "case", "expected", "verifier_calls", "verifier_fixture",
              "verified_signing_hex", "verified_signature_hex", "frame_hex", "canonical_hex")
    payload = ("\t".join(header) + "\n" + "".join("\t".join(row) + "\n" for row in rows)).encode("ascii")
    fields = fields_snapshot(rows)
    manifest = {"header_bytes": HEADER_LEN, "signature_bytes": SIGNATURE_LEN, "max_frame_bytes": MAX_FRAME_LEN,
                "rows": len(rows), "bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest(),
                "fields_snapshot": {"file": "billboard-fields.tsv", "rows": sum(row[2] == "OK" for row in rows),
                    "bytes": len(fields), "sha256": hashlib.sha256(fields).hexdigest(),
                    "evidence": "independently parsed semantic fields for identical default/std and bare decode comparisons"},
                "family_counts": dict(sorted(Counter(row[0] for row in rows).items())),
                "verdict_counts": dict(sorted(Counter(row[2] for row in rows).items())),
                "evidence": "stdlib layout oracle and exact literal-prefix/signature fixtures; no signing or cryptography",
                "choices": ["RPPB version1; Fact1/Rule2; big-endian lengths and u64 times are IMPOSED",
                            "issuer/machine UTF-8: 1..64 Unicode scalars, at most256 bytes each",
                            "fact printable ASCII1..256 bytes; receipt ASCIIalnum/-_.1..64; since<until",
                            "malformed structural rows bind to their own raw bytes; binding rows retain a valid reference",
                            "canonical_hex is a separate valid field reference, not the structural-row verifier fixture"]}
    return {"billboard-corpus.tsv": payload, "billboard-fields.tsv": fields,
            "billboard-manifest.json": (json.dumps(manifest, sort_keys=True, indent=2) + "\n").encode("utf-8")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    outputs = artifacts()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for name, payload in outputs.items():
        (args.output_dir / name).write_bytes(payload)
    print(outputs["billboard-manifest.json"].decode("utf-8"), end="")


if __name__ == "__main__":
    main()
