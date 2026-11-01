"""Offline PR checks; Git arguments are never interpreted by a shell."""
import argparse
from pathlib import Path
import re
import subprocess
import sys

import yaml

SOURCE = {'.py', '.rs', '.v', '.sv', '.c', '.h', '.cpp', '.js', '.ts', '.tsx', '.jsx', '.go', '.hs', '.sh'}
IGNORABLE = [(0xad, 0xad), (0x34f, 0x34f), (0x61c, 0x61c), (0x115f, 0x1160), (0x17b4, 0x17b5), (0x180b, 0x180f), (0x200b, 0x200f), (0x202a, 0x202e), (0x2060, 0x206f), (0x3164, 0x3164), (0xfe00, 0xfe0f), (0xfeff, 0xfeff), (0xffa0, 0xffa0), (0xfff0, 0xfff8), (0x1bca0, 0x1bca3), (0x1d173, 0x1d17a), (0xe0000, 0xe0fff)]


def git(*args):
    return subprocess.check_output(['git', '--literal-pathspecs', *args]).decode('utf-8')


def pairs(node):
    if not isinstance(node, yaml.MappingNode):
        raise ValueError('expected YAML mapping')
    result = {}
    for key, value in node.value:
        if not isinstance(key, yaml.ScalarNode) or key.value in result:
            raise ValueError(f'{key.start_mark.name}:{key.start_mark.line + 1}: complex or duplicate YAML key')
        result[key.value] = value
    return result


def walk(node, seen=None):
    seen = set() if seen is None else seen
    if node is None or id(node) in seen:
        return
    seen.add(id(node))
    yield node
    children = pairs(node).values() if isinstance(node, yaml.MappingNode) else node.value if isinstance(node, yaml.SequenceNode) else []
    for child in children:
        yield from walk(child, seen)


def documents(root):
    for path in sorted((root / '.github').rglob('*')):
        if path.suffix in {'.yml', '.yaml'}:
            if path.is_symlink():
                raise ValueError(f'{path}: symlink YAML refused')
            with path.open(encoding='utf-8') as stream:
                yield path, yaml.compose(stream, Loader=yaml.SafeLoader)


def actions(root, base, head, allow):
    errors = []
    for path, document in documents(root):
        for node in walk(document):
            if isinstance(node, yaml.MappingNode) and 'uses' in pairs(node):
                value = pairs(node)['uses']
                if not isinstance(value, yaml.ScalarNode) or not re.fullmatch(r'(?:\./\S+|[^\s/@]+/[^\s@]+@[0-9a-fA-F]{40})', value.value):
                    errors.append(f'{ascii(str(path))}:{value.start_mark.line + 1}: unpinned uses')
    return errors


def writes(node):
    if isinstance(node, yaml.MappingNode):
        values = [value.value if isinstance(value, yaml.ScalarNode) else '' for value in pairs(node).values()]
        if any(value not in {'read', 'write', 'none'} for value in values):
            raise ValueError('invalid permissions value')
        return 'write' in values
    if not isinstance(node, yaml.ScalarNode) or node.value != 'read-all':
        raise ValueError('missing permissions or write-all/unknown permissions')
    return False


def permissions(root, base, head, allow):
    errors = []
    for path, document in documents(root):
        if path.parent != root / '.github/workflows':
            continue
        top = pairs(document)
        try:
            writes(top.get('permissions'))
            for name, job in pairs(top.get('jobs')).items():
                fields = pairs(job)
                if not writes(fields.get('permissions', top['permissions'])):
                    continue
                nodes = list(walk(job)) + list(walk(top.get('env')))
                inherited = fields.get('secrets')
                if inherited is not None and getattr(inherited, 'value', '') == 'inherit':
                    errors.append(f'{ascii(str(path))}:{inherited.start_mark.line + 1}: {ascii(name)}: secrets inherit with write')
                for node in nodes:
                    if isinstance(node, yaml.ScalarNode):
                        text = re.sub(r'\bsecrets\s*(?:\.\s*GITHUB_TOKEN\b|\[\s*([\'"])GITHUB_TOKEN\1\s*\])', '', node.value, flags=re.I)
                        if '${{' in text and re.search(r'\bsecrets\b', text, re.I):
                            errors.append(f'{ascii(str(path))}:{node.start_mark.line + 1}: {ascii(name)}: secret with write')
        except (ValueError, AttributeError) as error:
            errors.append(f'{ascii(str(path))}:1: {ascii(str(error))}')
    return errors


