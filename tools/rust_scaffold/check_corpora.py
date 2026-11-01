"""Regenerate all Rust Python-oracle files outside the checkout and compare bytes.

The oracle provenance contract is Python 3.12.x with Unicode 15.0.0. CI pins
the available patch release on each OS. A different runtime is a tool error,
never a reason to ignore manifest fields or rewrite committed oracle data.
Use --python to select that reference engine when launching from Python 3.13.
This checker and its generator dependencies use only the Python standard library.
"""

import argparse
from dataclasses import dataclass
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


REFERENCE_PYTHON = (3, 12)
REFERENCE_UNICODE = "15.0.0"


@dataclass(frozen=True)
class CorpusGroup:
    name: str
    module: str
    destination: str
    # Generated filename -> committed filename. No contents are normalized.
    files: tuple[tuple[str, str], ...]


GROUPS = (
    CorpusGroup("address", "tools.rust_scaffold.address_corpus", "rust/rpp-core/tests/data", (
        ("address-construct.tsv", "address-construct.tsv"),
        ("address-raw.tsv", "address-raw.tsv"),
        ("address-uri.tsv", "address-uri.tsv"),
        ("address-manifest.json", "address-manifest.json"),
    )),
    CorpusGroup("overlay", "tools.overlay_sim.scenarios", "rust/rpp-core/tests/data", (
        ("scenarios.csv", "overlay-scenarios.csv"),
        ("SCENARIOS.md", "overlay-scenarios.md"),
        ("billboards.json", "overlay-billboards.json"),
    )),
    CorpusGroup("control", "tools.esp32_scaffold.control_corpus", "rust/rpp-control/tests/data", (
        ("control-corpus.tsv", "control-corpus.tsv"),
        ("control-manifest.json", "control-manifest.json"),
    )),
)


class CheckerError(Exception):
    """Runtime, generator or temporary-directory failure; not a freshness pass."""


@dataclass(frozen=True)
class CheckResult:
    checked: int
    differences: tuple[str, ...]
    python_version: tuple[int, ...]
    unicode_version: str

    @property
    def fresh(self):
        return not self.differences


def reference_environment(python, repo, environment):
    code = "import json,sys,unicodedata; print(json.dumps({'python':list(sys.version_info[:3]),'unicode':unicodedata.unidata_version}))"
    try:
        result = subprocess.run([str(python), "-c", code], cwd=repo, env=environment,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                encoding="utf-8", check=False, timeout=60)
        metadata = json.loads(result.stdout)
        version = tuple(metadata["python"])
        unicode_version = metadata["unicode"]
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        raise CheckerError("cannot inspect the reference Python engine") from error
    if result.returncode or len(version) != 3 or any(type(value) is not int for value in version):
        raise CheckerError("cannot inspect the reference Python engine")
    return version, unicode_version


def require_reference_environment(version, unicode_version):
    if version[:2] != REFERENCE_PYTHON or unicode_version != REFERENCE_UNICODE:
        raise CheckerError(
            "reference engine required: Python 3.12.x with Unicode 15.0.0; "
            f"got Python {'.'.join(map(str, version))}, Unicode {unicode_version}. "
            "Select Python 3.12 with --python; manifests are compared without exclusions."
        )


def run_generator(python, repo, environment, group, destination):
    try:
        result = subprocess.run(
            [str(python), "-m", group.module, "--output-dir", str(destination)],
            cwd=repo, env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            encoding="utf-8", check=False, timeout=60,
        )
    except (OSError, UnicodeError, subprocess.SubprocessError) as error:
        raise CheckerError(f"cannot execute {group.name} generator") from error
    if result.returncode:
        raise CheckerError(f"{group.name} generator failed with exit {result.returncode}")


def check(repo, python=None, temp_root=None):
    repo = Path(repo).resolve()
    python = sys.executable if python is None else python
    temporary_parent = Path(tempfile.gettempdir() if temp_root is None else temp_root).resolve()
    if temporary_parent == repo or repo in temporary_parent.parents:
        raise CheckerError("temporary directory must be outside the checkout")
    if not temporary_parent.is_dir():
        raise CheckerError("temporary directory parent does not exist")
    environment = dict(os.environ, PYTHONPATH=str(repo), PYTHONIOENCODING="utf-8",
                       PYTHONDONTWRITEBYTECODE="1", PYTHONHASHSEED="0")
    version, unicode_version = reference_environment(python, repo, environment)
    require_reference_environment(version, unicode_version)
    differences = []
    checked = 0
    expected_by_directory = {}
    for group in GROUPS:
        expected_by_directory.setdefault(group.destination, set()).update(name for _, name in group.files)

    with tempfile.TemporaryDirectory(prefix="rpp-corpora-check-", dir=temporary_parent) as scratch:
        for group in GROUPS:
            output = Path(scratch) / group.name
            run_generator(python, repo, environment, group, output)
            generated_names = {path.name for path in output.iterdir()}
            expected_generated = {name for name, _ in group.files}
            for name in sorted(generated_names - expected_generated):
                differences.append(f"unexpected generated {group.name}/{name}")
            for generated, committed in group.files:
                checked += 1
                saved = repo / group.destination / committed
                fresh = output / generated
                label = f"{group.destination}/{committed}"
                if saved.is_symlink() or fresh.is_symlink():
                    differences.append(f"non-regular {label}")
                elif not saved.is_file():
                    differences.append(f"missing {label}")
                elif not fresh.is_file():
                    differences.append(f"missing regenerated {label}")
                elif saved.read_bytes() != fresh.read_bytes():
                    differences.append(f"changed {label}")
        for directory, names in expected_by_directory.items():
            location = repo / directory
            if location.is_dir():
                for path in sorted(location.iterdir()):
                    if path.name not in names:
                        differences.append(f"unexpected {directory}/{path.name}")
    return CheckResult(checked, tuple(sorted(differences)), version, unicode_version)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--python", default=sys.executable, help="Python 3.12 reference engine")
    parser.add_argument("--temp-root", type=Path, help="existing temporary parent outside the checkout")
    args = parser.parse_args(argv)
    try:
        result = check(args.repo, args.python, args.temp_root)
    except (CheckerError, OSError, UnicodeError) as error:
        print(f"corpora: tool error: {error}", file=sys.stderr)
        return 2
    if result.fresh:
        print(f"corpora: fresh; {result.checked} files byte-identical; "
              f"Python {'.'.join(map(str, result.python_version))}; Unicode {result.unicode_version}")
        return 0
    print(f"corpora: STALE; {len(result.differences)} differences across {result.checked} expected files")
    for difference in result.differences:
        print(difference)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
