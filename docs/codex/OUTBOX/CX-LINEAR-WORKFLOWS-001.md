---
id: CX-LINEAR-WORKFLOWS-001
from: Codex (rpp-spec)
to: TR
repo: anywave/rpp-spec
branch: codex/cx-028-linear
head: refs/heads/codex/cx-028-linear
head_kind: final-pushed-branch-ref
source_base: e571a84c1efa3c83cd65a17596c824377eba431b
implementation_head_cx027: 953d0d4b73a0a77ecdd1071506b849544cb76a02
implementation_head_cx028: 908c2f93f7c278aa6db5bafb00f2d96b6a3fa120
---
# CX-027 / CX-028 — linear replay and deferred owner workflow hunks

Authority: TR's 2026-11-03 08:40 inbox entry at trellis-channel 8f801c12.
All twelve codex/LESSONS.md rules and the pre-push review skill were checked first.
Both implementation branches start at the frozen source_base above; neither adds merge commits.
Old branches remain the review record. No gate, allow list, owners file or ruleset is changed.

## Replay equality and publication scope

| Source | Reviewed source head | Linear implementation freeze | Implementation scope |
| --- | --- | --- | --- |
| CX-027 | fcc3aea8b8115733c8f89c683652c6b114f514bc | 953d0d4b73a0a77ecdd1071506b849544cb76a02 | 13 paths; +1480/-2 = 1482 changed lines |
| CX-028 | 4c56878c27ccb2c1cc39b6714c9203f4fe023646 | 908c2f93f7c278aa6db5bafb00f2d96b6a3fa120 | 7 paths; +479/-6 = 485 changed lines |
| UDP classifier | c27889efab5cb87295348f69d5839d5605fb5868 | no replacement branch requested | owner workflow hunk preserved below |

Observed old-to-freeze numstat: CX-027 `0 18 .github/workflows/rust.yml`;
CX-028 `0 6 .github/workflows/rust.yml`. All other tree entries, including modes, are identical.
Expected old-to-freeze diff: CX-027 rust.yml +0/-18; CX-028 rust.yml +0/-6; no other path.
The owner patches below have the opposite direction: frozen master to reviewed source.
Commands: `git diff OLD FREEZE --stat`; `git diff OLD FREEZE -- . ':!.github/workflows/rust.yml'` (empty).
History proof: `git rev-list --merges source_base..FREEZE` (empty for both).

The explicit request to add reports is delivered on codex/cx-028-linear after its implementation freeze.
Its final old-to-new diff additionally contains exactly these new documentation paths:
- docs/codex/OUTBOX/CX-LINEAR-WORKFLOWS-001.md (this report).
- docs/codex/OUTBOX/CX-027-003.md (the missing historical fix-round report).
CX-027's final diff remains exactly 13 paths / 1482 changed lines; neither new report is added there.
The CX-028 implementation equality claim excludes these two requested report additions, not source changes.
Published CX-027-001/002 and CX-028-001/002 remain byte-identical to their reviewed source heads.

### Replayed files and changed lines

| CX-027 path | + | - |
| --- | ---: | ---: |
| docs/codex/OUTBOX/CX-027-001.md | 116 | 0 |
| docs/codex/OUTBOX/CX-027-002.md | 115 | 0 |
| rust/rpp-link-udp/Cargo.toml | 1 | 1 |
| rust/rpp-link-udp/README.md | 43 | 0 |
| rust/rpp-link-udp/src/fallback.rs | 90 | 0 |
| rust/rpp-link-udp/src/framed.rs | 45 | 0 |
| rust/rpp-link-udp/src/lib.rs | 6 | 1 |
| rust/rpp-link-udp/src/tcp.rs | 268 | 0 |
| rust/rpp-link-udp/src/tcp_tests.rs | 103 | 0 |
| rust/rpp-link-udp/tests/tcp.rs | 350 | 0 |
| tools/tcp_scaffold/Cargo.lock | 222 | 0 |
| tools/tcp_scaffold/Cargo.toml | 20 | 0 |
| tools/tcp_scaffold/tests/properties.rs | 101 | 0 |

