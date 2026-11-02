"""Finite offline-readiness witnesses; fake tool verdicts do not prove cross-builds."""
from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

from tools.esp32_scaffold import check_no_std as guard


RISCV = "riscv32imc-unknown-none-elf"
THUMB = "thumbv7em-none-eabihf"
PACKAGES = ["rpp-billboard", "rpp-frag", "rpp-steer"]


class NoStdCheckTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="rpp-embedded-check-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.repo = self.root / "checkout"
        rust = self.repo / "rust"
        rust.mkdir(parents=True)
        (rust / "Cargo.toml").write_text('[workspace]\nmembers = ["rpp-billboard", "rpp-frag", "rpp-steer"]\nresolver = "2"\n')
        (rust / "Cargo.lock").write_text("version = 4\n")
        for package in PACKAGES:
            directory = rust / package
            (directory / "src").mkdir(parents=True)
            (directory / "Cargo.toml").write_text(f'[package]\nname = "{package}"\nversion = "0.1.0"\nedition = "2021"\n')
            (directory / "src/lib.rs").write_text("#![no_std]\n#![forbid(unsafe_code)]\n")
        self.calls = []
        self.rust_version = "rustc 1.85.1 (fixture)\n"
        self.cargo_version = "cargo 1.85.1 (fixture)\n"
        self.build_error = None
        self.probe_override = None
        self.work = self.root / "scratch"

    def install(self, target):
        library = self.root / "sysroot" / "lib/rustlib" / target / "lib"
        library.mkdir(parents=True, exist_ok=True)
        for name in ("libcore-fixture.rlib", "libcompiler_builtins-fixture.rlib"):
            (library / name).write_bytes(b"!<arch>\nfixture")
        return library

    def tool(self, command, env, timeout=30):
        self.calls.append((list(command), dict(env), timeout))
        if "--version" in command:
            return self.rust_version if command[0] == "rustc-fixture" else self.cargo_version
        if "--print" in command:
            if self.probe_override is not None:
                return self.probe_override
            target = command[command.index("--target") + 1]
            return str(self.root / "sysroot" / "lib/rustlib" / target / "lib") + "\n"
        if self.build_error:
            raise guard.CheckError(self.build_error)
        return "compiled fixture\n"

    def check(self, **options):
        with mock.patch.object(guard, "execute", side_effect=self.tool):
            return guard.check(self.repo, cargo=["cargo-fixture"], rustc=["rustc-fixture"], work_dir=self.work, **options)

    def builds(self):
        return [call for call in self.calls if "build" in call[0]]

    def test_execute_rejects_nonzero_missing_tool_and_timeout(self):
        """Kills nonzero-to-success and missing/timeout tool errors converted into a skip."""
        commands = (([sys.executable, "-I", "-c", "raise SystemExit(7)"], 30),
                    ([str(self.root / "missing-executable")], 30),
                    ([sys.executable, "-I", "-c", "import time; time.sleep(5)"], 0.1))
        for command, timeout in commands:
            with self.subTest(command=command), self.assertRaises(guard.CheckError):
                guard.execute(command, guard.environment(), timeout=timeout)

    def test_windows_stop_falls_back_when_tree_kill_helper_is_unavailable(self):
        """Kills skipping parent kill/wait when taskkill is missing or times out."""
        errors = (FileNotFoundError("taskkill absent"), guard.subprocess.TimeoutExpired("taskkill", 10))
        for failure in errors:
            process = mock.Mock(pid=123)
            process.poll.return_value = None
            error = None
            with self.subTest(error=type(failure).__name__), mock.patch.object(guard.os, "name", "nt"):
                with mock.patch.object(guard.subprocess, "run", side_effect=failure):
                    try:
                        guard.stop(process)
                    except (OSError, guard.subprocess.TimeoutExpired) as raised:
                        error = raised
            self.assertIsNone(error)
            process.kill.assert_called_once_with()
            process.wait.assert_called_once_with(timeout=10)

    def test_execute_rejects_output_overflow_instead_of_capturing_it_unbounded(self):
        """Kills an ignored output limit while a controlled child writes beyond that limit."""
        for stream in ("stdout", "stderr"):
            command = [sys.executable, "-I", "-c", f"import sys; sys.{stream}.buffer.write(b'x' * 4096)"]
            with self.subTest(stream=stream), mock.patch.object(guard, "OUTPUT_LIMIT", 1024):
                with self.assertRaises(guard.CheckError):
                    guard.execute(command, guard.environment())

    def test_execute_rejects_invalid_utf8_instead_of_replacement_decoding(self):
        """Kills accepting malformed tool output after replacing undecodable bytes."""
        command = [sys.executable, "-I", "-c", "import sys; sys.stdout.buffer.write(bytes([255]))"]
        with self.assertRaises(guard.CheckError):
            guard.execute(command, guard.environment())

    def test_cli_fails_on_check_error_and_preserves_explicit_skip_exit(self):
        """Kills a zero exit after a build error or a missing-target SKIP changed to FAIL."""
        arguments = ["check_no_std.py", "--repo", str(self.repo)]
        output = io.StringIO()
        with mock.patch.object(sys, "argv", arguments), mock.patch.object(guard, "check", side_effect=guard.CheckError("build failed")), redirect_stdout(output):
            self.assertEqual(guard.main(), 1)
        self.assertEqual(json.loads(output.getvalue())["status"], "FAIL")
        output = io.StringIO()
        skipped = {"status": "SKIP", "target": None, "reason": "target absent"}
        with mock.patch.object(sys, "argv", arguments), mock.patch.object(guard, "check", return_value=skipped), redirect_stdout(output):
            self.assertEqual(guard.main(), 0)
        self.assertEqual(json.loads(output.getvalue()), skipped)

    def test_installed_riscv_is_preferred_over_thumb(self):
        """Kills unconditional Thumb fallback or selecting a target merely from target-list."""
        self.install(RISCV)
        self.install(THUMB)
        result = self.check()
        self.assertEqual((result["status"], result["target"]), ("PASS", RISCV))
        self.assertEqual(len(self.builds()), 1)
        self.assertIn(RISCV, self.builds()[0][0])

    def test_missing_targets_skip_without_cargo_build(self):
        """Kills compiling an absent target or reporting missing target libraries as PASS."""
        result = self.check()
        self.assertEqual((result["status"], result["target"]), ("SKIP", None))
        self.assertTrue(result["reason"])
        self.assertEqual(self.builds(), [])

    def test_thumb_is_only_the_missing_riscv_fallback(self):
        """Kills ignoring the installed fallback or describing Thumb as an ESP32-C3 build."""
        self.install(THUMB)
        result = self.check()
        self.assertEqual((result["status"], result["target"]), ("PASS", THUMB))
        self.assertIn(THUMB, self.builds()[0][0])

    def test_partial_or_malformed_target_is_failure_not_skip(self):
        """Kills treating a partial installation, empty rlib or nonarchive rlib as absent."""
        library = self.install(RISCV)
        self.install(THUMB)
        core = library / "libcore-fixture.rlib"
        for content in (None, b"", b"not an archive"):
            if content is None:
                core.unlink()
            else:
                core.write_bytes(content)
            with self.subTest(content=content), self.assertRaises(guard.CheckError):
                self.check()
            self.assertEqual(self.builds(), [])

    def test_dangling_target_link_is_failure_instead_of_fallback(self):
        """Kills treating a dangling target-library link as absent and accepting Thumb."""
        self.install(THUMB)
        missing = self.root / "sysroot/lib/rustlib" / RISCV / "lib"
        with mock.patch.object(Path, "is_symlink", autospec=True, side_effect=lambda path: path == missing):
            with self.assertRaises(guard.CheckError):
                self.check()
        self.assertEqual(self.builds(), [])

    def test_target_root_without_lib_is_partial_installation_not_fallback(self):
        """Kills treating an installed target root with missing libraries as an absent target."""
        self.install(THUMB)
        (self.root / "sysroot/lib/rustlib" / RISCV).mkdir()
        with self.assertRaises(guard.CheckError):
            self.check()
        self.assertEqual(self.builds(), [])

    def test_malformed_target_probe_is_failure_not_skip(self):
        """Kills accepting relative, empty or multiline target-library probe output."""
        for value in ("relative/lib\n", "", "/first\n/second\n"):
            self.probe_override = value
            with self.subTest(probe=value), self.assertRaises(guard.CheckError):
                self.check()
        self.assertEqual(self.builds(), [])

    def test_compile_failure_does_not_skip_or_retry_thumb(self):
        """Kills converting a real build failure into SKIP or a fallback success."""
        self.install(RISCV)
        self.install(THUMB)
        self.build_error = "deliberate compile failure"
        with self.assertRaises(guard.CheckError):
            self.check()
        self.assertEqual(len(self.builds()), 1)
        self.assertIn(RISCV, self.builds()[0][0])

    def test_wrong_compiler_or_cargo_pin_fails_before_target_skip(self):
        """Kills accepting 1.85.10 by prefix or skipping before validating the toolchain."""
        for field, value in (("rust_version", "rustc 1.85.10 (fixture)\n"),
                             ("cargo_version", "cargo 1.85.10 (fixture)\n")):
            original = getattr(self, field)
            setattr(self, field, value)
            with self.subTest(tool=field), self.assertRaises(guard.CheckError):
                self.check()
            setattr(self, field, original)
        self.assertEqual(self.builds(), [])

    def test_genuine_tool_absence_skips_but_partial_configuration_fails(self):
        """Kills treating absent tools as PASS or incomplete explicit/discovered tools as SKIP."""
        with mock.patch.object(guard, "discover", return_value=None):
            result = guard.check(self.repo, work_dir=self.work)
        self.assertEqual((result["status"], result["target"]), ("SKIP", None))
        with self.assertRaises(guard.CheckError):
            guard.check(self.repo, cargo=["cargo-fixture"], work_dir=self.work)
        cargo = self.root / "cargo"
        cargo.touch()
        with mock.patch.object(guard.shutil, "which", side_effect=lambda name: str(cargo) if name == "cargo" else None):
            with self.assertRaises(guard.CheckError):
                guard.check(self.repo, work_dir=self.work)
        self.assertEqual(self.builds(), [])

    def test_present_rustup_malformed_inventory_fails_instead_of_claiming_absence(self):
        """Kills treating empty, control-containing or malformed rustup metadata as missing tools."""
        with mock.patch.object(guard.shutil, "which", return_value="rustup-fixture"):
            for listing in ("", "broken\x00metadata\n", "broken metadata\n"):
                with self.subTest(listing=listing), mock.patch.object(guard, "execute", return_value=listing):
                    with self.assertRaises(guard.CheckError):
                        guard.discover(guard.environment())
            for listing in ("custom-toolchain\n", "custom-toolchain (active, default)\n", "no installed toolchains\n"):
                with self.subTest(control=listing), mock.patch.object(guard, "execute", return_value=listing):
                    self.assertIsNone(guard.discover(guard.environment()))

    def test_missing_steer_is_an_input_failure_even_when_targets_are_absent(self):
        """Kills a green target-missing skip that silently omits the required steer crate."""
        (self.repo / "rust/rpp-steer/src/lib.rs").unlink()
        with self.assertRaises(guard.CheckError):
            self.check()
        self.assertEqual(self.builds(), [])

    def test_ancestor_cache_directory_is_rejected_before_build(self):
        """Kills accepting an ancestor cache path whose derived writes may enter the checkout."""
        self.install(RISCV)
        with mock.patch.object(guard, "execute", side_effect=self.tool):
            with self.assertRaises(guard.CheckError):
                guard.check(self.repo, cargo=["cargo-fixture"], rustc=["rustc-fixture"], work_dir=self.root)
        self.assertEqual(self.builds(), [])

    def test_derived_cache_links_cannot_resolve_into_the_checkout(self):
        """Kills validating only the cache root while target or Cargo home resolves inside source."""
        self.install(RISCV)
        original = Path.resolve
        for name in ("target", "cargo-home"):
            def redirected(path, *args, **kwargs):
                return self.repo if path == self.work / name else original(path, *args, **kwargs)
            with self.subTest(cache=name), mock.patch.object(Path, "resolve", autospec=True, side_effect=redirected):
                with self.assertRaises(guard.CheckError):
                    self.check()
        self.assertEqual(self.builds(), [])

    def test_build_is_exactly_three_bare_libraries_with_offline_clean_environment(self):
        """Kills omitted crates, default/std features, unlocked/network builds or ambient wrappers."""
        self.install(RISCV)
        sysroot = self.root / "sysroot with spaces"
        sysroot.mkdir()
        poison = {"RUSTFLAGS": "--cfg poisoned", "CARGO_ENCODED_RUSTFLAGS": "poisoned",
                  "RUSTC_WRAPPER": "poisoned", "RUSTC_WORKSPACE_WRAPPER": "poisoned"}
        with mock.patch.dict(os.environ, poison):
            self.check(sysroot=sysroot)
        command, env, _ = self.builds()[0]
        packages = [command[index + 1] for index, value in enumerate(command) if value in ("-p", "--package")]
        self.assertEqual(packages, PACKAGES)
        for flag in ("--lib", "--no-default-features", "--offline", "--locked"):
            self.assertIn(flag, command)
        self.assertNotIn("--features", command)
        self.assertEqual(env["CARGO_NET_OFFLINE"], "true")
        self.assertEqual(env["RUSTUP_AUTO_INSTALL"], "0")
        self.assertEqual(env["RUSTUP_TOOLCHAIN"], "1.85.1")
        self.assertEqual(env["RUSTC"], "rustc-fixture")
        self.assertEqual(env["CARGO_ENCODED_RUSTFLAGS"], "--sysroot\x1f" + str(sysroot))
        for name in poison:
            if name != "CARGO_ENCODED_RUSTFLAGS":
                self.assertNotIn(name, env)


if __name__ == "__main__":
    unittest.main()
