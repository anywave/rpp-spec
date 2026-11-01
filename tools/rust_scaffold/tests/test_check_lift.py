"""Offline lift guard witnesses; every test states its failing mutation."""
import importlib.util
from contextlib import chdir
from pathlib import Path
import subprocess
import tempfile
import textwrap
from types import SimpleNamespace
import unittest
from unittest import mock

SPEC = importlib.util.spec_from_file_location("lift", Path(__file__).parents[1] / "check_lift.py")
lift = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(lift)


class LiftTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "rust"
        (self.root / "src").mkdir(parents=True)
        (self.root / "data.txt").write_text("fixture\n", encoding="utf-8")
        (self.root.parent / "spec").mkdir()
        (self.root.parent / "spec/x").write_text("outside\n", encoding="utf-8")

    def inspect(self, source="pub fn fixture() {}", manifest="[workspace]\n"):
        (self.root / "src/lib.rs").write_text(source, encoding="utf-8")
        (self.root / "Cargo.toml").write_text(manifest, encoding="utf-8")
        return lift.check(self.root)

    def denied(self, source="pub fn fixture() {}", manifest="[workspace]\n", reason="escapes rust/"):
        _, errors = self.inspect(source, manifest)
        self.assertTrue(errors)
        self.assertTrue(any(reason in error for error in errors), errors)

    def test_local_paths_and_cross_crate_includes_are_allowed(self):
        """Mutation: reject every ../ component rather than checking resolved containment."""
        counts, errors = self.inspect('include_bytes!("../data.txt");', '[workspace]\n[lib]\npath="src/lib.rs"\n')
        self.assertEqual(errors, [])
        self.assertEqual(counts, dict(manifests=1, rust_sources=1, references=2))

    def test_workspace_target_and_patch_dependency_escapes_are_rejected(self):
        """Mutation ../spec path dependency escapes rust, including nested/aliased TOML tables."""
        for table in ("workspace.dependencies", "target.'cfg(unix)'.dependencies", "patch.crates-io", "replace"):
            self.denied(manifest=f'[{table}]\nrenamed={{path="../spec"}}\n')

    def test_literal_macro_escapes_and_public_aliases_are_rejected(self):
        """Mutation include_bytes!(../../../spec/x), qualified or aliased, must be caught."""
        for source in ('include_bytes!("../../../spec/x");',
                       'std::include_str! { r#"../../../spec/x"# };',
                       'use std::{include_bytes as data}; data!["../../../spec/x"];',
                       'use std::include_str as données; données!("../../../spec/x");',
                       'use std::include_str as first; use first as second; second!("../../../spec/x");'):
            self.denied(source)
        self.inspect()
        nested = self.root / "src/target"
        nested.mkdir()
        (nested / "escape.rs").write_text('include_str!("../../../spec/x");', encoding="utf-8")
        self.assertTrue(any("escapes rust/" in error for error in lift.check(self.root)[1]))

    def test_path_attributes_and_cfg_attr_escapes_are_rejected(self):
        """Mutation: scan direct #[path] only and miss nested cfg_attr module paths."""
        for source in ('#[path="../../../spec/x"] mod external;',
                       '#[cfg_attr(any(), path = r"../../../spec/x")] mod external;'):
            self.denied(source)

    def test_dynamic_escaped_absolute_and_windows_paths_require_review(self):
        """Mutation: silently ignore unresolvable include expressions or platform aliases."""
        for source, reason in (
            ('include_str!(concat!("../", "data.txt"));', "dynamic"),
            ('#[path=concat!("x", "y")] mod x;', "dynamic"),
            ('include_str!("../data\\x2etxt");', "escaped"),
            ('include_str!(r"C:\\spec\\x");', "Windows"),
            ('include_str!("/spec/x");', "absolute"),
            ('include_str!(r"C:spec/x");', "Windows"),
            ('use std::include_str as a' + chr(0x0301) + '; a' + chr(0x0301) + '!("../../spec/x");', "requires review"),
        ):
            self.denied(source, reason=reason)

    def test_comments_strings_characters_and_raw_byte_strings_are_not_code(self):
        """Mutation: regex scans comment/string examples or loses raw-string boundaries."""
        source = '''/* nested /* include_str!("../../../spec/x") */ comment */
// include_bytes!("../../../spec/x")
const TEXT: &str = r##"include_str!("../../../spec/x")"##;
const BYTES: &[u8] = br#"include_str!("../../../spec/x")"#;
const CH: char = '"';
include_str!(r"../data.txt");'''
        counts, errors = self.inspect(source)
        self.assertEqual(errors, [])
        self.assertEqual(counts["references"], 1)

    def test_symlink_aliases_are_refused_even_when_the_target_is_internal(self):
        """Mutation: drop explicit symlink rejection because only external targets seem relevant."""
        self.inspect()
        alias = self.root / "link"
        alias.write_text("fixture", encoding="utf-8")
        original = Path.is_symlink
        with mock.patch.object(Path, "is_symlink", lambda path: path == alias or original(path)):
            self.assertTrue(any("symlink" in error for error in lift.check(self.root)[1]))
        lstat = Path.lstat
        def reparse(path):
            return SimpleNamespace(st_mode=0, st_file_attributes=0x400) if path == alias else lstat(path)
        with mock.patch.object(Path, "lstat", reparse):
            self.assertTrue(any("junction" in error for error in lift.check(self.root)[1]))

    def test_empty_malformed_and_oversized_sources_fail_closed(self):
        """Mutation: empty input, malformed tokens or over-limit source returns a clean result."""
        for source in ('/* unterminated', 'include_str!("../data.txt";', 'r' + '#' * 33 + '"x"' + '#' * 33):
            self.denied(source, reason="limit" if source.startswith("r") else "terminat")
        with mock.patch.object(lift, "MAX_FILE_BYTES", 4):
            self.denied(reason="exceeds")
        with tempfile.TemporaryDirectory() as empty:
            self.assertTrue(lift.check(Path(empty))[1])

    def test_unreadable_directories_and_excluded_output_references_fail_closed(self):
        """Mutation: let os.walk skip unreadable directories or permit references into omitted target/.git."""
        self.inspect()
        walk = lift.os.walk
        def blocked(*args, **kwargs):
            kwargs["onerror"](PermissionError(13, "denied", str(self.root / "blocked")))
            return walk(*args, **kwargs)
        with mock.patch.object(lift.os, "walk", side_effect=blocked):
            self.assertTrue(any("traversal failed" in error for error in lift.check(self.root)[1]))
        (self.root / "target").mkdir()
        (self.root / "target/data").write_text("fixture", encoding="utf-8")
        self.denied('include_str!("../target/data");', reason="excluded")

    def test_checker_does_not_invoke_cargo_or_other_subprocesses(self):
        """Mutation: invoke Cargo while checking paths instead of remaining an offline scanner."""
        with mock.patch.object(subprocess, "run", side_effect=AssertionError("subprocess forbidden")):
            self.assertEqual(self.inspect()[1], [])

    def test_ci_copies_outside_checkout_preserves_nested_targets_and_pins_commands(self):
        """Mutation: build original checkout, omit nested target sources, or drop the pinned offline locked commands."""
        workflow = Path(__file__).parents[3] / ".github/workflows/rust.yml"
        step = workflow.read_text(encoding="utf-8").split("      - name: Prove copied Rust workspace\n", 1)[1].split("\n      - name:", 1)[0]
        self.assertIn("        shell: python", step)
        script = textwrap.dedent(step.split("        run: |\n", 1)[1])
        self.inspect()
        for directory in ("target", "src/target"):
            (self.root / directory).mkdir()
            (self.root / directory / "kept.rs").write_text("fixture", encoding="utf-8")
        calls = []
        def capture(command, *, cwd, env, check, timeout):
            copied = Path(cwd)
            self.assertFalse(copied.is_relative_to(self.root))
            self.assertEqual((copied / "src/lib.rs").read_bytes(), (self.root / "src/lib.rs").read_bytes())
            self.assertTrue((copied / "src/target/kept.rs").is_file())
            self.assertFalse((copied / "target/kept.rs").exists())
            self.assertEqual(env["CARGO_NET_OFFLINE"], "true")
            self.assertEqual(env["CARGO_TARGET_DIR"], str(copied / "target"))
            self.assertTrue(check)
            self.assertEqual(timeout, 300)
            calls.append(command)
        with chdir(self.root.parent), mock.patch.object(subprocess, "run", side_effect=capture):
            exec(compile(script, str(workflow), "exec"), {})
        self.assertEqual(calls, [["cargo", "+1.85.1", command, "--workspace", "--locked"] for command in ("build", "test")])
