"""Offline PR checks; Git arguments are never interpreted by a shell."""
import argparse
import ast
from pathlib import Path
import re
import subprocess
import sys
import tempfile

import yaml

SOURCE = {'.py', '.rs', '.v', '.sv', '.c', '.h', '.cpp', '.js', '.ts', '.tsx', '.jsx', '.go', '.hs', '.sh'}
IGNORABLE = [(0xad, 0xad), (0x34f, 0x34f), (0x61c, 0x61c), (0x115f, 0x1160), (0x17b4, 0x17b5), (0x180b, 0x180f), (0x200b, 0x200f), (0x202a, 0x202e), (0x2060, 0x206f), (0x3164, 0x3164), (0xfe00, 0xfe0f), (0xfeff, 0xfeff), (0xffa0, 0xffa0), (0xfff0, 0xfff8), (0x1bca0, 0x1bca3), (0x1d173, 0x1d17a), (0xe0000, 0xe0fff)]


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


def git(*args):
    return git_bytes(*args).decode('utf-8', errors='replace')


def pairs(node):
    if not isinstance(node, yaml.MappingNode):
        raise ValueError('expected YAML mapping')
    result = {}
    for key, value in node.value:
        if not isinstance(key, yaml.ScalarNode) or key.value in result or key.value == '<<':
            raise ValueError(f'{key.start_mark.name}:{key.start_mark.line + 1}: complex, duplicate or merge YAML key')
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
    paths = set((root / '.github').rglob('*')) | set(root.rglob('action.yml')) | set(root.rglob('action.yaml'))
    for path in sorted(paths):
        if path.is_file() and path.suffix in {'.yml', '.yaml'}:
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
                    errors.append(f'{ascii(path.relative_to(root).as_posix())}:{value.start_mark.line + 1}: unpinned uses')
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
                    errors.append(f'{ascii(path.relative_to(root).as_posix())}:{inherited.start_mark.line + 1}: {ascii(name)}: secrets inherit with write')
                for node in nodes:
                    if isinstance(node, yaml.ScalarNode):
                        text = re.sub(r'\bsecrets\s*(?:\.\s*GITHUB_TOKEN\b|\[\s*([\'"])GITHUB_TOKEN\1\s*\])', '', node.value, flags=re.I)
                        if '${{' in text and re.search(r'\bsecrets\b', text, re.I):
                            errors.append(f'{ascii(path.relative_to(root).as_posix())}:{node.start_mark.line + 1}: {ascii(name)}: secret with write')
        except (ValueError, AttributeError) as error:
            errors.append(f'{ascii(path.relative_to(root).as_posix())}:1: {ascii(str(error))}')
    return errors


def message_bytes(commit):
    if int(git('cat-file', '-s', commit)) > 1024 * 1024:
        raise ValueError('commit object exceeds 1 MiB')
    return git_bytes('cat-file', 'commit', commit).partition(b'\n\n')[2]


def message(commit):
    return message_bytes(commit).decode('utf-8', errors='replace')


def commits(base, head):
    items = git('rev-list', '--reverse', '--max-count=129', f'{base}..{head}').splitlines()
    if len(items) > 128:
        raise ValueError('PR history exceeds 128 commits')
    return items


def merge_base(base, head):
    candidates = git('merge-base', '--all', base, head).splitlines()
    if len(candidates) != 1:
        raise ValueError('exactly one merge base required; criss-cross history refused')
    return candidates[0]


def ancestor_of(ancestor, descendant):
    try:
        git('merge-base', '--is-ancestor', ancestor, descendant)
    except subprocess.CalledProcessError as error:
        if error.returncode == 1:
            return False
        raise
    return True


def changed(base, head, *options):
    base = merge_base(base, head)
    return git('diff', '--no-renames', '--name-only', '-z', *options, base, head).split('\0')[:-1]


def slice_counts(records, allow):
    files = lines = 0
    for record in records.split('\0')[:-1]:
        added, deleted, path = record.split('\t', 2)
        if path not in allow:
            files += 1
            lines += int(added) + int(deleted) if added != '-' else 401
    return files, lines


