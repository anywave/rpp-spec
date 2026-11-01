"""Bounded adversarial fixtures never execute code or dependencies from HEAD."""
import importlib.util
import json
import marshal
import os
from pathlib import Path
import subprocess
import struct
import sys
import tempfile
import unittest
from unittest import mock

HERE = Path(__file__).absolute().parent
OWNER = 'Gate Owner <owner@example.invalid>'


def load(path):
    spec = importlib.util.spec_from_file_location('trusted_fixture', path)
    module = importlib.util.module_from_spec(spec)
    exec(compile(path.read_bytes(), str(path), 'exec'), module.__dict__)
    return module


class TrustedGateTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.old = Path.cwd()
        self.root = Path(self.temporary.name) / 'repo'
        self.output = Path(self.temporary.name) / 'output'
        self.root.mkdir()
        self.output.mkdir()
        os.chdir(self.root)
        self.git('init', '-q', '-b', 'master')
        for key, value in [('user.name', 'Fixture'), ('user.email', 'fixture@example.invalid'), ('core.hooksPath', str(self.output)), ('commit.gpgsign', 'false')]:
            self.git('config', key, value)
        for name in ('gate.py', 'trusted_gate.py'):
            self.write('scripts/ci/' + name, (HERE / name).read_bytes())
        self.write('.github/codex-gate-owners.txt', '')
        self.write('.github/codex-gate-allow.txt', '')
        self.base = self.commit()
        self.runner = load(self.root / 'scripts/ci/trusted_gate.py')

    def tearDown(self):
        os.chdir(self.old)
        self.temporary.cleanup()

    def git(self, *args, **kwargs):
        return subprocess.check_output(['git', '--literal-pathspecs', *args], **kwargs).decode().strip()

    def write(self, path, value):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(value if isinstance(value, bytes) else value.encode())

    def commit(self, *options, staged=False):
        if not staged:
            self.git('add', '-A')
        authors = [value for value in options if value.startswith('--author=')]
        self.git(*[value for value in options if value not in authors], 'commit', *authors, '-qm', 'fixture\n\nno-test: adversarial metadata fixture')
        return self.git('rev-parse', 'HEAD')

    def checkout_base(self):
        self.git('checkout', '-q', '--detach', self.base)

    def findings(self, report, check):
        return next(item['findings'] for item in report['checks'] if item['check'] == check)

    def test_isolated_base_runner_never_executes_head_gate_requirements_or_scripts(self):
        """Kills importing HEAD gate, installing HEAD requirements, or executing HEAD shell/YAML."""
        marker = self.output / 'executed'
        command = 'python -c ' + json.dumps(f"__import__('pathlib').Path({marker.as_posix()!r}).touch()")
        self.write('scripts/ci/gate.py', f'from pathlib import Path; Path({str(marker)!r}).touch(); raise RuntimeError("HEAD")\n')
        self.write('requirements.txt', 'malicious-package @ file:///never-install\n')
        self.write('widget/run.sh', command + '\n')
        self.write('widget/action.yaml', 'runs: {using: composite, steps: [{uses: other/action@v1}]}\n')
        head = self.commit()
        self.checkout_base()
        result = subprocess.run([sys.executable, '-I', str(self.root / 'scripts/ci/trusted_gate.py'), '--base', self.base, '--head', head, '--output', str(self.output / 'receipt.json')], capture_output=True, text=True, timeout=30)
        report = json.loads(result.stdout)
        self.assertFalse(marker.exists())
        self.assertEqual(result.returncode, 1)
        self.assertEqual((report['base'], report['head']), (self.base, head))
        self.assertTrue(any('widget/action.yaml' in item for item in self.findings(report, 'actions')))
        self.assertEqual(json.loads((self.output / 'receipt.json').read_text()), report)

    def test_empty_base_owners_ignore_head_owner_file_and_mailmap_self_approval(self):
        """Kills reading owners/mailmap from HEAD or treating a branch name as owner approval."""
        self.write('.github/codex-gate-owners.txt', 'Fixture <fixture@example.invalid>\n')
        self.write('.mailmap', 'Gate Owner <owner@example.invalid> Fixture <fixture@example.invalid>\n')
        for path in ('scripts/ci/new.py', '.github/new.txt', 'nested/codex-gate-extra', 'nested/requirements-ci.txt'):
            self.write(path, 'inert\n')
        head = self.commit()
        self.checkout_base()
        with mock.patch.dict(os.environ, {'GITHUB_HEAD_REF': 'codex/ops3-spoof'}):
            errors = self.runner.owner_findings(self.base, head)
        self.assertEqual(len(errors), 5)
        self.assertTrue(all('needs TR review' in error for error in errors))

    def test_exact_base_owner_author_or_committer_is_allowed_from_raw_headers(self):
        """Kills requiring both identities or ignoring the author/committer owner alternative."""
        self.write('.github/codex-gate-owners.txt', OWNER + '\n')
        self.base = self.commit()
        self.write('.mailmap', 'Gate Owner <owner@example.invalid> Fixture <fixture@example.invalid>\n')
        self.write('nested/requirements-extra.txt', 'inert\n')
        self.assertTrue(self.runner.owner_findings(self.base, self.commit()))
        for options in [('--author=' + OWNER,), ('--author=Other <other@example.invalid>',)]:
            self.checkout_base()
            self.write('nested/requirements-extra.txt', 'inert\n')
            committer = 'Fixture' if options[0].endswith(OWNER) else 'Gate Owner'
            email = 'fixture@example.invalid' if committer == 'Fixture' else 'owner@example.invalid'
            head = self.commit('-c', 'user.name=' + committer, '-c', 'user.email=' + email, *options)
            self.assertEqual(self.runner.owner_findings(self.base, head), [])

    def test_exporter_rejects_parent_backslash_and_colon_path_mutations(self):
        """Kills path traversal and Windows separator/drive interpretation in metadata export."""
        for path in ('.github/../action.yaml', '.github/a\\b.yaml', '.github/a:b.yaml'):
            record = b'100644 blob ' + b'a' * 40 + b'\t' + path.encode() + b'\0'
            def metadata(*args):
                return record if args[0] == 'ls-tree' else b'6\n' if args[:2] == ('cat-file', '-s') else b'x: ok\n'
            with mock.patch.object(self.runner, 'git_bytes', side_effect=metadata):
                with self.assertRaises(ValueError):
                    self.runner.export_metadata(self.output, self.base)

    def test_exporter_rejects_git_symlink_mode_without_creating_a_local_symlink(self):
        """Kills treating Git mode 120000 metadata as a regular file on either platform."""
        blob = self.git('hash-object', '-w', '--stdin', input=b'../../outside')
        self.git('update-index', '--add', '--cacheinfo', '120000', blob, '.github/action.yaml')
        head = self.commit(staged=True)
        self.checkout_base()
        with self.assertRaises(ValueError):
            self.runner.export_metadata(self.output, head)
        with self.assertRaises(ValueError):
            self.runner.base_lines(head, '.github/action.yaml')
        self.assertFalse((self.output / '.github/action.yaml').exists())

    def test_exporter_enforces_exact_one_mib_metadata_boundary(self):
        """Kills an omitted size cap or an off-by-one rejection at exactly 1 MiB."""
        self.write('.github/large.yaml', b'x: ' + b'a' * (1024 * 1024 - 4) + b'\n')
        exact = self.commit()
        self.runner.export_metadata(self.output, exact)
        self.assertEqual((self.output / '.github/large.yaml').stat().st_size, 1024 * 1024)
        self.write('.github/large.yaml', b'x' * (1024 * 1024 + 1))
        oversized = self.commit()
        with self.assertRaises(ValueError):
            self.runner.export_metadata(self.output, oversized)

    def test_base_allow_controls_head_data_and_head_cannot_waive_itself(self):
        """Kills loading allow entries from HEAD rather than the verified BASE policy."""
        self.write('.github/codex-gate-allow.txt', 'approved.txt\n')
        self.base = self.commit()
        self.write('approved.txt', 'a\u200bb\n')
        self.write('new-waiver.txt', 'a\u200bb\n')
        self.write('.github/codex-gate-allow.txt', 'approved.txt\nnew-waiver.txt\n')
        head = self.commit()
        self.checkout_base()
        errors = self.findings(self.runner.run(self.base, head), 'readable')
        self.assertTrue(any('new-waiver.txt' in error for error in errors))
        self.assertFalse(any('approved.txt' in error for error in errors))

    def test_yaml_tags_and_composite_run_commands_remain_inert_head_data(self):
        """Kills unsafe YAML construction or executing composite commands while scanning uses."""
        marker = self.output / 'yaml-executed'
        payload = f"__import__('pathlib').Path({marker.as_posix()!r}).touch()"
        self.write('.github/inert.yaml', '!!python/object/apply:builtins.eval [' + json.dumps(payload) + ']\n')
        self.write('widget/action.yaml', 'runs:\n  using: composite\n  steps:\n    - run: ' + json.dumps('python -c ' + json.dumps(payload)) + '\n      shell: bash\n    - uses: other/action@v1\n')
        head = self.commit()
        self.checkout_base()
        report = self.runner.run(self.base, head)
        self.assertFalse(marker.exists())
        self.assertTrue(any('widget/action.yaml' in error for error in self.findings(report, 'actions')))

    def test_runner_refuses_wrong_checkout_tampered_base_files_and_external_code_identity(self):
        """Kills trusting HEAD cwd, modified BASE runner/gate bytes, or a runner outside the BASE tree."""
        self.write('README.md', 'head\n')
        head = self.commit()
        with self.assertRaises(ValueError):
            self.runner.run(self.base, head)
        self.checkout_base()
        for path in ('scripts/ci/gate.py', 'scripts/ci/trusted_gate.py'):
            original = (self.root / path).read_bytes()
            self.write(path, original + b'\n# tampered\n')
            with self.assertRaises(ValueError):
                self.runner.run(self.base, head)
            self.write(path, original)
        with self.assertRaises(ValueError):
            load(HERE / 'trusted_gate.py').run(self.base, head)

    def test_runner_ignores_valid_timestamp_pyc_poison_beside_verified_base_gate(self):
        """Kills executing cached bytecode instead of compiling the verified BASE Git blob."""
        self.write('widget/action.yml', 'runs: {using: composite, steps: [{uses: other/action@v1}]}\n')
        head = self.commit()
        self.checkout_base()
        gatepath = self.root / 'scripts/ci/gate.py'
        marker = self.output / 'pyc-executed'
        payload = gatepath.read_text(encoding='utf-8') + f'\nfrom pathlib import Path; Path({str(marker)!r}).touch()\n'
        source = gatepath.stat()
        header = importlib.util.MAGIC_NUMBER + struct.pack('<III', 0, int(source.st_mtime) & 0xffffffff, source.st_size)
        cachepath = Path(importlib.util.cache_from_source(str(gatepath)))
        cachepath.parent.mkdir(parents=True, exist_ok=True)
        cachepath.write_bytes(header + marshal.dumps(compile(payload, str(gatepath), 'exec')))
        report = self.runner.run(self.base, head)
        self.assertTrue(any('widget/action.yml' in error for error in self.findings(report, 'actions')))
        self.assertFalse(marker.exists())

    def test_optional_pr_fetch_verifies_full_head_sha_and_rejects_mismatch(self):
        """Kills accepting a fetched different commit or a short/event-mutable HEAD reference."""
        self.write('README.md', 'head\n')
        head = self.commit()
        self.checkout_base()
        actual = self.runner.git_bytes
        def fetched(*args):
            return b'' if args[0] == 'fetch' else (head + '\n').encode() if args == ('rev-parse', 'FETCH_HEAD^{commit}') else actual(*args)
        with mock.patch.object(self.runner, 'git_bytes', side_effect=fetched):
            self.assertEqual(self.runner.run(self.base, head, pr=7)['head'], head)
        for bad_head in (head[:7], 'HEAD'):
            with self.assertRaises(ValueError):
                self.runner.run(self.base, bad_head)
        with mock.patch.object(self.runner, 'git_bytes', side_effect=lambda *args: b'' if args[0] == 'fetch' else b'0' * 40 if args == ('rev-parse', 'FETCH_HEAD^{commit}') else actual(*args)):
            with self.assertRaises(ValueError):
                self.runner.run(self.base, head, pr=7)

    def test_git_output_limit_prevents_unbounded_object_reads(self):
        """Kills unbounded Git object buffering before policy checks."""
        self.write('large.bin', b'x' * (8 * 1024 * 1024 + 1))
        head = self.commit()
        with self.assertRaisesRegex(ValueError, 'Git output exceeds 8 MiB'):
            self.runner.git_bytes('show', f'{head}:large.bin')

    def test_crlf_checkout_still_executes_canonical_base_source(self):
        """Kills rejecting a Windows checkout of semantically identical BASE Python."""
        self.write('README.md', 'head\n')
        head = self.commit()
        self.checkout_base()
        for path in ('scripts/ci/gate.py', 'scripts/ci/trusted_gate.py'):
            self.write(path, (self.root / path).read_bytes().replace(b'\n', b'\r\n'))
        try:
            report = self.runner.run(self.base, head)
        except ValueError as error:
            self.fail(f'canonical CRLF checkout rejected: {error}')
        self.assertEqual(report['findings'], 0)
