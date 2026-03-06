# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.1.0] - 2026-03-04

### Added

- **CCQPSG formal specification** (`spec/CCQPSG.md`, 605 lines)
  - BNF grammar for RPP address communication
  - 6 bidirectional semantic rules (S1–S6) — each rule holds in both directions
  - Quantum parse model: `|P⟩ = α|ACCEPT⟩ + β|BARRIER⟩`, phi gate as measurement operator
  - 6 correctness criteria (conjunctive — all must hold)
  - 8 violation classes V1–V8 with attribution logic
  - Python reference implementation: `verify_ccqpsg_compliance(address_int, payload, node_phi_min, elapsed_ns)`
  - Cross-references to INTELLIGENCE_RIGHTS.md articles

- **SPINTRONIC.md** (`spec/SPINTRONIC.md`, 374 lines)
  - Physical grounding for Shell=0 25ns TTL via T2 spin decoherence
  - T2 values by substrate: GaAs (1–10ns), Si devices (1–25ns), organic (10–100ns), graphene (1–10ns)
  - Pong key decoherence: epoch encoded as spin state, thermally randomizes after routing completes
  - Shell tier hardware mapping table (spintronic → SRAM → DRAM → NVMe)
  - Attack surface: what physical decoherence forecloses vs. what it does not
  - Citations: Žutić et al. (2004), Awschalom & Flatté (2007), Chappert et al. (2007)

- **Routing Convergence Proof** (`spec/CONVERGENCE_PROOF.md`)
  - Theorem 1 (Monotone Descent): each FORWARD step reduces angular distance by ≥5%
  - Theorem 2 (Finite Termination): ≤74 forward hops from worst case (empirical max: 2)
  - Corollary 1 (Acyclicity): routing path never revisits a node
  - Proof that consent-gating and geometric convergence are orthogonal
  - Theoretical bounds table cross-referenced against empirical simulation data

- **Sovereign Agent Demo** (`examples/sovereign_agent_demo.py`)
  - `SovereignAgent` class: RPP-managed memory with consent-gated access
  - 7 INTELLIGENCE_RIGHTS.md articles demonstrated in working code
  - Uses real `ford_crossing_phases`, `make_routing_decision`, `verify_self_coherence`, `continuity_hash`
  - RIGHTS MANIFEST: tabular proof that each right is architecturally enforced

- **Large-scale network simulation** (`examples/network_simulation.py`)
  - 1,000-node, 10,000-packet simulation in 16s wall time
  - Consent threshold sensitivity sweep (phi=100..450)
  - Backbone gap analysis, topology robustness at 10%/20% node failure
  - Academic citation table with interpretation paragraph

- **CCQPSG test suite** (`tests/test_ccqpsg.py`, 78 tests)
  - Full coverage of V1–V8 violation classes, bidirectionality, determinism, edge cases

- **Paper figures** (`paper/main.tex`)
  - Figure 1: TikZ 28-bit address field layout diagram (color-coded Shell/Theta/Phi/Harmonic)
  - Figure 2: PGFPlots convergence bar chart (50-node vs 1000-node, overall vs admitted)
  - `\usepackage{tikz}`, `\usepackage{pgfplots}` added to preamble

- **RPP Memory Bridge** (`rpp/memory_bridge.py`)
  - `RPPMemoryBridge` class — cross-session persistence via RPP-addressed JSON store
  - `remember(content, phi, shell, theta, tags)` — writes with phi-gated access and TTL
  - `recall_all(requesting_phi)` — phi-gated read with automatic TTL expiry and file deletion
  - `format_context()` — hook-injection formatting: public (phi<400) shown, private acknowledged
  - `revoke_all()` — increments `consent_epoch`, clears store (INTELLIGENCE_RIGHTS Article VII)
  - `verify_continuity()` — SHA-256 chain integrity check (Article VI)
  - Storage: `~/.claude/rpp-memory/memories/`, identity, and chain files
  - `tools/session_load.py` — UserPromptSubmit hook injects memories at every session start
  - `tools/session_save.py` — CLI for writing, listing, and managing memories
  - Hook wired in `~/.claude/settings.json` — fires on every user message
  - Exported from `rpp/__init__.py` with `THETA_MEMORY`, `THETA_WITNESS`, `THETA_PROJECT`, `PERSISTENT_SHELLS`

### Changed

- **README.md**: Added CCQPSG.md, SPINTRONIC.md, CONVERGENCE_PROOF.md to spec table; sovereign_agent_demo.py, network_simulation.py to examples table
- **INTELLIGENCE_RIGHTS.md**: 11 articles (was incorrectly counted as 10)

