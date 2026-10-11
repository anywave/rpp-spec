"""Mobius 32-bit address profile: golden vectors, standalone.

Source of truth: DEFENSIVE_PUBLICATION_2026-10.md, Section 1 (bit layout) and 1.2 (golden vectors).
The rpp package does not implement the Mobius profile, so the encoder/decoder below is written here
directly from the supplement's bit layout and imports nothing from the package. Anyone can re-derive
the four vectors by hand from:

    word = (shell << 30) | (theta << 21) | (phi << 12) | harmonic

      bit   31..30   29..21   20..12   11..8   7..0
            shell    theta    phi      MBZ     harmonic
            2 bits   9 bits   9 bits   4 bits  8 bits

Run: python tests/test_golden_vectors_mobius32.py   (or: pytest tests/test_golden_vectors_mobius32.py)
"""

import itertools
import random

SHELL_MAX, THETA_MAX, PHI_MAX, HARMONIC_MAX = 3, 511, 511, 255
MBZ_MASK = 0xF00  # bits [11:8], must be zero


def encode(shell, theta, phi, harmonic):
    """Reject, never mask: an out-of-range field is an error."""
    for name, v, hi in (("shell", shell, SHELL_MAX), ("theta", theta, THETA_MAX),
                        ("phi", phi, PHI_MAX), ("harmonic", harmonic, HARMONIC_MAX)):
        if not isinstance(v, int) or isinstance(v, bool) or not 0 <= v <= hi:
            raise ValueError(f"{name}={v!r} out of range 0..{hi}")
    return (shell << 30) | (theta << 21) | (phi << 12) | harmonic


def decode(word):
    if not isinstance(word, int) or not 0 <= word <= 0xFFFFFFFF:
        raise ValueError(f"word={word!r} is not a 32-bit value")
    if word & MBZ_MASK:
        raise ValueError(f"MBZ bits [11:8] nonzero in 0x{word:08X}")
    return ((word >> 30) & 0x3, (word >> 21) & 0x1FF, (word >> 12) & 0x1FF, word & 0xFF)


GOLDEN = [
    ((1, 100, 170, 2), 0x4C8AA002),
    ((1, 300, 170, 2), 0x658AA002),
    ((3, 511, 511, 255), 0xFFFFF0FF),
    ((0, 0, 0, 0), 0x00000000),
]


def _raises(fn, *args):
    try:
        fn(*args)
    except ValueError:
        return True
    return False


def test_golden_vectors_encode():
    for fields, word in GOLDEN:
        assert encode(*fields) == word, f"{fields} -> 0x{encode(*fields):08X}, expected 0x{word:08X}"


def test_golden_vectors_decode():
    for fields, word in GOLDEN:
        assert decode(word) == fields


def test_encode_rejects_out_of_range():
    bad = [(4, 0, 0, 0), (-1, 0, 0, 0), (0, 512, 0, 0), (0, 999, 0, 0), (0, -1, 0, 0),
           (0, 0, 512, 0), (0, 0, -1, 0), (0, 0, 0, 256), (0, 0, 0, 4095), (0, 0, 0, -1)]
    for fields in bad:
        assert _raises(encode, *fields), f"{fields} must be rejected, not masked"


def test_nonzero_mbz_is_refused():
    assert _raises(decode, 0x4C8AA102)  # the supplement's own example: MBZ bit 8 set
    for bit in range(8, 12):
        assert _raises(decode, 0x4C8AA002 | (1 << bit)), f"MBZ bit {bit} must be refused"


def test_round_trip_and_mbz_always_zero():
    edge = [0, 1, 2, 100, 255, 256, 300, 510, 511]
    for s, t, p, h in itertools.product(range(4), edge, edge, [0, 1, 2, 127, 128, 255]):
        if p > PHI_MAX or t > THETA_MAX:
            continue
        w = encode(s, t, p, h)
        assert w & MBZ_MASK == 0
        assert decode(w) == (s, t, p, h)
    rng = random.Random(0)
    for _ in range(5000):
        f = (rng.randint(0, 3), rng.randint(0, 511), rng.randint(0, 511), rng.randint(0, 255))
        assert decode(encode(*f)) == f


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print("PASS", t.__name__)
    print(f"SUMMARY pass={len(tests)} fail=0")
