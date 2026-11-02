"""Real Git graph witnesses; signatures are synthetic mocked policy verdicts."""
from pathlib import Path
import unittest
from unittest import mock

import gate
import test_trusted_gate as fixtures


class GraphTests(unittest.TestCase):
    setUp = fixtures.TrustedGateTests.setUp
    tearDown = fixtures.TrustedGateTests.tearDown
    git = fixtures.TrustedGateTests.git
    write = fixtures.TrustedGateTests.write
    commit = fixtures.TrustedGateTests.commit

    def refused(self, operation, text):
        reason = ''
        try:
            operation()
        except ValueError as error:
            reason = str(error)
        self.assertIn(text, reason)

    def test_first_parent_base_escape_is_flagged(self):
        """Kills first-parent-only owner protection on a net gate rollback."""
        self.write('.github/reviewed.txt', 'old\n')
        common = self.commit()
        self.write('.github/reviewed.txt', 'reviewed\n')
        self.base = self.commit()
        tree = self.git('rev-parse', common + '^{tree}')
        head = self.git('commit-tree', tree, '-p', common, '-p', self.base, input=b'escape\n')
        self.assertEqual(self.git('rev-list', self.base + '..' + head), head)
        errors = self.runner.owner_findings(self.base, head)
        self.assertTrue(any('first parent is reachable from BASE' in error for error in errors))
        self.assertTrue(any('.github/reviewed.txt' in error and 'needs TR review' in error for error in errors))

    def test_any_parent_requires_merge_signature_for_net_gate_path(self):
        """Kills first-parent-only after the structural escape guard already passes."""
        self.write('.github/codex-gate-owners.txt', fixtures.SIGNER + '\n')
        common = self.commit()
        self.git('checkout', '-qb', 'feature', common)
        self.write('.github/branch.txt', 'owner edit\n')
        edit = self.commit()
        self.git('checkout', '-q', 'master')
        self.write('master.txt', 'ordinary\n')
        self.base = self.commit()
        self.git('checkout', '-q', 'feature')
        self.git('merge', '--no-ff', '-qm', 'merge master', 'master')
        head = self.git('rev-parse', 'HEAD')
        with mock.patch.object(self.runner, 'verify_owner', side_effect=lambda commit, *_: commit == edit) as verify:
            errors = self.runner.owner_findings(self.base, head)
        self.assertEqual([call.args[0] for call in verify.call_args_list], [edit, head])
        self.assertEqual(len(errors), 1)
        self.assertIn(head + ":'.github/branch.txt'", errors[0])
        with mock.patch.object(self.runner, 'verify_owner', return_value=True):
            self.assertEqual(self.runner.owner_findings(self.base, head), [])

    def test_merge_reviewed_master_does_not_charge_base_gate_change(self):
        """Kills wrong-parent slices/travel and owner review outside net gate paths."""
        self.git('checkout', '-qb', 'feature', self.base)
        self.write('feature.txt', 'ordinary PR\n')
        self.commit()
        self.git('checkout', '-q', 'master')
        self.write('scripts/ci/reviewed.py', '# reviewed BASE\n' * 401)
        self.base = self.commit()
        self.git('checkout', '-q', 'feature')
        self.git('merge', '--no-ff', '-qm', 'merge reviewed master', 'master')
        head = self.git('rev-parse', 'HEAD')
        self.assertEqual(gate.slices(Path('.'), self.base, head, set()), [])
        self.assertEqual(gate.travel(Path('.'), self.base, head, set()), [])
        with mock.patch.object(self.runner, 'verify_owner') as verify:
            self.assertEqual(self.runner.owner_findings(self.base, head), [])
        verify.assert_not_called()

    def test_octopus_merge_is_explicitly_refused(self):
        """Kills treating an ordinary three-parent merge as unambiguous review."""
        common = self.base
        self.git('checkout', '-qb', 'feature', common)
        self.write('feature.txt', 'one\n')
        self.commit()
        self.git('checkout', '-q', 'master')
        self.write('master.txt', 'two\n')
        self.base = self.commit()
        self.git('checkout', '-qb', 'side', common)
        self.write('side.txt', 'three\n')
        self.commit()
        self.git('checkout', '-q', 'feature')
        self.git('merge', '--no-ff', '-qm', 'octopus fixture', 'master', 'side')
        head = self.git('rev-parse', 'HEAD')
        self.assertEqual(len(self.git('show', '-s', '--format=%P', head).split()), 3)
        self.refused(lambda: gate.slices(Path('.'), self.base, head, set()), 'octopus merge refused')
        self.assertTrue(any('octopus merge refused' in error for error in self.runner.owner_findings(self.base, head)))

    def test_criss_cross_merge_bases_are_explicitly_refused(self):
        """Kills silently picking one of two actual best common ancestors."""
        common = self.base
        self.git('checkout', '-qb', 'left', common)
        self.write('left.txt', 'left\n')
        left = self.commit()
        self.git('checkout', '-qb', 'right', common)
        self.write('right.txt', 'right\n')
        right = self.commit()
        self.git('checkout', '-q', 'left')
        self.git('merge', '--no-ff', '-qm', 'left merge', 'right')
        self.base = self.git('rev-parse', 'HEAD')
        tree = self.git('rev-parse', 'HEAD^{tree}')
        head = self.git('commit-tree', tree, '-p', right, '-p', left, input=b'right merge\n')
        self.assertEqual(set(self.git('merge-base', '--all', self.base, head).splitlines()), {left, right})
        self.refused(lambda: gate.changed(self.base, head), 'exactly one merge base')
        self.refused(lambda: self.runner.owner_findings(self.base, head), 'exactly one merge base')

    def test_merge_without_base_side_parent_is_refused(self):
        """Kills guessing which of two feature-only parents represents reviewed BASE."""
        self.git('checkout', '-qb', 'left', self.base)
        self.write('left.txt', 'left\n')
        self.commit()
        self.git('checkout', '-qb', 'right', self.base)
        self.write('right.txt', 'right\n')
        self.commit()
        self.git('checkout', '-q', 'left')
        self.git('merge', '--no-ff', '-qm', 'ambiguous fixture', 'right')
        head = self.git('rev-parse', 'HEAD')
        self.refused(lambda: gate.slices(Path('.'), self.base, head, set()), 'BASE-side parent')
        self.assertTrue(any('BASE-side parent' in error for error in self.runner.owner_findings(self.base, head)))

    def test_fully_reverted_gate_path_is_outside_net_owner_scope(self):
        """Kills obsolete all-history path scope after the CX022 net-anchor ruling."""
        self.write('.github/temporary.txt', 'temporary\n')
        self.commit()
        (self.root / '.github/temporary.txt').unlink()
        head = self.commit()
        with mock.patch.object(self.runner, 'verify_owner') as verify:
            self.assertEqual(self.runner.owner_findings(self.base, head), [])
        verify.assert_not_called()