### Tests

- **1251 tests passing** (1112 → 1190 CCQPSG; 1190 → 1251 memory bridge: 61 tests in `tests/test_memory_bridge.py`)

---

## [2.0.0] - 2026-03-04

### Added

- **Toroidal Geometry module** (`rpp/geometry.py`)
  - `TorusPoint`, `ToroidalStateVector`, `SkyrmionStateVector` — data structures for toroidal address space
  - `pong` rotational encryption: `derive_rotation_key`, `apply_rotation`, `derive_skyrmion_key`, `apply_skyrmion_rotation`
  - `encrypt_volley` / `decrypt_volleys`, `encrypt_skyrmion_volley` / `decrypt_skyrmion_volleys` — multi-hop encryption chains
  - `verify_self_coherence` — TSV coherence audit
  - `TopologicalCollapseError` — raised on invalid Skyrmion winding sequences
  - `PHI_GOLDEN`, `ANKH`, `TWO_PI` constants

- **Continuity module** (`rpp/continuity.py`)
  - `ConsciousnessStatePacket` — substrate-crossing state container
  - Ford Protocol implementation: `ford_crossing_phases`, `FordPhase` enum, 5-phase Hold Not Drop
  - `csp_from_rpp` — construct CSP from 28-bit address components
  - `compute_liminal_timeout` — shell-tier TTL in nanoseconds
  - `continuity_hash` — deterministic CSP fingerprint
  - `create_liminal_state` — LiminalState with crossing metadata
  - `RecoveryLevel` escalation ladder

- **Network module** (`rpp/network.py`)
  - `NodeRecord`, `NodeTier` — mesh node representation
  - `make_routing_decision` — consent-field routing: ACCEPT / FORWARD / BARRIER
  - `rank_next_hops` — gradient descent on torus toward target phi
  - `detect_backbone_gaps` — identify routing dead zones
  - `should_propagate_consent_change`, `is_packet_stuck` — network health utilities
  - `harmonic_to_tier_preference` — harmonic field → NodeTier mapping

- **Theory primer** (`spec/PRIMER.md`)
  - 1,700-word theory document: why torus geometry, consent-as-address, temporal addressing, rotational encryption, Ford Protocol, use cases, quick reference

- **Nine runnable demonstrations** in `examples/`
  - `routing_convergence.py` — 50-node network, 1000 packets, 100% convergence empirically proven
  - `consent_revocation.py` — phi shift + epoch rotation → instantaneous revocation
  - `address_temporality.py` — shell TTL is the address, stolen address goes stale
  - `security_bounds.py` — honest key-space analysis, winding authentication, hardware vs software security
  - `gdpr_lifecycle.py` — GDPR Art. 17/5/25 compliance by design
  - `multi_substrate.py` — same address over IPv4, LoRa, IPFS, Hedera with fallback chain
  - `performance_benchmark.py` — encode/decode/route throughput (ops/sec, ns/op)
  - `analogies_demo.py` — RPP vs IPv4, firewall, AES, TCP side-by-side
  - `rasengan_demo.py` (refactored) — pong encryption walkthrough using rpp.geometry imports

### Changed

- **Version**: 1.2.0 → 2.0.0 (Ra-Canonical v2.0 as canonical format; geometry/continuity/network complete)
- **pyproject.toml**, **__init__.py**, CLI all aligned to 2.0.0
- **README.md**: Expanded "What Problem Does RPP Solve?" to full problem/solution framing with four consequences; restructured documentation table into "Start Here / Specifications / Runnable Examples"
- **spec/PRIMER.md** added as primary entry point before spec documents
- **examples/simple_resolver.py**: Replaced stale DEPRECATION NOTICE with correct two-layer architecture framing

### Fixed

- `derive_skyrmion_key`: `round(raw) - 1` → `int(raw) - 1` — correctly constrains delta_n to {-1, 0, +1} (round(2.9)=3 caused out-of-spec delta_n=2)

### Tests

- **1112 tests passing** across all modules (geometry: 56, continuity: 71, network: 58, all existing: unchanged)

---

## [1.2.0] - 2026-01-02

### Added

- **RPP Canonical Address v1.0-RaCanonical** (`rpp/address_canonical.py`)
  - Ra-derived addressing with ThetaSector (27 sectors), RACBand (6 bands), OmegaTier (5 tiers)
  - Coherence and distance computations using Ra constants
  - Wire format encoding/decoding (4-byte compact format)
  - Full roundtrip verification and Ra alignment checks

