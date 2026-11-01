"""Bounded mutation witnesses for each of the five gate entry scripts."""
import os
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
        """Kills tag/docker-ref and duplicate-uses bypasses; local/SHA controls pass."""
        for ref in ('a/b@v1', 'docker://image', './local', 'a/b@' + 'a' * 40):
            self.write('.github/actions/action.yaml', 'runs: {steps: [{uses: "' + ref + '"}]}\n')
            self.assertEqual(bool(self.check('actions')), ref in ('a/b@v1', 'docker://image'))
        self.write('.github/x.yml', 'uses: a/b@v1\nuses: ./local\n')
        with self.assertRaises(ValueError):
            self.check('actions')

    def test_permissions_reject_write_secret_inheritance_mutations(self):
        """Kills missing/write-all permissions, inherited/dynamic secrets and job-write bypasses."""
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
        ]:
            self.write('.github/workflows/x.yml', permission + env + 'jobs:\n  x:\n    ' + job + '\n')
            self.assertEqual(bool(self.check('permissions')), fails)

    def test_slice_cap_rejects_file_line_binary_and_merge_bypasses(self):
        """Kills 11-file, 401-line, binary and ignored-merge counting mutations."""
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
        gate.git('merge', '--no-ff', '--no-commit', '-q', 'side')
        self.write('merge-resolution', 'x\n' * 401)
        self.commit('merge')
        self.assertTrue(self.check('slices', gate.git('rev-parse', 'HEAD').strip()))

    def test_readable_rejects_added_removed_header_like_and_message_mutations(self):
        """Kills omitted default-ignorables, removed/header/literal-path/binary/line-break and message bypasses."""
        for code in (27, 0x34f, 0x115f, 0x200d, 0x202e, 0xfe0f, 0xe0061, 0xe0100):
            self.assertTrue(gate.unreadable(chr(code), 'fixture', 1))
        self.assertFalse(gate.unreadable('plain Greek: theta', 'fixture', 1))
        self.write('.gitattributes', '*.py -diff\n')
        self.write('odd[1] name.py', '++safe' + chr(0x2028) + chr(0x200b) + '\n')
        head = self.commit('added')
        self.assertIn('U+200B', self.check('readable', head)[0])
        self.assertFalse(self.check('readable', head, {'odd[1] name.py'}))
        self.base = head
        self.write('odd[1] name.py', 'clean\n')
        head = self.commit('removed')
        self.assertTrue(self.check('readable', head))
        self.base = head
        self.write('README.md', 'next\n')
        self.assertTrue(self.check('readable', self.commit('bad ' + chr(0x202e))))

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
