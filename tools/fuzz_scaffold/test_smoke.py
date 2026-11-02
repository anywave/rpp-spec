"""Counterfactuals for optional-tool skipping and bounded outside-only fuzz runs."""
from hashlib import sha256
import json
from pathlib import Path
import signal
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import MagicMock, patch
from tools.fuzz_scaffold import smoke


class SmokeTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(TemporaryDirectory(prefix="cx024-smoke-test-")))
        self.source = self.root / "source/tools/fuzz_scaffold"
        (self.source / "seeds").mkdir(parents=True)
        (self.root / "source/rust").mkdir()
        (self.source / "Cargo.lock").write_text("frozen\n")
        rows = []
        for target in smoke.TARGETS:
            name = target + "-valid"
            (self.source / "seeds" / (name + ".hex")).write_text("00\n")
            rows.append(dict(target=target, name=name, file=name + ".hex", sha256=sha256(b"\0").hexdigest()))
        self.manifest = self.source / "seeds/manifest.json"
        self.manifest.write_text(json.dumps(dict(schema=1, seeds=rows)))
        self.output = self.root / "output"

    def test_missing_toolchain_skips_but_present_wrong_pin_fails(self):
        """Mutations: launch/install absent tools, or accept a present wrong tool pin."""
        with patch.object(smoke.platform, "system", return_value="Linux"), \
                patch.object(smoke.shutil, "which", return_value=None), \
                patch.object(smoke, "execute") as execute:
            result = smoke.run(self.output, scaffold=self.source)
        self.assertEqual(result["status"], "SKIP")
        self.assertIn("preinstalled", result["reason"])
        self.assertFalse(self.output.exists())
        execute.assert_not_called()
        with patch.object(smoke.platform, "system", return_value="Linux"), \
                patch.object(smoke.shutil, "which", return_value="installed"), \
                patch.object(smoke, "execute", side_effect=["nightly-host", "rustc 1.86.0-nightly (fixture)", "cargo-fuzz 0.13.0"]):
            with self.assertRaisesRegex(RuntimeError, "match"):
                smoke.preflight()

    def test_present_build_and_run_failures_are_never_skipped(self):
        """Mutation: swallow build/run failures as an optional-tool skip."""
        for fail_label in ("build.log", "decode.log"):
            with self.subTest(fail_label=fail_label):
                output = self.root / fail_label
                def execute(command, timeout, env, log, cwd):
                    if log.name == fail_label:
                        raise RuntimeError("actual tool failed")
                    return ""
                with patch.object(smoke, "preflight", return_value=(("nightly", "rustc nightly", "cargo-fuzz 0.12.0"), None)), \
                        patch.object(smoke, "execute", side_effect=execute):
                    with self.assertRaisesRegex(RuntimeError, "actual tool failed"):
                        smoke.run(output, scaffold=self.source)
                self.assertEqual((output / "corpus/decode/decode-valid").read_bytes(), b"\0")

    def test_success_has_two_bounded_targets_offline_and_outside_checkout(self):
        """Mutation: unbounded time/input, bootstrap/network enablement or original-source execution."""
        calls = []
        def execute(command, timeout, env, log, cwd):
            calls.append((command, timeout, env, log, cwd))
            return ""
        with patch.object(smoke, "preflight", return_value=(("nightly", "rustc nightly", "cargo-fuzz 0.12.0"), None)), \
                patch.object(smoke, "execute", side_effect=execute):
            result = smoke.run(self.output, scaffold=self.source)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual([call[3].name for call in calls], ["metadata.log", "build.log", "decode.log", "reassemble.log"])
        for command, timeout, env, log, cwd in calls:
            self.assertEqual(env["CARGO_NET_OFFLINE"], "true")
            self.assertNotIn("RUSTC_BOOTSTRAP", env)
            self.assertNotIn("RUSTC", env)
            self.assertEqual(cwd, self.output / "project/tools/fuzz_scaffold")
            self.assertTrue(log.is_relative_to(self.output))
            self.assertLessEqual(timeout, 180)
            self.assertNotIn(str(self.source), command)
        for command, _, _, _, _ in calls[-2:]:
            for flag in ("-max_total_time=30", "-max_len=4096", "-timeout=2", "-rss_limit_mb=512"):
                self.assertIn(flag, command)
        self.assertEqual((self.source / "Cargo.lock").read_text(), "frozen\n")

    def test_seed_bounds_hashes_and_disjoint_output_fail_closed(self):
        """Mutation: accept traversal, malformed/oversized hex, bad hashes or checkout output."""
        for data in ("zz", "00" * 4097, "00" * 9000, "01"):
            (self.source / "seeds/decode-valid.hex").write_text(data)
            with self.subTest(data_length=len(data)), self.assertRaises(ValueError):
                smoke.seeds(self.source)
        (self.source / "seeds/decode-valid.hex").write_text("00")
        with patch.object(smoke, "preflight", return_value=(None, "fixture unavailable")):
            for output in (self.source / "out", self.root / "source", self.root):
                with self.subTest(output=output), self.assertRaisesRegex(ValueError, "outside"):
                    smoke.run(output, scaffold=self.source)
        rows = json.loads(self.manifest.read_text())
        rows["seeds"][0]["file"] = "../escape.hex"
        self.manifest.write_text(json.dumps(rows))
        with self.assertRaises(ValueError):
            smoke.seeds(self.source)

    @patch.object(smoke.signal, "SIGKILL", 9, create=True)
    def test_outer_timeout_kills_group_and_retains_partial_log(self):
        """Mutation: leave fuzz descendants running after the outer deadline."""
        process = MagicMock(pid=123)
        with patch.object(smoke.subprocess, "Popen") as popen, patch.object(smoke.os, "killpg", create=True) as kill, \
                patch.object(smoke.selectors, "DefaultSelector") as selector, \
                patch.object(smoke.os, "read", return_value=b"partial output"), \
                patch.object(smoke.time, "monotonic", side_effect=[0, 0, 2]):
            popen.return_value.__enter__.return_value = process
            selector.return_value.__enter__.return_value.select.return_value = [True]
            with self.assertRaisesRegex(RuntimeError, "outer timeout"):
                smoke.execute(["cargo"], 1, log=self.root / "timeout.log")
        kill.assert_called_once_with(123, signal.SIGKILL)
        self.assertEqual((self.root / "timeout.log").read_bytes(), b"partial output")

    @patch.object(smoke.signal, "SIGKILL", 9, create=True)
    def test_output_cap_bounds_reads_and_raw_log_before_killing_group(self):
        """Mutation: read unbounded output first or expand invalid UTF-8 into an oversized log."""
        process = MagicMock(pid=456)
        with patch.object(smoke.subprocess, "Popen") as popen, patch.object(smoke.os, "killpg", create=True) as kill, \
                patch.object(smoke.selectors, "DefaultSelector") as selector, \
                patch.object(smoke.os, "read", side_effect=lambda fd, size: b"\xff" * size) as read, \
                patch.object(smoke, "OUTPUT_LIMIT", 1024):
            popen.return_value.__enter__.return_value = process
            selector.return_value.__enter__.return_value.select.return_value = [True]
            with self.assertRaisesRegex(RuntimeError, "output limit"):
                smoke.execute(["cargo"], 1, log=self.root / "bounded.log")
        self.assertEqual([call.args[1] for call in read.call_args_list], [1024])
        self.assertEqual((self.root / "bounded.log").read_bytes(), b"\xff" * 1024)
        kill.assert_called_once_with(456, signal.SIGKILL)


if __name__ == "__main__":
    unittest.main()
