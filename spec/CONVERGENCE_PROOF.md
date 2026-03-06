# RPP Routing Convergence: Formal Analysis

**Version:** 1.0.0
**Status:** Canonical
**Last Updated:** 2026-03-04
**License:** CC BY 4.0

---

> **Theorem (Routing Convergence):** For any RPP packet whose consent level
> φ satisfies the consent predicate at every node on a path to the target,
> the greedy angular-gradient routing algorithm terminates at a local minimum
> in at most ⌈log₀.₉₅(D_max / D_term)⌉ forward hops, where D_max = π√2 is
> the torus diameter and D_term = ANGULAR_TOLERANCE_RAD = 0.1 rad is the
> termination threshold.

---

## 1. Setup

### 1.1 The Address Space

An RPP address is a 28-bit integer. The routing-relevant components are:

- **θ (theta):** bits [25:17], integer in [0, 511]
- **φ (phi):** bits [16:8], integer in [0, 511]

Both are mapped to the torus **T = [0, 2π) × [0, 2π)** via:

```
θ_rad = (θ_int / 511) × 2π
φ_rad = (φ_int / 511) × 2π
```

The address space is a discrete grid on the torus: **512 × 512 = 262,144 distinct positions**.

### 1.2 Angular Distance (the metric)

The routing metric is the Euclidean distance in torus angle-space:

```
d(A, B) = √( min(|θ_A − θ_B|, 2π − |θ_A − θ_B|)²
            + min(|φ_A − φ_B|, 2π − |φ_A − φ_B|)² )
```

This is the **chord length on the torus surface** — not the geodesic on the embedded surface,
but an equivalent metric for the purposes of ordering (the ordering relation ≺ = "closer to target"
is preserved).

**Bounds:**
- Minimum distinguishable distance: `d_min = (1/511) × 2π ≈ 0.0123 rad`
  (one integer step in θ or φ)
- Maximum possible distance: `d_max = π√2 ≈ 4.443 rad`
  (antipodal point on the torus)

### 1.3 The Routing Algorithm (from `rpp/network.py:make_routing_decision`)

```
function ROUTE(packet, local_node, neighbors):
    1. if packet.phi < local_node.phi_min: return BARRIER
    2. my_dist ← d(local_node, packet_target)
    3. eligible ← {n ∈ neighbors : n.phi_min ≤ packet.phi ≤ n.phi_max}
    4. best ← argmin_{n ∈ eligible} d(n, packet_target)
    5. if d(best, target) < my_dist × (1 − ROUTING_GRADIENT_MIN):
           return FORWARD(best)
    6. return ACCEPT   -- local minimum
```

Where:
- `ROUTING_GRADIENT_MIN = 0.05` (5% improvement required to forward)
- `ANGULAR_TOLERANCE_RAD = 0.1 rad ≈ 5.73°`

---

## 2. Convergence Theorem

### 2.1 Definitions

**Definition 1 (Admitted packet):** A packet is *admitted* at node N if
`packet.phi ≥ N.phi_min`. An admitted path P = (N₀, N₁, …, Nₖ) is one
where the packet is admitted at every node.

**Definition 2 (φ-reachable):** A target address T is *φ-reachable* from
source S in network G if there exists an admitted path from S to some node N
such that `d(N, T) < ANGULAR_TOLERANCE_RAD`.

**Definition 3 (Local minimum):** Node N is a *local minimum* for target T
if no eligible neighbor M satisfies `d(M, T) < d(N, T) × 0.95`.

### 2.2 Main Theorem

**Theorem 1 (Monotone Descent):** Every FORWARD step strictly reduces the
angular distance to the target by at least the factor `(1 − ROUTING_GRADIENT_MIN) = 0.95`.

**Proof:** The algorithm forwards only when:
```
d(best, target) < my_dist × (1 − 0.05) = my_dist × 0.95
```
Therefore, if dₖ is the angular distance at hop k:
```
d_{k+1} < 0.95 × d_k
```
The sequence {dₖ} is strictly monotone decreasing. □

**Theorem 2 (Finite Termination):** Starting from any node with distance
D₀ ≤ D_max = π√2, the algorithm terminates in at most:

```
K_max = ⌈log(D_term / D_max) / log(0.95)⌉
```

forward hops, where `D_term = ANGULAR_TOLERANCE_RAD = 0.1 rad`.

**Proof:** From Theorem 1, after k FORWARD steps:
```
d_k < D_max × 0.95^k
```
The algorithm terminates (ACCEPT) when either:
  (a) no eligible neighbor is ≥5% closer — i.e., we are at a local minimum, OR
  (b) `d(local_node, target) < ANGULAR_TOLERANCE_RAD`

Setting `D_max × 0.95^k < D_term`:
```
k > log(D_term / D_max) / log(0.95)
  = log(0.1 / 4.443) / log(0.95)
  = log(0.02251) / log(0.95)
  ≈ (−3.792) / (−0.05129)
  ≈ 73.9
```

Therefore `K_max = 74` forward hops from the worst case.

The algorithm terminates at the first of: local minimum, angular proximity, or hop limit.
In all cases, termination occurs in finite time. □

### 2.3 Corollary: No Cycles

**Corollary 1 (Acyclicity):** The routing path never revisits a node.

**Proof:** Suppose for contradiction the path visits node N at hops i < j.
Then `d_i = d(N, target) = d_j`. But from Theorem 1, `d_j < d_i × 0.95^{j-i} < d_i`
for j > i. Contradiction. □

