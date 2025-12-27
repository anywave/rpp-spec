# RPP Boundaries: Where RPP Must Stop

**Version:** 1.0.0
**Author:** Alexander Liam Lennon
**Last Updated:** 2024-12-27
**License:** CC BY 4.0

---

## Purpose

This document defines **exact boundaries** for RPP scope. These are not suggestions—they are hard constraints that preserve the irreducible core and prevent scope creep.

**Rule:** If a feature crosses a boundary, it belongs outside RPP.

---

## Boundary A — RPP Is Not Storage

**RPP must never:**
- Store user data as its primary job
- Become a filesystem
- Become a database
- Own durability/replication/backup

**RPP may:**
- ✅ Store only minimal routing metadata (addresses, small policies, pointers)

**Test:** If you're debating "how to persist bytes," you are outside RPP.

---

## Boundary B — RPP Is Not Identity

**RPP must never:**
- Become an identity provider (IdP)
- Issue accounts
- Replace OAuth/OIDC
- Decide "who someone is"

**RPP may:**
- ✅ Consume identity context (`user_id`, `roles`) as inputs

**Test:** If you're debating login/SSO/recovery, you are outside RPP.

---

## Boundary C — RPP Is Not a Policy Language

**RPP must never:**
- Become a Rego/OPA competitor
- Create a general-purpose rule DSL
- Try to encode every edge case

**RPP may:**
- ✅ Support a tiny fixed decision function (allow/deny + route) with a few parameters

**Test:** If users start writing "scripts" inside RPP, you've lost.

---

## Boundary D — RPP Is Not an Ontology

**RPP must never:**
- Define universal semantics for all domains
- Attempt a knowledge graph / taxonomy of reality
- Prescribe "the correct meaning of X"

**RPP may:**
- ✅ Define only a coordinate schema and leave meaning mapping to implementers

**Test:** If you're arguing about "the correct meaning of X," you are outside RPP.

---

## Boundary E — RPP Is Not AI

**RPP must never:**
- Require embeddings
- Require an LLM
- Claim it understands meaning via inference

**RPP may:**
- ✅ Gate AI actions using the same address semantics

**Test:** If RPP needs a model to interpret an address, it's failed.

---

## Boundary F — RPP Is Not Physics

**RPP must never:**
- Claim real-world wave mechanics
- Require holography math to be valid
- Depend on "coherence" as anything more than an input scalar

**RPP may:**
- ✅ Use the metaphor, but the spec must remain purely computational

**Test:** If adoption requires belief, it's dead.

---

## Boundary G — RPP Must Remain Bounded

**RPP must never:**
- Add unlimited fields
- Accept arbitrary key/value tags as "core"
- Become "just JSON metadata"

**RPP must:**
- ✅ Keep core as a fixed-size label (tuple/struct)

**Test:** If people can add fields without a version bump, it's not a standard.

---

## Boundary H — RPP Should Not Try to Be "Global Truth"

**RPP must never:**
- Require every system in the world to use it
- Require universal adoption to be valuable

**RPP must:**
- ✅ Be useful in one service, one repo, one day

**Test:** If it only works at scale, it doesn't work.

---

## Summary Table

| Boundary | RPP Is NOT | RPP MAY |
|----------|------------|---------|
| A | Storage | Store routing metadata only |
| B | Identity | Consume identity as input |
| C | Policy language | Fixed allow/deny/route function |
| D | Ontology | Coordinate schema only |
| E | AI | Gate AI actions |
| F | Physics | Use metaphor, stay computational |
| G | Unbounded | Fixed-size label |
| H | Global truth | Valuable in one service |

---

## Boundary Violations (Examples)

| Proposed Feature | Violates | Why |
|------------------|----------|-----|
| "Store encrypted blobs in RPP" | A | RPP routes to storage, doesn't provide it |
| "RPP should issue JWTs" | B | That's an IdP, not a router |
| "Add if/else logic to addresses" | C | That's a policy engine |
| "Define standard meaning for 'PII'" | D | That's an ontology |
| "Use embeddings to match addresses" | E | That requires inference |
| "Coherence requires quantum effects" | F | Belief kills adoption |
| "Add custom fields per-deployment" | G | Unbounded = not a standard |
| "Only works with 100+ services" | H | Must work at N=1 |

---

## How to Use This Document

**Before proposing a feature:**
1. Check if it crosses any boundary
2. If yes → it belongs in an extension, adapter, or separate system
3. If no → proceed with RFC process

**When reviewing contributions:**
1. Apply boundary tests
2. Reject anything that requires RPP to become something else

---

## These Boundaries Are Permanent

Boundaries A–H are **architectural commitments**, not temporary limitations.

Relaxing a boundary would:
1. Require major version bump (2.0.0)
2. Likely fork the project
3. Violate the irreducibility proof

**Boundaries are as stable as the spec itself.**

---

## The Clean Rule (Anchor This)

> **RPP defines how packets are understood.**
> **It does not define how packets are stored.**
>
> **Everything else is optional.**

---

## The Critical Distinction (This Is the Line)

### RPP Core (Must Exist)

| What It Does | Required? |
|--------------|-----------|
| Defines how a packet is addressed | ✅ Yes |
| Defines how meaning is encoded | ✅ Yes |
| Defines how decisions are made | ✅ Yes |
| Works even if the packet carries zero bytes | ✅ Yes |

### Rotational Packet Payload / Holographic Storage (Optional)

| What It Does | Required? |
|--------------|-----------|
| Defines how data may be embedded | ❌ Optional |
| Defines how packets may self-contain | ❌ Optional |
| Defines advanced storage mechanics | ❌ Optional |
| Comes later, or never, and RPP still survives | ❌ Optional |

### The Test

| Statement | Valid? |
|-----------|--------|
| If RPP needs holographic storage to be valid | ❌ FAIL |
| If holographic storage can use RPP | ✅ CORRECT |

---

## What a Rotational Packet Actually Is (Grounded)

> A rotational packet is simply:
> **A small envelope with a structured address and an optional payload.**
>
> That's it.

The payload can be:
- Empty
- A pointer
- A hash
- A few bytes
- A lot of bytes (in advanced forms)

**But the address always comes first.**

---

## The Safe Mental Model

| Protocol | What It Doesn't Care About |
|----------|---------------------------|
| TCP/IP | What your packet contains |
| HTTP | How your server stores data |
| RPP | Where your bytes live physically |

**RPP answers:**
> "How should this packet be treated?"

**RPP does NOT answer:**
> "Where should these bytes live physically?"

---

*"The art of a good abstraction is knowing what to leave out."*
