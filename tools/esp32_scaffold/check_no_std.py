"""Compile the three bare embedded libraries using installed tools only."""
import argparse
import json
import os
import re
import signal
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
import time

PIN = '1.85.1'
TARGETS = ('riscv32imc-unknown-none-elf', 'thumbv7em-none-eabihf')
PACKAGES = ('rpp-billboard', 'rpp-frag', 'rpp-steer')
OUTPUT_LIMIT = 1024 * 1024
PROBE = Path(__file__).resolve().with_name('memory_probe.rs')


class CheckError(RuntimeError):
    """A present tool, installation or build failed; never a skip."""


def stop(process):
    try:
        if os.name == 'nt':
            try:
                subprocess.run(['taskkill', '/F', '/T', '/PID', str(process.pid)],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
            except (OSError, subprocess.TimeoutExpired):
                pass
        else:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
    finally:
        if process.poll() is None:
            process.kill()
        process.wait(timeout=10)


def execute(command, env, timeout=30):
    output = bytearray()
    done = threading.Event()
    failures = []
    options = {'creationflags': subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == 'nt' else {'start_new_session': True}
    try:
        with subprocess.Popen(command, env=env, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, bufsize=0, **options) as process:
            def drain():
                try:
                    while True:
                        block = process.stdout.read(min(65536, OUTPUT_LIMIT + 1 - len(output)))
                        if not block:
                            break
                        output.extend(block)
                        if len(output) > OUTPUT_LIMIT:
                            failures.append('tool output limit exceeded')
                            break
                except (OSError, ValueError):
                    failures.append('tool output read failed')
                finally:
                    done.set()
            reader = threading.Thread(target=drain, daemon=True)
            reader.start()
            deadline = time.monotonic() + timeout
            try:
                if not done.wait(timeout):
                    raise subprocess.TimeoutExpired(command, timeout)
                if failures:
                    raise CheckError(failures[0])
                process.wait(timeout=max(0, deadline - time.monotonic()))
                if process.returncode:
                    raise CheckError(f'tool exited {process.returncode}: {output.decode("utf-8", errors="replace")}')
                return output.decode('utf-8')
            except (CheckError, OSError, UnicodeError, subprocess.TimeoutExpired):
                stop(process)
                raise
            finally:
                process.stdout.close()
                reader.join(timeout=1)
    except (OSError, UnicodeError, subprocess.TimeoutExpired) as error:
        raise CheckError(f'tool invocation failed: {error}') from error


def environment():
    env = dict(os.environ)
    for key in ('RUSTFLAGS', 'CARGO_ENCODED_RUSTFLAGS', 'RUSTC_WRAPPER',
                'RUSTC_WORKSPACE_WRAPPER', 'RUSTC_BOOTSTRAP'):
        env.pop(key, None)
    env.update(RUSTUP_AUTO_INSTALL='0', RUSTUP_TOOLCHAIN=PIN, CARGO_NET_OFFLINE='true')
    return env


def discover(env):
    rustup = shutil.which('rustup')
    if rustup:
        listing = execute([rustup, 'toolchain', 'list'], env)
        if any(not char.isprintable() and char not in '\r\n' for char in listing):
            raise CheckError('malformed installed toolchain list')
        if listing.strip() == 'no installed toolchains':
            return None
        installed = [re.fullmatch(r'(\S+)(?: \([^()\r\n]+\))?', line) for line in listing.strip().splitlines()]
        if not installed or not all(installed):
            raise CheckError('malformed installed toolchain list')
        if not any(item[1] == PIN or item[1].startswith(PIN + '-') for item in installed):
            return None
        paths = [execute([rustup, 'which', '--toolchain', PIN, name], env).strip()
                 for name in ('cargo', 'rustc')]
    else:
        paths = [shutil.which(name) for name in ('cargo', 'rustc')]
        if not any(paths):
            return None
    if not all(path and Path(path).is_file() for path in paths):
        raise CheckError('partial or broken installed Rust toolchain')
    return [paths[0]], [paths[1]]


def installed_target(rustc, sysroot, env):
    for target in TARGETS:
        command = rustc + (['--sysroot', str(sysroot)] if sysroot else [])
        value = execute(command + ['--print', 'target-libdir', '--target', target], env).removesuffix('\n').removesuffix('\r')
        directory = Path(value)
        if not directory.is_absolute() or not value.isprintable():
            raise CheckError('malformed target library path')
        if not directory.exists():
            if directory.is_symlink() or directory.parent.exists() or directory.parent.is_symlink():
                raise CheckError('partial or broken target installation')
            continue
        if not directory.is_dir():
            raise CheckError(f'target library path is not a directory: {target}')
        for component in ('core', 'compiler_builtins'):
            archives = list(directory.glob('lib' + component + '-*.rlib'))
            if len(archives) != 1 or not archives[0].is_file():
                raise CheckError(f'partial target installation: {target}/{component}')
            try:
                with archives[0].open('rb') as stream:
                    valid = stream.read(8) == b'!<arch>\n'
            except OSError as error:
                raise CheckError(f'unreadable target library: {target}/{component}') from error
            if not valid:
                raise CheckError(f'broken target library: {target}/{component}')
        return target
    return None


def compile_probe(rustc, target, sysroot, work, env):
    library = work / 'target' / target / 'debug'
    command = rustc + (['--sysroot', str(sysroot)] if sysroot else [])
    command += ['--crate-name', 'rpp_readiness_layout', '--crate-type', 'lib',
                '--edition', '2021', '--target', target, '--emit=llvm-ir', str(PROBE),
                '-o', str(work / 'memory_probe.ll'), '-L', 'dependency=' + str(library / 'deps')]
    for package in PACKAGES:
        name = package.replace('-', '_')
        command += ['--extern', name + '=' + str(library / ('lib' + name + '.rlib'))]
    return command, execute(command, env)


def check(repo, cargo=None, rustc=None, sysroot=None, work_dir=None):
    repo = Path(repo).resolve()
    required = [PROBE] + [repo / 'rust' / name for name in ('Cargo.toml', 'Cargo.lock')]
    required += [repo / 'rust' / package / name for package in PACKAGES
                 for name in ('Cargo.toml', 'src/lib.rs')]
    if not all(path.is_file() for path in required):
        raise CheckError('probe, all three crate manifests/sources and the workspace lock are required')
    if (cargo is None) != (rustc is None):
        raise CheckError('explicit cargo and rustc must be supplied together')
    env = environment()
    if cargo is None:
        tools = discover(env)
        if tools is None:
            return {'status': 'SKIP', 'target': None, 'reason': 'installed Rust 1.85.1 tools are absent; no build ran'}
        cargo, rustc = tools
    if not cargo or not rustc:
        raise CheckError('empty compiler or Cargo command')
    for name, command in (('cargo', cargo), ('rustc', rustc)):
        raw_version = execute(command + ['--version'], env).removesuffix('\n').removesuffix('\r')
        if not raw_version.isprintable():
            raise CheckError('malformed tool version output')
        version = raw_version.split()
        if len(version) < 2 or version[:2] != [name, PIN]:
            raise CheckError(f'{name} must be exactly {PIN}')
    if sysroot is not None:
        sysroot = Path(sysroot).resolve()
        if not sysroot.is_dir():
            raise CheckError('explicit sysroot is missing or invalid')
    target = installed_target(rustc, sysroot, env)
    if target is None:
        return {'status': 'SKIP', 'target': None, 'reason': 'neither embedded target is installed; no build ran'}
    temporary = tempfile.TemporaryDirectory(prefix='rpp-embedded-check-') if work_dir is None else None
    work = Path(temporary.name if temporary else work_dir).resolve()
    protected = (repo, Path(__file__).resolve().parents[2], PROBE.resolve())
    try:
        if any(work == source or source in work.parents or work in source.parents for source in protected):
            raise CheckError('build/cache directory must be disjoint from checkout and probe sources')
        work.mkdir(parents=True, exist_ok=True)
        for directory in (work / 'cargo-home', work / 'target', work / 'memory_probe.ll'):
            resolved = directory.resolve()
            if any(resolved == source or source in resolved.parents or resolved in source.parents for source in protected):
                raise CheckError('derived output must be disjoint from checkout and probe sources')
        env.update(RUSTC=str(rustc[0]), CARGO_HOME=str(work / 'cargo-home'),
                   CARGO_TARGET_DIR=str(work / 'target'),
                   CARGO_ENCODED_RUSTFLAGS='\x1f'.join(['--sysroot', str(sysroot)]) if sysroot else '')
        command = cargo + ['build', '--manifest-path', str(repo / 'rust/Cargo.toml'), '--lib']
        for package in PACKAGES:
            command += ['-p', package]
        command += ['--no-default-features', '--target', target, '--offline', '--locked']
        output = execute(command, env, timeout=180)
        probe_command, probe_output = compile_probe(rustc, target, sysroot, work, env)
        return {'status': 'PASS', 'target': target, 'reason': 'three no-default libraries and safe memory probe compiled offline',
                'command': command, 'build_output': output,
                'probe_command': probe_command, 'probe_output': probe_output}
    finally:
        if temporary:
            temporary.cleanup()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--cargo', type=Path)
    parser.add_argument('--rustc', type=Path)
    parser.add_argument('--sysroot', type=Path)
    parser.add_argument('--work-dir', type=Path, help='Retain build/cache outside the checkout')
    args = parser.parse_args()
    try:
        result = check(args.repo, [str(args.cargo.resolve())] if args.cargo else None,
                       [str(args.rustc.resolve())] if args.rustc else None, args.sysroot, args.work_dir)
    except (CheckError, OSError) as error:
        result = {'status': 'FAIL', 'target': None, 'reason': str(error)}
    print(json.dumps(result, sort_keys=True, indent=2))
    return int(result['status'] == 'FAIL')


if __name__ == '__main__':
    raise SystemExit(main())