def novel_merge_records(commit, paid=None):
    paid = {} if paid is None else paid
    raw = git_bytes('diff-tree', '--cc', '--raw', '-z', '--no-abbrev', '--no-commit-id', '-r', '--no-renames', commit).split(b'\0')
    if raw.pop() != b'' or len(raw) % 2:
        raise ValueError('malformed combined raw diff')
    records = {}
    for header, path in zip(raw[::2], raw[1::2]):
        fields = header.split()
        if not re.fullmatch(rb'::[0-7]{6} [0-7]{6} [0-7]{6}(?: [0-9a-f]{40}){3} [ADMT]{2}', header) or not path or path in records:
            raise ValueError('unsupported combined raw record')
        path.decode('utf-8')  # Never replace invalid bytes in a path identity.
        modes = [fields[0][2:], fields[1], fields[2]]
        records[path] = [0, 0, False, all(mode != modes[2] for mode in modes[:2])]
        paid[path.decode('utf-8')] = {'added': set(), 'deleted': set(), 'binary': False, 'mode': records[path][3]}
    current, active = None, False
    exclusive = [0, 0]
    pending = []
    def finish_deletion_run():
        # Pair private deletions only within one contiguous removed run.
        if current is not None and all(exclusive):
            current[1] += max(exclusive)
            covered['deleted'].update(pending)
        exclusive[:] = [0, 0]
        pending.clear()
    patch = git_bytes('-c', 'diff.suppressBlankEmpty=false', '-c', 'core.quotePath=true', 'show', '--cc', '--submodule=short', '--ignore-submodules=none', '--diff-algorithm=myers', '--no-indent-heuristic', '--inter-hunk-context=0', '--format=', '--unified=1', '--no-ext-diff', '--no-textconv', '--no-color', '--no-renames', commit)
    for line in patch.split(b'\n'):
        if line.startswith(b'diff --cc '):
            finish_deletion_run()
            value = line[len(b'diff --cc '):]
            path = path_value(value)
            if not isinstance(path, bytes) or path not in records:
                raise ValueError('combined patch path differs from raw inventory')
            current, active = records[path], False
            covered = paid[path.decode('utf-8')]
        elif line.startswith(b'@@@ '):
            finish_deletion_run()
            if current is None:
                raise ValueError('combined hunk lacks a path')
            first, _, second, _, result, _ = ranges(line, 2)
            active = True
        elif current is not None and not active and line.startswith(b'Binary files '):
            current[2] = True
            covered['binary'] = True
        elif active and line.startswith(b'++'):
            finish_deletion_run()
            current[0] += 1
            covered['added'].add((result, line[2:]))
            result += 1
        elif active and line.startswith(b'--'):
            current[1] += 1
            covered['deleted'].add((second, line[2:]))
            first += 1
            second += 1
        elif active and line.startswith(b'- '):
            exclusive[0] += 1
            first += 1
        elif active and line.startswith(b' -'):
            exclusive[1] += 1
            pending.append((second, line[2:]))
            second += 1
        elif active and line[:2] in {b'  ', b' +', b'+ '}:
            finish_deletion_run()
            first += line[0] == 32
            second += line[1] == 32
            result += 1
        elif active and line and not line.startswith(b'\\ No newline') and line[:2] not in {b'  ', b' +', b'+ '}:
            raise ValueError('unsupported combined row')
    finish_deletion_run()
    return [(('-' if binary else str(added)), ('-' if binary else str(deleted)), path.decode('utf-8'))
            for path, (added, deleted, binary, mode) in records.items() if added or deleted or binary or mode]


def path_value(value):
    try:
        result = ast.literal_eval('b' + value.decode('ascii')) if value.startswith(b'"') else value
    except (ValueError, SyntaxError) as error:
        raise ValueError('unsupported path quoting') from error
    if not isinstance(result, bytes):
        raise ValueError('unsupported path value')
    return result


def ranges(line, parents=1):
    marker = b'@' * (parents + 1)
    atom = rb'(\d+)(?:,(\d+))?'
    pattern = marker + b' ' + b' '.join([b'-' + atom] * parents + [re.escape(b'+') + atom]) + b' ' + marker + rb'(?: .*)?'
    match = re.fullmatch(pattern, line)
    if match is None:
        raise ValueError('unsupported diff hunk')
    result = []
    for start, count in zip(match.groups()[::2], match.groups()[1::2]):
        count = int(count or b'1')
        result += [int(start) - (count != 0), count]
    return tuple(result)


