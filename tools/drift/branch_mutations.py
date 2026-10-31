"""Trusted coordinator mutants and their positive/clean test pairs.

This module is used only by the test fixture and mutation runner. Production
checker modules never inspect mutation environment variables or import it.
Every source replacement has an exact, unique anchor; stale anchors are errors.
"""

import importlib
from pathlib import Path


INTERACTION = "tools/drift/tests/test_boundary_interactions.py::"
GIT = "tools/drift/tests/test_git_boundaries.py::"
PHYSICAL_CONTROL = INTERACTION + "test_same_passage_physical_rewrite_is_not_baseline_removal"
WORD_CONTROL = INTERACTION + "test_valid_word_only_markdown_is_reviewed"


BRANCH_MUTANTS = {
    "restore_hunk_scope": {
        "module": "boundary",
        "replacements": [("    replacements = replacement_pairs(old, new, diff, paired, used)\n", '''    replacements = {}
    for i, p in enumerate(old):
        if i in paired:
            continue
        old_headers = {e.evidence.split("\\n", 1)[0] for e in diff[p.path]
                       if e.side == "-" and p.line <= e.line <= p.end}
        for j, q in enumerate(new):
            if j in used or q.path != p.path or classify(q) is None:
                continue
            new_headers = {e.evidence.split("\\n", 1)[0] for e in diff[q.path]
                           if e.side == "+" and q.line <= e.line <= q.end}
            if old_headers & new_headers:
                replacements[i] = j
                break
''')],
        "positive": INTERACTION + "test_removed_baseline_not_hidden_by_independent_same_hunk_physics[cx001_003_repro]",
        "control": INTERACTION + "test_removed_baseline_not_hidden_by_independent_same_hunk_physics[control]",
        "meaning": "Restore the former whole-hunk physics borrowing bug.",
    },
    "omit_unchanged_line_edges": {
        "module": "boundary",
        "replacements": [("        for i in by_path_old[path]:\n", "        for i in ():\n")],
        "positive": INTERACTION + "test_physics_sentence_appended_to_same_passage_is_physical_rewrite",
        "control": PHYSICAL_CONTROL,
        "meaning": "Ignore unchanged source lines that establish insertion ownership.",
    },
    "omit_atomic_edit_edges": {
        "module": "boundary",
        "replacements": [("        for start, end, new_start, new_end in edits:\n            left =", "        for start, end, new_start, new_end in ():\n            left =")],
        "positive": PHYSICAL_CONTROL,
        "control": INTERACTION + "test_physics_sentence_appended_to_same_passage_is_physical_rewrite",
        "meaning": "Ignore exact replacement blocks when all old passage lines change.",
    },
    "allow_ambiguous_components": {
        "module": "boundary",
        "replacements": [("        if len(left) != 1 or len(right) != 1:\n", "        if not left or not right:\n")],
        "positive": INTERACTION + "test_two_baselines_merged_is_conservative_identity_loss",
        "control": PHYSICAL_CONTROL,
        "meaning": "Borrow one new merged physics unit for the first old baseline.",
    },
    "ignore_passage_kind": {
        "module": "boundary",
        "replacements": [("        if (old[i].path, old[i].kind, old[i].context) != (new[j].path, new[j].kind, new[j].context):\n", "        if (old[i].path, old[i].context) != (new[j].path, new[j].context):\n")],
        "positive": INTERACTION + "test_docstring_and_comment_replacement_kinds[changed_kind-docstring]",
        "control": INTERACTION + "test_docstring_and_comment_replacement_kinds[same_kind_rewrite-docstring]",
        "meaning": "Treat a comment as the replacement of an old docstring.",
    },
    "ignore_passage_owner": {
        "module": "boundary",
        "replacements": [("        if (old[i].path, old[i].kind, old[i].context) != (new[j].path, new[j].kind, new[j].context):\n", "        if (old[i].path, old[i].kind) != (new[j].path, new[j].kind):\n")],
        "positive": INTERACTION + "test_changed_owner_and_changed_text_are_conservative_identity_loss[heading]",
        "control": PHYSICAL_CONTROL,
        "meaning": "Ignore an owner-heading change while pairing changed text.",
    },
    "disable_equal_hash_moves": {
        "module": "boundary",
        "replacements": [("    for same_path in (True, False):\n", "    for same_path in ():\n")],
        "positive": INTERACTION + "test_renamed_file_baseline_identity[same_text_move]",
        "control": PHYSICAL_CONTROL,
        "meaning": "Stop recognizing exact normalized moves across paths.",
    },
    "omit_rewrapped_move_event": {
        "module": "boundary",
        "replacements": [("            if (p.path, p.line, p.end, p.text, p.context) != (target.path, target.line, target.end, target.text, target.context):\n", "            if (p.path, p.line) != (target.path, target.line):\n")],
        "positive": INTERACTION + "test_rewrapped_passage_with_optional_word_change[rewrap_only]",
        "control": INTERACTION + "test_renamed_file_baseline_identity[same_text_move]",
        "meaning": "Lose normalized rewrap events whose starting coordinate is unchanged.",
    },
    "allow_git_color": {
        "module": "checker",
        "replacements": [("\"-c\", \"color.ui=false\",", ""), ("\"--no-color\", ", "")],
        "counts": [1, 2],
        "positive": GIT + "test_color_cannot_hide_storage_boundary",
        "control": WORD_CONTROL,
        "meaning": "Let local Git ANSI coloring alter parsed diff evidence.",
    },
    "respect_binary_diff_attributes": {
        "module": "checker",
        "replacements": [("\"--text\", ", "")],
        "positive": GIT + "test_binary_diff_attribute_cannot_hide_word_claim",
        "control": WORD_CONTROL,
        "meaning": "Let a -diff attribute hide reviewed Markdown content.",
    },
    "omit_review_blob_validation": {
        "module": "checker",
        "replacements": [("        blob(root, base, path)\n        blob(root, head, path)\n", "")],
        "positive": INTERACTION + "test_word_only_markdown_binary_is_tool_error_in_process",
        "control": WORD_CONTROL,
        "meaning": "Skip reviewed-blob validation for WORD-only Markdown.",
    },
    "use_unicode_splitlines": {
        "module": "checker",
        "replacements": [("        lines = patch.decode(\"utf-8\").split(\"\\n\")\n", "        lines = patch.decode(\"utf-8\").splitlines()\n")],
        "positive": INTERACTION + "test_unicode_separator_keeps_valid_review_in_process",
        "control": WORD_CONTROL,
        "meaning": "Confuse Unicode separators with Git's LF line grammar.",
    },
    "retain_configured_function_caption": {
        "module": "checker",
        "replacements": [("            hunk[0] = match.group(0)\n", "")],
        "positive": GIT + "test_function_captions_do_not_depend_on_diff_attributes",
        "control": WORD_CONTROL,
        "meaning": "Let a configured xfuncname caption change report bytes.",
    },
    "allow_blank_context_suppression": {
        "module": "checker",
        "replacements": [("\"-c\", \"diff.suppressBlankEmpty=false\",", "")],
        "positive": INTERACTION + "test_blank_context_config_does_not_break_valid_review",
        "control": WORD_CONTROL,
        "meaning": "Let Git erase the prefix of valid blank context lines.",
    },
    "omit_atomic_edit_metadata": {
        "module": "checker",
        "replacements": [("edits.append(Change(path, side, line_number, body, evidence, span))", "edits.append(Change(path, side, line_number, body, evidence))")],
        "positive": GIT + "test_atomic_edit_spans_are_passage_inputs_not_hunk_scope",
        "control": WORD_CONTROL,
        "meaning": "Remove the exact passage-alignment edit coordinates.",
    },
    "zero_based_added_file_coordinate": {
        "module": "checker",
        "replacements": [("            old, new = (max(1, int(value)) for value in match.groups())\n", "            old, new = (int(value) for value in match.groups())\n")],
        "positive": GIT + "test_added_file_edit_coordinates_are_one_based",
        "control": GIT + "test_atomic_edit_spans_are_passage_inputs_not_hunk_scope",
        "meaning": "Treat Git's empty-file zero offset as a source line number.",
    },
    "skip_catalog_validation": {
        "module": "checker",
        "replacements": [("    require(isinstance(catalog, dict))\n", "    return catalog\n    require(isinstance(catalog, dict))\n")],
        "positive": "tools/drift/tests/test_catalog_errors.py::test_invalid_catalog_is_tool_error[zero_rules]",
        "control": "tools/drift/tests/test_catalog_errors.py::test_valid_catalog_control",
        "meaning": "Accept a zero-rule catalog as a successful review configuration.",
    },
    "strip_repository_path_whitespace": {
        "module": "checker",
        "replacements": [("    value = output.decode(\"utf-8\")\n", "    value = output.decode(\"utf-8\").strip()\n")],
        "positive": GIT + "test_repository_root_preserves_trailing_space",
        "control": GIT + "test_repository_root_normal_control",
        "meaning": "Strip a valid repository-directory trailing space with the record terminator.",
    },
}


