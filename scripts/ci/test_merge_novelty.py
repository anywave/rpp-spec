"""Pure gate fixtures: no trusted-layer imports, keys or merge-driver execution."""
from pathlib import Path
import unittest

import gate
import test_gate as fixtures


class MergeNoveltyTests(unittest.TestCase):
    setUp = fixtures.GateTests.setUp
    tearDown = fixtures.GateTests.tearDown
    write = fixtures.GateTests.write
    commit = fixtures.GateTests.commit

    def test_update_does_not_recharge_two_small_commits_or_eleven_inherited_paths(self):
        """Kills base-side cumulative charging and counting zero-novel raw candidates."""
        original = '# top\n' + '# anchor\n' * 10 + '# bottom\n'
        for index in range(11):
            self.write(f'f{index}.py', original)
        common = self.commit('reviewed baseline')
        gate.git('checkout', '-qb', 'feature')
        for group in (range(6), range(6, 11)):
            for index in group:
                self.write(f'f{index}.py', '# branch\n' * 38 + original.split('\n', 1)[1])
            self.commit('bounded branch slice\n\nno-test: controlled graph fixture')
        gate.git('checkout', '-q', 'master')
        for group in (range(6), range(6, 11)):
            for index in group:
                self.write(f'f{index}.py', original.replace('# bottom', '# reviewed BASE'))
            self.base = self.commit('reviewed BASE slice')
        gate.git('checkout', '-q', 'feature')
        gate.git('-c', 'commit.gpgsign=false', 'merge', '--no-ff', '-qm', 'update from master', 'master')
        head = gate.git('rev-parse', 'HEAD').strip()
        self.assertGreater(gate.slice_counts(gate.git('diff', '--numstat', '-z', common, head), set())[1], 400)
        self.assertEqual(len(gate.git('diff-tree', '--cc', '--name-only', '-z', '-r', '--no-commit-id', head).split('\0')[:-1]), 11)
        self.assertEqual(gate.slices(Path('.'), self.base, head, set()), [])
        self.assertEqual(gate.travel(Path('.'), self.base, head, set()), [])
        self.assertEqual(gate.novel_merge_records(head), [])

    def test_novel_resolution_counts_401_lines_but_not_inherited_changes(self):
        """Kills ignored merge-resolution additions or counting an inherited branch file."""
        gate.git('checkout', '-qb', 'feature')
        self.write('branch.txt', 'inherited\n')
        self.commit('branch')
        gate.git('checkout', '-q', 'master')
        self.write('master.txt', 'reviewed\n')
        self.base = self.commit('reviewed BASE')
        gate.git('checkout', '-q', 'feature')
        gate.git('merge', '--no-ff', '--no-commit', '-q', 'master')
        self.write('novel.py', '# novel\n' * 401)
        head = self.commit('novel merge resolution')
        self.assertTrue(any('files=1 lines=401' in finding for finding in gate.slices(Path('.'), self.base, head, set())))
        self.assertEqual(gate.novel_merge_records(head), [('401', '0', 'novel.py')])
        self.assertTrue(gate.travel(Path('.'), self.base, head, set()))

    def node(self, label, *parents):
        command = ['-c', 'commit.gpgsign=false', 'commit-tree', gate.git('rev-parse', self.base + '^{tree}').strip(), '-m', label]
        for parent in parents:
            command += ['-p', parent]
        return gate.git(*command).strip()

    def test_unsafe_or_ambiguous_merge_graphs_still_fail_closed(self):
        """Kills removed first-parent, octopus, ambiguous-side or criss-cross guards."""
        common = self.base
        left, side = self.node('left', common), self.node('side', common)
        self.base = self.node('BASE', common)
        cases = [(self.node('escape', common, self.base), 'first parent'),
                 (self.node('octopus', left, self.base, side), 'octopus'),
                 (self.node('ambiguous', left, side), 'BASE-side parent')]
        for head, reason in cases:
            with self.assertRaisesRegex(ValueError, reason):
                gate.slices(Path('.'), self.base, head, set())
        self.base = self.node('left merge', left, side)
        head = self.node('right merge', side, left)
        with self.assertRaisesRegex(ValueError, 'exactly one merge base'):
            gate.slices(Path('.'), self.base, head, set())

    def test_update_cannot_revert_401_base_rows_by_keeping_the_branch_tree(self):
        """Kills combined-only charging and accepting a clean but nonmatching text certificate."""
        self.write('source.py', ''.join(f'# original {i}\n' for i in range(201)))
        common = self.commit('reviewed source')
        gate.git('checkout', '-qb', 'feature')
        self.write('branch.txt', 'branch\n')
        feature = self.commit('branch')
        gate.git('checkout', '-q', 'master')
        for start in (0, 100, 200):
            lines = Path('source.py').read_text().splitlines(True)
            for index in range(start, min(start + 100, 201)):
                lines[index] = f'# reviewed {index}\n'
            self.write('source.py', ''.join(lines))
            self.base = self.commit('bounded reviewed BASE slice')
        tree = gate.git('rev-parse', feature + '^{tree}').strip()
        head = gate.git('-c', 'commit.gpgsign=false', 'commit-tree', tree, '-p', feature, '-p', self.base, '-m', 'keep branch').strip()
        self.assertEqual(gate.merge_base(feature, self.base), common)
        self.assertEqual(gate.novel_merge_records(head), [])
        self.assertEqual(gate.slice_counts(gate.commit_diff(self.base, head, '--numstat', '-z'), set()), (1, 402))
        self.assertTrue(gate.slices(Path('.'), self.base, head, set()))
        self.assertTrue(gate.travel(Path('.'), self.base, head, set()))

    def test_redundant_current_or_historical_base_parent_is_refused(self):
        """Kills accepting a redundant merge that restores the older BASE tree."""
        common = self.base
        self.write('README.md', 'branch\n')
        feature = self.commit('branch')
        head = self.node('restore old BASE', feature, common)
        for base in (common, self.node('advanced BASE', common)):
            with self.assertRaisesRegex(ValueError, 'redundant BASE-side parent'):
                gate.commit_diff(base, head, '--numstat', '-z')
