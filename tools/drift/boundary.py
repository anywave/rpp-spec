"""Passage-level diff review, normalized baseline movement, and MUST anchors."""

from collections import defaultdict
import hashlib
from bisect import bisect_right

from .passages import classify, digest, extract, in_scope, normalize


def replacement_pairs(old, new, diff, paired, used):
    """Exact edit/unchanged-line graph; never infer replacement from hunk proximity.

    All passage kinds, including nonphysics and already matched units, participate
    in the graph. Only a unique 1:1 same-owner, same-kind component is a rewrite.
    Splits/merges or uncertain cross-container correspondence retain a tombstone.
    """
    size = len(old)
    parent = list(range(size + len(new)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def join(i, j):
        a, b = find(i), find(size + j)
        if a != b:
            parent[b] = a

    by_path_old, by_path_new = defaultdict(list), defaultdict(list)
    for i, p in enumerate(old):
        by_path_old[p.path].append(i)
    for j, p in enumerate(new):
        by_path_new[p.path].append(j)
    for path in sorted(set(by_path_old) | set(by_path_new)):
        edits = sorted({e.edit for e in diff[path] if e.edit is not None})
        edit_starts = [item[0] for item in edits]
        old_lines = defaultdict(list)
        for index in by_path_old[path]:
            for coordinate in range(old[index].line, old[index].end + 1):
                old_lines[coordinate].append(index)
        new_lines = defaultdict(list)
        for j in by_path_new[path]:
            for line in range(new[j].line, new[j].end + 1):
                new_lines[line].append(j)

        # Unchanged lines map by exact edit coordinates, not textual similarity.
        for i in by_path_old[path]:
            for line in range(old[i].line, old[i].end + 1):
                delta, deleted = 0, False
                position = bisect_right(edit_starts, line) - 1
                if position >= 0:
                    start, end, new_start, new_end = edits[position]
                    deleted = start <= line < end
                    delta = new_end - end
                if not deleted:
                    for j in new_lines.get(line + delta, []):
                        join(i, j)

        # A single uninterrupted edit run may connect several actual passages.
        # Cardinality below rejects that ambiguity rather than sharing scope.
        for start, end, new_start, new_end in edits:
            left = sorted({i for line in range(start, end) for i in old_lines.get(line, ())})
            right = sorted({j for line in range(new_start, new_end) for j in new_lines.get(line, ())})
            if left and right:
                # A star has the same connected component as the complete
                # bipartite graph, without quadratic work on a large edit run.
                for i in left:
                    join(i, right[0])
                for j in right[1:]:
                    join(left[0], j)

    components = defaultdict(lambda: ([], []))
    for i in range(size):
        components[find(i)][0].append(i)
    for j in range(len(new)):
        components[find(size + j)][1].append(j)
    result = {}
    for left, right in components.values():
        if len(left) != 1 or len(right) != 1:
            continue
        i, j = left[0], right[0]
        if i in paired or j in used:
            continue
        if (old[i].path, old[i].kind, old[i].context) != (new[j].path, new[j].kind, new[j].context):
            continue
        result[i] = j
    return result


def approved_transition(index, old, new, replacements, read, base, head, catalog, exists):
    """Recognize only an exact ruled transition, never a decided file or rule."""
    target = new[index]
    for finding in catalog["rulings"]["findings"]:
        if finding["rule_id"] != "BND-F-2" or finding["path"] != target.path:
            continue
        if finding["after"]["sha256"] != target.sha256:
            continue
        same_new = [p for p in new if p.path == target.path and p.sha256 == target.sha256]
        same_old = [p for p in old if p.path == target.path and p.sha256 == target.sha256]
        if len(same_new) != 1 or same_old:
            continue
        before = finding["before"]
        if before is None:
            if exists(base, target.path):
                continue
            current_file = hashlib.sha256(read(head, target.path).encode("utf-8")).hexdigest()
            if current_file != finding["created_file_sha256"]:
                continue
            return True
        for old_index, new_index in replacements.items():
            if new_index == index and old[old_index].sha256 == before["sha256"]:
                return True
    return False


def review(diff, read, base, head, catalog, add, first_event, exists):
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

    replacements = replacement_pairs(old, new, diff, paired, used)
    for j, p in enumerate(new):
        if j in used:
            continue
        rule_id = classify(p)
        if rule_id and not (rule_id == "BND-F-2" and approved_transition(j, old, new, replacements, read, base, head, catalog, exists)):
            add(rule_id, event(p, "+"), f"{p.kind}; normalized passage SHA-256 {p.sha256}")

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
            if (p.path, p.line, p.end, p.text, p.context) != (target.path, target.line, target.end, target.text, target.context):
                baseline_events.append(dict(data, change="moved", new_path=target.path,
                                            new_line=target.line, new_sha256=target.sha256,
                                            movement="position" if (p.path, p.line) != (target.path, target.line) else "normalized_text_or_owner"))
            continue

        target = new[replacements[i]] if i in replacements else None
        physics_replacement = target is not None and classify(target) is not None
        changed = target is not None
        baseline_events.append(dict(data, change="changed" if changed else "removed",
                                    replacement_sha256=[target.sha256] if target is not None else []))
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
