# RPP Non-Goals

**Version:** 1.0.0
**Last Updated:** 2024-12-27
**License:** CC BY 4.0

---

## Purpose of This Document

This document explicitly states what RPP does **NOT** attempt to do, claim, or provide. Non-goals are as important as goals for:

1. **Preventing scope creep** — Features that violate non-goals should be rejected
2. **Setting expectations** — Users know what not to expect
3. **Guiding contributions** — Contributors know what's out of scope
4. **Legal clarity** — No implied warranties for non-goals

---

## Explicit Non-Goals

### 1. RPP Is NOT a Filesystem

**What this means:**
- RPP does not store bytes on disk
- RPP does not manage inodes, blocks, or sectors
- RPP does not provide POSIX semantics
- RPP does not replace ext4, NTFS, ZFS, or any filesystem

**Why:**
Filesystems are mature, optimized, and everywhere. RPP adds semantic routing *on top of* filesystems, not instead of them.

**Implication:**
If you need file storage, use a filesystem. RPP tells you *which* file to access.

---

### 2. RPP Is NOT a Database

**What this means:**
- RPP does not provide SQL or query languages
- RPP does not manage transactions or ACID guarantees
- RPP does not index or search content
- RPP does not replace PostgreSQL, MySQL, MongoDB, or Redis

**Why:**
Databases are specialized for queries, consistency, and scale. RPP routes *to* databases; it doesn't replicate their functionality.

**Implication:**
If you need to query data, use a database. RPP tells you *which* database and *which* key.

---

### 3. RPP Is NOT a Blockchain

**What this means:**
- RPP has no consensus mechanism
- RPP has no distributed ledger
- RPP has no cryptocurrency or tokens
- RPP does not provide immutability guarantees
- RPP does not replace Ethereum, Hedera, or any blockchain

**Why:**
Blockchains solve trust in adversarial environments. RPP solves semantic routing in trusted environments. Different problems.

**Implication:**
If you need decentralized consensus, use a blockchain. RPP can *route to* blockchain data.

---

### 4. RPP Is NOT an AI/ML System

**What this means:**
- RPP does not generate content
- RPP does not train models
- RPP does not perform inference
- RPP does not understand natural language
- RPP does not replace GPT, Claude, or any LLM

**Why:**
AI systems produce content. RPP routes content. The semantic addressing is geometric, not learned.

**Implication:**
If you need AI capabilities, use an AI system. RPP can route AI inputs and outputs.

---

### 5. RPP Is NOT a Security Product

**What this means:**
- RPP is not a firewall
- RPP is not an intrusion detection system
- RPP is not an encryption layer
- RPP is not a VPN or secure tunnel
- RPP does not replace security infrastructure

**Why:**
Security products defend perimeters. RPP enables consent-aware routing *after* authentication. Different layers.

**Implication:**
If you need security, use security tools. RPP assumes you've already authenticated.

---

### 6. RPP Is NOT a Medical Device

**What this means:**
- RPP does not diagnose conditions
- RPP does not measure health metrics
- RPP does not provide medical advice
- RPP is not FDA-approved or CE-marked
- RPP coherence is not a health indicator

**Why:**
Medical devices require extensive validation, certification, and liability frameworks. RPP is infrastructure, not healthcare.

**Implication:**
Do not use RPP addresses or coherence values for medical decisions. Ever.

---

### 7. RPP Is NOT a Truth Detector

**What this means:**
- RPP does not determine if content is true
- RPP does not fact-check
- RPP does not verify claims
- High coherence ≠ correctness
- Grounded phi ≠ truth

**Why:**
Truth is epistemological. RPP is infrastructural. Address semantics describe *classification*, not *validity*.

**Implication:**
Do not use RPP to determine if something is true. Use it to route and classify.

---

### 8. RPP Is NOT a Performance Optimizer

**What this means:**
- RPP does not make storage faster
- RPP does not reduce latency
- RPP does not optimize I/O patterns
- RPP adds overhead (resolver lookup)

**Why:**
RPP trades raw speed for semantic awareness. The resolver is an additional layer.

**Implication:**
If you need maximum I/O performance, access storage directly. RPP is for when meaning matters more than microseconds.

---

### 9. RPP Is NOT a Replacement for Anything

**What this means:**
- RPP does not replace existing infrastructure
- RPP does not require migration
- RPP does not deprecate current systems
- RPP is additive, not substitutive

**Why:**
Replacement architectures fail. Bridge architectures succeed. We chose adoption over purity.

**Implication:**
Keep your current systems. Add RPP as a routing layer when semantic addressing adds value.

---

### 10. RPP Is NOT Patentable

**What this means:**
- No contributor may patent RPP concepts
- No company may enclose RPP addressing
- No license restricts implementation
- Prior art is intentionally published

**Why:**
A consent-based architecture cannot be coercively controlled. Open infrastructure prevents capture.

**Implication:**
Anyone can implement RPP. No one can own it. That's the point.

---

## What RPP IS (For Contrast)

| RPP IS | RPP IS NOT |
|--------|------------|
| A semantic addressing scheme | A storage system |
| A routing layer | A database |
| A bridge architecture | A replacement architecture |
| Consent-aware | A security product |
| Open infrastructure | Patentable IP |
| A specification | A complete solution |

---

## How to Use This Document

### For Users
Before asking "Can RPP do X?", check if X is listed as a non-goal.
If it is, the answer is "No, and that's intentional."

### For Contributors
Before proposing a feature, check if it violates a non-goal.
If it does, the proposal should be rejected or redirected.

### For Integrators
RPP is designed to work *with* existing systems, not replace them.
Choose RPP for semantic routing; choose other tools for their strengths.

---

## Non-Goals Are Permanent

These non-goals are architectural commitments, not temporary limitations.

Changing a non-goal into a goal would:
1. Require major version bump
2. Likely fork the project
3. Violate existing user expectations

**Non-goals are as stable as the spec itself.**

---

## Frequently Asked Questions

**Q: Can RPP ever become a database?**
A: No. If you need that, fork it and call it something else.

**Q: Can RPP add AI features?**
A: No. AI systems can use RPP. RPP won't contain AI.

**Q: Can RPP be patented by anyone?**
A: No. The defensive publication prevents this globally.

**Q: Can RPP replace my current storage?**
A: No. It routes to your current storage. Keep what works.

**Q: Can RPP make medical claims?**
A: Absolutely not. This is non-negotiable.

---

*"Knowing what not to build is as important as knowing what to build."*