def apply_mutant(monkeypatch, name):
    """Compile only local trusted coordinator code; never a Git target's code."""
    if name not in BRANCH_MUTANTS:
        raise ValueError("unknown coordinator branch mutant")
    spec = BRANCH_MUTANTS[name]
    module = importlib.import_module("tools.drift." + spec["module"])
    source = Path(module.__file__).read_text(encoding="utf-8")
    counts = spec.get("counts", [1] * len(spec["replacements"]))
    if len(counts) != len(spec["replacements"]):
        raise ValueError("mutant anchor count declaration is invalid")
    for (before, after), expected in zip(spec["replacements"], counts):
        if source.count(before) != expected:
            raise ValueError(f"stale mutation anchor for {name}")
        source = source.replace(before, after)
    namespace = dict(module.__dict__)
    exec(compile(source, "<trusted-coordinator-mutant:" + name + ">", "exec"), namespace)
    checker = importlib.import_module("tools.drift.checker")
    if spec["module"] == "boundary":
        monkeypatch.setattr(checker, "boundary_review", namespace["review"])
    else:
        def mutated_check(*args, **kwargs):
            # Tests may deliberately substitute a catalog after fixture setup.
            # Keep that caller-selected input visible to the compiled coordinator.
            namespace["DATA"] = checker.DATA
            return namespace["check"](*args, **kwargs)

        monkeypatch.setattr(checker, "check", mutated_check)
        monkeypatch.setattr(checker, "changes", namespace["changes"])
        monkeypatch.setattr(checker, "load_catalog", namespace["load_catalog"])
        monkeypatch.setattr(checker, "parse_repository_root", namespace["parse_repository_root"])
        monkeypatch.setattr(checker, "ToolError", namespace["ToolError"])
