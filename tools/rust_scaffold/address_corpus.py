"""Generate bounded Rust address fixtures by executing the unchanged Python reference.

This development scaffold is not packaged in the Rust crate or the Python rpp
package. The Rust library performs no fixture generation, I/O or randomness.
"""

import argparse
import hashlib
import json
from pathlib import Path
import random
import struct
import unicodedata

from rpp.address_canonical import RPPAddress


def bits(value):
    return struct.pack(">d", value).hex()


def number(encoded):
    return struct.unpack(">d", bytes.fromhex(encoded))[0]


def address_fields(address):
    return [f"{address.to_int():08x}", address.to_bytes().hex(), address.to_uri(),
            str(int(address.is_valid())), str(int(address.is_reserved())),
            str(int(address.is_null)), str(int(address.is_wildcard)), address.sector.name]


def construction_cases():
    cases = []
    radii = [0.0, -0.0, 1.0, 0.5, 1 / 510, 5 / 510, 0.125, 0.005, 0.995,
             float("nan"), float("inf"), -float("inf"), -0.01, 1.01]
    import math
    for encoded in range(256):
        radii.append(encoded / 255)
    for encoded in range(255):
        tie = (encoded + 0.5) / 255
        radii.extend((math.nextafter(tie, -math.inf), tie, math.nextafter(tie, math.inf)))
    for radius in radii:
        cases.append((14, 3, 2, 0, bits(radius)))
    # Every accepted combination of the three discrete constructor fields is
    # exercised once; radius/reserved are varied without a large Cartesian file.
    for theta in range(32):
        for phi in range(1, 9):
            for omega in range(8):
                radius = (theta * 37 + phi * 11 + omega * 7) % 256 / 255
                cases.append((theta, phi, omega, (theta * 257 + phi * 31 + omega) % 8192, bits(radius)))
    for theta, phi, omega, reserved in [(-1, 1, 0, 0), (32, 1, 0, 0), (1, 0, 0, 0),
                                      (1, 9, 0, 0), (1, 1, -1, 0), (1, 1, 8, 0),
                                      (1, 1, 0, -1), (1, 1, 0, 8192)]:
        cases.append((theta, phi, omega, reserved, bits(0.5)))
    rng = random.Random(0)
    for _ in range(1024):
        cases.append((rng.randrange(32), rng.randrange(1, 9), rng.randrange(8), rng.randrange(8192), bits(rng.random())))
    return list(dict.fromkeys(cases))


def construct_rows():
    rows = []
    for theta, phi, omega, reserved, radius in construction_cases():
        prefix = list(map(str, (theta, phi, omega, reserved))) + [radius]
        try:
            address = RPPAddress(theta, phi, omega, number(radius), reserved)
        except ValueError:
            rows.append(prefix + ["ERR"] + ["-"] * 8)
        else:
            rows.append(prefix + ["OK"] + address_fields(address))
    return rows


def raw_rows():
    rng = random.Random(1)
    words = [0, 1, 0xFFFFFFFF, -1, -(1 << 63), (1 << 63) - 1, 1 << 32, (1 << 32) + 7]
    words += [1 << bit for bit in range(32)]
    words += [0xFFFFFFFF ^ (1 << bit) for bit in range(32)]
    words += [rng.getrandbits(32) for _ in range(2048)]
    rows = []
    for raw in dict.fromkeys(words):
        address = RPPAddress.from_int(raw)
        rows.append([str(raw), str(address.theta), str(address.phi), str(address.omega),
                     str(address.reserved), bits(address.radius)] + address_fields(address))
    return rows


