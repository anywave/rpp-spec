"""Static trust-contract witnesses for the BASE-owned workflow."""
from pathlib import Path
import unittest

import yaml


class WorkflowTests(unittest.TestCase):
    def contract(self, text):
        data = yaml.load(text, Loader=yaml.BaseLoader)
        self.assertEqual(data['on'], 'pull_request_target')
        self.assertEqual(data['permissions'], {'contents': 'read'})
        job = data['jobs']['base-code']
        self.assertEqual(job['name'], 'codex-gate-trusted')
        steps = job['steps']
        checkouts = [step for step in steps if step.get('uses', '').startswith('actions/checkout@')]
        self.assertEqual(len(checkouts), 1)
        self.assertEqual(checkouts[0]['with']['ref'], '${{ github.event.pull_request.base.sha }}')
        self.assertEqual(checkouts[0]['with']['persist-credentials'], 'false')
        runs = [step['run'].strip() for step in steps if 'run' in step]
        self.assertEqual(runs, [
            'python -I -m pip install --only-binary=:all: --require-hashes -r scripts/ci/requirements.txt',
            'python -I scripts/ci/trusted_gate.py --base "$BASE_SHA" --head "$HEAD_SHA" --pr "$PR_NUMBER" --output "$RUNNER_TEMP/codex-gate-trusted.json"',
        ])
        self.assertNotIn('secrets.', text)

    def test_workflow_rejects_head_checkout_install_or_runner_mutations(self):
        """Kills PR checkout, write token persistence, HEAD pip and HEAD script execution."""
        text = Path('.github/workflows/codex-gate-trusted.yml').read_text()
        self.contract(text)
        for old, new in [
            ('pull_request_target', 'pull_request'),
            ('pull_request.base.sha', 'pull_request.head.sha'),
            ('persist-credentials: false', 'persist-credentials: true'),
            ('-r scripts/ci/requirements.txt', '-r head/requirements.txt'),
            ('python -I scripts/ci/trusted_gate.py', 'python head/scripts/ci/gate.py'),
        ]:
            with self.assertRaises(AssertionError):
                self.contract(text.replace(old, new))

    def test_initial_owner_file_has_no_auto_approved_identity(self):
        """Kills silently seeding a privileged identity instead of leaving TR's list empty."""
        entries = [line for line in Path('.github/codex-gate-owners.txt').read_text().splitlines() if line and not line.startswith('#')]
        self.assertEqual(entries, [])
