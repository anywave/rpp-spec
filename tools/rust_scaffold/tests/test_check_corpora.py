"""Four bounded end-to-end freshness cases with named concrete failure witnesses."""

from contextlib import redirect_stdout
import io
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from tools.rust_scaffold import check_corpora


REPO = Path(__file__).resolve().parents[3]


class CorpusFreshnessTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="rpp-corpus-regression-")
        self.addCleanup(self.temporary.cleanup)
        self.repo = Path(self.temporary.name) / "checkout"
        self.repo.mkdir()
        shutil.copytree(REPO / "rpp", self.repo / "rpp", ignore=shutil.ignore_patterns("__pycache__"))
        for relative in ("tools/rust_scaffold", "tools/esp32_scaffold", "tools/overlay_sim", "tools/fleet_scaffold"):
            shutil.copytree(REPO / relative, self.repo / relative, ignore=shutil.ignore_patterns("__pycache__"))
        for relative in ("rust/rpp-core/tests/data", "rust/rpp-control/tests/data", "rust/rpp-fleet/tests/data"):
            shutil.copytree(REPO / relative, self.repo / relative)

    def test_fresh_and_edited_oracle_rows_in_all_four_groups(self):
        """Mutation witnesses: change one saved address/control/overlay/fleet row byte."""
        fresh = check_corpora.check(self.repo)
        self.assertTrue(fresh.fresh)
        self.assertEqual(fresh.checked, 12)
        for relative in ("rust/rpp-core/tests/data/address-construct.tsv",
                         "rust/rpp-core/tests/data/overlay-scenarios.csv",
                         "rust/rpp-control/tests/data/control-corpus.tsv",
                         "rust/rpp-fleet/tests/data/fleet-scenarios.tsv"):
            path = self.repo / relative
            original = path.read_bytes()
            changed = bytearray(original)
            offset = original.index(b"\n") + 1
            changed[offset] = ord("X") if changed[offset] != ord("X") else ord("Y")
            path.write_bytes(changed)
            try:
                stale = check_corpora.check(self.repo)
                self.assertFalse(stale.fresh)
                self.assertEqual(stale.differences, (f"changed {relative}",))
                if relative.endswith("address-construct.tsv"):
                    output = io.StringIO()
                    with redirect_stdout(output):
                        self.assertEqual(check_corpora.main(["--repo", str(self.repo)]), 1)
                    self.assertIn(f"changed {relative}", output.getvalue())
            finally:
                path.write_bytes(original)

    def test_manifest_edits_are_not_ignored_as_environment_metadata(self):
        """Mutation witnesses: alter provenance Unicode version or control row count."""
        cases = (("rust/rpp-core/tests/data/address-manifest.json", b'"15.0.0"', b'"15.1.0"'),
                 ("rust/rpp-control/tests/data/control-manifest.json", b'"rows": 1373', b'"rows": 1374'))
        for relative, before, after in cases:
            path = self.repo / relative
            original = path.read_bytes()
            self.assertEqual(original.count(before), 1)
            path.write_bytes(original.replace(before, after))
            try:
                stale = check_corpora.check(self.repo)
                self.assertEqual(stale.differences, (f"changed {relative}",))
            finally:
                path.write_bytes(original)

    def test_missing_and_unexpected_files_are_stale(self):
        """Mutation witnesses: drop a committed oracle or add an unreviewed file."""
        relative = "rust/rpp-control/tests/data/control-corpus.tsv"
        path = self.repo / relative
        original = path.read_bytes()
        path.unlink()
        try:
            self.assertEqual(check_corpora.check(self.repo).differences, (f"missing {relative}",))
        finally:
            path.write_bytes(original)
        extra = self.repo / "rust/rpp-core/tests/data/address-unreviewed.tsv"
        extra.write_bytes(b"unreviewed\n")
        self.assertEqual(check_corpora.check(self.repo).differences,
                         ("unexpected rust/rpp-core/tests/data/address-unreviewed.tsv",))

    def test_wrong_reference_runtime_and_in_checkout_scratch_are_rejected(self):
        """Mutation witnesses: accept Unicode15.1/Python3.13 or generate in checkout."""
        for metadata in (((3, 13, 2), "15.1.0"), ((3, 12, 10), "15.1.0"), ((3, 13, 2), "15.0.0")):
            with patch.object(check_corpora, "reference_environment", return_value=metadata), \
                    patch.object(check_corpora, "run_generator") as generate:
                with self.assertRaisesRegex(check_corpora.CheckerError, "reference engine required"):
                    check_corpora.check(self.repo)
                generate.assert_not_called()
        with self.assertRaisesRegex(check_corpora.CheckerError, "outside"):
            check_corpora.check(self.repo, temp_root=self.repo)
        # CI's two exact patches belong to the same recorded provenance family.
        check_corpora.require_reference_environment((3, 12, 10), "15.0.0")
        check_corpora.require_reference_environment((3, 12, 14), "15.0.0")


if __name__ == "__main__":
    unittest.main()
