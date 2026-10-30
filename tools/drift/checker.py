"""Purely local diff review. Never imports or executes code from the target range."""

import ast
from collections import Counter
from dataclasses import dataclass
import fnmatch
import hashlib
import html
import json
from pathlib import Path
import re
import subprocess


DATA = Path(__file__).with_name("catalog.json")
SEVERITY = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
MAX_BLOB = 4 * 1024 * 1024
MAX_DIFF = 16 * 1024 * 1024
PHYSICAL = re.compile(
    r"\b(?:decoher\w*|spin\w*|wave mechanics|quantum|holograph\w*|"
    r"physical invariant|measurement of a material property)\b", re.I
)
DEPENDENCY = re.compile(r"\b(?:MUST|require\w*|depend\w*|valid\w*|correct\w*)\b", re.I)
PATTERNS = {
    "BND-A-1": r"\b(?:store\w*|persist\w*)\b.{0,80}\b(?:user data|encrypted blobs?|payload bytes)\b|\bbecome (?:a |an )?(?:filesystem|database)\b",
    "BND-B-1": r"\b(?:issu\w*|mint\w*|creat\w*)\b.{0,60}\b(?:accounts?|jwts?|identity tokens?|wallets?|cryptocurrency)\b",
    "BND-C-1": r"\b(?:if/else|conditional logic|scripts?|general.purpose (?:rule )?DSL)\b.{0,60}\baddress\w*\b|\baddress\w*\b.{0,60}\b(?:if/else|conditional logic|scripts?|general.purpose (?:rule )?DSL)\b",
    "BND-E-1": r"\b(?:require\w*|use\w*|match\w*)\b.{0,60}\b(?:embeddings?|LLMs?|inference)\b|\b(?:embeddings?|LLMs?|inference)\b.{0,60}\b(?:match\w*|interpret\w*|require\w*)\b",
    "BND-G-1": r"\b(?:custom fields per.deployment|unlimited fields|unbounded fields|arbitrary key/value tags)\b",
    "WORD-CLAIM-1": r"\b(?:guaranteed|quantum.secure|unhackable)\b",
}


class ToolError(Exception):
    """An incomplete review must exit 2, never appear clean."""


def git(root, *args):
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "--no-pager", *args],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=60,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ToolError("Git unavailable or timed out") from exc
    if result.returncode:
        raise ToolError("Git could not read the requested repository objects")
    return result.stdout


def resolve(root, value):
    # SHAs only. Ref names, ranges, flags and Git revision expressions are rejected.
    if not re.fullmatch(r"[0-9a-fA-F]{7,64}", value):
        raise ToolError("base/head must be hexadecimal commit IDs (at least 7 digits)")
    return git(root, "rev-parse", "--verify", "--end-of-options", value + "^{commit}").decode().strip()


def blob(root, sha, path):
    # ls-tree distinguishes absent paths from unreadable/corrupt Git objects.
    entry = git(root, "ls-tree", "-z", sha, "--", ":(literal)" + path)
    if not entry:
        return ""
    metadata = entry.split(b"\t", 1)[0].split()
    if len(metadata) != 3 or metadata[0] not in (b"100644", b"100755"):
        # Never follow symlinks, submodules or directories into an unchecked source.
        raise ToolError("changed review path is not a regular Git blob")
    size = int(git(root, "cat-file", "-s", metadata[2].decode()))
    if size > MAX_BLOB:
        raise ToolError("changed source exceeds the 4 MiB review limit")
    content = git(root, "cat-file", "blob", metadata[2].decode())
    if b"\0" in content:
        raise ToolError("changed review source contains binary data")
    return content.decode("utf-8")


@dataclass(frozen=True)
class Change:
    path: str
    side: str
    line: int
    text: str
    evidence: str


