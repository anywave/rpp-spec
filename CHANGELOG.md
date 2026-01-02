# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