def changes(old, new):
    options = ('--no-renames', '--no-ext-diff', '--no-textconv', '--no-color', '--submodule=short', '--ignore-submodules=none', '--diff-algorithm=myers', '--no-indent-heuristic', '--inter-hunk-context=0')
    parts = git_bytes('diff', *options, '--raw', '--numstat', '--no-abbrev', '-z', old, new).split(b'\0')
    if parts.pop() != b'':
        raise ValueError('unterminated ordinary diff')
    result = {}
    index = 0
    while index < len(parts):
        value = parts[index]
        if value.startswith(b':'):
            if not re.fullmatch(rb':[0-7]{6} [0-7]{6}(?: [0-9a-f]{40}){2} [ADMT]', value) or index + 1 == len(parts):
                raise ValueError('unsupported ordinary raw record')
            fields, path = value.split(), parts[index + 1].decode('utf-8')
            if not path or path in result:
                raise ValueError('duplicate ordinary path')
            result[path] = {'modes': (fields[0][1:], fields[1]), 'blobs': tuple(fields[2:4]),
                            'hunks': [], 'deleted': set(), 'added': set()}
            index += 2
        else:
            added, deleted, path = value.split(b'\t', 2)
            entry = result[path.decode('utf-8')]
            if 'binary' in entry or not (added == deleted == b'-' or added.isdigit() and deleted.isdigit()):
                raise ValueError('unsupported ordinary numstat')
            entry['binary'] = added == b'-'
            index += 1
    if any('binary' not in entry for entry in result.values()):
        raise ValueError('missing ordinary numstat')
    old_path = path = None
    active = False
    patch = git_bytes('-c', 'core.quotePath=true', '-c', 'diff.suppressBlankEmpty=false',
                           'diff', *options, '--src-prefix=a/', '--dst-prefix=b/', '--unified=0', old, new)
    for line in patch.split(b'\n'):
        if line.startswith(b'diff --git '):
            old_path = path = None
            active = False
        elif not active and line.startswith((b'--- ', b'+++ ')):
            value = path_value(line[4:])
            if value != b'/dev/null' and not value.startswith(b'a/' if line.startswith(b'--- ') else b'b/'):
                raise ValueError('unexpected ordinary path prefix')
            decoded = None if value == b'/dev/null' else value[2:].decode('utf-8')
            if line.startswith(b'--- '):
                old_path = decoded
            else:
                path = decoded or old_path
                if path not in result or decoded and old_path and decoded != old_path:
                    raise ValueError('ordinary path differs from raw inventory')
        elif line.startswith(b'@@ '):
            if path is None:
                raise ValueError('hunk lacks an ordinary path')
            old_row, old_count, new_row, new_count = ranges(line)
            result[path]['hunks'].append((old_row, old_count, new_row, new_count))
            active = True
        elif active and line.startswith(b'-'):
            result[path]['deleted'].add((old_row, line[1:]))
            old_row += 1
        elif active and line.startswith(b'+'):
            result[path]['added'].add((new_row, line[1:]))
            new_row += 1
        elif active and line.startswith(b' '):
            old_row += 1
            new_row += 1
        elif active and line and not line.startswith(b'\\ No newline'):
            raise ValueError('unsupported ordinary row')
    for entry in result.values():
        if entry['blobs'][0] == entry['blobs'][1]:
            entry.update(hunks=[], deleted=set(), added=set())
    return result


def origin(row, hunks):
    shift = 0
    for old_start, old_count, new_start, new_count in hunks:
        if row < new_start:
            break
        if row < new_start + new_count:
            return None
        shift += old_count - new_count
    return row + shift


def overlaps(left, right):
    return left[0] <= right[0] + right[1] and right[0] <= left[0] + left[1]


def moved_regions(entry):
    common = {text for _, text in entry.get('added', set())} & {text for _, text in entry.get('deleted', set())}
    bounds = {}
    for row, text in entry.get('deleted', set()):
        if text in common:
            low, high = bounds.get(text, (row, row + 1))
            bounds[text] = min(low, row), max(high, row + 1)
    for row, text in entry.get('added', set()):
        if text in common:
            hunk = next((h for h in entry['hunks'] if h[2] <= row < h[2] + h[3]), None)
            if hunk is None:
                raise ValueError('added row has no source hunk')
            low, high = bounds[text]
            bounds[text] = min(low, hunk[0]), max(high, hunk[0] + hunk[1])
    return [(low, high - low, 0, 0) for low, high in bounds.values()]


