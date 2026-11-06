# RPP conformance kit

One command compares pinned native sources with independent Node/Python adapters:

```sh
python tools/conformance/run.py --latticeworks /path/to/latticeworks
```

Python is build/reference scaffolding; the runner is Rust. Use Rust 1.85.1+,
Node 18+ and Python 3.10+. Cargo dependencies are locked; first build may download
packages. The bootstrap exports three pure crates from your authorized LW Git
checkout into ignored tools/.conformance-sources and verifies every cached byte.
It changes no LW source. Missing pins refuse; full clones normally contain them.
LW pin: 86899f736f751e32603129fcdaf47e4aa313052f. Serde 1.0.229 / serde_json
1.0.151 match that source lock. Handoff needs RPP e96ef4939650268c216c5343f29e765db54cd047.

| Profile | Proof / source rule |
|---|---|
| jobcard-json, jobcard-attempt | Actual lw-jobcard lib.rs:131 and typed Attempt; generic JSON also calls actual lw-registry:186; independent Node emitter. |
| registry-json, registry-fact | Actual lw-registry lib.rs:186/:264 versus Node; fact domain is inside its signed array. |
| meter-csv | Actual rpp-core overlay.rs:980 versus Node CSV; unsigned transcript. Adapter tick is canonical decimal text for full i128. |
| overlay-csv, overlay-md, overlay-json | Actual Rust scenarios::artifacts versus actual Python scenarios.artifacts; 17 rows / 16 requests. |
| plan-json | Actual lw-pool shard::plan / Plan::canonical_json (:190/:208) versus Node encoding of its unsorted serialized value. Unsigned; no second-planner or admission claim. |
| lend-proof | Source-derived Rust/JS ports of lw-link pair.rs:82 and pairing-vectors.mjs:32; existing public golden included. Full iroh crate/key validation was not run. |
| handoff | Rust shape port versus the actual pinned Python tests/test_handoff_vectors.py:34 method; source SHA checked. Verdict parity only, no byte/value-domain adoption. |
| index | Unavailable: shared-index schema/handshake remains open (trellis-channel/codex/PRODUCT_DESIGN_MAP.md:120). --profile index refuses with exit 2. |

The ten review vectors remain, with typed/malformed/unknown-field negatives.
Integers stay lossless; UTF-8 keys sort recursively; inner sig and array order stay.
NFC/NFD differ. Float diagnostics cover 1.0/-0.0; other floats refuse, not pass.
The kit creates no signatures/private keys and proves no signer authorization.

--vectors FILE accepts bounded JSON arrays or JSONL (1..256 cases, 2 MiB).
Cases contain id, profile, raw json, optional domain and expected outcome.
--candidate EXE plus repeated --candidate-arg ARG compares your trusted program.
Stdin is an array of {id,profile,json,domain,value}; stdout is {id,outcome} rows.
Expected bytes are withheld. Plan value is producer JSON; other values are null.
Outcomes: {"status":"bytes","hex":"lowercase hex"}, {"status":"reject"}, or
{"status":"valid"} for handoff. IDs/row counts and frozen expectations must match.
Normal reports contain IDs/results, not payloads. --emit-native is explicitly a
byte diagnostic, never conformance proof. Exit 0: selected supported cases pass;
1: mismatch; 2: unavailable/invalid. Bounds cover the immediate child, not a sandbox.
The corpus is finite evidence; four source readers and two security lenses helped.

1. Install the tools above and keep both repos' pinned Git objects available.
2. Run the command above; -- --profile NAME selects one implemented profile.
3. Run the same command with --test, then python -m unittest tools.conformance.test_scaffold.
4. Use -- --candidate EXE for your adapter; --python / --node select runtimes.
5. Review the JSON results; PL must define index before any index conformance claim.
