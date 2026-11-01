"""Purely local diff review. Never imports or executes code from the target range."""

import ast
from collections import Counter
from copy import deepcopy
from dataclasses import dataclass
import fnmatch
import hashlib
import html
import json
import os
from pathlib import Path
import re
import subprocess

from .boundary import review as boundary_review
from .passages import digest, in_scope, normalize
from .rulings import BASELINE_DECISIONS, BEFORE, DECIDED, DECISION_LINES, FINDING_KEYS, ITEM_DECISIONS, REVISION, RULED


DATA = Path(__file__).with_name("catalog.json")
SEVERITY = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
MAX_BLOB = 4 * 1024 * 1024
MAX_DIFF = 16 * 1024 * 1024
SOURCE_REVISION = "0a12c8dc311e27816a99b69c1cb2f1e7d9cb282e"
UNRESOLVED = "unresolved - steward decision (RADIX)"
FOUNDATION_SHA256 = "b69bc6f3d30eff3add7ba530942d4082cc3ac1d79727fee665ab16dd735df6ce"
APPROVED_OVERLAY_SHA256 = "fae35d63cce3e11f363cba32fb7617c112040e3e819aefe4ff33c39c870e4868"
IMPLEMENTED_RULES = {
    **{key: "HIGH" for key in (
        "BND-A-1", "BND-B-1", "BND-C-1", "BND-E-1", "BND-G-1", "BND-F-1",
        "VER-FORMAT-1", "VER-RADIUS-API", "VER-RADIUS-ENC", "VER-RADIUS-TIES",
        "VEC-1", "NET-INV-1", "NET-INV-2",
    )},
    **{key: "MEDIUM" for key in (
        "BND-F-2", "BND-F-BASELINE-REMOVED", "STEWARD-TTL-1", "STEWARD-T2-1",
        "STEWARD-CLAIM-1", "STEWARD-RADIUS-DERIVATION",
    )},
    **{key: "LOW" for key in ("WORD-CLAIM-1", "WORD-RADIUS-1", "WORD-RADIUS-EDGE")},
}
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