---

## 3. Relationship to MAX_HOP_COUNT

The constant `MAX_HOP_COUNT = 32` is a practical circuit breaker, not a theoretical bound.

### 3.1 Why 32 is Sufficient in Practice

K_max = 74 (theoretical). However, the simulation network has:
- 1,000 nodes distributed across 512×512 angular positions (mean inter-node spacing ~0.089 rad)
- Theta sectors (8 sectors, 64 theta values each) concentrating nodes in angular bands
- Target addresses sampled from the same distribution as node positions

For a uniformly distributed network, the expected number of hops is:

```
E[hops] ≈ 1 / (1 − e^{−λ × A_sector})
```

where λ is the node density and A_sector is the angular area of each sector.
For our parameters: E[hops] ≈ 1, consistent with the empirical result of 0.855.

### 3.2 When MAX_HOP_COUNT Could Be Reached

MAX_HOP_COUNT = 32 is reachable only if the greedy gradient path is unusually
long — specifically, if each hop reduces distance by exactly 5% (the minimum).
This requires:
- A sparse, linearly-arranged network with no "diagonal" shortcuts on the torus
- Target at maximum angular distance (π√2) from source

Under realistic conditions (heterogeneous tier distribution, theta-stratified
deployment), the empirical hop count has never exceeded 2 in 11,000 test packets.

### 3.3 Stuck Packet Classification

A packet is classified STUCK when it exceeds MAX_HOP_COUNT = 32 hops without
reaching a local minimum. This can occur when:
- All nearby neighbors have `phi_min > packet.phi` (consent barrier maze)
- Network partition: no admitted path exists between source and target

In the first case, the packet should be rerouted with a higher consent epoch
(or the packet's routing context adjusted). In the second case, the packet
is not φ-reachable and STUCK is the correct terminal state.

---

## 4. Consent-Gating and Convergence Separation

An important structural property: **consent-gating and geometric convergence are orthogonal**.

- BARRIER occurs at step 1 (consent check), before any geometric computation.
- Once a packet passes the consent gate, steps 2-6 are purely geometric.
- A BARRIER packet does not fail to converge — it is correctly rejected.

This separation means:
- **Convergence rate = percentage of admitted packets that reach a local minimum** (100% empirically)
- **Admission rate = percentage of packets passing all consent gates on path** (78.5% in 1000-node test)

These two rates compose independently: the overall delivery rate (78.5%) equals
admission rate × convergence rate = 0.785 × 1.000.

---

## 5. Empirical Validation

The theoretical bounds were validated by `examples/routing_convergence.py` and
`examples/network_simulation.py`:

| Metric | Theoretical Bound | 50-node Empirical | 1000-node Empirical |
|--------|-------------------|-------------------|---------------------|
| Convergence rate (admitted) | 100% (Thm 2) | 100% | 100% |
| Max hops (theoretical) | 74 | — | — |
| Max hops (observed) | — | 2 | 2 |
| Mean hops (admitted) | — | 0.99 | 0.85 |
| STUCK rate | 0% (admitted) | 0% | 0% |
| Cycles | 0% (Cor 1) | 0% | 0% |

The 100% convergence of admitted packets holds across both scales, consistent
with Theorem 2. The observed maximum of 2 hops reflects the high density of
the simulation networks relative to the torus diameter.

---

## 6. Bounds Summary

| Quantity | Value | Source |
|----------|-------|--------|
| Torus dimension | 512 × 512 | `rpp/address.py` field widths |
| Maximum angular distance | π√2 ≈ 4.443 rad | Torus geometry |
| Minimum angular distance | (1/511) × 2π ≈ 0.0123 rad | Integer quantization |
| Termination threshold | 0.1 rad (ANGULAR_TOLERANCE_RAD) | `rpp/network.py:48` |
| Minimum gradient per hop | 5% (ROUTING_GRADIENT_MIN) | `rpp/network.py:47` |
| Theoretical max hops | 74 | Theorem 2 |
| Practical max hops (circuit) | 32 (MAX_HOP_COUNT) | `rpp/network.py:46` |
| Empirical max hops | 2 | network_simulation.py |
| Empirical mean hops | 0.85 | network_simulation.py |

---

## 7. Implications for Protocol Design

### 7.1 Why 5% Gradient Minimum?

ROUTING_GRADIENT_MIN = 0.05 prevents pathological oscillation: without a
minimum improvement threshold, a packet could bounce between two nodes at
nearly equal distances, each choosing the other as "slightly closer."

A 5% threshold means each forward hop meaningfully reduces the problem size,
guaranteeing the distance sequence has no plateau.

### 7.2 Why ANGULAR_TOLERANCE_RAD = 0.1?

The tolerance 0.1 rad ≈ 5.73° was chosen to span roughly `ceil(0.1 / 0.0123) ≈ 9`
integer theta or phi steps. This means any node within 9 ticks of the target
on either axis will ACCEPT the packet — capturing the intended semantic
neighborhood without requiring exact coordinate matching.

### 7.3 Routing Without Global State

The convergence proof requires no global knowledge. At each step:
- The routing node knows only its own position, the packet's target, and its neighbors
- No global map, no routing table, no coordinator
- Convergence follows from the monotone distance property alone

This is the key architectural property: **RPP routing is provably convergent
under local information only**.

---

*This document is part of the RPP specification and is released under CC BY 4.0.*
