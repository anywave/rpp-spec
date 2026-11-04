"""CX-029 fixture checks only; no RPP runtime or external job-card contract."""
import json
from pathlib import Path
import re
import unittest

HERE = Path(__file__).resolve().parent
DOC = HERE.parent / "docs/design/JOB_ATTEMPT_PROOF_HANDOFF.md"
EXPECTED_NAMES = [
    "job_id", "attempt_id", "worker", "slot", "epoch", "fence", "component", "result_sha256",
]
EXPECTED_BANS = ["sign", "signing", "signature", "door", "state"]
REQUIRED_CASES = [
    "two attempts", "result by reference", "proof without job_id", "attempt without job_id",
    "outside eight names", "nested job card", "key_sign", "key_signing", "key_signature",
    "key_door", "key_state",
]
RULE = (
    b'"The A3 job card is the Rust draft lw-jobcard on anywave/latticeworks branch '
    b"pl/lw-jobcard-v0 (draft_only, not a frozen contract, PL's JS draft is input only), "
    b'so CX-029 must not define its own job card and may rely only on the names job_id, '
    b'attempt_id, worker, slot, epoch, fence, component and result_sha256 as ResultPacket '
    b'has them, with attempt and proof always carried by reference to job_id, and on '
    b'nothing about signing bytes, door records or states, which may still change."'
)


class HandoffVectorsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.vectors = json.loads((HERE / "handoff_vectors.json").read_text(encoding="utf-8"))
        cls.doc = DOC.read_bytes()

    def valid_references(self, references):
        names = set(self.vectors["allowed_names"])
        return bool(references) and all(
            isinstance(ref, dict) and "job_id" in ref and set(ref) <= names
            and not any(isinstance(value, (dict, list)) for value in ref.values())
            for ref in references
        )

    def banned_matches(self, text):
        words = "|".join(re.escape(word) for word in self.vectors["banned_words"])
        return re.findall(r"\b(?:" + words + r")\b", text, flags=re.IGNORECASE)

    def case(self, name):
        return next(case for case in self.vectors["cases"] if case["name"] == name)

    def test_allowed_names_rejects_ninth_name(self):
        """Kills CX029-M1: adding a ninth allowed name cannot redefine the pack."""
        self.assertEqual(self.vectors["allowed_names"], EXPECTED_NAMES)
        self.assertEqual(self.vectors["banned_words"], EXPECTED_BANS)

    def test_quote_is_byte_identical(self):
        """Kills CX029-M2: changing one word of the released opening paragraph."""
        self.assertEqual(self.doc.splitlines()[0], RULE, "released quote differs")

    def test_doc_table_has_eight_names_only(self):
        """Kills adding a new documented name while leaving the fixture list unchanged."""
        names = re.findall(r"^\| `([^`]+)` \|", self.doc.decode("utf-8"), re.MULTILINE)
        self.assertEqual(names, EXPECTED_NAMES)

    def test_vectors_have_expected_validity(self):
        """Kills CX029-M3/M4: missing job reference or an extra key in a valid case."""
        cases = self.vectors["cases"]
        self.assertEqual([case["name"] for case in cases], REQUIRED_CASES)
        for case in cases:
            with self.subTest(case=case["name"]):
                self.assertIsInstance(case["valid"], bool)
                self.assertEqual(self.valid_references(case["references"]), case["valid"])

    def test_two_attempts_keep_reference_identity(self):
        """Kills CX029-M3 and merging two attempts by their repeated local counters."""
        case = self.case("two attempts")
        self.assertEqual(case["meter_rows"], [[1, 1], [1, 1]])
        refs = case["references"]
        self.assertEqual(len(refs), 2)
        self.assertNotIn(None, {ref.get("job_id") for ref in refs})
        self.assertEqual(len({ref.get("job_id") for ref in refs}), 1)
        self.assertNotIn(None, {ref.get("attempt_id") for ref in refs})
        self.assertEqual(len({ref.get("attempt_id") for ref in refs}), 2)
        keys = {
            (ref.get("job_id"), ref.get("attempt_id"), *meter)
            for ref, meter in zip(refs, case["meter_rows"])
        }
        self.assertEqual(len(keys), 2)

    def test_result_stays_by_reference(self):
        """Kills removing job_id from the valid result reference or nesting its proof."""
        refs = self.case("result by reference")["references"]
        self.assertEqual(len(refs), 1)
        self.assertIn("job_id", refs[0])
        self.assertIn("result_sha256", refs[0])
        self.assertTrue(self.valid_references(refs))

    def test_doc_and_valid_vectors_have_no_banned_whole_words(self):
        """Kills CX029-M4 and prohibited wording outside the exact opening quote."""
        self.assertEqual(self.doc.splitlines()[0], RULE, "released quote differs")
        self.assertEqual(self.banned_matches(b"\n".join(self.doc.splitlines()[1:]).decode("utf-8")), [])
        valid = {key: value for key, value in self.vectors.items() if key != "banned_words"}
        # All invalid fixtures, including the named nested-card fixture, are exempt.
        valid["cases"] = [case for case in self.vectors["cases"] if case["valid"]]
        self.assertEqual(self.banned_matches(json.dumps(valid, ensure_ascii=False)), [])

    def test_word_boundaries_ignore_design_and_statement(self):
        """Kills substring matching and a disabled/case-sensitive whole-word check."""
        self.assertEqual(self.banned_matches("design statement designed restatement"), [])
        self.assertEqual(self.banned_matches("SIGN signing signature door state"),
                         ["SIGN", "signing", "signature", "door", "state"])


if __name__ == "__main__":
    unittest.main()
