"""SipHash-2-4 (64-bit tag) reference, for the rpp_update_mac test bench.

Self-check against the published SipHash-2-4 vector: key = 00 01 .. 0f, empty message -> 0x726fdb47dd0e0e31
(the first entry of the reference implementation's vectors_sip64). Run: python siphash_ref.py
"""
import struct
import sys

M64 = (1 << 64) - 1


def rotl(x, b):
    return ((x << b) | (x >> (64 - b))) & M64


def sipround(v0, v1, v2, v3):
    v0 = (v0 + v1) & M64; v1 = rotl(v1, 13); v1 ^= v0; v0 = rotl(v0, 32)
    v2 = (v2 + v3) & M64; v3 = rotl(v3, 16); v3 ^= v2
    v0 = (v0 + v3) & M64; v3 = rotl(v3, 21); v3 ^= v0
    v2 = (v2 + v1) & M64; v1 = rotl(v1, 17); v1 ^= v2; v2 = rotl(v2, 32)
    return v0, v1, v2, v3


def siphash24(key: bytes, msg: bytes) -> int:
    k0, k1 = struct.unpack("<QQ", key)
    v0 = k0 ^ 0x736F6D6570736575
    v1 = k1 ^ 0x646F72616E646F6D
    v2 = k0 ^ 0x6C7967656E657261
    v3 = k1 ^ 0x7465646279746573
    n = len(msg)
    end = n - (n % 8)
    for i in range(0, end, 8):
        m = struct.unpack("<Q", msg[i:i + 8])[0]
        v3 ^= m
        for _ in range(2):
            v0, v1, v2, v3 = sipround(v0, v1, v2, v3)
        v0 ^= m
    b = (n & 0xFF) << 56
    tail = msg[end:]
    for i, c in enumerate(tail):
        b |= c << (8 * i)
    v3 ^= b
    for _ in range(2):
        v0, v1, v2, v3 = sipround(v0, v1, v2, v3)
    v0 ^= b
    v2 ^= 0xFF
    for _ in range(4):
        v0, v1, v2, v3 = sipround(v0, v1, v2, v3)
    return v0 ^ v1 ^ v2 ^ v3


def update_record(epoch: int, sector: int, state: int) -> bytes:
    """The 8-byte record the board authenticates: little-endian u64 = epoch[15:0] | sector[8:0]<<16 | state[1:0]<<25."""
    return struct.pack("<Q", (epoch & 0xFFFF) | ((sector & 0x1FF) << 16) | ((state & 0x3) << 25))


if __name__ == "__main__":
    KEY = bytes(range(16))
    got = siphash24(KEY, b"")
    ok = got == 0x726FDB47DD0E0E31
    print(f"self-check empty message: {got:016x} {'OK' if ok else 'MISMATCH'}")
    if not ok:
        sys.exit(1)
    # Vectors for the Verilog test bench: (epoch, sector, state) -> tag, key 00..0f
    for e, s, st in [(5, 7, 0), (6, 11, 0), (5, 9, 3), (65535, 511, 2)]:
        m = update_record(e, s, st)
        print(f"VEC epoch={e} sector={s} state={st} msg={int.from_bytes(m, 'little'):016x} tag={siphash24(KEY, m):016x}")
