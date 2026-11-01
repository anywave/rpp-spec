"""Exact CX-006 ruling overlay; the original scan and unruled entries stay frozen."""

from copy import deepcopy
import hashlib

from .passages import digest, extract


REVISION = "5677ea21b5ba3320109dc7dcb61d4b4c22b5881a"
BEFORE = "275a115efad591304221e832c194a75f7749f9b0"
RULED = "ruled - RADIX CX-006"
DECIDED = "decided - RADIX CX-006"
BASELINE_DECISIONS = {"F-BASE-0038": "D4", "F-BASE-0049": "D2", "F-BASE-0213": "D3", "F-BASE-0221": "D3"}
ITEM_DECISIONS = {"STEWARD-TTL-1": "D2", "STEWARD-T2-1": "D3", "STEWARD-CLAIM-1": "D4", "STEWARD-RADIUS-DERIVATION": "D1", "WORD-RADIUS-1": "A1"}
DECISION_LINES = {"D1": 19, "D2": 58, "D3": 76, "D4": 86, "A1": 170}
FINDING_KEYS = [
    ("VER-FORMAT-1", "HIGH", "VERSION_POLICY.md", 70, "A1"),
    ("VER-FORMAT-1", "HIGH", "VERSION_POLICY.md", 83, "A1"),
    ("BND-F-2", "MEDIUM", "DECISIONS.md", 78, "D3"),
    ("BND-F-2", "MEDIUM", "spec/SPINTRONIC.md", 288, "D3"),
    ("BND-F-2", "MEDIUM", "spec/SPINTRONIC.md", 311, "D3"),
    ("BND-F-BASELINE-REMOVED", "MEDIUM", "rpp/continuity.py", 276, "D4"),
    ("BND-F-BASELINE-REMOVED", "MEDIUM", "spec/CCQPSG.md", 108, "D2"),
    ("STEWARD-CLAIM-1", "MEDIUM", "rpp/continuity.py", 276, "D4"),
    ("STEWARD-RADIUS-DERIVATION", "MEDIUM", "spec/ADDRESSING-LAYERS.md", 142, "D1"),
    ("STEWARD-RADIUS-DERIVATION", "MEDIUM", "spec/RPP-CANONICAL-v2.md", 347, "D1"),
    ("STEWARD-T2-1", "MEDIUM", "spec/SPINTRONIC.md", 288, "D3"),
    ("STEWARD-T2-1", "MEDIUM", "spec/SPINTRONIC.md", 311, "D3"),
    ("STEWARD-TTL-1", "MEDIUM", "spec/CCQPSG.md", 108, "D2"),
    ("STEWARD-TTL-1", "MEDIUM", "spec/SPEC.md", 94, "D2"),
    ("WORD-RADIUS-1", "LOW", "VERSION_POLICY.md", 70, "A1"),
    ("WORD-RADIUS-1", "LOW", "VERSION_POLICY.md", 74, "A1"),
    ("WORD-RADIUS-1", "LOW", "VERSION_POLICY.md", 83, "A1"),
    ("WORD-RADIUS-1", "LOW", "spec/ADDRESSING-LAYERS.md", 114, "A1"),
    ("WORD-RADIUS-1", "LOW", "spec/PMA-SCHEMA-v1.md", 116, "A1"),
    ("WORD-RADIUS-1", "LOW", "spec/README.md", 92, "A1"),
]


def passage_record(passage):
    return dict(path=passage.path, line=passage.line, end=passage.end,
                kind=passage.kind, text=passage.text, sha256=passage.sha256)


def containing(read, revision, path, line):
    return next(p for p in extract(path, read(revision, path)) if p.line <= line <= p.end)


def section(read, code):
    text = read(REVISION, "DECISIONS.md")
    lines = text.split("\n")
    first = DECISION_LINES[code]
    assert lines[first - 1].startswith(f"### [RFC] CX-006-{code} ")
    end = next((i for i in range(first, len(lines)) if lines[i].startswith("### ")), len(lines))
    value = "\n".join(lines[first - 1:end]).rstrip()
    return dict(id="CX-006-" + code, path="DECISIONS.md", line=first, end=end,
                text=value, sha256=digest(value), authority="RADIX", date="2026-10-31")


