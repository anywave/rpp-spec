# RPP Decision Record

Version: 1.0.0. Updated: 2026-10-31.

## [RFC] CX-006 — RADIX steward rulings, 2026-10-31

**Decision authority:** RADIX, through TR; release: “go”, 2026-10-31.
**Record source:** `anywave/trellis-channel`, `codex/inbox/rpp-spec.md` at
`9d8dca46`, “CX-006 RADIX steward rulings + RTL repair”.
**Implementation base:** `275a115`.

`GOVERNANCE.md:63–71` requires a decision in this file. These records document
the released steward answers and their rationale. The source card is the
authority; this implementation creates no remote RFC issue and makes no claim
that an issue or a two-week discussion occurred. The approved scope is the
selected packet edits and review annotations, not a general specification
rewrite. Earlier outboxes remain historical records.

### [RFC] CX-006-D1 — explicit migration alternatives

**Ruling:** `explicit-alternatives`. **Decision date:** 2026-10-31.
Apply packet D1 option 3 in `spec/RPP-CANONICAL-v2.md` and
`spec/ADDRESSING-LAYERS.md`. Label `neutral-radius` and `shell-projection`;
neither formula is a universal default. Rationale: the two published formulas
discard/preserve different information, so their choice belongs to the caller.

**Named-policy contract:** this requirement applies only to a future conversion
of a legacy v1 address to canonical v2. A migration API MUST require its caller
to name `neutral-radius` or `shell-projection`; omitting the policy or supplying
an unknown policy must be rejected, without silently selecting a formula.

- `neutral-radius`: `radius_v2 = 0.5`; the v1 shell is not carried by radius.
- `shell-projection`: `radius_v2 = shell_v1 / 3.0`, for integer shell 0–3.

Both alternatives use the existing documented theta, phi and harmonic
projection. The radius byte remains `round(radius_v2 * 255) & 0xFF`, with the
existing IMPOSED Python half-to-even tie interpretation. Layouts, field ranges,
encoding constants and vectors do not change. The requirement defines a future
migration interface: the package currently supplies no v1→canonical-v2 migration
API. Existing ordinary-v2 constructors/default radii and unrelated geometry or
extended-address adapters are unaffected.

Discriminating examples, with the other v1 fields held fixed:

| v1 shell | `neutral-radius` API value | Encoded byte | `shell-projection` API value | Encoded byte |
|---:|---:|---:|---:|---:|
| 0 | 0.5 | 128 | 0 / 3 = 0 | 0 |
| 1 | 0.5 | 128 | 1 / 3 | 85 |
| 2 | 0.5 | 128 | 2 / 3 | 170 |
| 3 | 0.5 | 128 | 3 / 3 = 1 | 255 |

The shell-projection examples recover their original shell under the existing
informational `round(radius_v2 * 3)` reverse rule. Neutral-radius does not
preserve shell and provides no shell recovery promise. Neither projection
promises semantic-sector name preservation. No migration API is implemented by
this documentation change.

### [RFC] CX-006-D2 — reference Shell-0 software deadline

**Ruling:** `reference-25ns`. **Decision date:** 2026-10-31.
Apply packet D2 option 1: label the Shell-0 row in `spec/SPEC.md` as the 25 ns
reference software TTL; replace the specified `spec/CCQPSG.md` rule with the
reference rejection boundary `elapsed time >= 25 ns`. The earlier “session
duration”/“session-scoped” wording did not describe that implementation.
Rationale: document the existing stricter policy without increasing retention
or implying physical erasure. No clock precision or scheduler guarantee follows
from this deadline. The protected cross-session MUST sentence is retained.

### [RFC] CX-006-D3 — experimental device support

**Ruling:** `experimental`. **Decision date:** 2026-10-31.
Apply packet D3 option 3 at the two cited `spec/SPINTRONIC.md` paragraphs.
The reference 25 ns admission value alone supplies no device characterization,
conformance or attestation. Separate routing and expiry criteria need a
characterized profile. Rationale: numerical software evidence does not establish
a real-device guarantee. Other historical device passages remain in the frozen
baseline for review; this decision does not validate or rewrite them.

### [RFC] CX-006-D4 — software timeout docstring

**Ruling:** `software-docstring`. **Decision date:** 2026-10-31.
Apply packet D4 option 1 in `rpp/continuity.py`: describe the returned value as
a policy deadline rather than an erasure mechanism. Rationale: the function
returns a table value and has no device-erasure primitive. Only the docstring
changes; executable statements and published values remain identical.

### [RFC] CX-006-D5 — keep quantities as experiments

**Ruling:** `experiments`. **Decision date:** 2026-10-31.
Keep the optional, profile-tagged reference quantities under `tools/prove_out/`.
No package API or generic coherence/sector readout is adopted. Rationale: finite
engineering evidence does not establish a universal meaning or calibration.
The overall coherence and sector verdicts remain partly proved.

