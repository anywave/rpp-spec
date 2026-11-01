"""Rebuild the complete verified Boundary F baseline from immutable Git blobs."""

import argparse
import json
from pathlib import Path
import sys

from .checker import DATA, ToolError, blob, git, resolve
from .passages import classify, digest, extract, in_scope
from .rulings import DECIDED, REVISION, RULED, apply_rulings


STATUS = "unresolved - steward decision (RADIX)"
ROUTE = "[RFC] via TR; GOVERNANCE.md:63-71; DECISIONS.md absent at source revision"


def scan(root, revision):
    revision = resolve(root, revision)
    paths = git(root, "ls-tree", "-r", "-z", "--name-only", revision).split(b"\0")
    scanned = sorted(p.decode("utf-8") for p in paths if p and in_scope(p.decode("utf-8")))
    entries = []
    for path in scanned:
        for passage in extract(path, blob(root, revision, path)):
            rule_id = classify(passage)
            if rule_id:
                entries.append(dict(
                    id=f"F-BASE-{len(entries) + 1:04}", path=path, line=passage.line,
                    end=passage.end, kind=passage.kind, text=passage.text, sha256=passage.sha256,
                    rule_id=rule_id, tag="IMPOSED", status=STATUS, route=ROUTE,
                ))
    return scanned, entries


def source(root, revision, path, first, last=None, text=None):
    lines = blob(root, revision, path).splitlines()
    passage = "\n".join(lines[first - 1:(last or first)])
    if text is not None:
        if text not in passage:
            raise ValueError(f"anchor not found in its source citation: {path}:{first}")
        passage = text
    return dict(path=path, line=first, end=last or first, text=passage, sha256=digest(passage))


