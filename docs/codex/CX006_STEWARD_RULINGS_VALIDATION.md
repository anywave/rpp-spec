# CX-006 steward rulings — validation and scoped change map

Date: 2026-10-31. Branch: `codex/steward-rulings-2026-10-31`.
Base: `275a115`. Implementation commit: `f75c6bdf6938bb0267299e1aa0c4107107525cc6`.
The following documentation commit adds this record, the PR body and the exact
review-register checkout attribute; no executable behavior is changed.
Authority: RADIX's released CX-006 card, `anywave/trellis-channel` at `9d8dca46`,
`codex/inbox/rpp-spec.md`. No published outbox is edited and no remote write is
performed by this branch's implementation task.

**READY for TR review.** Package tests, golden vectors, lint and whitespace checks
pass. The advisory drift review deliberately exits **1** with **2 HIGH / 12 MEDIUM /
6 LOW** findings on the approved edits. No finding is suppressed or re-baselined.
All seven software-MUST anchors remain verbatim. The two HIGH findings concern
frozen format-guard wording, not a changed layout, bit position or constant.

## Ruling → exact location

| Ruling | Applied location / disposition |
|---|---|
| D1 explicit-alternatives | `spec/RPP-CANONICAL-v2.md:347`; named shell-projection pseudocode at `spec/ADDRESSING-LAYERS.md:134` and `:142`; future API contract and four discriminating examples at `DECISIONS.md:19`. No migration API is implemented. |
| D2 reference-25ns | `spec/SPEC.md:94`, `spec/CCQPSG.md:108`; record at `DECISIONS.md:58`. Runtime tables, elapsed-time checks and protected cross-session wording remain unchanged. |
| D3 experimental | Exact two paragraph replacements at `spec/SPINTRONIC.md:288` and `:311`; record at `DECISIONS.md:76`. No device evidence or conformance is inferred. |
| D4 software-docstring | `rpp/continuity.py:276`; record at `DECISIONS.md:86`. AST equality holds after excluding only this authorized function docstring. |
| D5 experiments | Record at `DECISIONS.md:94`; optional reference quantities stay under tools, with no core API/readout adoption. |
| D6 expectation-fix | Already merged #8; record at `DECISIONS.md:102`. No testbench/RTL edit here. Numeric repair is the separate approved branch. |
| D7 review-proposal + reuse | Separate informative status at `spec/RESOLVER.md:738`, exact inserted profile at `:745`, reuse direction at `:796`; record at `DECISIONS.md:111`. No implementation or current normative-conformance claim. |
| B1–B6 annotate | Exact manifest preamble + 243 ID-ordered lines in `docs/codex/steward/BASELINE_REVIEW.md:1`; records at `DECISIONS.md:128`. Frozen source manifest/catalog remain unchanged. |
| A1 clarify | `VERSION_POLICY.md:70`, `:74`, `:85`; encoding explanation after the complete table at `:77`; `spec/README.md:92`, `spec/PMA-SCHEMA-v1.md:116`, `spec/ADDRESSING-LAYERS.md:114`; record at `DECISIONS.md:170`. |
| A2 separate-proposal | Record at `DECISIONS.md:180`; the existing packet proposal remains separate; behavior unchanged. |
| RTL repair | Record of separate approval at `DECISIONS.md:187`; no RTL change on this branch. |
| Current packet disposition | New prefix in `docs/codex/STEWARD_PACKET.md:1`; prior proposal/evidence body is explicitly historical. |

`GOVERNANCE.md:71` explicitly requires `DECISIONS.md`, so the previously absent
file is created. Each ruling is an `[RFC]` record with RADIX's released answer,
date, provenance and rationale. No issue or completed discussion is invented.
Unrelated historical contradictions and device claims remain in the frozen
baseline; this limited edit does not claim full specification coherence. In
particular, `spec/CCQPSG.md:102–104` / `F-BASE-0048` still says session-scoped
on software. The RFC records that retained legacy mismatch explicitly; the
reference policy at `:108` governs the unchanged implementation. No additional
source rewrite is inferred from D2.

## Commands and observed gates

Python 3.12.14 and Ruff 0.14.10 came from `/workspace/work/cx005/venv/bin`.
Each command ran from this checkout with `PYTHONPATH=.` for Python imports.