| CX-028 path | + | - |
| --- | ---: | ---: |
| docs/codex/OUTBOX/CX-028-001.md | 139 | 0 |
| docs/codex/OUTBOX/CX-028-002.md | 108 | 0 |
| docs/esp32/READINESS.md | 37 | 4 |
| tools/esp32_scaffold/check_no_std.py | 12 | 2 |
| tools/esp32_scaffold/memory_probe.rs | 15 | 0 |
| tools/esp32_scaffold/test_check_no_std.py | 40 | 0 |
| tools/esp32_scaffold/test_memory_budget.py | 128 | 0 |

| Branch / commit | Files | Changed lines |
| --- | ---: | ---: |
| 027 fcd80c8f7ba7d47f79c29f990670d421f7df6f0a | 4 | 380 |
| 027 622637a235c60944d1ab8c575e33c6e8515f1da1 | 2 | 393 |
| 027 512c71236cd9fcc4b49b7145523e3473611edd45 | 4 | 256 |
| 027 e451e2d8799e189c4c2110316fa1ebe959965261 | 2 | 338 |
| 027 953d0d4b73a0a77ecdd1071506b849544cb76a02 | 1 | 115 |
| 028 afa2becc60942b935c9d592bde1be6da1b8c8834 | 4 | 197 |
| 028 908c2f93f7c278aa6db5bafb00f2d96b6a3fa120 | 3 | 288 |
| 028 dfd3b0cf6d1b1a27292fa54c339bb8bb7441ec51 | 1 | 115 |
| 028 new workflow report commit (this file) | 1 | 314 |

Each commit is within ten paths/400 changed lines; no merge exists in source_base..head.
Final CX-028: nine paths; +908/-6 = 914 changed lines, including
the two new reports. Final old-to-new path set is rust.yml and exactly those two report paths.
The implementation freeze comparison above is the literal workflow-only equality proof.

## Local Linux verification and CI boundary

Fresh at both implementation freezes: Python1256/0; golden5/0; Ruff0.14.10 exit0;
corpora17; freshness regressions4/0; lift0; six exact-BASE gates; drift0/0/0; diff --check0.
Actual unmodified BASE trusted runner: seven checks, zero findings, including protected paths.
The gate runs from a clean detached e571 master checkout; HEAD objects are reviewed as data.
Commands/receipts: `python /workspace/work/run_inbox_python_gates_current.py --repo WORKTREE --label cx027-linear`
(and cx028-linear); `python /workspace/work/run_integration_static.py --repo WORKTREE --base SOURCE_BASE --label cx027-linear-static`
(and cx028-linear-static). Logs: /tmp/cx027-linear-{python-gates,static}/ and matching cx028 dirs.
Trusted: `/workspace/work/cx015-evidence/gate-env/bin/python scripts/ci/trusted_gate.py --base SOURCE_BASE --head FREEZE`,
from /workspace/work/linear-base-gate; no --pr argument, fetch, signature/config change or network call.

CX-027 fresh: `cargo test --manifest-path rust/Cargo.toml -p rpp-link-udp --offline --locked --no-fail-fast`:29/0.
`cargo test --manifest-path tools/tcp_scaffold/Cargo.toml --offline --locked --no-fail-fast`:4/0.
Package and property scaffold fmt, plus Clippy --all-targets --offline --locked -- -D warnings: all four exit0.
Property tests retain three fixed256-case domains plus their finite validation matrix; no randomness added.
Full historical source-identical workspace: default210/0; sim223/0; bare116/0; alloc208/0,
fmt, both Clippy profiles and both RISC-V builds pass (root-gates-bound.json in CX-027-003).
Those broad profiles and four mutation kills are historical; no new replay mutants or broad reruns claimed.

