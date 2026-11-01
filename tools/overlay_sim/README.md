# Deterministic overlay policy simulator

This stdlib-only model runs scripted readings and prior verification outcomes. It
opens no socket, signs nothing, has no secret/key material, implements no cipher or
handshake, and calls no model. It demonstrates routing policy, not deployment
security or physical independence. `Auth.signature_verified` and tunnel verification
are fixture verdicts that a production system would obtain from reviewed protocols.

Run from the repository root with the active checkout on `PYTHONPATH`:

```bash
python -m tools.overlay_sim.scenarios --output-dir /tmp/rpp-overlay-scenarios
python -m pytest tools/overlay_sim/tests/ -q -o addopts=
python -m tools.overlay_sim.mutation_check
```

The CLI requires an explicit `--output-dir`; omitting it exits 2 without writing
artifacts. Regenerate the checked-in snapshots only by explicitly selecting
`tools/overlay_sim/results/`. `scenarios.csv` and
`SCENARIOS.md` contain every scripted request/attempt. `billboards.json` records the
active structured statements at ticks 8, 9, 10 and 11. LF/UTF-8 output, explicit
sorting and deterministic fixture order make reruns byte-identical. No seed or
random generator is used. The model does not import `rpp` or change any runtime
behavior; the design document maps these proposed layers to the existing resolver.

The eligible-path property is conditional: if there is at least one authorized,
fresh, available reachable path with a closed breaker and verified data tunnel,
selection returns a path. Real outages, unavailable observations, denied consent,
open breakers or lack of an independent control path produce explicit ledger
statuses; the simulator does not invent connectivity.

The following choices are **IMPOSED demonstration policies**, not adopted protocol
constants or cryptographic specifications:

- A reading is fresh for five integer scenario ticks. Future or unverified readings
  are ineligible. Scripted latency and jitter use milliseconds; loss uses ppm.
  The cost is `1000*(latency+2*jitter)+loss_ppm`, summed over hops; ties use hop
  count then link-ID tuples. Relay routes are also eligible when their measured
  cost beats a direct path; the demo does not impose direct-first preference.
  These weights establish no universal best-link rule.
- A link's two failed attempts open its breaker for two ticks. A successful
  attempt resets its failure count. A failed path is excluded for the current
  request. Retry occurs only with zero emitted tokens; any nonzero token count
  terminates the request. Every attempt, denial, invalid operation and no-path
  outcome receives a numbered row. A terminal no-path row after a failed attempt
  records the outcome; it does not pretend a second transport attempt occurred.
- All nodes/relays are already members. Endpoint consent and directed hop consent
  must already exist; discovery, RESUME and any transport do not add either.
- LAN, Wi-Fi and internet fixture links can carry abstract verified data tunnels.
  Bluetooth/LoRa links carry data only when an explicit hypothetical reviewed
  adapter is enabled. Default scenarios enable no radio data adapter. They do
  show Bluetooth ALIVE and LoRa ROUTE-AROUND as independent status paths.
- Failure domains are fixture labels. A control path excludes every failure
  domain used by a nonempty, known data path: this same simulator must previously
  have selected its exact immutable Link snapshot for these endpoints, at or
  before the control tick. Missing/default, forged or future references are denied.
  Every control hop requires a verified tunnel verdict too; a signature verdict
  alone does not establish an authenticated path. This demonstrates the rule; it does not
  prove that real devices lack shared radios, power, operators or relay failures.
- Control accepts exactly `{source,target,kind,sequence}`; IDs are at most 64
  characters and sequence is a nonnegative 64-bit integer. Only ALIVE,
  MEMBER-CHANGED, STOP, PAUSE, ROUTE-AROUND and RESUME are permitted. Signature
  verdict, issuer, membership, consent and strictly increasing per-pair sequence
  are checked. START and all extra fields (including grant, consent, key, model,
  prompt, answer and payload) are rejected. State is ephemeral; production replay
  epochs, persistent counters and wire encoding still need an adopted design.
- A billboard has exactly `{machine,kind,fact,since,until,receipt}`. `kind` is
  `fact` or `rule`; fact text is at most 256 UTF-8 bytes; receipt is a bounded
  identifier. A separate fixture verification envelope supplies the issuer and
  signature verdict. An explicit `(issuer,machine,kind)` scope, recipient match,
  member/consent checks and unique `(issuer,receipt)` are required. One issuer
  cannot consume another issuer's receipt identifier. Delivery may hold a
  future statement; it is active only during `[since,until)`. Every application
  query reevaluates that interval. No statement is executed or inserted into a
  prompt. Consent/member state cannot be changed by any billboard.
- Scenario time is an external monotonic logical clock, never a message field.
  Inputs, authorization and eligible paths are checked before accepted time
  advances. Denied, malformed, expired and no-path operations leave accepted
  time unchanged, so an invalid far-future call cannot lock out later work. An
  accepted data attempt can advance time even when its transport subsequently
  fails. Operations with clock rollback are metered INVALID_INPUT; applying billboards
  with rollback raises before returning a rule. This prevents expired rules from
  reappearing through a historical application query. Real clock validation and
  trusted time are deferred. Invalid `Link` construction is a programmer error
  before any operation begins; malformed operations have their own meter rows.
  Methods take a sized list/tuple of constructed `Link` fixtures; malformed link
  collections are metered INVALID_INPUT. Non-Auth/non-Billboard arguments and
  malformed issuer fields fail closed. Self-target operations produce the
  explicit DENIED_SELF_TARGET status and do not use a network path.

Tests use a bounded fixed input matrix. Each test docstring names its failing
mutation. The executable mutation checker runs twelve selected in-memory mutants
and a clean control for each; only exit 1, a one-test failure summary and an
explicit pytest `E ... AssertionError` line count as a kill. A bounded regression
rejects runtime errors, collection errors and misleading quoted text. The runner
never changes repository sources:

| Mutant | Assertion that must fail | Clean control |
|---|---|---|
| Ignore unavailable readings | all eight availability masks select only available links | trusted available path |
| Add START to control kinds | START with true fixture verdict is denied | allowed independent status frames |
| Omit billboard `until` check | no rule at/after expiry | rule before expiry |
| Treat nonzero failed tokens as zero | no retry after token one | retry before token one |
| Drop failed meter rows | failed attempt plus retry has two rows | success has one row |
| Append a per-call counter to output | rerun bytes are identical | available channel selection |
| Ignore control failure domains | shared data/control route is rejected | verified independent path |
| Accept unknown/empty data reference | missing reference is denied | known data reference |
| Ignore control tunnel verdict | unverified control tunnel is rejected | verified control tunnel |
| Replay receipts globally | two issuers can independently use the same receipt ID | first authorized delivery |
| Ignore delivery-time expiry | already-expired delivery is rejected before storage | unexpired delivery |
| Advance time before validation | invalid future calls cannot lock out work | accepted data operation |

Other tests cover relay consent, breaker cooldown/recovery, stale/future/unverified
readings, all control payload fields, signature/member/consent/replay rejection,
radio adapter/tunnel eligibility, receipt/scope/shape checks, future billboard
holding, strict boolean readings, bounded sequence, duplicate links, invalid
failure scripts, rejected far-future clock poisoning, malformed verification
objects, self-target denial, required explicit output destinations, CRLF-normalized
committed snapshot comparisons, and input-order-independent tie breaking. These
are policy tests of this simulator, not proof of the unimplemented transport.