def message(commit):
    return git('cat-file', 'commit', commit).partition('\n\n')[2]


def commits(base, head):
    return git('rev-list', '--reverse', f'{base}..{head}').splitlines()


def changed(base, head, *options):
    return git('diff', '--no-renames', '--name-only', '-z', *options, base, head).split('\0')[:-1]


def slice_counts(records, allow):
    files = lines = 0
    for record in records.split('\0')[:-1]:
        added, deleted, path = record.split('\t', 2)
        if path not in allow:
            files += 1
            lines += int(added) + int(deleted) if added != '-' else 401
    return files, lines


def slices(root, base, head, allow):
    errors = []
    for commit in commits(base, head):
        records = git('diff-tree', '--root', '--no-commit-id', '-m', '--first-parent', '--numstat', '-z', '-r', '--no-renames', commit)
        files, lines = slice_counts(records, allow)
        if files > 10 or lines > 400:
            errors.append(f'{commit}: files={files} lines={lines}; cap=10/400 (binary=401)')
    return errors


def unreadable(text, path, line):
    return [f'{ascii(str(path))}:{line}: U+{ord(char):04X}' for char in text if ord(char) == 27 or any(lo <= ord(char) <= hi for lo, hi in IGNORABLE)]


def readable(root, base, head, allow):
    errors = []
    for path in changed(base, head):
        if path in allow:
            continue
        errors += unreadable(path, path, 0)
        old = new = 0
        active = False
        for line in git('diff', '--no-ext-diff', '--no-textconv', '--text', '--no-color', '--no-renames', '--unified=0', base, head, '--', path).split('\n'):
            hunk = re.match(r'@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@', line)
            if hunk:
                old, new = map(int, hunk.groups())
                active = True
            elif active and line.startswith(('+', '-')):
                errors += unreadable(line[1:], path, new if line[0] == '+' else old)
                old += line[0] == '-'
                new += line[0] == '+'
    for commit in commits(base, head):
        for number, line in enumerate(message(commit).split('\n'), 1):
            errors += unreadable(line, commit, number)
    return errors


def test_path(path):
    p = Path(path)
    return p.suffix in SOURCE and ('tests' in p.parts or 'test' in p.parts or p.name.startswith('test_') or re.search(r'(?:_test|\.test)\.', p.name))


def travel(root, base, head, allow):
    if any(test_path(path) for path in changed(base, head, '--diff-filter=AM')):
        return []
    errors = []
    for commit in commits(base, head):
        paths = git('diff-tree', '--root', '--no-commit-id', '-m', '--first-parent', '--name-only', '-z', '-r', commit).split('\0')[:-1]
        if any(Path(path).suffix in SOURCE and not test_path(path) for path in paths) and not re.search(r'(?m)^no-test:\s*\S[^\n]*$', message(commit)):
            errors.append(f'{commit}: source changed without PR test file or no-test: reason')
    return errors


def main(check):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', required=True)
    parser.add_argument('--head', required=True)
    args = parser.parse_args()
    try:
        base, head = [git('rev-parse', '--verify', '--end-of-options', f'{ref}^{{commit}}').strip() for ref in (args.base, args.head)]
        prior = subprocess.run(['git', 'show', f'{base}:.github/codex-gate-allow.txt'], capture_output=True)
        allow = {line for line in prior.stdout.decode('utf-8').splitlines() if line and not line.startswith('#')}
        if '.github/codex-gate-allow.txt' in allow:
            raise ValueError('allow file cannot exempt itself')
        errors = globals()[check](Path('.'), base, head, allow)
    except (ValueError, UnicodeError, yaml.YAMLError, subprocess.CalledProcessError) as error:
        errors = [f'gate tool error: {ascii(str(error))}']
    for error in errors:
        print(error)
    print(f'{check}: findings={len(errors)}')
    sys.exit(bool(errors))
