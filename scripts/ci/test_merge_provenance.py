"""Object-only provenance and clean-carry witnesses compose with the A gate."""
from pathlib import Path
import unittest
from unittest import mock

import gate
import test_gate as fixtures


class ProvenanceTests(unittest.TestCase):
    setUp = fixtures.GateTests.setUp
    tearDown = fixtures.GateTests.tearDown
    write = fixtures.GateTests.write
    commit = fixtures.GateTests.commit

    def test_zero_length_hunks_use_gap_origins_instead_of_preceding_rows(self):
        """Kills subtracting one from zero-count gaps in either hunk axis."""
        self.assertEqual(gate.ranges(b'@@ -2 +1,0 @@'), (1, 1, 1, 0))
        self.assertEqual([gate.origin(row, [(1, 1, 1, 0)]) for row in (0, 1)], [0, 2])
        self.assertEqual(gate.ranges(b'@@ -1,0 +2 @@'), (1, 0, 1, 1))
        self.assertEqual([gate.origin(row, [(1, 0, 1, 1)]) for row in (0, 1, 2)], [0, None, 1])

    def test_repeated_line_origins_cannot_launder_base_reversions(self):
        """Kills blind text budgets, interior-only overlap and incomplete repeated-origin guards."""
        initial = self.base
        cases = [('AAAA', 'BAAB', 'AABA'), ('ABBB', 'BABA', 'ABAB'),
                 ('BAAA', 'ABAB', 'BABA'), ('AAAAB', 'BABAA', 'ABAAB')]
        for original, branch, baseline in cases:
            gate.git('checkout', '-q', '--detach', initial)
            self.write('source.py', ''.join('# ' + value + '\n' for value in original))
            common = self.commit('common')
            self.write('source.py', ''.join('# ' + value + '\n' for value in branch))
            feature = self.commit('branch\n\nno-test: controlled source fixture')
            gate.git('checkout', '-q', '--detach', common)
            self.write('source.py', ''.join('# ' + value + '\n' for value in baseline))
            self.base = self.commit('reviewed BASE')
            tree = gate.git('rev-parse', feature + '^{tree}').strip()
            head = gate.git('-c', 'commit.gpgsign=false', 'commit-tree', tree, '-p', feature, '-p', self.base, '-m', 'restore branch').strip()
            self.assertTrue(gate.commit_diff(self.base, head, '--numstat', '-z'), (original, branch, baseline))

    def test_clean_distant_moves_do_not_recharge_independent_401_row_insert(self):
        """Kills path-wide movement vetoes and disabling the exact clean-text certificate."""
        def rows(label, count):
            return [f'# {label}-{index}\n' for index in range(count)]
        original = (rows('top-pre', 10) + ['# repeated\n'] + rows('top-gap', 20)
                    + ['# top-target\n'] + rows('middle-pre', 30) + ['# middle-marker\n']
                    + rows('middle-post', 30) + rows('bottom-pre', 10) + ['# repeated\n']
                    + rows('bottom-gap', 20) + ['# bottom-target\n'])
        self.write('source.py', ''.join(original))
        self.commit('reviewed anchored source')
        gate.git('checkout', '-qb', 'feature')
        point = original.index('# middle-marker\n') + 1
        for count in (200, 401):
            self.write('source.py', ''.join(original[:point] + ['# branch payload\n'] * count + original[point:]))
            self.commit('bounded branch insert\n\nno-test: controlled source fixture')
        gate.git('checkout', '-q', 'master')
        body = [line for line in original if line != '# repeated\n']
        for marker in ('# top-target\n', '# bottom-target\n'):
            body.insert(body.index(marker), '# repeated\n')
        self.write('source.py', ''.join(body))
        self.base = self.commit('reviewed independent distant moves')
        gate.git('checkout', '-q', 'feature')
        gate.git('-c', 'commit.gpgsign=false', 'merge', '--no-ff', '-qm', 'automatic update', 'master')
        head = gate.git('rev-parse', 'HEAD').strip()
        self.assertEqual(gate.commit_diff(self.base, head, '--numstat', '-z'), '')
        self.assertEqual(gate.slices(Path('.'), self.base, head, set()), [])
        self.assertEqual(gate.travel(Path('.'), self.base, head, set()), [])

    def test_text_certificate_refuses_unavailable_commands_and_nonregular_blobs(self):
        """Kills treating a failed command, binary data or a symlink as clean text proof."""
        entry = {'modes': (b'100644', b'100644'), 'blobs': (b'a' * 40, b'b' * 40)}
        with mock.patch.object(gate, 'git_bytes', return_value=b'text\n'), mock.patch.object(gate.subprocess, 'run', side_effect=gate.subprocess.TimeoutExpired('git', 30)):
            with self.assertRaisesRegex(ValueError, 'unavailable'):
                gate.automatic_text_carry(entry, {}, {})
        for content, mode in ((b'text\0binary', b'100644'), (b'text\n', b'120000')):
            entry['modes'] = mode, mode
            with mock.patch.object(gate, 'git_bytes', return_value=content), mock.patch.object(gate.subprocess, 'run') as run:
                self.assertFalse(gate.automatic_text_carry(entry, {}, {}))
                run.assert_not_called()
