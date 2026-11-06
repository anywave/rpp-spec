"""Explicit local build of the optional CPython Hedera signer owner.

The default package and wheel remain pure Python. This helper uses the active
interpreter's compiler settings and never reads Hedera configuration or keys.
"""
from __future__ import annotations

import argparse
import os
import shlex
import shutil
import subprocess
import sys
import sysconfig
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "rpp" / "adapters" / "_hedera_signer_native.c"


def build_native(output_dir: Path | None = None, source: Path | None = None) -> Path:
    """Build for this GIL-enabled CPython; return the extension's local path."""
    if (sys.implementation.name != "cpython" or
            sysconfig.get_config_var("Py_GIL_DISABLED") or sys.version_info < (3, 10)):
        raise RuntimeError("Native Hedera signing requires GIL-enabled CPython >=3.10")
    if os.name != "posix":
        raise RuntimeError("The experimental local native builder requires POSIX")
    source = Path(source or SOURCE).resolve()
    output_dir = Path(output_dir or SOURCE.parent).resolve()
    suffix = sysconfig.get_config_var("EXT_SUFFIX")
    include = sysconfig.get_path("include")
    linker = sysconfig.get_config_var("LDSHARED")
    if not suffix or not include or not linker:
        raise RuntimeError("CPython native compiler configuration is unavailable")
    output_dir.mkdir(parents=True, exist_ok=True)
    destination = output_dir / ("_hedera_signer_native" + suffix)
    linker_command = shlex.split(linker)
    if os.environ.get("CC"):
        linker_command[:1] = shlex.split(os.environ["CC"])
    elif not shutil.which(linker_command[0]):
        compiler = shutil.which("cc")
        if compiler is None:
            raise RuntimeError("A compatible C compiler is unavailable")
        linker_command[0] = compiler
    command = (linker_command +
               shlex.split(sysconfig.get_config_var("CFLAGS") or "") +
               shlex.split(sysconfig.get_config_var("CCSHARED") or "") +
               ["-I" + include, str(source)])
    # Replace atomically: a failed build must not truncate an imported extension.
    with tempfile.TemporaryDirectory(prefix="rpp-hedera-native-", dir=output_dir) as temporary:
        artifact = Path(temporary) / destination.name
        subprocess.run(command + ["-o", str(artifact)], check=True)
        artifact.replace(destination)
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--source", type=Path)
    arguments = parser.parse_args()
    try:
        build_native(arguments.output_dir, arguments.source)
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        raise SystemExit("Native Hedera signer build failed; install a compatible CPython compiler toolchain") from error
    print("Native Hedera signer built for the active CPython interpreter")


if __name__ == "__main__":
    main()
