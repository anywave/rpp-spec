"""Bounded mutation witnesses for the gate entry scripts."""
import os
import shutil
from pathlib import Path
import tempfile
import unittest

import gate


class GateTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.old = Path.cwd()
        self.root = Path(self.directory.name)
        os.chdir(self.root)
        gate.git('init', '-q', '-b', 'master')
        gate.git('config', 'user.name', 'Gate fixture')
        gate.git('config', 'user.email', 'gate@example.invalid')
        gate.git('config', 'core.hooksPath', str(self.root / 'empty-hooks'))
        self.write('README.md', 'fixture\n')
        self.base = self.commit('base')

    def tearDown(self):
        os.chdir(self.old)
        self.directory.cleanup()

    def write(self, path, text):
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding='utf-8')

    def commit(self, message):
        gate.git('add', '-A')
        gate.git('-c', 'commit.gpgsign=false', 'commit', '-qm', message)
        return gate.git('rev-parse', 'HEAD').strip()

    def check(self, name, head=None, allow=None):
        return getattr(gate, name)(Path('.'), self.base, head or self.base, allow or set())

    def test_actions_reject_unpinned_and_duplicate_key_mutations(self):
        """Kills tag/docker/39-hex/7-hex and duplicate-uses bypasses; local/SHA controls pass."""
        for ref, fails in [
            ('a/b@v1', True), ('docker://image', True),
            ('a/b@' + 'a' * 39, True), ('a/b@' + 'a' * 7, True),
            ('./local', False), ('a/b@' + 'a' * 40, False),
        ]:
            self.write('.github/actions/action.yaml', 'runs: {steps: [{uses: "' + ref + '"}]}\n')
            self.assertEqual(bool(self.check('actions')), fails, ref)
        self.write('.github/x.yml', 'uses: a/b@v1\nuses: ./local\n')
        with self.assertRaises(ValueError):
            self.check('actions')

    def test_permissions_reject_write_secret_inheritance_mutations(self):
        """Kills missing/write-all permissions, inherited/dynamic secrets, YAML-merge and job-write bypasses."""
        for permission, env, job, fails in [
            ('', '', 'runs-on: ubuntu-latest', True),
            ('permissions: write-all\n', '', 'runs-on: ubuntu-latest', True),
            ('permissions: {contents: read}\n', '', 'permissions: {id-token: write}', False),
            ('permissions: {contents: write}\n', '', 'env: {K: "${{ secrets.PRIVATE }}"}', True),
            ('permissions: {contents: read}\n', 'env: {K: "${{ secrets[inputs.key] }}"}\n', 'permissions: {contents: write}', True),
            ('permissions: {contents: write}\n', '', 'secrets: inherit', True),
            ('permissions: {contents: write}\n', '', 'env: {K: "${{ toJSON(secrets) }}"}', True),
            ('permissions: {contents: write}\n', '', 'env: {K: "${{ SECRETS.PRIVATE }}"}', True),
            ('permissions: {contents: write}\n', '', 'env: {K: "${{ secrets.GITHUB_TOKEN }}"}', False),
            ('permissions: {contents: read}\n', '', '<<: {permissions: {contents: write}, env: {K: "${{ secrets.PRIVATE }}"}}', True),
        ]:
            self.write('.github/workflows/x.yml', permission + env + 'jobs:\n  x:\n    ' + job + '\n')
            self.assertEqual(bool(self.check('permissions')), fails)

    def test_slice_cap_rejects_file_line_binary_and_merge_bypasses(self):
        """Kills 11-file, 401-line, binary, ignored-merge and both-parent counting mutations."""
        self.assertEqual(gate.slice_counts('200\t200\ta b\0', set()), (1, 400))
        self.write('limit', 'x\n' * 400)
        head = self.commit('exactly 400')
        self.assertEqual(self.check('slices', head), [])
        self.base = head
        self.assertEqual(gate.slice_counts('401\t0\tgold\0', {'gold'}), (0, 0))
        self.assertEqual(gate.slice_counts('-\t-\timage\0', set()), (1, 401))
        for i in range(11):
            self.write(f'f{i}', 'x\n')
        head = self.commit('eleven files')
        self.assertIn('files=11', self.check('slices', head)[0])
        self.assertEqual(self.check('slices', head, {'f0'}), [])
        self.write('large', 'x\n' * 401)
        self.assertTrue(self.check('slices', self.commit('over lines')))
        self.base = gate.git('rev-parse', 'HEAD').strip()
        gate.git('checkout', '-qb', 'side', self.base)
        self.write('side', 'x\n')
        self.commit('side change')
        gate.git('checkout', '-q', 'master')
        self.write('base-only', 'reviewed\n')
        self.base = self.commit('advance BASE')
        gate.git('checkout', '-q', 'side')
        gate.git('merge', '--no-ff', '--no-commit', '-q', 'master')
        self.write('merge-resolution', 'x\n' * 401)
        self.commit('merge')
        self.assertTrue(self.check('slices', gate.git('rev-parse', 'HEAD').strip()))
        gate.git('checkout', '-qb', 'small-side', self.base)
        self.write('small', 'x\n')
        self.commit('small side')
        gate.git('checkout', '-q', 'master')
        self.write('next-base', 'reviewed\n')
        self.base = self.commit('advance BASE again')
        gate.git('checkout', '-q', 'small-side')
        gate.git('-c', 'commit.gpgsign=false', 'merge', '--no-ff', '-qm', 'small merge', 'master')
        self.assertEqual(self.check('slices', gate.git('rev-parse', 'HEAD').strip()), [])

    def test_readable_rejects_c0_c1_and_unicode_line_separator_mutations(self):
        """Kills missing C0/C1/DEL/line-separator checks while preserving tab and LF controls."""
        for code in [*range(9), *range(11, 32), *range(127, 160), 0x2028, 0x2029]:
            self.assertTrue(gate.unreadable(chr(code), 'fixture', 1), hex(code))
        self.assertEqual(gate.unreadable('plain\ttext\nnext', 'fixture', 1), [])

    def test_merge_base_excludes_base_side_tests_and_hidden_text_mutations(self):
        """Kills direct-base diffs that invent PR test coverage or restore BASE-only cleaned text."""
        self.write('tests/test_existing.py', 'assert True\n')
        self.write('baseline.md', 'old ' + chr(0x200b) + '\n')
        self.write('scripts/ci/base.py', '# original\n')
        common = self.commit('common baseline')
        gate.git('checkout', '-qb', 'feature', common)
        self.write('source.rs', 'fn changed() {}\n')
        head = self.commit('source with no PR tests')
        gate.git('checkout', '-q', 'master')
        self.write('tests/test_existing.py', 'assert 1 == 1\n')
        self.write('baseline.md', 'clean\n')
        self.write('scripts/ci/base.py', '# BASE-only change\n')
        self.base = self.commit('advance BASE only')
        self.assertEqual(gate.changed(self.base, head), ['source.rs'])
        self.assertTrue(self.check('travel', head))
        self.assertEqual(self.check('readable', head), [])

    def test_tests_travel_rejects_missing_deleted_tests_and_empty_reason(self):
        """Kills test-presence-anywhere, deletion-as-test and empty no-test bypasses."""
        self.write('source.rs', 'fn main() {}\n')
        head = self.commit('source\n\nno-test: ')
        self.assertTrue(self.check('travel', head))
        self.base = head
        self.write('source.rs', 'fn main() { }\n')
        self.assertEqual(self.check('travel', self.commit('source\n\nno-test: fixture reason')), [])
        self.base = gate.git('rev-parse', 'HEAD').strip()
        self.write('source.rs', 'fn later() {}\n')
        self.assertTrue(self.check('travel', self.commit('another source change')))
        self.write('test_source.py', 'assert True\n')
        head = self.commit('tests in later PR commit')
        self.assertEqual(self.check('travel', head), [])
        self.base = head
        Path('test_source.py').unlink()
        self.write('source.rs', 'fn changed() {}\n')
        self.assertTrue(self.check('travel', self.commit('delete tests')))

    @unittest.skipUnless(shutil.which('bash'), 'Ubuntu workflow aggregation uses Bash')
    def test_workflow_runs_all_checks_after_failure_mutation(self):
        """Kills stopping at the first failed check or discarding its failure."""
        workflow = gate.yaml.safe_load((self.old / '.github/workflows/codex-gate.yml').read_text())
        script = next(step['run'] for step in workflow['jobs']['review']['steps'] if step.get('name') == 'Review PR range')
        stub = 'python() { printf "%s\\n" "$1" >> calls; [ "$1" != scripts/ci/pinned_actions.py ]; };\n'
        result = gate.subprocess.run(['bash', '-c', stub + script], capture_output=True)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(Path('calls').read_text().splitlines(), ['scripts/ci/' + name + '.py' for name in ('pinned_actions', 'permissions', 'slice_cap', 'readable_text', 'tests_travel', 'pr_total')])
