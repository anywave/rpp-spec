"""Mutation witnesses for composite metadata, PR totals and UTF-8 rules."""
import subprocess
import unittest

import gate
import test_gate as fixtures


class RuleTests(unittest.TestCase):
    setUp = fixtures.GateTests.setUp
    tearDown = fixtures.GateTests.tearDown
    write = fixtures.GateTests.write
    commit = fixtures.GateTests.commit
    check = fixtures.GateTests.check

    def test_composite_outside_github_cannot_hide_unpinned_uses(self):
        """Kills scanning only .github while composite actions elsewhere use tags."""
        for name in ('tools/widget/action.yml', 'nested/adapter/action.yaml'):
            self.write(name, 'runs: {using: composite, steps: [{uses: a/b@v1}]}\n')
            self.assertTrue(self.check('actions'))
            self.write(name, 'runs: {using: composite, steps: [{uses: a/b@' + 'a' * 40 + '}]}\n')
            self.assertEqual(self.check('actions'), [])

    def test_pr_total_rejects_31_files_and_1501_lines_with_exact_allowlist(self):
        """Kills omitted total cap, off-by-one thresholds and broad allowlist matches."""
        for index in range(30):
            self.write(f'f{index}', 'x\n' * 50)
        head = self.commit('exact total limit')
        self.assertEqual(self.check('total', head), [])
        self.write('extra', 'x\n')
        head = self.commit('past total limit')
        self.assertTrue(self.check('total', head))
        self.assertEqual(self.check('total', head, {'extra'}), [])
        self.base = head
        self.write('large', 'x\n' * 1501)
        self.assertTrue(self.check('total', self.commit('large PR delta')))

    def test_merge_master_first_parent_and_pr_total_exclude_base_only_changes(self):
        """Kills both-parent merge counting and counting integration changes as PR additions."""
        gate.git('checkout', '-qb', 'feature', self.base)
        self.write('feature.py', '# PR change\n')
        self.commit('feature')
        gate.git('checkout', '-q', 'master')
        self.write('base-update', 'x\n' * 300)
        self.base = self.commit('master update')
        gate.git('checkout', '-q', 'feature')
        gate.git('-c', 'commit.gpgsign=false', 'merge', '--no-ff', '-qm', 'merge master into feature', 'master')
        head = gate.git('rev-parse', 'HEAD').strip()
        self.assertEqual(gate.slice_counts(gate.commit_diff(head, '--numstat', '-z'), set()), (1, 300))
        self.assertEqual(gate.changed(self.base, head), ['feature.py'])
        self.assertEqual(self.check('slices', head), [])
        self.assertEqual(self.check('total', head), [])

    def test_non_utf8_commit_message_cannot_be_replacement_clean(self):
        """Kills replacement decoding that hides invalid raw commit-message bytes."""
        self.write('plain.txt', 'valid\n')
        head = self.commit('valid message')
        header = gate.git_bytes('cat-file', 'commit', head).partition(b'\n\n')[0]
        result = subprocess.run(['git', 'hash-object', '-w', '-t', 'commit', '--stdin'], input=header + b'\n\ninvalid \xff\n', capture_output=True, check=True)
        findings = self.check('readable', result.stdout.decode().strip())
        self.assertTrue(any('non-UTF-8 bytes' in finding for finding in findings))

    def test_readable_bounds_changed_content_before_patch_read(self):
        """Kills unbounded patch/blob reads on a huge single-line addition."""
        self.write('large.txt', 'a' * (4 * 1024 * 1024 + 1))
        findings = self.check('readable', self.commit('large single line'))
        self.assertTrue(any('exceeds 4 MiB' in finding for finding in findings))

    def test_commit_object_and_history_limits_fail_closed(self):
        """Kills unbounded commit-body reads and unbounded per-commit check loops."""
        self.write('plain.txt', 'valid\n')
        head = self.commit('valid')
        header = gate.git_bytes('cat-file', 'commit', head).partition(b'\n\n')[0]
        result = subprocess.run(['git', 'hash-object', '-w', '-t', 'commit', '--stdin'], input=header + b'\n\n' + b'x' * (1024 * 1024 + 1), capture_output=True, check=True)
        with self.assertRaisesRegex(ValueError, 'commit object exceeds 1 MiB'):
            gate.message_bytes(result.stdout.decode().strip())
        with unittest.mock.patch.object(gate, 'git', return_value='a' * 40 + '\n'):
            self.assertEqual(len(gate.commits(self.base, head)), 1)
        with unittest.mock.patch.object(gate, 'git', return_value=('a' * 40 + '\n') * 129):
            with self.assertRaisesRegex(ValueError, '128 commits'):
                gate.commits(self.base, head)
