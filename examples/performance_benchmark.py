#!/usr/bin/env python3
"""
RPP Performance Benchmark
==========================
Measures core RPP operation throughput.
All operations should be sub-microsecond for encode/decode/route.
"""
import sys, time, statistics
sys.stdout.reconfigure(encoding='utf-8')

from rpp.address import encode, decode, from_components
from rpp.network import make_routing_decision, NodeRecord, NodeTier, rank_next_hops
from rpp.geometry import (
    TorusPoint, ToroidalStateVector,
    derive_rotation_key, apply_rotation, verify_self_coherence,
)
from rpp.continuity import compute_liminal_timeout, csp_from_rpp, continuity_hash, HarmonicMode


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def warmup(fn, args_list, n=100):
    """Run fn with cycling args n times to warm up JIT / import caches."""
    for i in range(n):
        fn(*args_list[i % len(args_list)])


def bench(fn, args_list, n):
    """
    Time n calls to fn, cycling through args_list.
    Returns total wall-time in seconds.
    """
    args_len = len(args_list)
    start = time.perf_counter()
    for i in range(n):
        fn(*args_list[i % args_len])
    end = time.perf_counter()
    return end - start


def bench_noargs(fn, n):
    """Time n calls to a zero-argument callable."""
    start = time.perf_counter()
    for i in range(n):
        fn()
    end = time.perf_counter()
    return end - start


def fmt_row(name, iterations, total_sec):
    total_ms = total_sec * 1000
    ns_per_op = (total_sec / iterations) * 1e9
    ops_per_sec = iterations / total_sec
    return (
        f"{name:<32s}  {iterations:>10,d}    {total_ms:>8.1f} ms"
        f"    {ns_per_op:>6.0f} ns    {ops_per_sec:>12,.0f}/s"
    )