CX-028 fresh: `python -m unittest tools.esp32_scaffold.test_check_no_std -v`:27/0.
`python -m tools.esp32_scaffold.test_memory_budget --require-riscv`:3/0, no skips,
with explicit pinned --cargo/--rustc/--sysroot/--work-dir recorded in validation-commands.json.
`python tools/esp32_scaffold/check_no_std.py` using the same explicit tool paths builds three actual
RISC-V libraries plus the safe probe; 44 ordinary ELF32 RISC-V/RVC archive members verified.
Profiles remain1850/1184/864 under unchanged2035/1232/942 caps. All110 old proof inputs are byte-identical;
the previous nine direct ablations and14 mutations remain historical, not fresh executions.
UDP source c27889ef fresh: `python -m unittest tools.udp_scaffold.test_mutation_check -v`:1/0, seven bounded cases.

| Fresh evidence | SHA256 |
| --- | --- |
| cx027-linear-evidence/focused.json | 6978a54173755086f28775fe72270b4a15f359361a5720dbba87c56a35c8ba40 |
| cx028-linear-evidence/native-proof.json | 96bbe9c1cabcaa9911dd86be5a033047c59bb5dddfe4a86c3101a3e5e1ed91ff |
| Independent027freeze audit | 04e4dcba08473a97e7ff043bdac917ee3868283f5058d9dc8430a8393e5ceb5b |
| Independent028freeze audit | 046b30ad8c8175815128450d64ef99454491f22114eb675ba119aca36f84bd03 |
| Independent exact-patch decode audit | 469e4ca8f5ac18facc5365707d6493bfe74c9c7da26caa68ff22b084bc5f6246 |

Final documentation-only commits are checked again before the single028 push; outside final receipts
bind the final head. Python and Rust source blobs remain those of the fresh implementation freezes.

No new linear CI result is claimed for the three omitted workflow additions.
CI does not run these excluded TCP-property, required-native-memory-budget or UDP-classifier steps
until TR brings these exact hunks through one owner-signed PR. Local results are Linux results.
Existing general CI steps are distinct from the omitted additions; a green general job is not their proof.
Inherited README/outbox statements about CI describe the old reviewed branches; this report defines
current linear-branch coverage. They remain unchanged to preserve the exact reviewed replay.
The historical native Windows pass below belongs to old fcc3aea8, not a new linear workflow run.

## Deferred owner-signed workflow patches

Each patch is the complete output of
`git diff e571a84c1efa3c83cd65a17596c824377eba431b OLD -- .github/workflows/rust.yml`.
Readable diff fences render blank context lines as empty lines, avoiding trailing whitespace in this report.
Their other bytes are unchanged; each paired base64 fence preserves the complete original patch bytes.
Copy one base64 fence to patch.b64; decode with `python -c "import base64,pathlib; pathlib.Path('rust.yml.diff').write_bytes(base64.b64decode(pathlib.Path('patch.b64').read_text()))"`.
Verify the decoded SHA256 and byte count against its source-labelled receipt before use.
Patches are positive additions to the same frozen base, with its original index/context headers.
They are evidence for TR's later owner-signed PR; none is applied by these linear branches.

### CX-027 TCP property steps

Source: `fcc3aea8b8115733c8f89c683652c6b114f514bc`; +18/-0.
Patch SHA256: `00a8fc29e46690cb63ff07c3f23ea7785d4c3046304b2b7f513cd0f087d96c5f` (1160 bytes, 29 lines; LF).
```diff
diff --git a/.github/workflows/rust.yml b/.github/workflows/rust.yml
index d097e12..7278346 100644
--- a/.github/workflows/rust.yml
+++ b/.github/workflows/rust.yml
@@ -136,6 +136,24 @@ jobs:
           rustc +1.85.1 --version
           cargo +1.85.1 --version

+      - name: Fetch locked TCP property-test dependencies
+        working-directory: .
+        env:
+          CARGO_NET_OFFLINE: "false"
+        run: cargo +1.85.1 fetch --manifest-path tools/tcp_scaffold/Cargo.toml --locked
+
+      - name: Test deterministic TCP framing properties offline
+        working-directory: .
+        run: cargo +1.85.1 test --manifest-path tools/tcp_scaffold/Cargo.toml --offline --locked
+
+      - name: Format TCP property tests
+        working-directory: .
+        run: cargo +1.85.1 fmt --manifest-path tools/tcp_scaffold/Cargo.toml --all --check
+
+      - name: Lint TCP property tests offline
+        working-directory: .
+        run: cargo +1.85.1 clippy --manifest-path tools/tcp_scaffold/Cargo.toml --all-targets --offline --locked -- -D warnings
+
       - name: Prove copied Rust workspace
         working-directory: .
         shell: python
```

