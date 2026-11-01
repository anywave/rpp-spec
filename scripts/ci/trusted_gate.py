"""Run BASE policy over HEAD objects as data; owner identities are Git claims."""
import argparse
import fnmatch
import importlib.util
import json
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile

HERE = Path(__file__).absolute()
ALLOW = '.github/codex-gate-allow.txt'
OWNERS = '.github/codex-gate-owners.txt'


def git_bytes(*args):
    command = ['git', '--literal-pathspecs', *args]
    with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL) as process:
        data = process.stdout.read(8 * 1024 * 1024 + 1)
        if len(data) > 8 * 1024 * 1024:
            process.kill()
            raise ValueError('Git output exceeds 8 MiB')
        code = process.wait()
        if code:
            raise subprocess.CalledProcessError(code, command)
        return data


def base_lines(base, path):
    entry = git_bytes('ls-tree', base, '--', path).split()
    if not entry:
        return set()
    if entry[0] not in {b'100644', b'100755'} or entry[1] != b'blob':
        raise ValueError(f'{path}: BASE policy must be a regular blob')
    return {line for line in git_bytes('cat-file', 'blob', f'{base}:{path}').decode('utf-8').splitlines() if line and not line.startswith('#')}


def prepare(base, head, pr):
    base = git_bytes('rev-parse', '--verify', '--end-of-options', f'{base}^{{commit}}').decode().strip()
    root = Path(git_bytes('rev-parse', '--show-toplevel').decode().strip()).resolve()
    if git_bytes('rev-parse', 'HEAD').decode().strip() != base or HERE != root / 'scripts/ci/trusted_gate.py':
        raise ValueError('trusted runner requires its BASE checkout')
    for path in ('scripts/ci/gate.py', 'scripts/ci/trusted_gate.py'):
        target = root / path
        entry = git_bytes('ls-tree', base, '--', path).split()
        if not entry or entry[0] not in {b'100644', b'100755'} or not stat.S_ISREG(target.lstat().st_mode):
            raise ValueError(f'{path}: regular BASE code required')
        if target.read_bytes().replace(b'\r\n', b'\n') != git_bytes('cat-file', 'blob', f'{base}:{path}').replace(b'\r\n', b'\n'):
            raise ValueError(f'{path}: code differs from BASE')
    if not re.fullmatch(r'[0-9a-fA-F]{40}', head):
        raise ValueError('head must be a full commit SHA')
    if pr is not None:
        if not re.fullmatch(r'[1-9][0-9]*', str(pr)):
            raise ValueError('invalid PR number')
        git_bytes('fetch', '--no-tags', '--no-recurse-submodules', 'origin', f'pull/{pr}/head')
        if git_bytes('rev-parse', 'FETCH_HEAD^{commit}').decode().strip() != head.lower():
            raise ValueError('fetched PR head differs from event head')
    resolved = git_bytes('rev-parse', '--verify', '--end-of-options', f'{head}^{{commit}}').decode().strip()
    if resolved != head.lower():
        raise ValueError('head must identify that exact commit')
    spec = importlib.util.spec_from_file_location('_codex_gate_base', root / 'scripts/ci/gate.py')
    gate = importlib.util.module_from_spec(spec)
    exec(compile(git_bytes('cat-file', 'blob', f'{base}:scripts/ci/gate.py'), str(root / 'scripts/ci/gate.py'), 'exec'), gate.__dict__)
    return base, resolved, gate


def export_metadata(directory, head):
    for record in git_bytes('ls-tree', '-r', '-z', head).split(b'\0'):
        if not record:
            continue
        header, raw_path = record.split(b'\t', 1)
        mode, kind, digest = header.split()
        name = raw_path.rsplit(b'/', 1)[-1]
        if not (name in {b'action.yml', b'action.yaml'} or raw_path.startswith(b'.github/') and raw_path.endswith((b'.yml', b'.yaml'))):
            continue
        path = raw_path.decode('utf-8')
        if path.startswith('/') or '\\' in path or ':' in path or any(part in {'', '.', '..'} for part in path.split('/')):
            raise ValueError(f'unsafe metadata path: {ascii(path)}')
        if mode not in {b'100644', b'100755'} or kind != b'blob':
            raise ValueError(f'metadata must be a regular blob: {ascii(path)}')
        if int(git_bytes('cat-file', '-s', digest.decode())) > 1024 * 1024:
            raise ValueError(f'metadata exceeds 1 MiB: {ascii(path)}')
        target = directory / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(git_bytes('cat-file', 'blob', digest.decode()))


