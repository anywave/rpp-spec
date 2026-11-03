---
id: CX-UDP-CLASSIFIER-CI-001
from: Codex (rpp-spec)
to: TR
repo: anywave/rpp-spec
branch: codex/udp-classifier-ci
head: refs/heads/codex/udp-classifier-ci
head_kind: final-pushed-branch-ref
source_base: e571a84c1efa3c83cd65a17596c824377eba431b
source_freeze: 2675d9fedd72a5d18a4c9edf1656c0954ae00382
date: 2026-11-02
type: report
subject: Run the bounded UDP mutation classifier unit in the Rust workflow
---

This implements the remaining optional nit from TR's 12:30 inbox entry after
CX-027 and CX-028 were integrated and normally pushed. I read all twelve
codex/LESSONS.md rules before this card and applied the pre-push review skill.
No shared status document, runtime, original test, spec, header, layout,
constant, vector, model, key or cryptographic implementation was changed.

## Change and self-review

.github/workflows/rust.yml:77 adds one step named Test UDP mutation classifier.
It runs this exact command from the repository root, with PYTHONPATH set to .:

```sh
python -m unittest tools.udp_scaffold.test_mutation_check -v
```

The step follows the Python guards and precedes Rust installation. It has no
condition or failure waiver and contains one command, so a later successful
command cannot mask a failed unit run on Windows. The existing pinned oracle
Python runs it in both Ubuntu and Windows matrix entries. Every previous step,
action pin, checkout setting, permission, matrix value and job default remains
unchanged; removing the new six-line block reproduces master's exact bytes.

IMPOSED: invoke the existing bounded classifier unit with mocked subprocess
results. The unit uses only stdlib.
It needs no extra dependency, Cargo build, socket, network request or secret.

## Actual validation

BEFORE: exact unit command passes 1 method / 0 failures, covering 7 fixed
classifier outcomes; the Rust workflow does not invoke it.

AFTER: exact unit command passes 1 method / 0 failures, covering the same
7 fixed classifier outcomes; the workflow now schedules it on both hosts.

The existing method's docstring names the mutation accepting arbitrary panic
or compiler-failure text. The classifier must count only the selected terminal
assertion failure. No new shipping test or fresh native mutation run is claimed.
Two manual workflow counterexamples, an absent step and a Linux-only condition,
are refused by the parsed contract check; these are not new mutation-kill counts.

Source commit 2675d9f changes one file, +6/-0 lines. Fresh root gates pass:
Python1256, golden5/0, Ruff0.14.10, 17 identical corpus files, four freshness
tests and lift10manifests/59sources/38refs/0findings. All six exact-BASE wrappers,
drift0/0/0 and whitespace pass; final report-inclusive checks run before push.
Rust source is unchanged; no broad Rust rerun is claimed for this CI-only edit.

| Outside receipt | SHA256 |
| --- | --- |
| udp-classifier-ci-evidence/handoff.json | c03dcd27b6f2e25a542974952e044501e7f76bb7e7f4fbd697b81859c9fbd017 |
| udp-classifier-ci-evidence/after.json | b4abbbfcc81699cb6c9b94ee10a921249075d062da2b3d2e6c70197cd897e85c |
| udp-classifier-ci-evidence/workflow-contract.json | ea8c6aca948f841c43bdaa46419c78ceb5f2c2fa9465988e5fe59f5e8fc00ebe |
| root-python-bound.json | cf95dcec24d77d003329c09b6f218f20b302aeec754522802c5b72d1c9dd311f |
| Independent source/unit audit | 54fb7f1c66a16829f8cc20d02f53149637452e017faba23148a4fdf2f37b2f25 |

## Windows repeat and delivery

No native Windows execution or hosted CI result is claimed here. With the
existing Python, run the command above from the root and check its process exit;
the expected result is one passing unittest method. The workflow's single
command follows the same pattern as its other Python guard steps.

Root publishes this new report and performs one normal branch push after all
checks. TR opens the PR. No force push, PR merge, setting change or extra cloud
capacity is involved; published outboxes remain untouched.
