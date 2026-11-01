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
# Deliberately non-key placeholder; mocked verification is not cryptographic proof.
SIGNER = 'fixture-owner ssh-ed25519 Zml4dHVyZS1ub3QtYS1yZWFsLWtleQ=='


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
        """Kills HEAD policy, forgeable labels, branch waivers and missed setup paths."""
        self.write('.github/codex-gate-owners.txt', SIGNER + '\n')
        self.write('.mailmap', 'Gate Owner <owner@example.invalid> Fixture <fixture@example.invalid>\n')
        protected = ('scripts/ci/new.py', '.github/new.txt', 'nested/codex-gate-extra', 'nested/requirements-ci.txt', 'nested/pyproject.toml', 'nested/setup.cfg', 'nested/pip.conf', 'nested/.python-version', 'nested/sitecustomize.py', 'nested/usercustomize.py', 'nested/custom.pth')
        for path in protected:
            self.write(path, 'inert\n')
        head = self.commit()
        self.checkout_base()
        with mock.patch.dict(os.environ, {'GITHUB_HEAD_REF': 'codex/ops3-spoof'}), mock.patch.object(self.runner, 'verify_owner') as verify:
            errors = self.runner.owner_findings(self.base, head)
        self.assertEqual(len(errors), len(protected) + 1)
        for path in protected:
            self.assertTrue(any(path in error for error in errors))
        self.assertTrue(all('needs TR review' in error for error in errors))
        verify.assert_not_called()

    def test_unsigned_gate_commit_rejects_forged_author_and_committer_labels(self):
        """Kills author/committer metadata authorization without an owner signature."""
        self.write('.github/codex-gate-owners.txt', SIGNER + '\n')
        self.base = self.commit()
        self.write('nested/requirements-extra.txt', 'inert\n')
        head = self.commit('-c', 'user.name=fixture-owner', '-c', 'user.email=owner@example.invalid', '--author=fixture-owner <owner@example.invalid>')
        with mock.patch.object(self.runner.subprocess, 'run') as backend:
            self.assertTrue(self.runner.owner_findings(self.base, head))
        backend.assert_not_called()

    def test_owner_verification_checks_each_protected_commit_even_after_revert(self):
        """Kills tip-only approval, net-diff-only approval and checking ordinary commits."""
        self.write('.github/codex-gate-owners.txt', SIGNER + '\n')
        self.base = self.commit()
        self.write('nested/requirements-extra.txt', 'inert\n')
        edit = self.commit()
        self.write('README.md', 'ordinary change\n')
        ordinary = self.commit()
        (self.root / 'nested/requirements-extra.txt').unlink()
        tip = self.commit()
        self.assertEqual(self.git('diff', '--name-only', self.base, tip), 'README.md')
        with mock.patch.object(self.runner, 'verify_owner', side_effect=lambda commit, *_: commit == tip) as verify:
            self.assertTrue(self.runner.owner_findings(self.base, tip))
            self.assertEqual([call.args[0] for call in verify.call_args_list], [edit, tip])
            self.assertNotIn(ordinary, [call.args[0] for call in verify.call_args_list])
        with mock.patch.object(self.runner, 'verify_owner', return_value=True) as verify:
            self.assertEqual(self.runner.owner_findings(self.base, tip), [])
            self.assertEqual([call.args[0] for call in verify.call_args_list], [edit, tip])

    def test_owner_policy_exports_base_public_signers_and_empty_revocations(self):
        """Kills HEAD signer-list substitution; mocked positives prove policy, not crypto."""
        self.write('.github/codex-gate-owners.txt', SIGNER + '\n')
        self.base = self.commit()
        self.write('.github/codex-gate-owners.txt', 'head-owner ssh-ed25519 YWJjZA==\n')
        head = self.commit()
        def approved(commit, signers, revocations):
            self.assertEqual(commit, head)
            self.assertEqual(signers.read_text(), SIGNER + '\n')
            self.assertEqual(revocations.read_bytes(), b'')
            self.assertFalse(signers.resolve().is_relative_to(self.root))
            return True
        with mock.patch.object(self.runner, 'verify_owner', side_effect=approved) as verify:
            self.assertEqual(self.runner.owner_findings(self.base, head), [])
        self.assertEqual(verify.call_count, 1)

    def test_owner_backend_requires_single_ssh_signature_and_checked_exit(self):
        """Kills unsigned/other-format/duplicate acceptance, bad exits and omitted verifier guards."""
        self.write('plain.txt', 'inert\n')
        head = self.commit()
        header = subprocess.check_output(['git', 'cat-file', 'commit', head]).partition(b'\n\n')[0]
        ssh = b'\ngpgsig -----BEGIN SSH SIGNATURE-----\n Zml4dHVyZQ==\n -----END SSH SIGNATURE-----'
        def object_with(signature):
            return self.git('hash-object', '-w', '-t', 'commit', '--stdin', input=header + signature + b'\n\nfixture\n')
        signers, revoked = self.output / 'signers', self.output / 'revoked'
        signers.write_text(SIGNER + '\n')
        revoked.write_bytes(b'')
        for commit in (head, object_with(b'\ngpgsig -----BEGIN PGP SIGNATURE-----\n fixture'), object_with(ssh + ssh)):
            with mock.patch.object(self.runner.subprocess, 'run') as backend:
                self.assertFalse(self.runner.verify_owner(commit, signers, revoked))
            backend.assert_not_called()
        synthetic = object_with(ssh)  # No valid signature or key: the backend below is explicitly mocked.
        with mock.patch.object(self.runner.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0)) as backend:
            self.assertTrue(self.runner.verify_owner(synthetic, signers, revoked))
            command = backend.call_args.args[0]
            for option in ('gpg.format=ssh', 'gpg.ssh.program=ssh-keygen', f'gpg.ssh.allowedSignersFile={signers}', f'gpg.ssh.revocationFile={revoked}', 'gpg.minTrustLevel=fully'):
                self.assertIn(option, command)
            self.assertEqual(command[-3:], ['verify-commit', '--raw', synthetic])
            self.assertEqual(backend.call_args.kwargs['timeout'], 15)
        for failure in (subprocess.CompletedProcess([], 1), OSError('fixture verifier unavailable'), subprocess.TimeoutExpired('git', 15)):
            kwargs = {'side_effect': failure} if isinstance(failure, Exception) else {'return_value': failure}
            with mock.patch.object(self.runner.subprocess, 'run', **kwargs):
                self.assertFalse(self.runner.verify_owner(synthetic, signers, revoked))

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