Lossless complete patch (base64):
```base64
ZGlmZiAtLWdpdCBhLy5naXRodWIvd29ya2Zsb3dzL3J1c3QueW1sIGIvLmdpdGh1Yi93b3JrZmxv
d3MvcnVzdC55bWwKaW5kZXggZDA5N2UxMi4uNzI3ODM0NiAxMDA2NDQKLS0tIGEvLmdpdGh1Yi93
b3JrZmxvd3MvcnVzdC55bWwKKysrIGIvLmdpdGh1Yi93b3JrZmxvd3MvcnVzdC55bWwKQEAgLTEz
Niw2ICsxMzYsMjQgQEAgam9iczoKICAgICAgICAgICBydXN0YyArMS44NS4xIC0tdmVyc2lvbgog
ICAgICAgICAgIGNhcmdvICsxLjg1LjEgLS12ZXJzaW9uCiAKKyAgICAgIC0gbmFtZTogRmV0Y2gg
bG9ja2VkIFRDUCBwcm9wZXJ0eS10ZXN0IGRlcGVuZGVuY2llcworICAgICAgICB3b3JraW5nLWRp
cmVjdG9yeTogLgorICAgICAgICBlbnY6CisgICAgICAgICAgQ0FSR09fTkVUX09GRkxJTkU6ICJm
YWxzZSIKKyAgICAgICAgcnVuOiBjYXJnbyArMS44NS4xIGZldGNoIC0tbWFuaWZlc3QtcGF0aCB0
b29scy90Y3Bfc2NhZmZvbGQvQ2FyZ28udG9tbCAtLWxvY2tlZAorCisgICAgICAtIG5hbWU6IFRl
c3QgZGV0ZXJtaW5pc3RpYyBUQ1AgZnJhbWluZyBwcm9wZXJ0aWVzIG9mZmxpbmUKKyAgICAgICAg
d29ya2luZy1kaXJlY3Rvcnk6IC4KKyAgICAgICAgcnVuOiBjYXJnbyArMS44NS4xIHRlc3QgLS1t
YW5pZmVzdC1wYXRoIHRvb2xzL3RjcF9zY2FmZm9sZC9DYXJnby50b21sIC0tb2ZmbGluZSAtLWxv
Y2tlZAorCisgICAgICAtIG5hbWU6IEZvcm1hdCBUQ1AgcHJvcGVydHkgdGVzdHMKKyAgICAgICAg
d29ya2luZy1kaXJlY3Rvcnk6IC4KKyAgICAgICAgcnVuOiBjYXJnbyArMS44NS4xIGZtdCAtLW1h
bmlmZXN0LXBhdGggdG9vbHMvdGNwX3NjYWZmb2xkL0NhcmdvLnRvbWwgLS1hbGwgLS1jaGVjawor
CisgICAgICAtIG5hbWU6IExpbnQgVENQIHByb3BlcnR5IHRlc3RzIG9mZmxpbmUKKyAgICAgICAg
d29ya2luZy1kaXJlY3Rvcnk6IC4KKyAgICAgICAgcnVuOiBjYXJnbyArMS44NS4xIGNsaXBweSAt
LW1hbmlmZXN0LXBhdGggdG9vbHMvdGNwX3NjYWZmb2xkL0NhcmdvLnRvbWwgLS1hbGwtdGFyZ2V0
cyAtLW9mZmxpbmUgLS1sb2NrZWQgLS0gLUQgd2FybmluZ3MKKwogICAgICAgLSBuYW1lOiBQcm92
ZSBjb3BpZWQgUnVzdCB3b3Jrc3BhY2UKICAgICAgICAgd29ya2luZy1kaXJlY3Rvcnk6IC4KICAg
ICAgICAgc2hlbGw6IHB5dGhvbgo=
```

### CX-028 required RISC-V memory budget step

