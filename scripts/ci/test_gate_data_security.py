"""Deep HEAD-data fixtures compose with the A gate; no HEAD code is executed."""
from pathlib import Path
import shlex
import unittest
from unittest import mock

import gate
import test_gate as fixtures


class DataSecurityTests(unittest.TestCase):
    setUp = fixtures.GateTests.setUp
    tearDown = fixtures.GateTests.tearDown
    write = fixtures.GateTests.write
    commit = fixtures.GateTests.commit
    check = fixtures.GateTests.check

    def test_binary_mode_empty_and_quoted_paths_keep_their_costs(self):
        """Kills binary-as-zero, lost metadata-only paths and quoted-path identity loss."""
        gate.git('config', 'core.filemode', 'false')
        self.write('mode.py', '# same\n')
        self.base = self.commit('reviewed mode baseline')
        gate.git('checkout', '-qb', 'feature')
        self.write('branch.txt', 'branch\n')
        self.commit('branch')
        gate.git('checkout', '-q', 'master')
        self.write('master.txt', 'reviewed\n')
        gate.git('add', '-A')
        gate.git('update-index', '--chmod=+x', 'mode.py')
        gate.git('-c', 'commit.gpgsign=false', 'commit', '-qm', 'reviewed executable mode')
        self.base = gate.git('rev-parse', 'HEAD').strip()
        gate.git('checkout', '-q', 'feature')
        gate.git('merge', '--no-ff', '--no-commit', '-q', 'master')
        self.write('empty', '')
        names = ['odd[1] " name.py', 'tab\tname.py', 'line\nname.py', 'cafe_\u00e9.py']
        Path('new.bin').write_bytes(b'\0binary')
        gate.git('add', '-A')
        blob = gate.git('rev-parse', 'HEAD:mode.py').strip()
        for name in names:
            gate.git('-c', 'core.protectNTFS=false', 'update-index', '--add', '--cacheinfo', '100644', blob, name)
        gate.git('update-index', '--cacheinfo', '120000', blob, 'mode.py')
        gate.git('-c', 'commit.gpgsign=false', 'commit', '-qm', 'metadata and binary resolution')
        head = gate.git('rev-parse', 'HEAD').strip()
        self.assertEqual(gate.slice_counts(gate.commit_diff(self.base, head, '--numstat', '-z'), set()), (7, 405))
        self.assertEqual(set(gate.novel_merge_records(head)),
                         {('0', '0', 'empty'), ('0', '0', 'mode.py'), ('-', '-', 'new.bin')}
                         | {('1', '0', name) for name in names})


    def test_invalid_utf8_path_and_unsupported_raw_format_fail_closed(self):
        """Kills lossy path replacement and silently accepting malformed combined records."""
        header = b'::100644 100644 100644 ' + b'a' * 40 + b' ' + b'b' * 40 + b' ' + b'c' * 40 + b' MM\0'
        for raw, error in [(header + b'bad_\xff.py\0', UnicodeDecodeError),
                           (b'unsupported\0path\0', ValueError),
                           (header.replace(b' MM', b' ZZ') + b'path\0', ValueError)]:
            with mock.patch.object(gate, 'git_bytes', return_value=raw) as read:
                with self.assertRaises(error):
                    gate.novel_merge_records('fixture')
                read.assert_called_once()
        for patch in (b'diff --cc path\n@@@ invalid @@@\n', b'diff --cc other\n',
                      b'diff --cc "unterminated\n', b'diff --cc path\n@@@ -0,0 -0,0 +1,1 @@@\n??invalid\n'):
            with mock.patch.object(gate, 'git_bytes', side_effect=[header + b'path\0', patch]):
                with self.assertRaises(ValueError):
                    gate.novel_merge_records('fixture')


    def test_distinct_parent_deletions_count_symmetric_and_asymmetric_resolutions(self):
        """Kills dropping private deletions or using min(401, 1) for removed source."""
        self.write('big.py', ''.join(f'# common {i}\n' for i in range(401)))
        common = self.commit('reviewed deletion baseline')
        gate.git('checkout', '-qb', 'delete-feature')
        for start in range(0, 401, 100):
            lines = Path('big.py').read_text().splitlines(True)
            for index in range(start, min(start + 100, 401)):
                lines[index] = f'# feature {index}\n'
            self.write('big.py', ''.join(lines))
            feature = self.commit('small edit\n\nno-test: controlled source fixture')
        for count in (401, 1):
            gate.git('checkout', '-q', '--detach', common)
            self.write('big.py', ''.join(f'# BASE {i}\n' for i in range(count)))
            self.base = self.commit('reviewed BASE version')
            self.write('big.py', '')
            gate.git('add', 'big.py')
            tree = gate.git('write-tree').strip()
            head = gate.git('-c', 'commit.gpgsign=false', 'commit-tree', tree, '-p', feature, '-p', self.base, '-m', 'delete both versions').strip()
            gate.git('checkout', '-q', '--detach', head)
            self.assertTrue(any('lines=401' in finding for finding in gate.slices(Path('.'), self.base, head, set())))
            self.assertTrue(gate.travel(Path('.'), self.base, head, set()))
            self.assertEqual(gate.novel_merge_records(head), [('0', '401', 'big.py')])


    def test_kept_lines_separate_independent_private_deletion_runs(self):
        """Kills cross-run pairing, missing result/context rows and suppressed blank prefixes."""
        initial = self.base
        gate.git('config', 'diff.suppressBlankEmpty', 'true')
        for kept, middle, removed in (('# keep\n', '# keep\n', 2), ('# keep\n', '', 402), ('\n', '\n', 2)):
            gate.git('checkout', '-q', '--detach', initial)
            self.write('big.py', '# C1\n' + kept + '# C2\n')
            common = self.commit('reviewed source')
            self.write('big.py', '# C1\n' + '# A\n' * 400 + kept + '# C2\n')
            feature = self.commit('400 additions\n\nno-test: controlled source fixture')
            gate.git('checkout', '-q', '--detach', common)
            self.write('big.py', '# C1\n' + middle + '# C2\n' + '# B\n' * 400)
            self.base = self.commit('reviewed BASE source')
            self.write('big.py', kept)
            gate.git('add', 'big.py')
            tree = gate.git('write-tree').strip()
            head = gate.git('-c', 'commit.gpgsign=false', 'commit-tree', tree, '-p', feature, '-p', self.base, '-m', 'separate deletion runs').strip()
            gate.git('checkout', '-q', '--detach', head)
            self.assertEqual(gate.novel_merge_records(head), [('0', str(removed), 'big.py')], (repr(kept), repr(middle)))
            self.assertEqual(gate.slice_counts(gate.commit_diff(self.base, head, '--numstat', '-z'), set()), (1, 403 if not middle else 402))
            self.assertTrue(gate.slices(Path('.'), self.base, head, set()))
            self.assertTrue(gate.travel(Path('.'), self.base, head, set()))


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
        self.assertEqual(gate.slice_counts(gate.commit_diff(self.base, head, '--numstat', '-z'), set()), (1, 2))
        self.assertEqual(gate.novel_merge_records(head), [])
        self.assertFalse(marker.exists())
        self.assertEqual(gate.merge_base(self.base, head), self.base)
        self.assertNotEqual(common, self.base)


    def test_readable_rejects_added_header_like_and_message_mutations_but_allows_removal(self):
        """Kills omitted default-ignorables/header/literal-path/line-break/message and removed-text rejection mutations."""
        for code in (27, 0x34f, 0x115f, 0x200d, 0x202e, 0xfe0f, 0xe0061, 0xe0100):
            self.assertTrue(gate.unreadable(chr(code), 'fixture', 1))
        self.assertFalse(gate.unreadable('plain Greek: theta', 'fixture', 1))
        self.write('.gitattributes', '*.py -diff\n')
        self.write('odd[1] name.py', '++safe' + chr(0x2028) + chr(0x200b) + '\n')
        head = self.commit('added')
        findings = self.check('readable', head)
        self.assertTrue(any('U+200B' in finding for finding in findings))
        self.assertTrue(any('U+2028' in finding for finding in findings))
        self.assertFalse(self.check('readable', head, {'odd[1] name.py'}))
        self.base = head
        self.write('odd[1] name.py', 'clean\n')
        head = self.commit('removed')
        self.assertEqual(self.check('readable', head), [])
        self.base = head
        self.write('README.md', 'next\n')
        self.assertTrue(self.check('readable', self.commit('bad ' + chr(0x202e))))


    def test_readable_skips_binary_but_rejects_non_utf8_added_bytes(self):
        """Kills PNG-as-text and replacement-decoding that hides invalid added bytes."""
        Path('pixel.png').write_bytes(b'\x89PNG\r\n\x1a\n\0\x1b' + chr(0x200b).encode())
        head = self.commit('binary image')
        self.assertEqual(self.check('readable', head), [])
        self.assertIn('\ufffd', gate.git('show', f'{head}:pixel.png'))
        self.base = head
        Path('broken.txt').write_bytes(b'visible \xff text\n')
        head = self.commit('non UTF8 text')
        self.assertTrue(any('non-UTF-8 bytes' in finding for finding in self.check('readable', head)))
        self.base = head
        Path('broken.txt').write_bytes(b'visible \xff ' + chr(0x200b).encode() + b'\n')
        findings = self.check('readable', self.commit('hidden text after invalid UTF8'))
        self.assertTrue(any('non-UTF-8 bytes' in finding for finding in findings))


    def test_no_test_rejects_empty_reason_before_coauthor_trailer_mutation(self):
        """Kills newline-consuming no-test whitespace; a nonempty same-line reason still passes."""
        for index, reason in enumerate(('', ' ', '\t ')):
            self.write('source.rs', f'fn changed_{index}() {{}}\n')
            head = self.commit('source\n\nno-test:' + reason + '\n\nCo-authored-by: Fixture <fixture@example.invalid>')
            self.assertTrue(self.check('travel', head))
            self.base = head
        self.write('source.rs', 'fn documented() {}\n')
        head = self.commit('source\n\nno-test:\tfixture reason\n\nCo-authored-by: Fixture <fixture@example.invalid>')
        self.assertEqual(self.check('travel', head), [])


    def test_readable_rejects_lossy_filename_identity_mutation(self):
        """Kills replacement-decoded Git paths that silently select no diff."""
        original = gate.git_bytes
        def output(*args):
            return b'1\t0\tbad_\xff.py\0' if args[0] == 'diff' and '--numstat' in args else original(*args)
        with mock.patch.object(gate, 'git_bytes', side_effect=output):
            self.assertIn('non-UTF8 filename refused', self.check('readable')[0])