| Command | Observed result |
|---|---|
| `PYTHONPATH=. /workspace/work/cx005/venv/bin/python -m pytest tests/ -q` | **1256 passed**, one pre-existing legacy-format warning; existing pytest-asyncio configuration notice also visible. |
| `PYTHONPATH=. /workspace/work/cx005/venv/bin/python tests/test_golden_vectors_mobius32.py` | **SUMMARY pass=5 fail=0**. |
| `/workspace/work/cx005/venv/bin/ruff --version` | **ruff 0.14.10**. |
| `/workspace/work/cx005/venv/bin/ruff check rpp/ tests/ --ignore E501` | **exit 0**. |
| `git diff --check 275a115 HEAD`; `git diff --cached --check` | **exit 0**. |
| `python -m tools.drift check --base 275a115 --head <resolved-hex-head> --output-dir <scratch>` | **exit 1; HIGH 2 / MEDIUM 12 / LOW 6**; open **243 / 4 / 2**. |

There are no new package/tool test cases: this change consists of authorized
prose, a docstring, a fixed review register and its checkout attribute.
The package total remains 1256. Targeted read-only checks below verify the
approved boundaries; they do not claim executed source mutations.

## Targeted evidence and failing changes

| Check | Observed result | Change that would make the check fail (not executed) |
|---|---|---|
| Exact protected sentences from the frozen catalog | **7 retained / 0 lost** | Delete or alter any protected software-MUST sentence. |
| Parse `rpp/continuity.py` before/after, mask only `compute_liminal_timeout` docstring, compare AST dumps | **equal** | Change the timeout table, branch, return value or any other executable statement. |
| Exact JSON-preamble + ID-sorted `exact_annotation_edit.text` comparison | **243 unique / 243 complete**, class counts **37/108/30/11/42/15**, **46442 UTF-8 bytes** | Drop/reorder/modify an annotation or its status/hash. |
| Raw registry SHA-256 | `9d87dc975abec7d9f7f811874cfbc860011cee8f5cf6504f8cbfdade4f3ddc04` | Change any registry byte. |
| Real temporary Git checkout with `core.autocrlf=true` | Registry **byte-identical**; ordinary unprotected control becomes **CRLF** | Remove `docs/codex/steward/BASELINE_REVIEW.md -text` from the root attributes file. |
| Original resolver proposal file | **3479 bytes**, SHA-256 `296bbc18a827dfc939b8dc704af0a6b424dcbba9fd98000e241128446816086e` | Modify the approved source patch. |
| Concatenate all approved patch additions and locate in updated resolver | **3322-byte added payload present contiguously**, including both trailing blank lines | Alter or interleave the approved candidate profile. |
| Frozen manifest/catalog Git-blob comparison | **byte-identical**, inventory **243 baselines / 4 steward items / 2 advisories** | Rehash, suppress, close or accept an entry. |
| Current baseline hash presence | Four specifically authorized source overlaps: **F-BASE-0038, F-BASE-0049, F-BASE-0213, F-BASE-0221**; other **239** hashes still present | Rewrite a baseline outside D2/D3/D4's exact approved passages. |

The register alone performs no source rewrite. The four overlapping source
changes above are independently authorized by D2, D3 and D4; registry annotations
do not grant that authority or imply acceptance. All original per-ID source
hashes/statuses remain in the source manifest and catalog. The root attributes
file explicitly protects the new byte-hashed registry with `-text`.
The exact byte-hashed resolver proposal patch is also marked `-text`; a real
`core.autocrlf=true` checkout preserves both files while converting an ordinary
text control to CRLF.

## Exact unsuppressed drift findings

Implementation run: `275a115..f75c6bdf6938bb0267299e1aa0c4107107525cc6`.
The repeated run at `d7451f31f1d45398f218bfda80e35f1ae77d8848`, including
the decision-record supplement, PR body, validation and checkout attribute,
again returns **exit 1 / 2 HIGH / 12 MEDIUM / 6 LOW**. The table uses this
last run's line hints. A documentation-only recording commit follows; its
final-head drift run is repeated before handoff. No finding is quieted.
Line numbers below are the tool's base/head hints, as returned, rather than
silently rewritten to current line numbers. Full JSON/Markdown reports are
written only to the supplied scratch directory.