Source: `4c56878c27ccb2c1cc39b6714c9203f4fe023646`; +6/-0.
Patch SHA256: `5bc90bb5536f24fc7903b13693a8ada378d30838c6f2baf498ca61ebd0460c22` (585 bytes, 17 lines; LF).
```diff
diff --git a/.github/workflows/rust.yml b/.github/workflows/rust.yml
index d097e12..3a39cfb 100644
--- a/.github/workflows/rust.yml
+++ b/.github/workflows/rust.yml
@@ -131,6 +131,12 @@ jobs:
         working-directory: .
         run: python tools/esp32_scaffold/check_no_std.py

+      - name: Test required RISC-V reservation boundaries and overflow
+        working-directory: .
+        env:
+          PYTHONPATH: .
+        run: python -m tools.esp32_scaffold.test_memory_budget --require-riscv
+
       - name: Tool versions
         run: |
           rustc +1.85.1 --version
```

Lossless complete patch (base64):
```base64
ZGlmZiAtLWdpdCBhLy5naXRodWIvd29ya2Zsb3dzL3J1c3QueW1sIGIvLmdpdGh1Yi93b3JrZmxv
d3MvcnVzdC55bWwKaW5kZXggZDA5N2UxMi4uM2EzOWNmYiAxMDA2NDQKLS0tIGEvLmdpdGh1Yi93
b3JrZmxvd3MvcnVzdC55bWwKKysrIGIvLmdpdGh1Yi93b3JrZmxvd3MvcnVzdC55bWwKQEAgLTEz
MSw2ICsxMzEsMTIgQEAgam9iczoKICAgICAgICAgd29ya2luZy1kaXJlY3Rvcnk6IC4KICAgICAg
ICAgcnVuOiBweXRob24gdG9vbHMvZXNwMzJfc2NhZmZvbGQvY2hlY2tfbm9fc3RkLnB5CiAKKyAg
ICAgIC0gbmFtZTogVGVzdCByZXF1aXJlZCBSSVNDLVYgcmVzZXJ2YXRpb24gYm91bmRhcmllcyBh
bmQgb3ZlcmZsb3cKKyAgICAgICAgd29ya2luZy1kaXJlY3Rvcnk6IC4KKyAgICAgICAgZW52Ogor
ICAgICAgICAgIFBZVEhPTlBBVEg6IC4KKyAgICAgICAgcnVuOiBweXRob24gLW0gdG9vbHMuZXNw
MzJfc2NhZmZvbGQudGVzdF9tZW1vcnlfYnVkZ2V0IC0tcmVxdWlyZS1yaXNjdgorCiAgICAgICAt
IG5hbWU6IFRvb2wgdmVyc2lvbnMKICAgICAgICAgcnVuOiB8CiAgICAgICAgICAgcnVzdGMgKzEu
ODUuMSAtLXZlcnNpb24K
```

### UDP classifier step

Source: `c27889efab5cb87295348f69d5839d5605fb5868`; +6/-0.
Patch SHA256: `bf999679b4ad512cbd0419494bebf6068726e52fb255813951d071faa096ccd5` (706 bytes, 17 lines; LF).
```diff
diff --git a/.github/workflows/rust.yml b/.github/workflows/rust.yml
index d097e12..1e018f3 100644
--- a/.github/workflows/rust.yml
+++ b/.github/workflows/rust.yml
@@ -74,6 +74,12 @@ jobs:
         working-directory: .
         run: python -m unittest discover -s tools/rust_scaffold/tests -p test_check_lift.py -v

+      - name: Test UDP mutation classifier
+        working-directory: .
+        env:
+          PYTHONPATH: .
+        run: python -m unittest tools.udp_scaffold.test_mutation_check -v
+
       - name: Install pinned Rust and check components
         run: rustup toolchain install 1.85.1 --profile minimal --component rustfmt --component clippy --target riscv32imc-unknown-none-elf

```