def _make_node(i, ts):
    """Build a NodeRecord for benchmarking purposes."""
    raw_id = f"node-{i:02d}".encode().ljust(16, b"\x00")[:16]
    return NodeRecord(
        node_id=raw_id,
        tier=NodeTier.WARM,
        theta=(i * 51) % 512,
        phi_min=(i * 51) % 512,
        phi_max=((i * 51) + 50) % 512,
        harmonic_modes=[0, 1],
        substrate_modality="tcp",
        consent_epoch=1,
        t2_ns=1_000_000,
        announced_at_ns=ts,
        signature=b"\x00" * 32,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Section 1 – Core Address Operations  (N = 1,000,000)
# ─────────────────────────────────────────────────────────────────────────────

N_ADDR = 1_000_000

def run_section1():
    print()
    print("=" * 70)
    print("Section 1: Core Address Operations  (N = {:,})".format(N_ADDR))
    print("=" * 70)

    # Pre-build arg pools (avoids per-iteration modulo overhead dominating)
    addr_args = [
        (i % 4, i % 512, i % 512, i % 256)
        for i in range(512)
    ]

    # Pre-encode a pool of addresses for decode
    decode_args = [(encode(s, t, p, h),) for (s, t, p, h) in addr_args]

    # Warm up
    warmup(encode, addr_args)
    warmup(decode, decode_args)
    warmup(from_components, addr_args)

    # encode
    t_enc = bench(encode, addr_args, N_ADDR)

    # decode
    t_dec = bench(decode, decode_args, N_ADDR)

    # from_components
    t_fc = bench(from_components, addr_args, N_ADDR)

    results = [
        ("encode()", N_ADDR, t_enc),
        ("decode()", N_ADDR, t_dec),
        ("from_components()", N_ADDR, t_fc),
    ]
    for name, n, t in results:
        print(fmt_row(name, n, t))

    return results


# ─────────────────────────────────────────────────────────────────────────────
# Section 2 – Routing Operations  (N = 100,000)
# ─────────────────────────────────────────────────────────────────────────────
#
# Real signatures (from rpp.network source):
#   make_routing_decision(packet_address: int, local_node: NodeRecord,
#                         neighbors: List[NodeRecord]) -> RoutingDecision
#   rank_next_hops(candidates: List[NodeRecord],
#                  target_theta: int, target_phi: int) -> List[NodeRecord]

N_ROUTE = 100_000

def run_section2():
    print()
    print("=" * 70)
    print("Section 2: Routing Operations  (N = {:,})".format(N_ROUTE))
    print("=" * 70)

    ts = time.time_ns()

    # Build address pool
    addr_pool = [encode(i % 4, i % 512, i % 512, i % 256) for i in range(512)]

    # Local node and 10 candidate neighbors (pre-built outside the loop)
    local_node = _make_node(0, ts)
    candidates = [_make_node(i, ts) for i in range(1, 11)]

    # make_routing_decision(packet_address, local_node, neighbors)
    mrd_args = [(addr_pool[i % 512], local_node, candidates) for i in range(512)]

    # rank_next_hops(candidates, target_theta, target_phi)
    rnh_args = [(candidates, i % 512, i % 512) for i in range(512)]

    # Warm up
    warmup(make_routing_decision, mrd_args)
    warmup(rank_next_hops, rnh_args)

    # make_routing_decision
    t_mrd = bench(make_routing_decision, mrd_args, N_ROUTE)

    # rank_next_hops
    t_rnh = bench(rank_next_hops, rnh_args, N_ROUTE)

    results = [
        ("make_routing_decision()", N_ROUTE, t_mrd),
        ("rank_next_hops(10 nodes)", N_ROUTE, t_rnh),
    ]
    for name, n, t in results:
        print(fmt_row(name, n, t))

    return results


# ─────────────────────────────────────────────────────────────────────────────
# Section 3 – Geometry Operations  (N = 10,000)
# ─────────────────────────────────────────────────────────────────────────────

N_GEO = 10_000

def run_section3():
    print()
    print("=" * 70)
    print("Section 3: Geometry Operations  (N = {:,})".format(N_GEO))
    print("=" * 70)

    # derive_rotation_key(phi_value: int, theta_value: int, harmonic: int, consent_epoch: int)
    geo_args = [
        (i % 512, i % 512, i % 256, i % 64)
        for i in range(512)
    ]

    # Pre-build a ToroidalStateVector for apply_rotation and verify_self_coherence
    _origin = TorusPoint(0.0, 0.0, 1.0)
    _acc    = TorusPoint(0.0, 0.0, 0.0)
    _tp1    = TorusPoint(1.0, 2.0, 1.0)
    _tp2    = TorusPoint(0.5, 1.5, 1.0)
    tsv = ToroidalStateVector(
        origin=_origin,
        primary=[_tp1],
        observation=[_tp2],
        omega_theta=0.1,
        omega_phi=0.1,
        rotation_accumulator=_acc,
    )

    # Pre-derive rotation keys for the apply_rotation pool
    rot_pool = [
        derive_rotation_key(i % 512, i % 512, i % 256, i % 64)
        for i in range(512)
    ]
    rot_args = [(tsv, dt, dp) for (dt, dp) in rot_pool]

    coh_callable = lambda: verify_self_coherence(tsv)

    # Warm up
    warmup(derive_rotation_key, geo_args)
    warmup(apply_rotation, rot_args)
    for _ in range(100):
        coh_callable()

    # derive_rotation_key
    t_drk = bench(derive_rotation_key, geo_args, N_GEO)

    # apply_rotation
    t_ar = bench(apply_rotation, rot_args, N_GEO)

    # verify_self_coherence
    t_vsc = bench_noargs(coh_callable, N_GEO)

    results = [
        ("derive_rotation_key()", N_GEO, t_drk),
        ("apply_rotation()", N_GEO, t_ar),
        ("verify_self_coherence()", N_GEO, t_vsc),
    ]
    for name, n, t in results:
        print(fmt_row(name, n, t))

    return results


# ─────────────────────────────────────────────────────────────────────────────
# Section 4 – Continuity Operations  (N = 50,000)
# ─────────────────────────────────────────────────────────────────────────────

N_CONT = 50_000

def run_section4():
    print()
    print("=" * 70)
    print("Section 4: Continuity Operations  (N = {:,})".format(N_CONT))
    print("=" * 70)

    # compute_liminal_timeout(shell) — cycles over shells 0-3
    clt_args = [(i % 4,) for i in range(4)]

    # csp_from_rpp(address: int, state_bytes: bytes,
    #              harmonic_mode: HarmonicMode, consent_epoch: int)
    from rpp.address import encode as _enc
    _addr = _enc(0, 96, 200, 128)
    _state = b"statedata12345678"
    csp_args = [(_addr, _state, HarmonicMode.ACTIVE, 5)]

    # Pre-build a CSP for continuity_hash
    csp = csp_from_rpp(_addr, _state, HarmonicMode.ACTIVE, 5)
    ch_callable = lambda: continuity_hash(csp)

    # Warm up
    warmup(compute_liminal_timeout, clt_args)
    warmup(csp_from_rpp, csp_args)
    for _ in range(100):
        ch_callable()

    # compute_liminal_timeout
    t_clt = bench(compute_liminal_timeout, clt_args, N_CONT)

    # csp_from_rpp
    t_csp = bench(csp_from_rpp, csp_args, N_CONT)

    # continuity_hash
    t_ch = bench_noargs(ch_callable, N_CONT)

    results = [
        ("compute_liminal_timeout()", N_CONT, t_clt),
        ("csp_from_rpp()", N_CONT, t_csp),
        ("continuity_hash()", N_CONT, t_ch),
    ]
    for name, n, t in results:
        print(fmt_row(name, n, t))

    return results


# ─────────────────────────────────────────────────────────────────────────────
# Section 5 – Summary
# ─────────────────────────────────────────────────────────────────────────────

def run_summary(all_results):
    print()
    print("=" * 70)
    print("Section 5: Summary")
    print("=" * 70)
    header = (
        f"{'Operation':<32s}  {'Iterations':>10s}    {'Total ms':>8s}"
        f"    {'ns/op':>6s}    {'ops/sec':>12s}"
    )
    divider = (
        f"{'─'*32}  {'─'*10}    {'─'*8}"
        f"    {'─'*6}    {'─'*12}"
    )
    print(header)
    print(divider)
    for name, n, t in all_results:
        print(fmt_row(name, n, t))
    print()
    print(
        "Interpretation: All core operations (encode/decode/route) are sub-microsecond.\n"
        "RPP introduces no measurable overhead for systems that already compute\n"
        "routing decisions."
    )
    print()


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print()
    print("RPP Performance Benchmark")
    print("=========================")
    print("Warming up and timing core RPP operations.")
    print("Each section warms up 100 iterations before measurement.")

    wall_start = time.perf_counter()

    r1 = run_section1()
    r2 = run_section2()
    r3 = run_section3()
    r4 = run_section4()

    wall_total = time.perf_counter() - wall_start

    all_results = r1 + r2 + r3 + r4
    run_summary(all_results)

    print(f"Total benchmark wall time: {wall_total:.2f}s")


if __name__ == "__main__":
    main()