def ruling_route(code):
    return f"[RFC] CX-006-{code}; DECISIONS.md:{DECISION_LINES[code]}; RADIX 2026-10-31"


def apply_rulings(catalog, read):
    """Overlay only authorized entries on a freshly reconstructed original scan."""
    decisions = {"CX-006-" + code: section(read, code) for code in DECISION_LINES}
    catalog["catalog_revision"] = 2
    catalog["rulings"] = dict(source_revision=REVISION, original_range_base=BEFORE,
                              authority="RADIX", authorization="CX-007; trellis-channel c098c20e; inbox blob 1b01db5d154c6b237324f7fe5ad779b3ea1154c7",
                              decisions=decisions)
    for entry in catalog["baselines"]:
        if entry["id"] not in BASELINE_DECISIONS:
            continue
        original = deepcopy(entry)
        current = containing(read, REVISION, entry["path"], entry["line"])
        assert current.kind == entry["kind"]
        entry.update(passage_record(current), status=RULED, original=original,
                     source_revision=REVISION, decision_id="CX-006-" + BASELINE_DECISIONS[entry["id"]],
                     route=ruling_route(BASELINE_DECISIONS[entry["id"]]))

    # These two wording substitutions are the entire allowed guard change.
    for guard in catalog["guards"]:
        if guard["path"] != "VERSION_POLICY.md" or guard["rule_id"] != "VER-FORMAT-1":
            continue
        original = deepcopy(guard)
        if "(radius << 13)" in guard["text"]:
            expected = guard["text"].replace("(radius << 13)", "(r_enc << 13)")
            expected = expected.replace("| Radius decoding | `(address >> 13) & 0xFF` |", "| Radius decoding | `r_enc = (address >> 13) & 0xFF; radius = r_enc / 255.0` |")
        elif "| Radius | 0 | 255 | Normalized 0-1 |" in guard["text"]:
            expected = guard["text"].replace("Normalized 0-1", "Encoded byte; API radius = byte / 255 in 0–1")
            old_ranges = [line.split("|")[1:4] for line in guard["text"].split("\n")]
            new_ranges = [line.split("|")[1:4] for line in expected.split("\n")]
            assert old_ranges == new_ranges, "A1 cannot change fields or ranges"
        else:
            assert guard["text"] in read(REVISION, guard["path"]), "A1 cannot change field widths or positions"
            continue
        assert expected in read(REVISION, guard["path"]), "A1 guard differs beyond approved wording"
        guard.update(text=expected, original=original, source_revision=REVISION, decision_id="CX-006-A1")

    for group in ("steward_items", "advisories"):
        for item in catalog[group]:
            code = ITEM_DECISIONS.get(item["rule_id"])
            if code is None:
                continue
            original = deepcopy(item)
            sources = []
            for source in item["passages"]:
                line, end = source["line"], source["end"]
                if item["rule_id"] == "WORD-RADIUS-1" and source["path"] == "VERSION_POLICY.md" and line == 83:
                    line = end = 85
                elif item["rule_id"] == "STEWARD-CLAIM-1" and source["path"] == "rpp/continuity.py" and line == 276:
                    end = 278
                elif item["rule_id"] == "STEWARD-RADIUS-DERIVATION" and source["path"] == "spec/RPP-CANONICAL-v2.md":
                    end = 350
                value = "\n".join(read(REVISION, source["path"]).split("\n")[line - 1:end])
                sources.append(dict(path=source["path"], line=line, end=end, text=value, sha256=digest(value)))
            item.update(passages=sources, status=DECIDED, original=original,
                        source_revision=REVISION, decision_id="CX-006-" + code, route=ruling_route(code))

    findings = []
    for rule_id, severity, path, line, code in FINDING_KEYS:
        target_line = 85 if path == "VERSION_POLICY.md" and line == 83 else line
        after = passage_record(containing(read, REVISION, path, target_line))
        before_text = read(BEFORE, path)
        before = passage_record(containing(read, BEFORE, path, line)) if before_text else None
        finding = dict(rule_id=rule_id, severity=severity, path=path, line=line,
                       decision_id="CX-006-" + code, before=before, after=after)
        if before is None:
            finding["created_file_sha256"] = hashlib.sha256(read(REVISION, path).encode("utf-8")).hexdigest()
        findings.append(finding)
    catalog["rulings"]["findings"] = findings
    return catalog