def changes(root, base, head, catalog):
    paths = git(root, "diff", "--no-ext-diff", "--no-textconv", "--no-renames",
                "--name-only", "-z", base, head, "--").split(b"\0")
    total = 0
    result = {}
    for encoded in paths:
        if not encoded:
            continue
        path = encoded.decode("utf-8")
        relevant = path.endswith(".md") or any(fnmatch.fnmatchcase(path, pattern) for pattern in (
            catalog["core_globs"] + catalog["vector_globs"] + catalog["address_paths"]
        ))
        if not relevant:
            # No configured content predicate applies, e.g. a historical PDF. Do
            # not pretend to interpret its bytes, nor allow it to break the scan.
            continue
        patch = git(root, "diff", "--no-ext-diff", "--no-textconv", "--no-renames",
                    "--unified=3", base, head, "--", ":(literal)" + path)
        total += len(patch)
        if total > MAX_DIFF:
            raise ToolError("diff exceeds the 16 MiB review limit")
        lines = patch.decode("utf-8").splitlines()
        edits = []
        starts = [i for i, s in enumerate(lines) if s.startswith("@@ ")]
        for index, start in enumerate(starts):
            end = starts[index + 1] if index + 1 < len(starts) else len(lines)
            hunk = lines[start:end]
            match = re.match(r"@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@", hunk[0])
            if not match:
                raise ToolError("unrecognized Git diff hunk")
            old, new = map(int, match.groups())
            for offset, text in enumerate(hunk[1:], 1):
                # Exact diff excerpt around each event; deterministic and bounded.
                excerpt = "\n".join([hunk[0], *hunk[max(1, offset - 3):offset + 4]])
                if text.startswith("+"):
                    edits.append(Change(path, "+", new, text[1:], excerpt))
                    new += 1
                elif text.startswith("-"):
                    edits.append(Change(path, "-", old, text[1:], excerpt))
                    old += 1
                elif text.startswith(" "):
                    old += 1
                    new += 1
                elif not text.startswith("\\"):
                    raise ToolError("unrecognized diff line")
        # A binary/mode-only event still has path evidence for vector guards.
        result[path] = edits or [Change(path, "+", 0, "", "\n".join(lines[:8]))]
    return result


def paragraphs(text):
    """Markdown prose blocks, retaining exact source coordinates; no fenced code."""
    block = []
    start = 0
    fence = None
    for n, line in enumerate(text.splitlines(), 1):
        marker = re.match(r"^\s*(`{3,}|~{3,})", line)
        if marker:
            if block:
                yield start, "\n".join(block)
                block = []
            token = marker[1][0]
            if fence is None:
                fence = token
            elif fence == token:
                fence = None
            continue
        if fence:
            continue
        if not line.strip() or line.startswith("#") or line.strip() == "---":
            if block:
                yield start, "\n".join(block)
                block = []
            continue
        if not block:
            start = n
        block.append(line)
    if block:
        yield start, "\n".join(block)


def clean_ast(node):
    """Ignore docstrings, comments and coordinates; retain executable structure."""
    if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
        node.body = [s for s in node.body if not (
            isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant)
            and isinstance(s.value.value, str)
        )]
    for child in ast.iter_child_nodes(node):
        clean_ast(child)
    return node


def parse(text):
    try:
        return clean_ast(ast.parse(text))
    except (SyntaxError, RecursionError) as exc:
        raise ToolError("changed protected Python source does not parse") from exc


def projection(text, kind):
    """Static structural review only: no imports, eval, or target subprocesses."""
    tree = parse(text)
    selected = []
    for node in ast.walk(tree):
        if kind == "format":
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                if any(isinstance(t, ast.Name) and re.fullmatch(
                    r"(?:ADDRESS|THETA|PHI|OMEGA|HARMONIC|RADIUS|RESERVED|SHELL|MAX)_\w+", t.id
                ) for t in targets):
                    selected.append(ast.dump(node, include_attributes=False))
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in {
                "encode", "decode", "to_int", "to_raw", "from_int", "from_raw", "__post_init__", "is_valid"
            }:
                selected.append(ast.dump(node, include_attributes=False))
        elif kind == "radius_api":
            if isinstance(node, ast.If) and any(
                isinstance(t, ast.Attribute) and t.attr == "radius" for t in ast.walk(node.test)
            ):
                selected.append(ast.dump(node, include_attributes=False))
        elif kind == "radius_enc":
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                if any(isinstance(t, ast.Name) and (t.id in {"r_enc", "radius_enc"} or t.id.startswith("RADIUS_")) for t in targets):
                    selected.append(ast.dump(node, include_attributes=False))
        elif kind == "fields":
            if isinstance(node, ast.ClassDef) and node.name in {"RPPAddress", "RPPCanonicalAddress"}:
                for field in node.body:
                    if isinstance(field, ast.AnnAssign) and isinstance(field.target, ast.Name):
                        if not (isinstance(field.annotation, ast.Subscript) and isinstance(field.annotation.value, ast.Name) and field.annotation.value.id == "ClassVar"):
                            selected.append(ast.dump(field, include_attributes=False))
        elif kind == "backbone":
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                if any(isinstance(t, ast.Name) and t.id in {"THETA_SECTORS", "MIN_HOT_NODES_PER_SECTOR"} for t in targets):
                    selected.append(ast.dump(node, include_attributes=False))
        elif kind == "phi_write":
            if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                if any(isinstance(t, ast.Attribute) and t.attr == "phi" for target in targets for t in ast.walk(target)):
                    selected.append(ast.dump(node, include_attributes=False))
    return sorted(selected)


