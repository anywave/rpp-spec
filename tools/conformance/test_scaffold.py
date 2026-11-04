"""Named failures for the source-only bootstrap; no real repository changes."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from tools.conformance import run


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="conformance-scaffold-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.git("init", "-q")
        (self.repo / "Cargo.toml").write_text('[workspace]\nmembers=["crates/*"]\n')
        for name in run.CRATES:
            path = self.repo / "crates" / name
            (path / "src").mkdir(parents=True)
            (path / "Cargo.toml").write_text('[package]\nname="fixture"\n')
            (path / "src/lib.rs").write_text("// Synthetic source fixture.\n")
        self.git("add", ".")
        self.git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "fixture")
        pin = self.git("rev-parse", "HEAD").decode().strip()
        kit = self.root / "tools" / "conformance"
        kit.mkdir(parents=True)
        self.enterContext(patch.object(run, "ROOT", kit))
        self.enterContext(patch.object(run, "PIN", pin))
        self.target = kit.parent / ".conformance-sources/latticeworks"

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.repo), *args], stderr=subprocess.PIPE)

    def test_kills_modified_source_snapshot(self):
        run.snapshot(self.repo)
        run.snapshot(self.repo)
        (self.target / "crates/lw-jobcard/src/lib.rs").write_text("changed\n")
        with self.assertRaises(ValueError):
            run.snapshot(self.repo)

    def test_kills_changed_provenance(self):
        run.snapshot(self.repo)
        (self.target / "SOURCE.json").write_text(json.dumps({"commit": "0" * 40}))
        with self.assertRaises(ValueError):
            run.snapshot(self.repo)

    def test_kills_extra_snapshot_file(self):
        run.snapshot(self.repo)
        (self.target / "unexpected.rs").write_text("changed\n")
        with self.assertRaises(ValueError):
            run.snapshot(self.repo)

    @unittest.skipUnless(hasattr(Path, "symlink_to"), "symlink API unavailable")
    def test_kills_snapshot_parent_symlink(self):
        outside = self.root / "outside"
        outside.mkdir()
        try:
            self.target.parent.symlink_to(outside, target_is_directory=True)
        except OSError:
            self.skipTest("symlink privilege unavailable")
        with self.assertRaises(ValueError):
            run.snapshot(self.repo)
        self.assertEqual(list(outside.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