def owner_findings(base, head):
    ancestor = git_bytes('merge-base', base, head).decode().strip()
    paths = [path.decode('utf-8') for path in git_bytes('diff', '--no-renames', '--name-only', '-z', ancestor, head).split(b'\0') if path]
    protected = [path for path in paths if path == 'scripts/ci' or path.startswith('scripts/ci/') or path == '.github' or path.startswith('.github/') or Path(path).name.startswith('codex-gate') or fnmatch.fnmatchcase(Path(path).name, 'requirements*.txt')]
    if not protected:
        return []
    owners = base_lines(base, OWNERS)
    if any(not re.fullmatch(r'[^<>\r\n]+ <[^<>\r\n]+>', owner) for owner in owners):
        raise ValueError('BASE owners must be exact Name <email> entries')
    if int(git_bytes('cat-file', '-s', head)) > 1024 * 1024:
        raise ValueError('commit object exceeds 1 MiB')
    headers = git_bytes('cat-file', 'commit', head).split(b'\n\n', 1)[0].split(b'\n')
    identities = {line.split(b' ', 1)[1].rsplit(b' ', 2)[0].decode('utf-8') for line in headers if line.startswith((b'author ', b'committer '))}
    return [] if identities & owners else [f'{ascii(path)}: gate change: needs TR review' for path in protected]


def run(base, head, pr=None):
    base, head, gate = prepare(base, head, pr)
    allow = base_lines(base, ALLOW)
    if ALLOW in allow:
        raise ValueError('BASE allow file cannot exempt itself')
    result = {'base': base, 'head': head, 'checks': [], 'findings': 0}
    try:
        total_findings = gate.total(Path('.'), base, head, allow)
    except Exception as error:
        total_findings = [f'gate tool error: {ascii(str(error))}']
    with tempfile.TemporaryDirectory(prefix='codex-gate-data-') as directory:
        metadata = Path(directory)
        export_error = 'metadata review blocked by PR-total finding' if total_findings else None
        try:
            if not export_error:
                export_metadata(metadata, head)
        except Exception as error:
            export_error = f'metadata export: {ascii(str(error))}'
        checks = [
            ('actions', lambda: gate.actions(metadata, base, head, allow)),
            ('permissions', lambda: gate.permissions(metadata, base, head, allow)),
            ('slices', lambda: gate.slices(Path('.'), base, head, allow)),
            ('pr_total', lambda: total_findings),
            ('readable', lambda: gate.readable(Path('.'), base, head, allow)),
            ('travel', lambda: gate.travel(Path('.'), base, head, allow)),
            ('protected', lambda: owner_findings(base, head)),
        ]
        for name, check in checks:
            try:
                findings = [export_error] if export_error and name in {'actions', 'permissions'} else check()
            except Exception as error:
                findings = [f'gate tool error: {ascii(str(error))}']
            findings = [finding.replace(str(metadata) + '/', '') for finding in findings]
            result['checks'].append({'check': name, 'findings': findings})
            result['findings'] += len(findings)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', required=True)
    parser.add_argument('--head', required=True)
    parser.add_argument('--pr')
    parser.add_argument('--output')
    args = parser.parse_args()
    try:
        result = run(args.base, args.head, args.pr)
    except Exception as error:
        result = {'checks': [{'check': 'trusted_runner', 'findings': [f'gate tool error: {ascii(str(error))}']}], 'findings': 1}
    text = json.dumps(result, indent=2, sort_keys=True, ensure_ascii=True) + '\n'
    print(text, end='')
    if args.output:
        destination = Path(args.output).absolute()
        root = Path(git_bytes('rev-parse', '--show-toplevel').decode().strip()).resolve()
        if destination.resolve().is_relative_to(root):
            raise ValueError('receipt must be outside the checkout')
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(text, encoding='utf-8')
    return bool(result['findings'])


if __name__ == '__main__':
    sys.exit(main())