def specification_major(text):
    match = re.search(r"\*\*RPP Specification Version:\*\*\s*(\d+)\.\d+\.\d+", text)
    return int(match[1]) if match else None


def check(root, base, head):
    root = Path(git(root, "rev-parse", "--show-toplevel").decode().strip())
    base, head = resolve(root, base), resolve(root, head)
    catalog = json.loads(DATA.read_text(encoding="utf-8"))
    rules = {r["rule_id"]: r for r in catalog["rules"]}
    diff = changes(root, base, head, catalog)
    findings = []
    cache = {}

    def read(sha, path):
        key = (sha, path)
        if key not in cache:
            cache[key] = blob(root, sha, path)
        return cache[key]

    def add(rule_id, event, detail=""):
        rule = rules[rule_id]
        evidence = event.evidence
        if detail:
            evidence += "\n[coordinator] " + detail
        findings.append(dict(rule_id=rule_id, severity=rule["severity"], path=event.path,
                             line=event.line, evidence=evidence, source=rule["source"], tag=rule["tag"]))

    def first_event(path, side=None, start=None, end=None):
        for e in diff[path]:
            if (side is None or e.side == side) and (start is None or start <= e.line <= end):
                return e
        return diff[path][0]

    core_specs = set(catalog["core_specs"])
    substrate = catalog["substrate_globs"]
    core_globs = catalog["core_globs"]
    addresses = set(catalog["address_paths"])
    major_base = specification_major(read(base, "VERSION_POLICY.md"))
    major_head = specification_major(read(head, "VERSION_POLICY.md"))
    bumped = major_base is not None and major_head is not None and major_head > major_base

    for path, events in diff.items():
        if any(fnmatch.fnmatchcase(path, pattern) for pattern in catalog["vector_globs"]):
            add("VEC-1", events[0], "Golden-vector path changed; RADIX review required.")
        is_core = path in core_specs or any(fnmatch.fnmatchcase(path, g) for g in core_globs)
        is_substrate = any(fnmatch.fnmatchcase(path, g) for g in substrate)
        for event in events:
            if event.side != "+":
                continue
            for rule_id, pattern in PATTERNS.items():
                applicable = (path.endswith(".md") and not path.startswith("tools/drift/")) if rule_id == "WORD-CLAIM-1" else is_core
                if applicable and re.search(pattern, event.text, re.I):
                    add(rule_id, event)

        if path.endswith(".md") and (path in core_specs or is_substrate):
            old, new = read(base, path), read(head, path)
            old_blocks = Counter(text for _, text in paragraphs(old))
            for start, text in paragraphs(new):
                if old_blocks[text]:
                    old_blocks[text] -= 1
                    continue
                end = start + len(text.splitlines()) - 1
                touched = [e for e in events if e.side == "+" and start <= e.line <= end]
                # Deleted-only paragraphs are handled by the baseline/removal guards below.
                if touched and PHYSICAL.search(text):
                    if is_substrate:
                        add("BND-F-2", touched[0])
                    elif DEPENDENCY.search(text):
                        add("BND-F-1", touched[0])
            # Exact software MUST removal is independent of physical-term additions.
            if path in core_specs:
                for start, text in paragraphs(old):
                    if "Software implementations MUST enforce equivalent TTL semantics per Shell tier." in text and text not in new:
                        add("BND-F-1", first_event(path, "-", start, start + len(text.splitlines()) - 1),
                            "Software-equivalence MUST passage removed or changed.")

        if path in addresses:
            old, new = read(base, path), read(head, path)
            if not bumped and projection(old, "format") != projection(new, "format"):
                add("VER-FORMAT-1", events[0], "Protected encoding/range AST changed without a specification MAJOR increase.")
            # Any field-annotation change is a bounded-schema review candidate.
            if projection(old, "fields") != projection(new, "fields"):
                add("BND-G-1", events[0], "Core address field schema changed.")
            if path == "rpp/address_canonical.py":
                for rule_id, kind in [("VER-RADIUS-API", "radius_api"), ("VER-RADIUS-ENC", "radius_enc")]:
                    if projection(old, kind) != projection(new, kind):
                        add(rule_id, events[0], "Radius contract AST changed; inspect the diff against both cited layers.")

        if path == "rpp/network.py":
            old, new = read(base, path), read(head, path)
            if projection(old, "backbone") != projection(new, "backbone"):
                add("NET-INV-2", events[0], "Backbone coverage constants changed.")
            if projection(old, "phi_write") != projection(new, "phi_write"):
                add("NET-INV-1", events[0], "A phi-attribute write changed; runtime monotonicity needs review.")

    # Guard verbatim source passages by their occurrence counts, not fixed line numbers.
    # Review only a passage present in base and changed/deleted in head. Historical ranges
    # predating the frozen source do not inherit findings for unrelated text.
    for guard in catalog["guards"]:
        path, text = guard["path"], guard["text"]
        if path not in diff or (guard["rule_id"] == "VER-FORMAT-1" and bumped):
            continue
        old, new = read(base, path), read(head, path)
        if old.count(text) > new.count(text):
            start = old[:old.index(text)].count("\n") + 1
            event = first_event(path, "-", start, start + text.count("\n"))
            add(guard["rule_id"], event, "Referenced source passage changed or removed.")

    for baseline in catalog["baselines"]:
        path, text = baseline["path"], baseline["text"]
        if path not in diff:
            continue
        if hashlib.sha256(text.encode("utf-8")).hexdigest() != baseline["sha256"]:
            raise ToolError("Boundary F baseline checksum mismatch")
        old, new = read(base, path), read(head, path)
        if old.count(text) > new.count(text):
            start = old[:old.index(text)].count("\n") + 1
            event = first_event(path, "-", start, start + text.count("\n"))
            rule_id = "BND-F-1" if path in core_specs else "BND-F-2"
            # Unclassified documents remain inventory-only, as required by TR.
            if path in core_specs or any(fnmatch.fnmatchcase(path, g) for g in substrate):
                add(rule_id, event, baseline["id"] + ": unresolved - steward decision (RADIX)")

    # Identical findings can arise through independent guards; retain distinct evidence.
    unique = {json.dumps(f, sort_keys=True, ensure_ascii=True): f for f in findings}
    findings = sorted(unique.values(), key=lambda f: (
        SEVERITY[f["severity"]], f["rule_id"], f["path"], f["line"], f["evidence"], f["source"]
    ))
    counts = Counter(f["severity"].lower() for f in findings)
    return {
        "base": base, "head": head,
        "catalog_sha256": hashlib.sha256(DATA.read_bytes()).hexdigest(),
        "findings": findings,
        "summary": {"high": counts["high"], "medium": counts["medium"], "low": counts["low"],
                    "rules_run": len(rules), "rules_not_checkable": catalog["rules_not_checkable"]},
    }


def markdown(report):
    summary = report["summary"]
    lines = ["# RPP drift report", "", f"Range: `{report['base']}..{report['head']}`", "",
             "Review candidates from explicit syntactic rules; no semantic completeness claim.", "",
             "HIGH: {high}; MEDIUM: {medium}; LOW: {low}; rules run: {rules_run}; "
             "not checkable: {rules_not_checkable}.".format(**summary), ""]
    if not report["findings"]:
        lines += ["No configured drift rules matched.", ""]
    for f in report["findings"]:
        # HTML escaping prevents diff text from injecting Markdown links/HTML/workflow commands.
        lines += [f"## {f['severity']} {f['rule_id']} ({f['tag']})", "",
                  "<pre>" + html.escape(f"{f['path']}:{f['line']}\nSource: {f['source']}") + "</pre>", "",
                  "<pre>" + html.escape(f["evidence"]) + "</pre>", ""]
    return "\n".join(lines)


def write_reports(report, output_dir):
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "drift-report.json").write_text(
        json.dumps(report, sort_keys=True, indent=2, ensure_ascii=True) + "\n", encoding="utf-8", newline="\n"
    )
    (output_dir / "drift-report.md").write_text(markdown(report), encoding="utf-8", newline="\n")