def load_catalog(path=None):
    """Reject incomplete metadata rather than claiming zero or unknown rules ran.

    This engine implements the 22-rule frozen scan plus the exact CX-006 ruling
    overlay. A decided entry remains watched; only its approved identity changed.
    """
    try:
        catalog_path = DATA if path is None else Path(path)
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError, TypeError) as exc:
        raise ToolError("coordinator catalog is unreadable or invalid JSON") from exc

    def require(condition):
        if not condition:
            raise ToolError("coordinator catalog schema or coverage is invalid")

    def strings(item, keys):
        require(isinstance(item, dict))
        require(all(isinstance(item.get(key), str) and item[key].strip() for key in keys))

    def string_list(key, count=None):
        value = catalog.get(key)
        require(isinstance(value, list) and bool(value))
        require(all(isinstance(v, str) and bool(v.strip()) for v in value))
        require(len(value) == len(set(value)))
        if count is not None:
            require(len(value) == count)

    def passage(item):
        strings(item, ("path", "text", "sha256"))
        require(type(item.get("line")) is int and item["line"] > 0)
        require(type(item.get("end")) is int and item["end"] >= item["line"])
        require(re.fullmatch(r"[0-9a-f]{64}", item["sha256"]) is not None)
        require(digest(item["text"]) == item["sha256"])

    require(isinstance(catalog, dict))
    require(catalog.get("source_revision") == SOURCE_REVISION)
    strings(catalog, ("normalization",))
    require(type(catalog.get("rules_not_checkable")) is int and catalog["rules_not_checkable"] >= 0)
    for key in ("core_globs", "address_paths", "vector_globs", "boundary_text_paths"):
        string_list(key)
    string_list("scanned_paths", 75)

    rules = catalog.get("rules")
    require(isinstance(rules, list) and len(rules) == len(IMPLEMENTED_RULES))
    found = set()
    for rule in rules:
        strings(rule, ("rule_id", "source", "severity", "tag", "quote", "method", "positive", "negative"))
        key = rule["rule_id"]
        require(key in IMPLEMENTED_RULES and key not in found)
        found.add(key)
        require(rule["severity"] == IMPLEMENTED_RULES[key])
        require(rule["tag"] == ("SOURCED" if key in {"VER-RADIUS-API", "VER-RADIUS-ENC"} else "IMPOSED"))
    require(found == set(IMPLEMENTED_RULES))

    guards = catalog.get("guards")
    require(isinstance(guards, list) and bool(guards))
    for guard in guards:
        strings(guard, ("rule_id", "path", "text"))
        require(guard["rule_id"] in IMPLEMENTED_RULES)

    baselines = catalog.get("baselines")
    require(isinstance(baselines, list) and len(baselines) == 243)
    ids = set()
    for entry in baselines:
        passage(entry)
        strings(entry, ("id", "kind", "rule_id", "tag", "status", "route"))
        require(entry["id"] not in ids)
        ids.add(entry["id"])
        require(in_scope(entry["path"]) and entry["path"] in catalog["scanned_paths"])
        require(entry["kind"] in {"paragraph", "list_item", "table_row", "code_fence", "comment", "docstring"})
        require(entry["rule_id"] in {"BND-F-1", "BND-F-2"})
        require(entry["tag"] == "IMPOSED" and entry["route"].startswith("[RFC]"))
        if entry["id"] in BASELINE_DECISIONS:
            require(entry["status"] == RULED)
            require(entry.get("decision_id") == "CX-006-" + BASELINE_DECISIONS[entry["id"]])
            require(entry.get("source_revision") == REVISION)
            require(isinstance(entry.get("original"), dict))
            passage(entry["original"])
            require(entry["original"].get("id") == entry["id"] and entry["original"].get("status") == UNRESOLVED)
        else:
            require(entry["status"] == UNRESOLVED and "decision_id" not in entry and "original" not in entry)

    anchors = catalog.get("software_must_anchors")
    require(isinstance(anchors, list) and len(anchors) == 7)
    anchor_ids = set()
    for anchor in anchors:
        passage(anchor)
        key = (anchor["path"], anchor["line"])
        require(key not in anchor_ids)
        anchor_ids.add(key)

    for group, expected in (
        ("steward_items", {"STEWARD-TTL-1", "STEWARD-T2-1", "STEWARD-CLAIM-1", "STEWARD-RADIUS-DERIVATION"}),
        ("advisories", {"WORD-RADIUS-EDGE", "WORD-RADIUS-1"}),
    ):
        items = catalog.get(group)
        require(isinstance(items, list) and len(items) == len(expected))
        ids = set()
        for item in items:
            strings(item, ("rule_id", "severity", "tag", "status", "route", "description"))
            key = item["rule_id"]
            require(key in expected and key not in ids)
            ids.add(key)
            require(item["severity"] == IMPLEMENTED_RULES[key] and item["tag"] == "IMPOSED")
            require(item["route"].startswith("[RFC]"))
            if key in ITEM_DECISIONS:
                require(item["status"] == DECIDED and item.get("decision_id") == "CX-006-" + ITEM_DECISIONS[key])
                require(item.get("source_revision") == REVISION)
                require(isinstance(item.get("original"), dict) and item["original"].get("status") == UNRESOLVED)
            else:
                require(item["status"] == UNRESOLVED and "decision_id" not in item and "original" not in item)
            require(isinstance(item.get("passages"), list) and bool(item["passages"]))
            for source in item["passages"]:
                passage(source)
        require(ids == expected)
    require(catalog.get("catalog_revision") == 2)
    rulings = catalog.get("rulings")
    require(isinstance(rulings, dict) and rulings.get("source_revision") == REVISION)
    require(rulings.get("authority") == "RADIX")
    strings(rulings, ("authorization", "original_range_base"))
    require(rulings["original_range_base"] == BEFORE)
    require("c098c20e" in rulings["authorization"])
    decisions = rulings.get("decisions")
    require(isinstance(decisions, dict) and set(decisions) == {"CX-006-" + code for code in DECISION_LINES})
    for code, line in DECISION_LINES.items():
        decision = decisions["CX-006-" + code]
        passage(decision)
        require(decision.get("id") == "CX-006-" + code and decision["path"] == "DECISIONS.md" and decision["line"] == line)
        require(decision.get("authority") == "RADIX" and decision.get("date") == "2026-10-31")
        require(decision["text"].startswith(f"### [RFC] CX-006-{code} "))
    recorded = rulings.get("findings")
    require(isinstance(recorded, list) and len(recorded) == len(FINDING_KEYS))
    for finding, (rule_id, severity, path, line, code) in zip(recorded, FINDING_KEYS):
        require(isinstance(finding, dict))
        require((finding.get("rule_id"), finding.get("severity"), finding.get("path"), finding.get("line"), finding.get("decision_id"))
                == (rule_id, severity, path, line, "CX-006-" + code))
        passage(finding.get("after"))
        require(finding["after"]["path"] == path)
        if finding.get("before") is None:
            require(path == "DECISIONS.md" and rule_id == "BND-F-2")
            require(re.fullmatch(r"[0-9a-f]{64}", finding.get("created_file_sha256", "")) is not None)
        else:
            passage(finding["before"])
            require(finding["before"]["path"] == path)
    revised_guards = [guard for guard in guards if "decision_id" in guard]
    require(len(revised_guards) == 2)
    for guard in revised_guards:
        require(guard.get("decision_id") == "CX-006-A1" and guard.get("source_revision") == REVISION)
        original = guard.get("original")
        strings(original, ("rule_id", "path", "text"))
        require(guard["rule_id"] == original["rule_id"] == "VER-FORMAT-1")
        require(guard["path"] == original["path"] == "VERSION_POLICY.md")
        expected = original["text"].replace("(radius << 13)", "(r_enc << 13)")
        expected = expected.replace("| Radius decoding | `(address >> 13) & 0xFF` |", "| Radius decoding | `r_enc = (address >> 13) & 0xFF; radius = r_enc / 255.0` |")
        expected = expected.replace("Normalized 0-1", "Encoded byte; API radius = byte / 255 in 0–1")
        require(guard["text"] == expected and guard["text"] != original["text"])
    # Restoring only explicitly approved originals must reconstruct the entire
    # pre-revision catalog. This prevents changing any of the 239 pending entries,
    # original ruling evidence, other guard, rule, anchor or frozen scope field.
    foundation = deepcopy(catalog)
    foundation.pop("catalog_revision")
    foundation.pop("rulings")
    for group in ("baselines", "guards", "steward_items", "advisories"):
        foundation[group] = [item.get("original", item) for item in foundation[group]]
    signature = hashlib.sha256(json.dumps(foundation, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    require(signature == FOUNDATION_SHA256)
    approved = {group: [item for item in catalog[group] if "original" in item]
                for group in ("baselines", "guards", "steward_items", "advisories")}
    approved["rulings"] = rulings
    signature = hashlib.sha256(json.dumps(approved, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    require(signature == APPROVED_OVERLAY_SHA256)
    return catalog


def git(root, *args):
    command = ["git", "-c", "core.quotePath=false", "-c", "color.ui=false",
               "-c", "diff.suppressBlankEmpty=false", "-C", str(root), "--no-pager", *args]
    if os.name != "nt":
        # In a C locale with PYTHONUTF8=0, POSIX's filesystem codec can be ASCII.
        # Git still consumes UTF-8 pathspec bytes; Windows uses native Unicode argv.
        command = [arg.encode("utf-8") for arg in command]
    try:
        result = subprocess.run(
            command,
            # Git blobs and NUL-delimited paths require binary transport. Every
            # decode below explicitly uses UTF-8, never the Windows locale.
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=False, check=False, timeout=60,
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
    return git(root, "rev-parse", "--verify", "--end-of-options", value + "^{commit}").decode("utf-8").strip()


def blob(root, sha, path):
    # ls-tree distinguishes absent paths from unreadable/corrupt Git objects.
    entry = git(root, "ls-tree", "-z", sha, "--", ":(literal)" + path)
    if not entry:
        return ""
    metadata = entry.split(b"\t", 1)[0].split()
    if len(metadata) != 3 or metadata[0] not in (b"100644", b"100755"):
        # Never follow symlinks, submodules or directories into an unchecked source.
        raise ToolError("changed review path is not a regular Git blob")
    size = int(git(root, "cat-file", "-s", metadata[2].decode("utf-8")))
    if size > MAX_BLOB:
        raise ToolError("changed source exceeds the 4 MiB review limit")
    content = git(root, "cat-file", "blob", metadata[2].decode("utf-8"))
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
    # Atomic LF-line edit span: old_start, old_end, new_start, new_end; ends
    # are exclusive. A pure insertion/deletion has an empty opposite span.
    edit: tuple[int, int, int, int] | None = None


def changes(root, base, head, catalog):
    paths = git(root, "diff", "--no-ext-diff", "--no-textconv", "--no-renames",
                "--no-color", "--no-relative",
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
        # Every content-reviewed path, including WORD-only Markdown, must be
        # regular UTF-8 text. Validate both sides before asking Git for a patch:
        # binary attributes must not turn a failed inspection into a clean scan.
        blob(root, base, path)
        blob(root, head, path)
        patch = git(root, "diff", "--no-ext-diff", "--no-textconv", "--no-renames",
                    "--no-color", "--no-relative", "--text", "--full-index",
                    "--diff-algorithm=myers", "--no-indent-heuristic",
                    "--inter-hunk-context=0", "--src-prefix=a/", "--dst-prefix=b/",
                    "--unified=3", base, head, "--", ":(literal)" + path)
        total += len(patch)
        if total > MAX_DIFF:
            raise ToolError("diff exceeds the 16 MiB review limit")
        # Git numbers LF-delimited lines. Unicode U+2028/U+2029 and other
        # characters handled by str.splitlines() remain part of the source line.
        lines = patch.decode("utf-8").split("\n")
        if lines and lines[-1] == "":
            lines.pop()
        edits = []
        starts = [i for i, s in enumerate(lines) if s.startswith("@@ ")]
        for index, start in enumerate(starts):
            end = starts[index + 1] if index + 1 < len(starts) else len(lines)
            hunk = lines[start:end]
            match = re.match(r"@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@", hunk[0])
            if not match:
                raise ToolError("unrecognized Git diff hunk")
            # Function captions depend on attributes/config and are unnecessary
            # evidence: retain the exact hunk range, not the optional caption.
            hunk[0] = match.group(0)
            old, new = (max(1, int(value)) for value in match.groups())
            pending = []
            edit_start = None

            def flush_edit():
                nonlocal edit_start
                if pending:
                    span = (edit_start[0], old, edit_start[1], new)
                    for side, line_number, body, evidence in pending:
                        edits.append(Change(path, side, line_number, body, evidence, span))
                    pending.clear()
                    edit_start = None

            for offset, text in enumerate(hunk[1:], 1):
                # Exact diff excerpt around each event; deterministic and bounded.
                excerpt = "\n".join([hunk[0], *hunk[max(1, offset - 3):offset + 4]])
                if text.startswith("+"):
                    if edit_start is None:
                        edit_start = (old, new)
                    pending.append(("+", new, text[1:], excerpt))
                    new += 1
                elif text.startswith("-"):
                    if edit_start is None:
                        edit_start = (old, new)
                    pending.append(("-", old, text[1:], excerpt))
                    old += 1
                elif text.startswith(" "):
                    flush_edit()
                    old += 1
                    new += 1
                elif not text.startswith("\\"):
                    raise ToolError("unrecognized diff line")
            flush_edit()
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


def selected_nodes(text, kind):
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
                    selected.append(node)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in {
                "encode", "decode", "to_int", "to_raw", "from_int", "from_raw", "__post_init__", "is_valid"
            }:
                selected.append(node)
        elif kind == "radius_api":
            if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == "radius":
                selected.append(node)
            if isinstance(node, ast.If) and any(
                isinstance(t, ast.Attribute) and t.attr == "radius" for t in ast.walk(node.test)
            ):
                selected.append(node)
        elif kind == "radius_enc":
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                if any(isinstance(t, ast.Name) and (t.id in {"r_enc", "radius_enc"} or t.id.startswith("RADIUS_")) for t in targets):
                    selected.append(node)
        elif kind == "radius_ties":
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                if any(isinstance(t, ast.Name) and t.id in {"r_enc", "radius_enc"} for t in targets):
                    selected.extend(n for n in ast.walk(node.value) if isinstance(n, ast.Call))
        elif kind == "fields":
            if isinstance(node, ast.ClassDef) and node.name in {"RPPAddress", "RPPCanonicalAddress"}:
                for field in node.body:
                    if isinstance(field, ast.AnnAssign) and isinstance(field.target, ast.Name):
                        if not (isinstance(field.annotation, ast.Subscript) and isinstance(field.annotation.value, ast.Name) and field.annotation.value.id == "ClassVar"):
                            selected.append(field)
        elif kind == "backbone":
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                if any(isinstance(t, ast.Name) and t.id in {"THETA_SECTORS", "MIN_HOT_NODES_PER_SECTOR"} for t in targets):
                    selected.append(node)
        elif kind == "phi_write":
            if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                if any(isinstance(t, ast.Attribute) and t.attr == "phi" for target in targets for t in ast.walk(target)):
                    selected.append(node)
    return selected


def projection(text, kind):
    return sorted(ast.dump(node, include_attributes=False) for node in selected_nodes(text, kind))


def specification_major(text):
    match = re.search(r"\*\*RPP Specification Version:\*\*\s*(\d+)\.\d+\.\d+", text)
    return int(match[1]) if match else None


def parse_repository_root(output):
    """Remove Git's record terminator, never whitespace in the actual pathname."""
    value = output.decode("utf-8")
    if value.endswith("\n"):
        value = value[:-1]
    if os.name == "nt" and value.endswith("\r"):
        value = value[:-1]
    if not value:
        raise ToolError("Git did not report a repository root")
    return Path(value)


def check(root, base, head):
    root = parse_repository_root(git(root, "rev-parse", "--show-toplevel"))
    base, head = resolve(root, base), resolve(root, head)
    catalog = load_catalog()
    rules = {r["rule_id"]: r for r in catalog["rules"]}
    diff = changes(root, base, head, catalog)
    findings = []
    cache = {}

    def read(sha, path):
        key = (sha, path)
        if key not in cache:
            cache[key] = blob(root, sha, path)
        return cache[key]

    def exists(sha, path):
        # Empty regular files and absent tree entries have the same text value.
        # An exact creation permission must distinguish their Git identities.
        return bool(git(root, "ls-tree", "-z", sha, "--", ":(literal)" + path))

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

    def ast_event(path, kind):
        old_nodes = selected_nodes(read(base, path), kind)
        new_nodes = selected_nodes(read(head, path), kind)
        for side, nodes, other in [("+", new_nodes, old_nodes), ("-", old_nodes, new_nodes)]:
            remaining = Counter(ast.dump(n, include_attributes=False) for n in other)
            changed = []
            for node in nodes:
                signature = ast.dump(node, include_attributes=False)
                if remaining[signature]:
                    remaining[signature] -= 1
                else:
                    changed.append(node)
            # Prefer the smallest changed expression over its enclosing function.
            for node in sorted(changed, key=lambda n: (n.end_lineno - n.lineno, n.lineno)):
                for event in diff[path]:
                    if event.side == side and node.lineno <= event.line <= node.end_lineno:
                        return event
        return diff[path][0]

    boundary_text_paths = set(catalog["boundary_text_paths"])
    core_globs = catalog["core_globs"]
    addresses = set(catalog["address_paths"])
    major_base = specification_major(read(base, "VERSION_POLICY.md"))
    major_head = specification_major(read(head, "VERSION_POLICY.md"))
    bumped = major_base is not None and major_head is not None and major_head > major_base

    for path, events in diff.items():
        if any(fnmatch.fnmatchcase(path, pattern) for pattern in catalog["vector_globs"]):
            add("VEC-1", events[0], "Golden-vector path changed; RADIX review required.")
        is_core = path in boundary_text_paths or any(fnmatch.fnmatchcase(path, g) for g in core_globs)
        for event in events:
            if event.side != "+":
                continue
            for rule_id, pattern in PATTERNS.items():
                applicable = (path.endswith(".md") and not path.startswith("tools/drift/")) if rule_id == "WORD-CLAIM-1" else is_core
                if applicable and re.search(pattern, event.text, re.I):
                    add(rule_id, event)

        if path in addresses:
            old, new = read(base, path), read(head, path)
            if not bumped and projection(old, "format") != projection(new, "format"):
                add("VER-FORMAT-1", ast_event(path, "format"), "Protected encoding/range AST changed without a specification MAJOR increase.")
            # Any field-annotation change is a bounded-schema review candidate.
            if projection(old, "fields") != projection(new, "fields"):
                add("BND-G-1", ast_event(path, "fields"), "Core address field schema changed.")
            if path == "rpp/address_canonical.py":
                for rule_id, kind in [("VER-RADIUS-API", "radius_api"), ("VER-RADIUS-ENC", "radius_enc"), ("VER-RADIUS-TIES", "radius_ties")]:
                    if projection(old, kind) != projection(new, kind):
                        add(rule_id, ast_event(path, kind), "Radius contract AST changed; inspect the diff against both cited layers.")

        if path == "rpp/network.py":
            old, new = read(base, path), read(head, path)
            if projection(old, "backbone") != projection(new, "backbone"):
                add("NET-INV-2", ast_event(path, "backbone"), "Backbone coverage constants changed.")
            if projection(old, "phi_write") != projection(new, "phi_write"):
                add("NET-INV-1", ast_event(path, "phi_write"), "A phi-attribute write changed; runtime monotonicity needs review.")

    # Guard verbatim source passages by their occurrence counts, not fixed line numbers.
    # Review only a passage present in base and changed/deleted in head. Historical ranges
    # predating the frozen source do not inherit findings for unrelated text.
    for guard in catalog["guards"]:
        path, text = guard["path"], guard["text"]
        if path not in diff or (guard["rule_id"] == "VER-FORMAT-1" and bumped):
            continue
        old, new = read(base, path), read(head, path)
        normalized = normalize(text)
        if normalize(old).count(normalized) > normalize(new).count(normalized):
            witnesses = [e for e in diff[path] if e.side == "-" and normalize(e.text)
                         and normalize(e.text) in normalized]
            event = witnesses[0] if witnesses else first_event(path, "-")
            add(guard["rule_id"], event, "Referenced source passage changed or removed.")

    # Newly recorded ruled paragraphs are watched even when they were not part
    # of the original 243-entry scan. Removing their approved wording still needs
    # review; the historical-transition permission never blesses future edits.
    for recorded in catalog["rulings"]["findings"]:
        if recorded["rule_id"] != "BND-F-2":
            continue
        passage = recorded["after"]
        path, text = passage["path"], normalize(passage["text"])
        if path in diff and normalize(read(base, path)).count(text) > normalize(read(head, path)).count(text):
            witnesses = [event for event in diff[path] if event.side == "-" and normalize(event.text)
                         and normalize(event.text) in text]
            add("BND-F-2", witnesses[0] if witnesses else first_event(path, "-"),
                "Ruled passage changed or removed; prior decision " + recorded["decision_id"] + " is not a future waiver.")

    try:
        baseline_events = boundary_review(diff, read, base, head, catalog, add, first_event, exists)
    except (SyntaxError, RecursionError) as exc:
        raise ToolError("changed in-scope Python source does not parse for passage extraction") from exc

    def open_items(items):
        result = []
        for item in items:
            changed = False
            for passage in item["passages"]:
                path, text = passage["path"], normalize(passage["text"])
                if path not in diff:
                    continue
                if normalize(read(base, path)).count(text) > normalize(read(head, path)).count(text):
                    events = [e for e in diff[path] if e.side == "-" and normalize(e.text)
                              and normalize(e.text) in text]
                    witness = events[0] if events else first_event(path, "-")
                    add(item["rule_id"], witness, item["description"] + "; " + item["status"])
                    changed = True
            result.append(dict(item, change="changed" if changed else "unchanged"))
        return result

    steward_items = open_items(catalog["steward_items"])
    advisories = open_items(catalog["advisories"])

    # Identical findings can arise through independent guards; retain distinct evidence.
    unique = {json.dumps(f, sort_keys=True, ensure_ascii=True): f for f in findings}
    findings = sorted(unique.values(), key=lambda f: (
        SEVERITY[f["severity"]], f["rule_id"], f["path"], f["line"], f["evidence"], f["source"]
    ))
    counts = Counter(f["severity"].lower() for f in findings)
    return {
        "base": base, "head": head,
        "catalog_sha256": hashlib.sha256(json.dumps(
            catalog, sort_keys=True, ensure_ascii=True, separators=(",", ":")
        ).encode("utf-8")).hexdigest(),
        "findings": findings,
        "baseline_events": baseline_events,
        "steward_items": steward_items,
        "advisories": advisories,
        "rulings": catalog["rulings"],
        "summary": {"high": counts["high"], "medium": counts["medium"], "low": counts["low"],
                    "rules_run": len(rules), "rules_not_checkable": catalog["rules_not_checkable"],
                    "open_baselines": sum(item["status"] == UNRESOLVED for item in catalog["baselines"]),
                    "ruled_baselines": sum(item["status"] == RULED for item in catalog["baselines"]),
                    "open_steward_items": sum(item["status"] == UNRESOLVED for item in steward_items),
                    "decided_steward_items": sum(item["status"] == DECIDED for item in steward_items),
                    "open_advisories": sum(item["status"] == UNRESOLVED for item in advisories),
                    "decided_advisories": sum(item["status"] == DECIDED for item in advisories),
                    "recorded_ruling_findings": len(catalog["rulings"]["findings"])},
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
    lines += ["## Open Boundary F baseline", "",
              f"{summary['open_baselines']} review-pending/open; {summary['ruled_baselines']} ruled; all IMPOSED.",
              "Route: [RFC] via TR under GOVERNANCE.md:63-71. No entry is marked accepted.", ""]
    lines += ["## Recorded RADIX rulings", "", "These exact historical consequences are recorded, not blanket waivers for future edits.", ""]
    for finding in report["rulings"]["findings"]:
        decision = report["rulings"]["decisions"][finding["decision_id"]]
        body = (f"{finding['severity']} {finding['rule_id']} {finding['path']}:{finding['line']}\n"
                f"{finding['decision_id']} — {decision['path']}:{decision['line']}")
        lines += ["<pre>" + html.escape(body) + "</pre>", ""]
    if report["baseline_events"]:
        lines += ["## Baseline movement and text changes", "",
                  "Moves preserve normalized identity and do not count as drift findings.", ""]
        for event in report["baseline_events"]:
            lines += ["<pre>" + html.escape(json.dumps(event, sort_keys=True, ensure_ascii=False, indent=2)) + "</pre>", ""]
    for key, title in [("steward_items", "Steward items (open and decided)"),
                       ("advisories", "Wording/edge advisories (open and decided)")]:
        lines += ["## " + title, "",
                  "Unchanged items do not affect exit status; changed source passages appear as diff findings.", ""]
        for item in report[key]:
            if item["change"] != "unchanged":
                continue
            body = f"{item['rule_id']} {item['severity']} ({item['tag']})\n{item['description']}\n{item['status']}\n{item['route']}"
            if "decision_id" in item:
                decision = report["rulings"]["decisions"][item["decision_id"]]
                body += f"\n{item['decision_id']}: {decision['path']}:{decision['line']}"
            for source in item["passages"]:
                body += f"\n{source['path']}:{source['line']}\n{source['text']}"
            lines += ["<pre>" + html.escape(body) + "</pre>", ""]
    return "\n".join(lines)


def write_reports(report, output_dir):
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "drift-report.json").write_text(
        json.dumps(report, sort_keys=True, indent=2, ensure_ascii=True) + "\n", encoding="utf-8", newline="\n"
    )
    (output_dir / "drift-report.md").write_text(markdown(report), encoding="utf-8", newline="\n")