def automatic_text_carry(entry, prior, baseline):
    ancestral = prior or baseline or entry
    common = ancestral['modes'][0], ancestral['blobs'][0]
    branch = (prior['modes'][1], prior['blobs'][1]) if prior else common
    endpoints = [common, branch, (entry['modes'][0], entry['blobs'][0]), (entry['modes'][1], entry['blobs'][1])]
    if any(mode not in {b'100644', b'100755'} for mode, _ in endpoints):
        return False
    contents = [git_bytes('cat-file', 'blob', digest.decode()) for _, digest in endpoints]
    if any(b'\0' in value for value in contents):
        return False
    with tempfile.TemporaryDirectory(prefix='gate-text-carry-') as temporary:
        root = Path(temporary)
        for name, content in zip(('common', 'branch', 'base'), contents):
            (root / name).write_bytes(content)
        with (root / 'output').open('w+b') as output:
            command = ['git', 'merge-file', '--stdout', '--diff-algorithm=myers', '--marker-size=1', '-L', 'branch', '-L', 'common', '-L', 'base', str(root / 'branch'), str(root / 'common'), str(root / 'base')]
            try:
                status = subprocess.run(command, stdout=output, stderr=subprocess.DEVNULL, timeout=30).returncode
            except (OSError, subprocess.TimeoutExpired) as error:
                raise ValueError('automatic text carry check unavailable') from error
            if status not in range(128):
                raise ValueError('automatic text carry command failed')
            if status:
                return False
            output.seek(0)
            value = output.read(8 * 1024 * 1024 + 1)
            if len(value) > 8 * 1024 * 1024:
                raise ValueError('automatic text carry output exceeds 8 MiB')
            return value == contents[3]


def residual_rows(base_parent, branch_parent, head):
    common = merge_base(branch_parent, base_parent)
    branch = changes(common, branch_parent)
    baseline = changes(common, base_parent)
    result = changes(branch_parent, head)
    delta = changes(base_parent, head)
    residual = {}
    for path, entry in delta.items():
        prior = branch.get(path, {})
        base_hunks = baseline.get(path, {}).get('hunks', [])
        corridors = [region for region in moved_regions(prior) if any(overlaps(region, other) for other in base_hunks)]
        safe = [hunk for hunk in prior.get('hunks', []) if not any(overlaps(hunk, other) for other in base_hunks + corridors)]
        value = {'added': set(), 'deleted': set(), 'binary': False, 'mode': False}
        value['mode'] = entry['modes'][0] != entry['modes'][1] and entry['modes'] != prior.get('modes')
        if entry['blobs'][0] != entry['blobs'][1]:
            if entry['binary']:
                value['binary'] = entry['blobs'] != prior.get('blobs')
            elif not automatic_text_carry(entry, prior, baseline.get(path, {})):
                for polarity, provenance in [('deleted', baseline), ('added', result)]:
                    axis = 0 if polarity == 'deleted' else 2
                    history = provenance.get(path, {})
                    corridors = moved_regions(history)
                    for row, text in entry[polarity]:
                        source_row = origin(row, history.get('hunks', []))
                        if source_row is not None and any(region[0] <= source_row < region[0] + region[1] for region in corridors):
                            source_row = None
                        independent = source_row is not None and any(hunk[axis] <= source_row < hunk[axis] + hunk[axis + 1] for hunk in safe)
                        if not independent or (source_row, text) not in prior.get(polarity, set()):
                            value[polarity].add((row, text))
        if any(value.values()):
            residual[path] = value
    return residual


def augmented_merge_records(base_parent, branch_parent, head):
    paid = {}
    records = {path: [added, deleted] for added, deleted, path in novel_merge_records(head, paid)}
    for path, entry in residual_rows(base_parent, branch_parent, head).items():
        before = paid.get(path, {})
        current = records.setdefault(path, ['0', '0'])
        if current[0] == '-':
            continue
        if entry['binary']:
            current[:] = ['-', '-']
        else:
            for index, polarity in enumerate(('added', 'deleted')):
                current[index] = str(int(current[index]) + len(entry[polarity] - before.get(polarity, set())))
    return [(added, deleted, path) for path, (added, deleted) in records.items()]


def commit_diff(base, commit, *options):
    parents = git('show', '-s', '--format=%P', commit).split()
    if len(parents) > 2:
        raise ValueError(f'{commit}: octopus merge refused')
    if len(parents) == 2:
        if ancestor_of(parents[0], base):
            raise ValueError(f'{commit}: merge first parent is reachable from BASE')
        candidates = [parent for parent in parents if ancestor_of(parent, base)]
        if len(candidates) != 1:
            raise ValueError(f'{commit}: merge requires one BASE-side parent')
        if ancestor_of(candidates[0], parents[0]):
            raise ValueError(f'{commit}: redundant BASE-side parent refused')
        records = augmented_merge_records(candidates[0], parents[0], commit)
        if options == ('--numstat', '-z'):
            return ''.join('\t'.join(record) + '\0' for record in records)
        if options == ('--name-only', '-z'):
            return ''.join(record[2] + '\0' for record in records)
        raise ValueError('unsupported combined diff output')
    else:
        parent = parents[0] if parents else None
    return git('diff', '--no-renames', *options, parent, commit) if parent else git('diff-tree', '--root', '--no-commit-id', '-r', '--no-renames', *options, commit)


