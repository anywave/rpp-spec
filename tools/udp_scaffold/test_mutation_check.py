"""Mutation: treating arbitrary compiler/runtime failures as successful kills."""
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from tools.udp_scaffold.mutation_check import invoke


class ClassifierTests(unittest.TestCase):
    def test_only_selected_assertion_failure_counts(self):
        """Kill the mutation accepting arbitrary panic text or compiler failures."""
        prefix = "running 1 test\ntest bounded ... FAILED\n\nthread 'bounded' panicked at fixture.rs:1:1:\n"
        suffix = "\n\ntest result: FAILED. 0 passed; 1 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s\n"
        assertion = prefix + "assertion failed: false" + suffix
        passing = "running 1 test\ntest bounded ... ok\n\ntest result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s\n"
        cases = ((0, passing, "passed"), (101, assertion, "assertion_failure"),
                 (101, prefix + "explicit panic" + suffix, None),
                 (101, assertion + "error: could not compile", None),
                 (101, assertion.replace("test bounded ...", "test wrong ..."), None),
                 (0, passing.replace("test bounded ...", "test wrong ..."), None),
                 (101, prefix + "assertion failed: earlier\n\nthread 'bounded' panicked at fixture.rs:2:1:\nexplicit panic" + suffix, None))
        with TemporaryDirectory() as directory:
            for code, text, expected in cases:
                result = SimpleNamespace(returncode=code, stdout=text, stderr="")
                with self.subTest(code=code, expected=expected), patch("subprocess.run", return_value=result):
                    args = (Path("cargo"), Path(directory), {}, ("--lib", "bounded"), Path(directory) / "out.log")
                    if expected is None:
                        with self.assertRaises(RuntimeError):
                            invoke(*args)
                    else:
                        self.assertEqual(invoke(*args), expected)


if __name__ == "__main__":
    unittest.main()
