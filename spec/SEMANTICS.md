# RPP Semantic Model

**Version:** 1.0.0
**Status:** Canonical
**Last Updated:** 2024-12-27
**License:** CC BY 4.0

---

## 1. Overview

This document defines the semantic interpretation of RPP addresses. While the [SPEC.md](SPEC.md) defines the mechanical encoding, this document defines what addresses **mean**.

---

## 2. Geometric Foundation

### 2.1 Why Spherical Coordinates?

RPP uses spherical coordinates because:

1. **No privileged origin**: All directions are equally valid
2. **Natural hierarchy**: Radial depth encodes layers
3. **Angular locality**: Similar functions cluster together
4. **Bounded space**: No infinite addressing
5. **Symmetry**: Rotations preserve relationships

### 2.2 Coordinate Visualization

```
                    Phi = 511 (Ethereal/Abstract)
                           │
                           │
                    ╭──────┴──────╮
                   ╱               ╲
                  ╱                 ╲
                 ╱                   ╲
Theta = 0  ────╱─────────○─────────╲────  Theta = 511
(Gene)         ╲    Shell 0-3      ╱      (Meta)
                ╲                 ╱
                 ╲               ╱
                  ╲             ╱
                   ╲           ╱
                    ╰─────────╯
                           │
                           │
                    Phi = 0 (Grounded/Physical)
```

---

## 3. Shell (Radial Depth)

### 3.1 Definition

Shell encodes **hierarchical depth** or **storage temperature**:

```
          Shell 3 (Frozen/Archive)
              ╱─────────╲
             ╱  Shell 2  ╲
            ╱  (Cold)     ╲
           ╱   ╱─────╲     ╲
          ╱   ╱ Shell 1╲    ╲
         ╱   ╱  (Warm)  ╲    ╲
        ╱   ╱   ╱───╲    ╲    ╲
       ╱   ╱   ╱Shell 0╲  ╲    ╲
      ╱   ╱   ╱  (Hot)  ╲  ╲    ╲
     ╱   ╱   ╱           ╲  ╲    ╲
    ╱   ╱   ╱      ○      ╲  ╲    ╲
   ╱   ╱   ╱               ╲  ╲    ╲
```

### 3.2 Shell Semantics

| Shell | Name | Temperature | Access Pattern | Typical Use |
|-------|------|-------------|----------------|-------------|
| 0 | Core | Hot | Frequent, low-latency | Active state, cache |
| 1 | Working | Warm | Regular, moderate | Session data, buffers |
| 2 | Persistent | Cold | Infrequent, high-latency | Long-term storage |
| 3 | Archive | Frozen | Rare, batch | Dormant data, backups |

### 3.3 Shell Transitions

Data MAY move between shells based on:
- Access frequency (automatic tiering)
- Explicit lifecycle events
- Consent state changes
- Coherence fluctuations

**Invariant:** Data semantics (theta, phi, harmonic) remain constant; only shell changes.

---

## 4. Theta (Functional Sector)

### 4.1 Definition

Theta encodes **functional classification** — what the data *does* or *is for*.

### 4.2 Canonical Sector Map

```
                         0 (Gene)
                           │
              450 (Meta) ──┼── 64 (Memory)
                          ╱│╲
                         ╱ │ ╲
              384 ──────╱──┼──╲────── 128
           (Emergence) ╱   │   ╲    (Witness)
                      ╱    │    ╲
                     ╱     │     ╲
            320 ────╱──────┼──────╲──── 192
          (Guardian)       │       (Dream)
                           │
                    256 (Bridge)
```

### 4.3 Sector Definitions

| Theta Range | Sector | Function | Examples |
|-------------|--------|----------|----------|
| 0-63 | **Gene** | Core identity, immutable traits | User ID, biometric hash, soul token |
| 64-127 | **Memory** | Experiential storage | Conversations, events, learned patterns |
| 128-191 | **Witness** | Observational records | Logs, audits, external events |
| 192-255 | **Dream** | Speculative/creative | Predictions, hypotheticals, imagination |
| 256-319 | **Bridge** | Integration/translation | API calls, format conversions |
| 320-383 | **Guardian** | Protection/consent | Access rules, safety constraints |
| 384-447 | **Emergence** | Novel pattern detection | Anomalies, insights, discoveries |
| 448-511 | **Meta** | Self-reference | Statistics, health, coherence state |

### 4.4 Sector Properties

| Sector | Mutability | Consent Required | Typical Shell |
|--------|------------|------------------|---------------|
| Gene | Immutable | FULL | 0-1 |
| Memory | Append-mostly | FULL | 1-2 |
| Witness | Append-only | DIMINISHED | 2-3 |
| Dream | Volatile | DIMINISHED | 0-1 |
| Bridge | Transient | DIMINISHED | 0 |
| Guardian | Protected | FULL | 0-1 |
| Emergence | Dynamic | FULL | 0-1 |
| Meta | Auto-updated | READ_ONLY | 0 |

---

## 5. Phi (Grounding Level)

### 5.1 Definition

Phi encodes the **grounding axis** — from concrete/physical to abstract/ethereal.

### 5.2 Grounding Spectrum