### [RFC] CX-006-D6 — original testbench expectations

**Ruling:** `expectation-fix`. **Decision date:** 2026-10-31.
The expected-value correction is already merged in PR #8. Record that
disposition without editing its implementation here. Rationale: expected values
must describe the unchanged fixture inputs. The numeric scaling/overflow repair
is a distinct approved work item, not evidence that the original 33/33 smoke
checks proved scorer agreement.

### [RFC] CX-006-D7 — informative overlay proposal and reuse direction

**Ruling:** `review-proposal + reuse`. **Decision date:** 2026-10-31.
Apply the exact 3479-byte `docs/design/RESOLVER_OVERLAY_PROPOSAL.diff`, SHA-256
`296bbc18a827dfc939b8dc704af0a6b424dcbba9fd98000e241128446816086e`, to
`spec/RESOLVER.md`. A separate adjacent status notice marks section 11.3
**proposed/informative**: its uppercase requirements describe a candidate
profile, not a currently adopted normative implementation contract.

Reuse direction: existing Tailscale clients, self-hosted Headscale and authorized
DERP for IP LAN/Wi-Fi/internet paths; existing platform GATT API for bounded
signed control under the same consent/trust checks; assess Reticulum later for
LoRa/non-IP adapters after license/backend/profile review. Rationale: preserve
the approved policy proposal while reusing reviewed protocols. Deployment and
profile parameters remain separately reviewed. No tunnel, cipher, handshake,
key exchange or new cryptography is implemented.

### [RFC] CX-006-B1 — software-policy review annotations

**Ruling:** `annotate`. **Decision date:** 2026-10-31. **Entries:** 37.
Apply every B1 per-ID line from `docs/codex/steward/baseline-decisions.json` to
`docs/codex/steward/BASELINE_REVIEW.md` exactly. Rationale: preserve software
obligations while tracking profile ambiguity. No baseline passage is accepted
or changed by annotation.

### [RFC] CX-006-B2 — optional-device review annotations

**Ruling:** `annotate`. **Decision date:** 2026-10-31. **Entries:** 108.
Apply every B2 per-ID registry line exactly. Rationale: device claims remain
unvalidated pending characterization; class membership supplies no conformance.

### [RFC] CX-006-B3 — model-scope review annotations

**Ruling:** `annotate`. **Decision date:** 2026-10-31. **Entries:** 30.
Apply every B3 per-ID registry line exactly. Rationale: reproducible calculations
do not validate a materials interpretation.

### [RFC] CX-006-B4 — provenance/navigation review annotations

**Ruling:** `annotate`. **Decision date:** 2026-10-31. **Entries:** 11.
Apply every B4 per-ID registry line exactly. Rationale: retain historical/link
provenance without endorsing the referenced claims.

### [RFC] CX-006-B5 — explanatory-prose review annotations

**Ruling:** `annotate`. **Decision date:** 2026-10-31. **Entries:** 42.
Apply every B5 per-ID registry line exactly. Rationale: distinguish supported
software/transport behavior from interpretations requiring further evidence.

### [RFC] CX-006-B6 — package-documentation review annotations

**Ruling:** `annotate`. **Decision date:** 2026-10-31. **Entries:** 15.
Apply every B6 per-ID registry line exactly. Rationale: source comments cannot
establish device enforcement. B1–B6 total 243 unique ID-ordered lines after the
exact manifest preamble. Their `review-pending` annotation is not acceptance or
closure. The source manifest and frozen drift catalog remain unchanged at
243 baselines / 4 steward items / 2 advisories. D1–D4 are separately authorized
edits; the annotation decision grants no additional passage rewrite.

### [RFC] CX-006-A1 — normalized API value versus encoded byte

**Ruling:** `clarify`. **Decision date:** 2026-10-31.
Apply the six prescribed wording-site clarifications: three in
`VERSION_POLICY.md`, one each in `spec/README.md`, `spec/PMA-SCHEMA-v1.md` and
`spec/ADDRESSING-LAYERS.md`. Use `r_enc` for the shifted byte and put its
`round(radius * 255) & 0xFF` explanation after the complete formula table.
Rationale: distinguish the API's 0–1 value from its stored 0–255 byte without
changing bits, range, rounding policy or constants.

### [RFC] CX-006-A2 — separate radius behavior proposal

**Ruling:** `separate-proposal`. **Decision date:** 2026-10-31.
Leave bool/negative-zero/URI behavior unchanged; retain its separate core
proposal in the steward packet. Rationale: a wording clarification does not
authorize a compatibility change.

### [RFC] CX-006-RTL — separate approved arithmetic repair

**Ruling:** `approve repair`. **Decision date:** 2026-10-31.
The dedicated `codex/rtl-scaling-repair` branch addresses scaling and overflow
against the selected Python reference. It is outside this documentation branch.
Rationale: the previously executed shift-only diagnostic was incomplete.
No RTL, header, layout, golden vector or published constant is edited here.