| Severity | Rule | Path:line hint | Meaning / approved ruling |
|---|---|---|---|
| HIGH | `VER-FORMAT-1` | `VERSION_POLICY.md:70` | A1 changes frozen encoding/range-note wording; fields, shifts and constants are unchanged. |
| HIGH | `VER-FORMAT-1` | `VERSION_POLICY.md:83` | A1 changes frozen encoding/range-note wording; fields, shifts and constants are unchanged. |
| MEDIUM | `BND-F-2` | `DECISIONS.md:78` | D3 experimental-device wording or its RFC source citation is a report-only changed/new passage. |
| MEDIUM | `BND-F-2` | `spec/SPINTRONIC.md:288` | D3 experimental-device wording or its RFC source citation is a report-only changed/new passage. |
| MEDIUM | `BND-F-2` | `spec/SPINTRONIC.md:311` | D3 experimental-device wording or its RFC source citation is a report-only changed/new passage. |
| MEDIUM | `BND-F-BASELINE-REMOVED` | `rpp/continuity.py:276` | F-BASE-0038: D2/D4 removes physics wording from the cited passage; frozen entry remains unresolved. |
| MEDIUM | `BND-F-BASELINE-REMOVED` | `spec/CCQPSG.md:108` | F-BASE-0049: D2/D4 removes physics wording from the cited passage; frozen entry remains unresolved. |
| MEDIUM | `STEWARD-CLAIM-1` | `rpp/continuity.py:276` | D1/D2/D3/D4 changes a frozen cited steward passage; historical catalog status is intentionally unchanged. |
| MEDIUM | `STEWARD-RADIUS-DERIVATION` | `spec/ADDRESSING-LAYERS.md:142` | D1/D2/D3/D4 changes a frozen cited steward passage; historical catalog status is intentionally unchanged. |
| MEDIUM | `STEWARD-RADIUS-DERIVATION` | `spec/RPP-CANONICAL-v2.md:347` | D1/D2/D3/D4 changes a frozen cited steward passage; historical catalog status is intentionally unchanged. |
| MEDIUM | `STEWARD-T2-1` | `spec/SPINTRONIC.md:288` | D1/D2/D3/D4 changes a frozen cited steward passage; historical catalog status is intentionally unchanged. |
| MEDIUM | `STEWARD-T2-1` | `spec/SPINTRONIC.md:311` | D1/D2/D3/D4 changes a frozen cited steward passage; historical catalog status is intentionally unchanged. |
| MEDIUM | `STEWARD-TTL-1` | `spec/CCQPSG.md:108` | D1/D2/D3/D4 changes a frozen cited steward passage; historical catalog status is intentionally unchanged. |
| MEDIUM | `STEWARD-TTL-1` | `spec/SPEC.md:94` | D1/D2/D3/D4 changes a frozen cited steward passage; historical catalog status is intentionally unchanged. |
| LOW | `WORD-RADIUS-1` | `VERSION_POLICY.md:70` | A1 applies the approved normalized-API / encoded-byte wording; the frozen advisory stays visible. |
| LOW | `WORD-RADIUS-1` | `VERSION_POLICY.md:74` | A1 applies the approved normalized-API / encoded-byte wording; the frozen advisory stays visible. |
| LOW | `WORD-RADIUS-1` | `VERSION_POLICY.md:83` | A1 applies the approved normalized-API / encoded-byte wording; the frozen advisory stays visible. |
| LOW | `WORD-RADIUS-1` | `spec/ADDRESSING-LAYERS.md:114` | A1 applies the approved normalized-API / encoded-byte wording; the frozen advisory stays visible. |
| LOW | `WORD-RADIUS-1` | `spec/PMA-SCHEMA-v1.md:116` | A1 applies the approved normalized-API / encoded-byte wording; the frozen advisory stays visible. |
| LOW | `WORD-RADIUS-1` | `spec/README.md:92` | A1 applies the approved normalized-API / encoded-byte wording; the frozen advisory stays visible. |

Summary: **2 HIGH + 12 MEDIUM + 6 LOW = 20 findings**, **exit 1**.
There is **no `BND-F-1` software-MUST loss**. Both `VER-FORMAT-1` findings are
syntactic guard invalidations of the authorized wording sites; they are not
represented as a passing drift gate or an inferred layout change. The guard,
Boundary F rules, frozen hashes and statuses are not modified. Three `BND-F-2`
findings, two baseline-removal findings and seven changed-steward-passage findings
make up the 12 MEDIUM results; the six radius-wording sites make up the LOWs.

## Independent review and Windows repeat

Read-only peer reviews verified the exact packet patches, all seven anchors,
the contiguous resolver payload, proposed/informative scope and reuse direction,
the six A1 fragments, governance record requirement, future-only migration API
scope and all 243 registry bytes. No additional behavior change was requested.

Native Windows was not executed here. TR should repeat the common gates on
Windows 11 / Python 3.13 and review the same advisory drift findings. With
`core.autocrlf=true`, verify the checked-out review register equals its Git blob;
the Linux temporary-Git regression exercised real conversion with a CRLF ordinary
control. Do not expect a session-lifetime implementation or physical-erasure
proof from this documentation update.
