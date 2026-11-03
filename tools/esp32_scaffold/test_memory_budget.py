"""Native, offline RISC-V reservation witnesses; never a hardware stack measurement."""
import argparse
from pathlib import Path
import re
import sys
import tempfile
import unittest

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.esp32_scaffold import check_no_std as guard

RISCV = "riscv32imc-unknown-none-elf"
REPO = Path(__file__).resolve().parents[2]
CAPS = (("BILLBOARD_USED", 2035, "RPP_BILLBOARD_BUDGET_EXCEEDED"),
        ("FRAG_USED", 1232, "RPP_FRAG_BUDGET_EXCEEDED"),
        ("STEER_USED", 942, "RPP_STEER_BUDGET_EXCEEDED"))
OPTIONS = argparse.Namespace(cargo=None, rustc=None, sysroot=None, work_dir=None,
                             require_riscv=False)


def qualify(result, required):
    status, target = result.get("status"), result.get("target")
    if status == "PASS" and target == RISCV and result.get("budget_status") == "PASS":
        return
    reason = "native RISC-V budget not checked: " + result.get("reason", "invalid check result")
    if not required and (status == "SKIP" and target is None
                         or status == "PASS" and target == guard.TARGETS[1]
                         and result.get("budget_status") == "NOT_RISCV"):
        raise unittest.SkipTest(reason)
    raise RuntimeError(reason)


class QualificationTests(unittest.TestCase):
    def test_only_absence_or_known_thumb_can_skip_optional_native_tests(self):
        """Mutations: skip broken/unknown results or accept unavailable required RISC-V."""
        cases = (("SKIP", None, None, unittest.SkipTest),
                 ("PASS", guard.TARGETS[1], "NOT_RISCV", unittest.SkipTest),
                 ("SKIP", RISCV, None, RuntimeError),
                 ("PASS", guard.TARGETS[1], "PASS", RuntimeError),
                 ("FAIL", None, None, RuntimeError),
                 ("UNKNOWN", None, None, RuntimeError),
                 ("PASS", "x86_64-unknown-linux-gnu", "PASS", RuntimeError),
                 ("PASS", RISCV, "NOT_RISCV", RuntimeError),
                 ("PASS", RISCV, "PASS", None))
        for status, target, budget, expected in cases:
            for required in (False, True):
                with self.subTest(status=status, target=target, budget=budget, required=required):
                    error_type = None
                    try:
                        qualify(dict(status=status, target=target, budget_status=budget), required)
                    except (RuntimeError, unittest.SkipTest) as error:
                        error_type = type(error)
                    wanted = RuntimeError if required and expected is unittest.SkipTest else expected
                    self.assertIs(error_type, wanted)


class NativeMemoryBudgetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if OPTIONS.work_dir is None:
            temporary = tempfile.TemporaryDirectory(prefix="rpp-budget-native-")
            cls.addClassCleanup(temporary.cleanup)
            cls.work = Path(temporary.name).resolve()
        else:
            cls.work = OPTIONS.work_dir.resolve()
        cls.result = guard.check(REPO,
                                 cargo=[str(OPTIONS.cargo.resolve())] if OPTIONS.cargo else None,
                                 rustc=[str(OPTIONS.rustc.resolve())] if OPTIONS.rustc else None,
                                 sysroot=OPTIONS.sysroot, work_dir=cls.work)
        qualify(cls.result, OPTIONS.require_riscv)
        cls.rustc = [cls.result["probe_command"][0]]
        cls.environment = guard.environment()
        cls.source = guard.PROBE.read_text(encoding="utf-8")

    def test_baseline_reports_only_actual_riscv_budget_pass(self):
        """Mutations: misreport the target/budget verdict or omit the actual probe build."""
        self.assertEqual(self.result["status"], "PASS")
        self.assertEqual(self.result["target"], RISCV)
        self.assertEqual(self.result["budget_status"], "PASS")
        command = self.result["probe_command"]
        self.assertIn(str(guard.PROBE.resolve()), command)
        self.assertEqual(command[command.index("--target") + 1], RISCV)
        self.assertTrue((self.work / "memory_probe.ll").is_file())

    def test_exact_caps_pass_and_cap_plus_one_requires_named_budget_errors(self):
        """Mutations: ablate any reservation assertion or reject equality at its cap."""
        cases = Path(tempfile.mkdtemp(prefix="budget-cases-", dir=self.work)).resolve()
        for name, cap, marker in CAPS:
            for used in (cap, cap + 1):
                with self.subTest(reservation=name, used=used):
                    pattern = r"const\s+" + name + r":\s*usize\s*=\s*[^;]+;"
                    source, count = re.subn(pattern, f"const {name}: usize = {used};", self.source)
                    if count != 1:
                        raise RuntimeError("missing or ambiguous reservation source: " + name)
                    probe = cases / f"{name}-{used}.rs"
                    with probe.open("x", encoding="utf-8", newline="\n") as stream:
                        stream.write(source)
                    rejected = False
                    try:
                        guard.compile_probe(self.rustc, RISCV, OPTIONS.sysroot,
                                            self.work, self.environment, probe=probe)
                    except guard.CheckError as error:
                        diagnostic = str(error)
                        if not ("error[E0080]" in diagnostic and marker in diagnostic
                                and "the evaluated program panicked at" in diagnostic):
                            raise
                        rejected = True
                    self.assertEqual(rejected, used > cap,
                                     f"{name}: {used} bytes at declared cap {cap}")


def main():
    global OPTIONS
    parser = argparse.ArgumentParser(description=__doc__)
    for option in ("cargo", "rustc", "sysroot", "work-dir"):
        parser.add_argument("--" + option, type=Path)
    parser.add_argument("--require-riscv", action="store_true",
                        help="Fail instead of skipping when actual RISC-V compilation is unavailable")
    parser.add_argument("tests", nargs="*", help="Optional bounded unittest method selectors")
    OPTIONS = parser.parse_args()
    result = unittest.main(module=__name__, argv=[sys.argv[0], *OPTIONS.tests],
                           verbosity=2, exit=False).result
    return int(not result.wasSuccessful())


if __name__ == "__main__":
    raise SystemExit(main())