def revise_catalog(root):
    # Reconstruct from the immutable pre-overlay catalog, never from partially
    # edited current metadata. The source scan itself remains pinned to 0a12c8d.
    catalog = json.loads(blob(root, REVISION, "tools/drift/catalog.json"))
    revision = catalog["source_revision"]
    scanned, entries = scan(root, revision)
    catalog["scanned_paths"] = scanned
    catalog["baselines"] = entries
    catalog["normalization"] = "Git blob text; LF; Unicode NFC; whitespace collapsed; trimmed; SHA-256 of UTF-8"
    catalog["boundary_text_paths"] = catalog.pop("core_specs", catalog.get("boundary_text_paths", []))
    catalog.pop("substrate_globs", None)

    anchors = [
        source(root, revision, "spec/SPEC.md", 56),
        source(root, revision, "spec/SPEC.md", 90),
        source(root, revision, "spec/SPEC.md", 99),
        source(root, revision, "spec/NETWORK.md", 225,
               text="Software implementations MUST enforce equivalent TTL semantics."),
        source(root, revision, "spec/SPINTRONIC.md", 19,
               text="Implementations MUST enforce it to the best of the runtime's ability, but cannot provide the physical guarantee."),
        source(root, revision, "spec/SPINTRONIC.md", 275),
        source(root, revision, "spec/SPINTRONIC.md", 277),
    ]
    catalog["software_must_anchors"] = anchors

    rules = {r["rule_id"]: r for r in catalog["rules"]}

    def rule(rule_id, path, line, severity, method, positive, negative, tag="IMPOSED", more=""):
        data = source(root, revision, path, line)
        rules[rule_id] = dict(rule_id=rule_id, source=f"{path}:{line}" + more,
                             severity=severity, tag=tag, quote=data["text"], method=method,
                             positive=positive, negative=negative)

    rule("BND-F-1", "BOUNDARIES.md", 98, "HIGH",
         "New/changed in-scope passage: physics term plus normative marker, no qualifier; also HIGH when a normalized software-MUST anchor disappears. Classify by passage, never by file.",
         "Add an unqualified MUST plus T2 to a Markdown passage or Python comment.",
         "Add a qualified On spintronic hardware MUST passage (MEDIUM only), or move an unchanged passage.")
    rule("BND-F-2", "spec/SPINTRONIC.md", 21, "MEDIUM",
         "Any other new/changed in-scope physics-term passage. No semantic disclaimer/quantum/coherence inference. Report only.",
         "Add a physical invariant sentence to a root Markdown document.",
         "Change only quantum/coherence/hardware wording without a listed physics term.")
    rule("BND-F-BASELINE-REMOVED", "GOVERNANCE.md", 67, "MEDIUM",
         "Lost baseline identity emits MEDIUM unless its unique exact edit/unchanged-line component pairs it with one same-path, same-kind, same-owner physics replacement. Splits, merges, changed renames and ambiguous correspondence emit the stricter removal finding; equal-hash moves/rewrapping do not.",
         "Replace a known baseline passage with an ordinary nonphysics note.",
         "Move its normalized-equivalent text, including rewrapping/NFC changes.")
    rule("VER-RADIUS-API", "spec/RPP-CANONICAL-v2.md", 229, "HIGH",
         "Ra-Canonical v2 RPPAddress.radius only: normalized float 0.0–1.0 validation/annotation source and AST changes. Not GEOMETRY minor radius, Mobius32 or unbundled parl.",
         "Change RPPAddress radius guard upper bound to 2.0.",
         "Change a GEOMETRY minor-radius description.", tag="SOURCED",
         more="; spec/RPP-CANONICAL-v2.md:219,362; rpp/address_canonical.py:253")
    rule("VER-RADIUS-ENC", "spec/RPP-CANONICAL-v2.md", 239, "HIGH",
         "Ra-Canonical v2 encoded radius byte, bits [20:13], 0–255: round(radius*255) & 0xFF. HDL ports carry the byte. Half-to-even is a separate IMPOSED clause.",
         "Change the canonical multiplier 255 to 127.",
         "Edit only a noncanonical radius example.", tag="SOURCED",
         more="; spec/RPP-CANONICAL-v2.md:168-170,292; rpp/address_canonical.py:308")
    rule("VER-RADIUS-TIES", "spec/RPP-CANONICAL-v2.md", 239, "HIGH",
         "IMPOSED Python round half-to-even clause for the v2 encoder. Encoder AST or source quantization-expression change requires review; vectors 1/510→0, 5/510→2, 0.5→128.",
         "Replace round(radius*255) with int(radius*255+0.5).",
         "Change only an encoder comment.")

    def item(rule_id, severity, description, refs):
        passages = [source(root, revision, *ref) for ref in refs]
        rule(rule_id, refs[0][0], refs[0][1], severity,
             "Changed normalized steward/advisory source passage is a diff finding; unchanged item is displayed separately without affecting exit status.",
             "Edit the cited source passage.", "Edit an unrelated source passage.")
        return dict(rule_id=rule_id, severity=severity, tag="IMPOSED", status=STATUS,
                    route=ROUTE, description=description, passages=passages)

    catalog["steward_items"] = [
        item("STEWARD-TTL-1", "MEDIUM", "Shell-0 software TTL: session-scoped software text versus 25 ns enforced by rpp/ccqpsg.py and continuity.py.",
             [("spec/SPEC.md", 94), ("spec/CCQPSG.md", 108), ("rpp/ccqpsg.py", 151, 152), ("rpp/continuity.py", 46)]),
        item("STEWARD-T2-1", "MEDIUM", "Device T2 upper bound ≤25 ns versus destination requirement ≥25 ns.",
             [("spec/SPINTRONIC.md", 288), ("spec/SPINTRONIC.md", 311)]),
        item("STEWARD-CLAIM-1", "MEDIUM", "Unqualified physical timeout docstring versus prohibition on conventional-hardware physical-enforcement claims.",
             [("rpp/continuity.py", 276, 277), ("spec/SPINTRONIC.md", 278)]),
        item("STEWARD-RADIUS-DERIVATION", "MEDIUM", "Conflicting v1→v2 radius derivation: fixed 0.5 versus shell/3.0.",
             [("spec/RPP-CANONICAL-v2.md", 347), ("spec/ADDRESSING-LAYERS.md", 142)]),
    ]
    catalog["advisories"] = [
        item("WORD-RADIUS-EDGE", "LOW", "The source radius guard accepts True and -0.0; to_uri emits r:-0.00, which the from_uri regex refuses. Report only, no source fix.",
             [("rpp/address_canonical.py", 253, 254), ("rpp/address_canonical.py", 423), ("rpp/address_canonical.py", 430)]),
        item("WORD-RADIUS-1", "LOW", "Label API-normalized versus encoded radius at all six cited wording sites; do not edit the specification.",
             [("VERSION_POLICY.md", 83), ("VERSION_POLICY.md", 70), ("VERSION_POLICY.md", 74),
              ("spec/README.md", 92), ("spec/PMA-SCHEMA-v1.md", 116), ("spec/ADDRESSING-LAYERS.md", 114)]),
    ]

    # The amended radius scope excludes generic radius-related text in GEOMETRY,
    # Mobius32 and parl. Keep existing format guards, replace the radius clauses.
    catalog["guards"] = [g for g in catalog["guards"] if g["rule_id"] not in {
        "VER-RADIUS-API", "VER-RADIUS-ENC", "VER-RADIUS-TIES", "WORD-RADIUS-1"
    }]
    for rule_id, path, first, last in [
        ("VER-RADIUS-API", "spec/RPP-CANONICAL-v2.md", 219, 219),
        ("VER-RADIUS-API", "spec/RPP-CANONICAL-v2.md", 229, 230),
        ("VER-RADIUS-API", "spec/RPP-CANONICAL-v2.md", 362, 362),
        ("VER-RADIUS-ENC", "spec/RPP-CANONICAL-v2.md", 168, 170),
        ("VER-RADIUS-ENC", "spec/RPP-CANONICAL-v2.md", 239, 239),
        ("VER-RADIUS-ENC", "spec/RPP-CANONICAL-v2.md", 292, 292),
        ("VER-RADIUS-TIES", "spec/RPP-CANONICAL-v2.md", 239, 239),
    ]:
        data = source(root, revision, path, first, last)
        catalog["guards"].append(dict(rule_id=rule_id, path=path, text=data["text"]))
    catalog["rules"] = list(rules.values())
    apply_rulings(catalog, lambda sha, path: blob(root, sha, path))
    DATA.write_text(json.dumps(catalog, ensure_ascii=True, indent=2) + "\n", encoding="utf-8", newline="\n")
    return catalog


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    try:
        catalog = revise_catalog(Path.cwd())
    except (ToolError, OSError, UnicodeError, ValueError, SyntaxError, RecursionError):
        print("snapshot: tool error: invalid ruling source or catalog", file=sys.stderr)
        return 2
    print(f"SUMMARY scanned_paths={len(catalog['scanned_paths'])} "
          f"open_baselines={sum(e['status'] == STATUS for e in catalog['baselines'])} "
          f"ruled_baselines={sum(e['status'] == RULED for e in catalog['baselines'])} "
          f"open_steward_items={sum(e['status'] != DECIDED for e in catalog['steward_items'])} "
          f"open_advisories={sum(e['status'] != DECIDED for e in catalog['advisories'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
