"""Static trust-contract witnesses for the BASE-owned workflow."""
from pathlib import Path
import unittest

import yaml


PIP = 'python -I -m pip --isolated install --require-hashes --no-deps --only-binary=:all: -r scripts/ci/requirements.txt'
GUARD = "${{ always() && vars.CODEX_GATE_APP_READY == 'true' && github.event.pull_request.base.ref == github.event.repository.default_branch && github.ref == format('refs/heads/{0}', github.event.repository.default_branch) }}"
POST = '\n'.join([
    'gh api --hostname github.com --method POST "repos/$REPOSITORY/statuses/$HEAD_SHA" \\',
    '  --raw-field state="$GATE_STATE" \\',
    "  --raw-field context='anywave/codex-gate' \\",
    "  --raw-field description='BASE policy review' \\",
    '  --raw-field target_url="$TARGET_URL"',
])


class WorkflowTests(unittest.TestCase):
    def contract(self, text):
        data = yaml.load(text, Loader=yaml.BaseLoader)
        self.assertEqual(data['on'], 'pull_request_target')
        self.assertEqual(data['permissions'], {'contents': 'read'})
        self.assertNotIn('env', data)
        self.assertEqual(set(data['jobs']), {'base-code', 'app-status'})
        job = data['jobs']['base-code']
        self.assertEqual(job['name'], 'codex-gate-trusted')
        self.assertEqual(set(job), {'name', 'runs-on', 'timeout-minutes', 'steps'})
        steps = job['steps']
        self.assertEqual(len(steps), 6)
        checkouts = [step for step in steps if step.get('uses', '').startswith('actions/checkout@')]
        self.assertEqual(len(checkouts), 1)
        self.assertEqual(checkouts[0]['with']['ref'], '${{ github.event.pull_request.base.sha }}')
        self.assertEqual(checkouts[0]['with']['persist-credentials'], 'false')
        self.assertEqual(steps[2], {
            'uses': 'actions/checkout@11d5960a326750d5838078e36cf38b85af677262',
            'with': {'ref': '${{ github.event.pull_request.base.sha }}', 'fetch-depth': '0', 'persist-credentials': 'false'},
        })
        self.assertEqual(steps[3], {
            'uses': 'actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065',
            'with': {'python-version': '3.12'},
        })
        self.assertEqual(set(steps[4]), {'name', 'run'})
        self.assertEqual(set(steps[5]), {'name', 'env', 'run'})
        self.assertEqual(steps[0], {
            'name': 'Explain unconfigured App status',
            'if': "${{ vars.CODEX_GATE_APP_READY != 'true' }}",
            'run': "echo '::notice::App status posting skipped until RADIX configures the App and codex-gate environment and sets CODEX_GATE_APP_READY=true.'",
        })
        self.assertEqual(steps[1], {
            'name': 'Explain non-integration target',
            'if': "${{ github.event.pull_request.base.ref != github.event.repository.default_branch || github.ref != format('refs/heads/{0}', github.event.repository.default_branch) }}",
            'run': "echo '::notice::App status posting skipped because this run does not target the integration branch.'",
        })
        runs = [step['run'].strip() for step in steps if 'run' in step]
        self.assertEqual(runs[2:], [
            PIP,
            'python -I scripts/ci/trusted_gate.py --base "$BASE_SHA" --head "$HEAD_SHA" --pr "$PR_NUMBER" --output "$RUNNER_TEMP/codex-gate-trusted.json"',
        ])
        self.assertNotIn('secrets.', yaml.dump(job))
        self.assertNotIn('GH_TOKEN', yaml.dump(job))
        self.assertEqual(steps[-1]['env'], {
            'BASE_SHA': '${{ github.event.pull_request.base.sha }}',
            'HEAD_SHA': '${{ github.event.pull_request.head.sha }}',
            'PR_NUMBER': '${{ github.event.pull_request.number }}',
        })
        status = data['jobs']['app-status']
        self.assertEqual(set(status), {'name', 'needs', 'if', 'environment', 'runs-on', 'timeout-minutes', 'steps'})
        self.assertEqual(status['needs'], 'base-code')
        self.assertEqual(' '.join(status['if'].split()), GUARD)
        self.assertEqual(status['environment'], 'codex-gate')
        self.assertEqual(len(status['steps']), 2)
        mint, post = status['steps']
        self.assertEqual(mint, {
            'name': 'Mint repository status token', 'id': 'app-token',
            'uses': 'actions/create-github-app-token@64ab729a6294000f5aa4a4bc0b73d1f32bc45510',
            'with': {
                'client-id': '${{ vars.CODEX_GATE_APP_CLIENT_ID }}',
                'private-key': '${{ secrets.CODEX_GATE_APP_PRIVATE_KEY }}',
                'owner': '${{ github.repository_owner }}',
                'repositories': '${{ github.event.repository.name }}',
                'permission-statuses': 'write',
            },
        })
        self.assertEqual(set(post), {'name', 'env', 'run'})
        self.assertEqual(post['env'], {
            'GH_TOKEN': '${{ steps.app-token.outputs.token }}',
            'HEAD_SHA': '${{ github.event.pull_request.head.sha }}',
            'GATE_STATE': "${{ needs.base-code.result == 'success' && 'success' || 'failure' }}",
            'REPOSITORY': '${{ github.repository }}',
            'TARGET_URL': '${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}',
        })
        self.assertEqual(post['run'].strip(), POST)
        self.assertEqual(text.count('secrets.'), 1)
        self.assertEqual(text.count('${{ steps.app-token.outputs.token }}'), 1)

    def rejects(self, mutate):
        document = yaml.load(Path('.github/workflows/codex-gate-trusted.yml').read_text(), Loader=yaml.BaseLoader)
        mutate(document)
        with self.assertRaises(AssertionError):
            self.contract(yaml.dump(document))

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

    def test_status_requires_environment_ready_integration_ref_and_read_only_token(self):
        """Kills environment/READY/ref guard bypass, tag pin, expanded scope and GITHUB_TOKEN write mutations."""
        self.contract(Path('.github/workflows/codex-gate-trusted.yml').read_text())
        for field, value in [('environment', 'elsewhere'), ('if', '${{ always() }}'), ('needs', 'untrusted')]:
            self.rejects(lambda data: data['jobs']['app-status'].__setitem__(field, value))
        self.rejects(lambda data: data.__setitem__('permissions', {'statuses': 'write'}))
        self.rejects(lambda data: data['jobs']['app-status']['steps'][0].__setitem__('uses', 'actions/create-github-app-token@v3'))
        self.rejects(lambda data: data['jobs']['app-status']['steps'][0]['with'].__setitem__('repositories', 'another-repo'))

    def test_status_job_rejects_token_leaks_extra_steps_or_head_execution(self):
        """Kills job-wide tokens, extra steps, HEAD checkout, leaked key and skipped/failure-tolerant BASE evaluation."""
        self.contract(Path('.github/workflows/codex-gate-trusted.yml').read_text())
        self.rejects(lambda data: data['jobs']['app-status'].__setitem__('env', {'GH_TOKEN': '${{ steps.app-token.outputs.token }}'}))
        self.rejects(lambda data: data['jobs']['app-status']['steps'].append({'run': 'echo extra'}))
        self.rejects(lambda data: data['jobs']['app-status']['steps'].append({'uses': 'actions/checkout@' + 'a' * 40}))
        self.rejects(lambda data: data['jobs']['app-status']['steps'][1]['env'].__setitem__('KEY', '${{ secrets.CODEX_GATE_APP_PRIVATE_KEY }}'))
        self.rejects(lambda data: data['jobs']['base-code']['steps'][-1].__setitem__('if', '${{ false }}'))
        self.rejects(lambda data: data['jobs']['base-code']['steps'][-1].__setitem__('continue-on-error', 'true'))

    def test_status_targets_event_head_and_base_result_with_fixed_context(self):
        """Kills BASE-target status, unconditional success, PR-controlled state and forged context mutations."""
        self.contract(Path('.github/workflows/codex-gate-trusted.yml').read_text())
        for field, value in [('HEAD_SHA', '${{ github.sha }}'), ('GATE_STATE', 'success'), ('GATE_STATE', '${{ github.event.pull_request.title }}')]:
            self.rejects(lambda data: data['jobs']['app-status']['steps'][1]['env'].__setitem__(field, value))
        self.rejects(lambda data: data['jobs']['app-status']['steps'][1].__setitem__('run', POST.replace('anywave/codex-gate', 'forged/context')))
