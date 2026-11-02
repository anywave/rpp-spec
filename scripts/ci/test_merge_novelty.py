"""Pure gate fixtures: no trusted-layer imports, keys or merge-driver execution."""
from pathlib import Path
import shlex
import unittest
from unittest import mock

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
        self.assertEqual(gate.novel_merge_records(head), [('401', '0', 'novel.py')])
        self.assertTrue(any('files=1 lines=401' in finding for finding in gate.slices(Path('.'), self.base, head, set())))
        self.assertTrue(gate.travel(Path('.'), self.base, head, set()))

    def test_binary_mode_empty_and_quoted_paths_keep_their_costs(self):
        """Kills binary-as-zero, lost metadata-only paths and quoted-path identity loss."""
        self.write('mode.py', '# same\n')
        self.base = self.commit('reviewed mode baseline')
        gate.git('checkout', '-qb', 'feature')
        self.write('branch.txt', 'branch\n')
        self.commit('branch')
        gate.git('checkout', '-q', 'master')
        self.write('master.txt', 'reviewed\n')
        self.base = self.commit('BASE')
        gate.git('checkout', '-q', 'feature')
        gate.git('merge', '--no-ff', '--no-commit', '-q', 'master')
        self.write('empty', '')
        self.write('odd[1] " name.py', '# new\n')
        Path('new.bin').write_bytes(b'\0binary')
        gate.git('add', '-A')
        gate.git('update-index', '--chmod=+x', 'mode.py')
        gate.git('-c', 'commit.gpgsign=false', 'commit', '-qm', 'metadata and binary resolution')
        head = gate.git('rev-parse', 'HEAD').strip()
        self.assertEqual(set(gate.novel_merge_records(head)),
                         {('0', '0', 'empty'), ('0', '0', 'mode.py'),
                          ('-', '-', 'new.bin'), ('1', '0', 'odd[1] " name.py')})
        self.assertEqual(gate.slice_counts(gate.commit_diff(self.base, head, '--numstat', '-z'), set()), (4, 402))

    def test_invalid_utf8_path_and_unsupported_raw_format_fail_closed(self):
        """Kills lossy path replacement and silently accepting malformed combined records."""
        header = b'::100644 100644 100644 ' + b'a' * 40 + b' ' + b'b' * 40 + b' ' + b'c' * 40 + b' MM\0'
        for raw, error in [(header + b'bad_\xff.py\0', UnicodeDecodeError),
                           (b'unsupported\0path\0', ValueError)]:
            with mock.patch.object(gate, 'git_bytes', return_value=raw):
                with self.assertRaises(error):
                    gate.novel_merge_records('fixture')

    def node(self, label, *parents):
        command = ['-c', 'commit.gpgsign=false', 'commit-tree', gate.git('rev-parse', self.base + '^{tree}').strip(), '-m', label]
        for parent in parents:
            command += ['-p', parent]
        return gate.git(*command).strip()

    def test_configured_merge_driver_is_never_executed(self):
        """Kills remerge-diff executing a driver selected by tracked attributes."""
        self.write('.gitattributes', 'conflict.txt merge=fixture\n')
        self.write('conflict.txt', 'common\n')
        common = self.commit('driver fixture')
        gate.git('checkout', '-qb', 'feature')
        self.write('conflict.txt', 'feature\n')
        feature = self.commit('feature')
        gate.git('checkout', '-q', 'master')
        self.write('conflict.txt', 'reviewed\n')
        self.base = self.commit('reviewed BASE')
        tree = gate.git('rev-parse', feature + '^{tree}').strip()
        head = gate.git('-c', 'commit.gpgsign=false', 'commit-tree', tree, '-p', feature, '-p', self.base, '-m', 'choose feature').strip()
        marker = self.root / 'driver-ran'
        gate.git('config', 'merge.fixture.driver', 'echo ran > ' + shlex.quote(marker.as_posix()))
        self.assertEqual(gate.novel_merge_records(head), [])
        self.assertFalse(marker.exists())
        self.assertEqual(gate.slice_counts(gate.commit_diff(self.base, head, '--numstat', '-z'), set()), (0, 0))
        self.assertEqual(gate.merge_base(self.base, head), self.base)
        self.assertNotEqual(common, self.base)

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
