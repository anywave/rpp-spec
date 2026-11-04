# RPP conformance kit

Run from rpp-spec, with Rust 1.85.1+, Node and Python available:

```sh
python tools/conformance/run.py --latticeworks /path/to/latticeworks
```

The Python file is build scaffolding. It reads the pinned Git objects from your
authorized LatticeWorks checkout, verifies an existing build snapshot or exports
three pure crates to ignored tools/.conformance-sources, then runs the Rust CLI.
It does not change that checkout. First build needs Cargo's locked dependencies.
No LatticeWorks source is published in this kit. No credentials are configured.

The first slice compares the **actual** lw-jobcard and lw-registry canonical
functions, and an independent lossless JavaScript reader/emitter. All source
calls pin LatticeWorks 86899f736f751e32603129fcdaf47e4aa313052f. The ten vectors
from REV-JOBCARD-001 are included, plus two malformed-JSON negatives. They are
generic signing-helper diagnostics, not ten valid cards or authorization proof.
Rust and JavaScript must also match the frozen expected bytes. Shared serde_json
inside the two Rust libraries alone is not independent scalar-format evidence.

JavaScript preserves full i64/u64 integers, UTF-8 key ordering, nested signatures,
arrays and Unicode strings. Its floating diagnostics currently cover 1.0 and
negative zero; unsupported floats refuse rather than claim conformance. NFC
and NFD remain distinct. No new normalization, domain or signing rule is adopted.

`--profile jobcard-json` selects one profile. `--vectors FILE` loads up to 256
bounded JSONL cases. Every case has id, profile, raw JSON string, optional domain
and expected outcome. Native bytes must match both expectation and candidate.
Missing, duplicate or extra candidate rows refuse. Reports contain IDs/results,
not raw payloads. Exit 0 means selected cases conform, 1 means mismatch, 2 means
invalid/unavailable prerequisites or adapter protocol. This is finite corpus
evidence, not universal equivalence or a signature-verification claim.

To test your own implementation, pass --candidate EXE and repeated --candidate-arg
ARG. This executes a program you trust, without a shell. It reads one JSON array
of {id,profile,json,domain,value} from stdin and writes one array of
{id,outcome}. It receives no expected bytes. Byte outcomes are
{"status":"bytes","hex":"lowercase UTF-8 byte hex"}; invalid inputs return
{"status":"reject"}. The built-in Node adapter is the protocol example.
Runtime/output bounds apply; this is not a sandbox for an untrusted executable.

```sh
python tools/conformance/run.py --latticeworks /path/to/latticeworks --test
```

Tests run the real CLI and failing mutations for UTF-16 sort, lossy integers,
outer-signature removal, dropped rows and duplicate IDs. No keys are generated.
This slice changes no protocol, core behavior, workflow, golden vector or gate.