def uri_cases():
    uris = [RPPAddress(theta, phi, omega, radius).to_uri()
            for theta, phi, omega, radius in [(0, 1, 0, 0.0), (31, 8, 7, 1.0), (14, 3, 2, 0.5),
                                            (1, 1, 0, -0.0), (27, 6, 4, 1.0)]]
    base = "spiral://θ:1/φ:1/h:0/r:"
    uris += [base + value for value in ["0", "0.0", "00.50", ".5", "1.", ".", "0..5", "",
                                       "-0.0", "+0.5", "nan", "inf", "1.01", "0.5e-1", "0.5suffix",
                                       "0.5/extra", "0.5\nextra", "0.5\r\nextra", "0.5.ignored"]]
    uris += [" " + base + "0.5", base.upper() + "0.5", "spiral://theta:1/phi:1/h:0/r:0.5",
             "spiral://θ:32/φ:1/h:0/r:0.5", "spiral://θ:1/φ:0/h:0/r:0.5",
             "spiral://θ:1/φ:9/h:0/r:0.5", "spiral://θ:1/φ:1/h:8/r:0.5",
             "spiral://θ:-1/φ:1/h:0/r:0.5", "spiral://θ:0001/φ:0008/h:0007/r:0.50",
             "spiral://θ:²/φ:1/h:0/r:0.5", "spiral://θ:Ⅰ/φ:1/h:0/r:0.5"]
    for code in range(0x110000):
        character = chr(code)
        if unicodedata.category(character) == "Nd" and unicodedata.decimal(character) == 0:
            digits = [chr(code + digit) for digit in range(10)]
            uris.append(f"spiral://θ:{digits[1]}/φ:{digits[2]}/h:{digits[3]}/r:{digits[0]}.{digits[5]}{digits[0]}")
    for row in construct_rows():
        if row[5] == "OK":
            uris.append(row[8])
    return list(dict.fromkeys(uris))


def uri_rows():
    rows = []
    for uri in uri_cases():
        try:
            address = RPPAddress.from_uri(uri)
        except ValueError:
            rows.append([uri.encode("utf-8").hex(), "ERR"] + ["-"] * 9)
        else:
            rows.append([uri.encode("utf-8").hex(), "OK", bits(address.radius)] + address_fields(address))
    return rows


def tsv(header, rows):
    return ("\t".join(header) + "\n" + "".join("\t".join(row) + "\n" for row in rows)).encode("utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("rust/rpp-core/tests/data"))
    args = parser.parse_args()
    rows = {"construct": construct_rows(), "raw": raw_rows(), "uri": uri_rows()}
    suffix = ["word", "bytes", "uri", "valid", "reserved_state", "null", "wildcard", "sector"]
    headers = {
        "construct": ["theta", "phi", "omega", "reserved", "radius_bits", "status"] + suffix,
        "raw": ["raw", "theta", "phi", "omega", "reserved", "radius_bits"] + suffix,
        "uri": ["input_utf8_hex", "status", "radius_bits"] + suffix,
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    hashes = {}
    sizes = {}
    for kind in rows:
        name = f"address-{kind}.tsv"
        payload = tsv(headers[kind], rows[kind])
        (args.output_dir / name).write_bytes(payload)
        hashes[name] = hashlib.sha256(payload).hexdigest()
        sizes[name] = len(payload)
    source = Path(__file__).resolve().parents[2] / "rpp/address_canonical.py"
    summary = {"evidence": "actual unchanged Python RPPAddress outputs; Rust tests consume these fixtures",
               "python_unicode_version": unicodedata.unidata_version,
               "source_sha256_lf": hashlib.sha256(source.read_bytes().replace(b"\r\n", b"\n")).hexdigest(),
               "counts": {kind: len(values) for kind, values in rows.items()}, "sha256": hashes, "bytes": sizes,
               "limits": ["Rust integer fields cannot represent Python bool arguments", "Unicode Nd table frozen to Python Unicode15.0.0",
                          "signed raw corpus is bounded to i64; from_word handles all u32 values", "negative-zero URI and prefix parser behavior preserved"]}
    (args.output_dir / "address-manifest.json").write_bytes((json.dumps(summary, sort_keys=True, indent=2) + "\n").encode("utf-8"))
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