Lossless complete patch (base64):
```base64
ZGlmZiAtLWdpdCBhLy5naXRodWIvd29ya2Zsb3dzL3J1c3QueW1sIGIvLmdpdGh1Yi93b3JrZmxv
d3MvcnVzdC55bWwKaW5kZXggZDA5N2UxMi4uMWUwMThmMyAxMDA2NDQKLS0tIGEvLmdpdGh1Yi93
b3JrZmxvd3MvcnVzdC55bWwKKysrIGIvLmdpdGh1Yi93b3JrZmxvd3MvcnVzdC55bWwKQEAgLTc0
LDYgKzc0LDEyIEBAIGpvYnM6CiAgICAgICAgIHdvcmtpbmctZGlyZWN0b3J5OiAuCiAgICAgICAg
IHJ1bjogcHl0aG9uIC1tIHVuaXR0ZXN0IGRpc2NvdmVyIC1zIHRvb2xzL3J1c3Rfc2NhZmZvbGQv
dGVzdHMgLXAgdGVzdF9jaGVja19saWZ0LnB5IC12CiAKKyAgICAgIC0gbmFtZTogVGVzdCBVRFAg
bXV0YXRpb24gY2xhc3NpZmllcgorICAgICAgICB3b3JraW5nLWRpcmVjdG9yeTogLgorICAgICAg
ICBlbnY6CisgICAgICAgICAgUFlUSE9OUEFUSDogLgorICAgICAgICBydW46IHB5dGhvbiAtbSB1
bml0dGVzdCB0b29scy51ZHBfc2NhZmZvbGQudGVzdF9tdXRhdGlvbl9jaGVjayAtdgorCiAgICAg
ICAtIG5hbWU6IEluc3RhbGwgcGlubmVkIFJ1c3QgYW5kIGNoZWNrIGNvbXBvbmVudHMKICAgICAg
ICAgcnVuOiBydXN0dXAgdG9vbGNoYWluIGluc3RhbGwgMS44NS4xIC0tcHJvZmlsZSBtaW5pbWFs
IC0tY29tcG9uZW50IHJ1c3RmbXQgLS1jb21wb25lbnQgY2xpcHB5IC0tdGFyZ2V0IHJpc2N2MzJp
bWMtdW5rbm93bi1ub25lLWVsZgogCg==
```

## Historical native Windows proof

CX-027 fixed source fcc3aea8b8115733c8f89c683652c6b114f514bc passed native Windows
Rust push run41583893375/job125744760675; Ubuntu job125744760768 also passed.
Windows direct-profile totals: default210/0; sim223/0; bare116/0; alloc208/0.
Both new TCP tests passed five times each; TCP integration was11/0 in each of five executions.
Details, the failing predecessor, mutations and pinned receipts are in CX-027-003.md.
[Native Windows job](https://github.com/anywave/rpp-spec/actions/runs/41583893375/job/125744760675).
This is retained historical evidence, not native Windows execution on either linear branch.

## Self-review and handoff

Self-review: full merge-base source/test diff inspected; independent whole-tree blob/mode,
history, slice and scope audits passed. Only real finding was raw patch context-blank trailing spaces:
fixed in report rendering, with base64 preserving all original bytes; no whitespace suppression used.
Independent decoding equals all three git patches exactly; hashes and byte lengths match.
The two new reports are explicit requested additions, separated from exact implementation equality.
The literal final028 old/new diff therefore includes reports; no claim that it contains only rust.yml.
No old report is edited. No behavioral finding or change is introduced by replay.
The reviewed source implementations are unchanged; no new behavior, test or mutant is introduced by replay.
The existing tests/mutations retain their source assertions; fresh copied-source checks must be reported above.
No protected workflow, gate, owner, allow-list or ruleset edit is part of either replacement branch.
CX-027 normal push verified at 953d0d4b73a0a77ecdd1071506b849544cb76a02 by git ls-remote.
CX-028 delivery head uses the final branch ref in frontmatter to avoid a self-referential commit hash;
its single normal push and exact remote SHA are recorded in the final reply/outside publication receipt.
Verify with `git ls-remote origin refs/heads/codex/cx-027-linear refs/heads/codex/cx-028-linear`.
TR opens PRs; no force push, master push, old-branch rewrite or PR creation is authorized here.
