"""Cross-field first-error rules; old committed corpus bytes remain unchanged."""
import unittest
from tools.esp32_scaffold.billboard_corpus import frame, verdict


class FirstErrorTests(unittest.TestCase):
    def test_utf8_phase_precedes_logical_bounds(self):
        """Mutation: validate identifier/fact bounds before parsing later UTF-8 fields."""
        for options, expected in ((dict(issuer=b"", fact=b"\xff"), "InvalidFact"),
                                  (dict(fact=b"\x1b", receipt=b"\xff"), "InvalidReceipt"),
                                  (dict(issuer=b"", fact=b"\x1b"), "InvalidIdentifier")):
            data = frame(**options)
            self.assertEqual(verdict(data, data[:-64], data[-64:], "bound"), (expected, 0))


if __name__ == "__main__":
    unittest.main()