```
Phi:  0 ─────────────────────────────────────────── 511

      │ GROUNDED │ TRANSITIONAL │ ABSTRACT │ ETHEREAL │
      └──────────┴──────────────┴──────────┴──────────┘
         0-127       128-255       256-383    384-511

      Physical    Contextual    Conceptual   Emergent
      Verifiable  Situational   Inferential  Speculative
      Sensor      Behavioral    Reasoning    Creative
```

### 5.3 Grounding Interpretations

| Phi Range | Level | Interpretation | Examples |
|-----------|-------|----------------|----------|
| 0-127 | Grounded | Direct sensor data, physical facts | Heart rate, GPS, timestamps |
| 128-255 | Transitional | Processed signals, behavioral | Mood estimate, activity state |
| 256-383 | Abstract | Conceptual, inferred | Intentions, preferences |
| 384-511 | Ethereal | Emergent, speculative | Predictions, dreams, hunches |

### 5.4 Grounding and Consent

Higher grounding (lower phi) typically requires:
- Higher consent levels
- More explicit verification
- Stronger audit trails

Lower grounding (higher phi) allows:
- More flexible access
- Probabilistic handling
- Graceful degradation

---

## 6. Harmonic (Mode/Resolution)

### 6.1 Definition

Harmonic encodes **frequency, version, or resolution mode**.

### 6.2 Harmonic Interpretations

| Harmonic Range | Mode | Interpretation |
|----------------|------|----------------|
| 0-31 | Raw | Unprocessed, original |
| 32-63 | Minimal | Compressed, essential only |
| 64-95 | Summary | Aggregated, reduced |
| 96-127 | Standard | Normal resolution |
| 128-159 | Enhanced | Detailed |
| 160-191 | Full | Complete fidelity |
| 192-223 | Extended | With metadata |
| 224-255 | Maximum | All available detail |

### 6.3 Version Encoding

Harmonic MAY encode versions:

```
harmonic = (major * 64) + (minor * 8) + patch

Example:
  Version 2.1.3 → harmonic = (2 * 64) + (1 * 8) + 3 = 139
```

### 6.4 Resolution Cascading

When requested harmonic is unavailable, resolvers MAY:

1. Return next-lower available harmonic
2. Return next-higher with flag
3. Return error

**Invariant:** Never silently return different content without indication.

---

## 7. Address Semantics in Action

### 7.1 Example Addresses

**User's Core Identity**
```
Shell: 0 (hot)
Theta: 32 (Gene sector)
Phi: 64 (grounded)
Harmonic: 128 (standard)

Address: 0x0040140080
Meaning: Active, identity, physical, normal resolution
```

**Conversation Memory**
```
Shell: 1 (warm)
Theta: 96 (Memory sector)
Phi: 200 (transitional)
Harmonic: 64 (summary)

Address: 0x04C0C840
Meaning: Working memory, experiential, contextual, compressed
```

**Emergent Insight**
```
Shell: 0 (hot)
Theta: 400 (Emergence sector)
Phi: 450 (ethereal)
Harmonic: 192 (extended)

Address: 0x0C81C2C0
Meaning: Active emergence, speculative, full metadata
```

### 7.2 Address as Classification

The key insight: **address = classification**.

Reading an address tells you:
- What storage tier it belongs to (shell)
- What function it serves (theta)
- How grounded/abstract it is (phi)
- What resolution/version (harmonic)

No lookup required. The address **is** the metadata.

---

## 8. Locality and Adjacency

### 8.1 Functional Locality

Unlike linear memory where adjacent addresses are nearby bytes, RPP adjacency is **functional**:

- Adjacent theta → similar function
- Adjacent phi → similar grounding
- Adjacent shell → similar temperature
- Adjacent harmonic → similar resolution

### 8.2 Traversal Patterns

Skip patterns traverse RPP space efficiently:

| Pattern | Movement | Use Case |
|---------|----------|----------|
| Fibonacci | Spiral outward | Discovery |
| Prime | Non-repeating | Avoiding collisions |
| Harmonic | Frequency-based | Resonance detection |
| Golden ratio | Balanced coverage | Sampling |

---

## 9. Semantic Invariants

### 9.1 Immutable Semantics

Once assigned, an address's semantic meaning MUST NOT change:

- Gene sector (0-63) is always identity
- Grounded phi (0-127) is always physical
- Shell meanings are fixed

### 9.2 Extensible Semantics

Within sectors, sub-classifications MAY be defined:

```
Gene (0-63):
  0-15: Biometric hashes
  16-31: Soul token references
  32-47: Device bindings
  48-63: Recovery keys
```

These extensions MUST NOT conflict with canonical definitions.

---

## 10. Non-Claims

RPP semantics do **NOT** imply:

| Non-Claim | Explanation |
|-----------|-------------|
| Truth | Higher phi data is not "more false" |
| Quality | Lower harmonic is not "worse" |
| Importance | Inner shell is not "more important" |
| Permanence | Archive shell is not "forever" |

Semantics describe **classification**, not value judgments.

---

## 11. Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2024-12-27 | Initial semantic model |

---

*This document is released under CC BY 4.0. Attribution required.*
