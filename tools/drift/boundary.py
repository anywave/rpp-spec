"""Passage-level diff review, normalized baseline movement, and MUST anchors."""

from collections import defaultdict

from .passages import classify, digest, extract, in_scope, normalize


def review(diff, read, base, head, catalog, add, first_event):
    old, new = [], []
    for path in diff:
        if in_scope(path):
            old.extend(extract(path, read(base, path)))
            new.extend(extract(path, read(head, path)))
    old.sort(key=lambda p: (p.path, p.line, p.kind))
    new.sort(key=lambda p: (p.path, p.line, p.kind))

    def event(passage, side):
        return first_event(passage.path, side, passage.line, passage.end)

    # Prefer same-path equal hashes, then recognize moves between scanned paths.
    # No similarity matching is used to infer correspondence between changed text.
    candidates = defaultdict(list)
    for i, p in enumerate(new):
        candidates[p.sha256].append(i)
    paired, used = {}, set()
    for same_path in (True, False):
        for i, p in enumerate(old):
            if i in paired:
                continue
            for j in candidates[p.sha256]:
                if j not in used and (not same_path or new[j].path == p.path):
                    paired[i] = j
                    used.add(j)
                    break

    known = defaultdict(list)
    for entry in catalog["baselines"]:
        if digest(entry["text"]) != entry["sha256"]:
            raise ValueError("Boundary F normalized baseline checksum mismatch")
        known[entry["sha256"]].append(entry)
    allocated = set()
    entries = {}
    for i, p in enumerate(old):
        choices = sorted(known[p.sha256], key=lambda b: (b["path"] != p.path, b["id"]))
        for entry in choices:
            if entry["id"] not in allocated:
                entries[i] = entry
                allocated.add(entry["id"])
                break

    added = [p for j, p in enumerate(new) if j not in used]
    for p in added:
        rule_id = classify(p)
        if rule_id:
            add(rule_id, event(p, "+"), f"{p.kind}; normalized passage SHA-256 {p.sha256}")

    def hunk_events(p, side):
        return {e.evidence.split("\n", 1)[0] for e in diff[p.path]
                if e.side == side and p.line <= e.line <= p.end}

    baseline_events = []
    for i, p in enumerate(old):
        if i not in entries:
            continue
        entry = entries[i]
        detail = (f"{entry['id']}; baseline source {entry['path']}:{entry['line']} (old line hint); "
                  f"old normalized SHA-256 {entry['sha256']}; {entry['status']}; {entry['route']}")
        data = dict(baseline_id=entry["id"], old_path=p.path, old_line=p.line,
                    old_line_hint=entry["line"], old_sha256=entry["sha256"], tag="IMPOSED",
                    status=entry["status"], route=entry["route"])
        if i in paired:
            target = new[paired[i]]
            if p.path != target.path or p.line != target.line:
                baseline_events.append(dict(data, change="moved", new_path=target.path,
                                            new_line=target.line, new_sha256=target.sha256))
            continue

        # A rewrite is linked only through an exact Git hunk identity. The checker
        # makes no semantic correspondence claim for text with a different hash.
        hunks = hunk_events(p, "-")
        replacements = [q for q in added if q.path == p.path and hunks & hunk_events(q, "+")]
        physics_replacement = any(classify(q) for q in replacements)
        changed = any(e.side == "+" and e.evidence.split("\n", 1)[0] in hunks for e in diff[p.path])
        baseline_events.append(dict(data, change="changed" if changed else "removed",
                                    replacement_sha256=sorted(q.sha256 for q in replacements)))
        if not physics_replacement:
            add("BND-F-BASELINE-REMOVED", event(p, "-"), detail)

    for anchor in catalog["software_must_anchors"]:
        path, text = anchor["path"], normalize(anchor["text"])
        if path not in diff:
            continue
        if normalize(read(base, path)).count(text) > normalize(read(head, path)).count(text):
            events = [e for e in diff[path] if e.side == "-" and normalize(e.text)
                      and normalize(e.text) in text]
            witness = events[0] if events else first_event(path, "-")
            add("BND-F-1", witness,
                f"Software-MUST anchor disappeared: {path}:{anchor['line']}; {anchor['text']}")
    return sorted(baseline_events, key=lambda e: (e["baseline_id"], e["change"], e["old_path"], e["old_line"]))