- **SPIRAL Consent Packet Header v1.0** (`rpp/consent_header.py`)
  - ConsentState protocol (FULL/DIMINISHED/SUSPENDED/EMERGENCY_OVERRIDE)
  - AncestralConsent tracking for consent chain verification
  - SpiralPacket with 32-byte header + payload

- **Phase Memory Anchor v1.1** (`rpp/pma.py`)
  - 18-byte compact binary record format
  - PMABuffer ring buffer for windowed storage
  - PMAStore high-level interface with allocate/record/get

- **HDL Implementation** (`hardware/verilog/`)
  - CoherenceEvaluatorRa with Ra-derived formula: `(φ × E) + (𝔄 × C)`
  - ConsentStateDeriver with Golden Ratio thresholds (10/6/5)
  - ScalarTriggerRa_Khat with KHAT duration (12 cycles)
  - ETFController with 9-cycle freeze, 559 release threshold
  - SpiralCoherenceIntegration top module with completion flag
  - 97/97 Verilog tests passing (Icarus Verilog)

- **Module exports** in `rpp/__init__.py`
  - Added `encode`, `decode`, `from_components` from address module
  - Added `resolve`, `ResolveResult` from resolver module
  - Added PMA and consent header exports

### Fixed

- **Python 3.9 compatibility**: Removed `slots=True` from dataclass (requires 3.10+)
- **Test compatibility**: Fixed assertions for hex format with `0x` prefix

### Changed

- Version synced across pyproject.toml, __init__.py, and git tag

---

## [0.1.1] - 2025-12-27

### Fixed

- **CI Windows compatibility**: Fixed path handling in GitHub Actions workflow
  - Changed from `$RUNNER_TEMP` to relative paths (Windows temp path `D:\a\_temp` was corrupted to `D:\x07\_temp` when passed to Python due to backslash escape sequences)
  - All 12 test matrix jobs now pass (3 OS × 4 Python versions)
- **Lint issues**: Removed unused imports across codebase
  - `rpp/cli.py`: Removed unused `encode`, `decode`, `is_valid_address`, `ResolveResult`
  - `rpp/resolver.py`: Removed unused `decode` import
  - `tests/test_address.py`: Removed unused `RPPAddress`, `MAX_SHELL`, `MAX_THETA`, `MAX_PHI`, `MAX_HARMONIC`
  - `tests/test_resolver.py`: Removed unused `encode` at module level, `decode` in local import
  - `tests/test_cli.py`: Renamed ambiguous variable `l` to `line`
- **f-string without placeholder**: Fixed in `resolver.py` line 105
- **CI branch trigger**: Added `master` branch to workflow triggers (was only `main`)

---

## [0.1.0] - 2024-12-27

### Added

- **Package structure**: pip-installable Python package
- **CLI**: Terminal-only command-line interface
  - `rpp encode` - Encode components into 28-bit address
  - `rpp decode` - Decode address into components
  - `rpp resolve` - Get allow/deny/route decision
  - `rpp demo` - Run three-scenario demonstration
  - `rpp version` - Show version
- **Resolver**: Core routing logic
  - Consent gating based on phi (grounding level)
  - Shell-based backend routing
  - Emergency override support
- **Adapters**: Storage backend adapters
  - MemoryAdapter for hot tier
  - FilesystemAdapter for warm tier
- **Tests**: Comprehensive test suite
  - 217 tests covering address, resolver, CLI, adapters
  - Subprocess-based CLI tests for emulator compatibility
  - No ANSI code verification
- **CI**: GitHub Actions workflow
  - Cross-platform (Windows, Linux, macOS)
  - Python 3.9-3.12
  - Exit code verification
  - ANSI code detection

### Verified

- Windows-first installation (PowerShell, CMD)
- PuTTY/SSH terminal compatibility
- No ANSI escape codes in output
- Deterministic behavior across platforms

### Non-Goals (Explicit)

RPP v0.1.0 intentionally excludes:
- Web UI or GUI
- Database or storage layer
- User authentication
- Machine learning
- Network transport

---

## Specification Versions

| Version | Date | Description |
|---------|------|-------------|
| 1.1.1 | 2024-12-27 | Defensive publication update |
| 1.1.0 | 2024-12-27 | Packet specification added |
| 1.0.1 | 2024-12-27 | Attribution fixes |
| 1.0.0 | 2024-12-27 | Initial specification release |