def slices(root, base, head, allow):
    merge_base(base, head)
    errors = []
    for commit in commits(base, head):
        records = commit_diff(base, commit, '--numstat', '-z')
        files, lines = slice_counts(records, allow)
        if files > 10 or lines > 400:
            errors.append(f'{commit}: files={files} lines={lines}; cap=10/400 (binary=401)')
    return errors


def total(root, base, head, allow):
    ancestor = merge_base(base, head)
    files, lines = slice_counts(git('diff', '--no-renames', '--numstat', '-z', ancestor, head), allow)
    return [] if files <= 30 and lines <= 1500 else [f'PR total: files={files} lines={lines}; cap=30/1500']


def unreadable(text, path, line):
    points = {ord(char) for char in text if (ord(char) < 32 and char not in '\t\n') or 0x7f <= ord(char) <= 0x9f or ord(char) in {0x2028, 0x2029} or any(lo <= ord(char) <= hi for lo, hi in IGNORABLE)}
    return [f'{ascii(str(path))}:{line}: U+{point:04X}' for point in sorted(points)]


def readable(root, base, head, allow):
    errors = []
    ancestor = merge_base(base, head)
    records = git_bytes('diff', '--no-renames', '--numstat', '-z', ancestor, head).split(b'\0')[:-1]
    for record in records:
        added, deleted, raw_path = record.split(b'\t', 2)
        try:
            path = raw_path.decode('utf-8')
        except UnicodeDecodeError:
            errors.append(f'{ascii(raw_path)}:0: non-UTF8 filename refused')
            continue
        if path in allow:
            continue
        errors += unreadable(path, path, 0)
        if added == b'0':
            continue
        size = subprocess.run(['git', 'cat-file', '-s', f'{head}:{path}'], capture_output=True)
        if size.returncode and added == b'-':
            continue
        if size.returncode or int(size.stdout) > 4 * 1024 * 1024:
            errors.append(f'{ascii(path)}:0: changed content unavailable or exceeds 4 MiB')
            continue
        old_size = subprocess.run(['git', 'cat-file', '-s', f'{ancestor}:{path}'], capture_output=True)
        if old_size.returncode == 0 and int(old_size.stdout) > 4 * 1024 * 1024:
            errors.append(f'{ascii(path)}:0: prior content exceeds 4 MiB')
            continue
        if added == b'-':
            blob = subprocess.run(['git', 'show', f'{head}:{path}'], capture_output=True)
            if blob.returncode or b'\0' in blob.stdout[:8000]:
                continue
        new = 0
        active = False
        for line in git_bytes('diff', '--no-ext-diff', '--no-textconv', '--text', '--no-color', '--no-renames', '--unified=0', ancestor, head, '--', path).split(b'\n'):
            hunk = re.match(rb'@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@', line)
            if hunk:
                new = int(hunk.group(2))
                active = True
            elif active and line.startswith(b'+'):
                try:
                    errors += unreadable(line[1:].decode('utf-8'), path, new)
                except UnicodeDecodeError:
                    errors.append(f'{ascii(path)}:{new}: non-UTF-8 bytes')
                new += 1
    for commit in commits(base, head):
        for number, line in enumerate(message_bytes(commit).split(b'\n'), 1):
            try:
                errors += unreadable(line.decode('utf-8'), commit, number)
            except UnicodeDecodeError:
                errors.append(f'{commit}:{number}: non-UTF-8 bytes')
    return errors


def test_path(path):
    p = Path(path)
    return p.suffix in SOURCE and ('tests' in p.parts or 'test' in p.parts or p.name.startswith('test_') or re.search(r'(?:_test|\.test)\.', p.name))


def travel(root, base, head, allow):
    if any(test_path(path) for path in changed(base, head, '--diff-filter=AM')):
        return []
    errors = []
    for commit in commits(base, head):
        paths = commit_diff(base, commit, '--name-only', '-z').split('\0')[:-1]
        if any(Path(path).suffix in SOURCE and not test_path(path) for path in paths) and not re.search(r'(?m)^no-test:[ \t]*\S[^\n]*$', message(commit)):
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
        allow = {line for line in prior.stdout.decode('utf-8', errors='replace').splitlines() if line and not line.startswith('#')}
        if '.github/codex-gate-allow.txt' in allow:
            raise ValueError('allow file cannot exempt itself')
        errors = globals()[check](Path('.'), base, head, allow)
    except (ValueError, UnicodeError, yaml.YAMLError, subprocess.CalledProcessError) as error:
        errors = [f'gate tool error: {ascii(str(error))}']
    for error in errors:
        print(error)
    print(f'{check}: findings={len(errors)}')
    sys.exit(bool(errors))
