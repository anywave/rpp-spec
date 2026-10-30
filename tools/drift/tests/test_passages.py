"""Verified lexical lists, passage boundaries, and normalized Git-blob identity."""

import pytest

from tools.drift.passages import Passage, classify, digest, extract, in_scope, normalize


@pytest.mark.parametrize("path", ["README.md", "spec/SPEC.md", "spec/extensions/MESH.md", "rpp/network.py", "rpp/adapters/example.py"])
def test_verified_scope(path):
    assert in_scope(path)


@pytest.mark.parametrize("path", ["parl/phase_router.py", "hardware/verilog/README.md", "docs/codex/OUTBOX/CX-001-001.md", "tools/drift/RULES.md", "notes.txt"])
def test_unclassified_scope(path):
    assert not in_scope(path)


@pytest.mark.parametrize("term", ["spintronic", "spin state", "decoheres", "T2", "min_t2_ns", "thermalization", "thermodynamics", "Hamiltonian", "physics", "physically", "physical invariant", "material property", "holography", "wave interference"])
def test_physics_terms(term):
    passage = Passage("README.md", 1, 1, "paragraph", f"Core correctness MUST require {term}.")
    assert classify(passage) == "BND-F-1"


@pytest.mark.parametrize("term", ["coherence", "resonance", "substrate", "hardware", "physical", "quantum", "t2", "T2_NS", "T20", "ST2", "metaphysically"])
def test_nonterms_and_case(term):
    # T2_NS contains exact-case T2, so it remains a physics match by design.
    expected = "BND-F-1" if term == "T2_NS" else None
    assert classify(Passage("README.md", 1, 1, "paragraph", f"MUST require {term}.")) == expected


@pytest.mark.parametrize("norm", ["MUST", "MUST NOT", "SHALL", "SHALL NOT", "REQUIRED", "REQUIRED NOT", "not a valid", "must be rejected", "refuse", "ABORT"])
def test_normative_markers(norm):
    assert classify(Passage("README.md", 1, 1, "paragraph", f"Spin state: {norm}.")) == "BND-F-1"


@pytest.mark.parametrize("norm", ["must", "shall", "required", "Must", "advisory", "not a claim", "must not assert"])
def test_no_inference_from_lowercase_or_disclaimers(norm):
    assert classify(Passage("README.md", 1, 1, "paragraph", f"Spin state: {norm}.")) == "BND-F-2"


@pytest.mark.parametrize("qualifier", ["On spintronic", "On spintronics", "on spintronic hardware", "on spintronic platforms", "on spintronic substrates", "(spintronic)"])
def test_passage_qualifiers(qualifier):
    text = f"{qualifier}, routing MUST finish within T2."
    # The file does not determine classification.
    assert classify(Passage("spec/SPEC.md", 1, 1, "paragraph", text)) == "BND-F-2"
    assert classify(Passage("spec/SPINTRONIC.md", 1, 1, "paragraph", text)) == "BND-F-2"


def test_qualifier_cannot_leak_between_list_items():
    text = "- On spintronic hardware, T2 is measured.\n- Routing MUST use T2.\n"
    passages = extract("spec/SPEC.md", text)
    assert [p.kind for p in passages] == ["list_item", "list_item"]
    assert [classify(p) for p in passages] == ["BND-F-2", "BND-F-1"]


def test_markdown_block_kinds_and_code_fences():
    text = "# Heading\n\nParagraph\ncontinued.\n\n- One\n  continued.\n- Two\n\n| Name | Value |\n|---|---|\n| TTL | T2 |\n\n```python\n# MUST use T2\nvalue = 1\n```\n"
    blocks = extract("README.md", text)
    assert [p.kind for p in blocks] == ["paragraph", "list_item", "list_item", "table_row", "table_row", "code_fence"]
    assert [p.line for p in blocks] == [3, 6, 8, 10, 12, 14]
    assert blocks[-1].end == 17
    assert classify(blocks[-1]) == "BND-F-1"


def test_python_comments_and_docstrings_only():
    text = '"""Module T2."""\nvalue = "MUST use T2"\n# MUST use T2\nclass Example:\n    """On spintronic platforms, MUST use T2."""\n    def method(self):\n        """MUST use T2."""\n        return "MUST use T2"\n'
    blocks = extract("rpp/example.py", text)
    assert [(p.line, p.kind) for p in blocks] == [(1, "docstring"), (3, "comment"), (5, "docstring"), (7, "docstring")]
    assert [classify(p) for p in blocks] == ["BND-F-2", "BND-F-1", "BND-F-2", "BND-F-1"]


def test_normalized_identity_ignores_wrapping_crlf_and_nfc_spelling():
    first = "  Cafe\u0301\tMUST use\r\nT2.  "
    second = "Caf\u00e9 MUST use T2."
    assert normalize(first) == second
    assert digest(first) == digest(second)
    assert digest(second) != digest("Caf\u00e9 MAY use T2.")
