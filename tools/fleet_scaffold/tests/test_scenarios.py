"""Bounded corpus provenance and host-fixture mutation witnesses."""
import unittest

from tools.fleet_scaffold import scenarios


class ScenarioTests(unittest.TestCase):
    def test_numeric_update_contract_rejects_before_constructing_or_replacing_link(self):
        """Kills accepting sentinel/ppm updates or writing the bad reading before rejection."""
        original = scenarios.link(1, 10)
        fixture = scenarios.FleetReadingFixture(original)
        # Python core accepts this latency; fleet rejection is a separate contract.
        self.assertEqual(scenarios.link(1, 2**64 - 1).latency, 2**64 - 1)
        for update in ({"latency": 2**64 - 1}, {"loss": 1_000_001}):
            self.assertEqual(fixture.update(**update), "INVALID_READING")
            self.assertEqual(fixture.current, original)
        self.assertEqual(fixture.update(latency=20, loss=1_000_000), "OK")
        self.assertEqual((fixture.current.latency, fixture.current.loss_ppm), (20, 1_000_000))

    def test_seventeen_rows_preserve_errors_ties_and_live_fallback_meanings(self):
        """Kills omitted cases, replay-as-OK, rollback-as-no-channel and stale ws selection."""
        rows = {row["scenario"]: row for row in scenarios.rows()}
        self.assertEqual(len(rows), 17)
        for name, status in [("control-replay", "DENIED"), ("clock-rollback", "CLOCK_ROLLBACK"),
                             ("xiaozhi-ws-lost", "NO_CHANNEL"), ("empty-endpoints-no-channel", "NO_CHANNEL")]:
            self.assertEqual(rows[name]["status"], status)
            self.assertEqual(rows[name]["endpoint"], "-")
        self.assertEqual(rows["equal-score-tie"]["failover"], "1,2")
        self.assertEqual(rows["xiaozhi-ws-lost-lan-fallback"]["failover"], "1")
        for name in scenarios.BOUNDARY_ROWS[:2]:
            self.assertEqual(rows[name]["traffic"], "fleet-update")
            self.assertEqual(rows[name]["status"], "INVALID_READING")

    def test_rendered_provenance_and_bytes_do_not_claim_independent_boundary_parity(self):
        """Kills hiding contract provenance, changing the seven columns or nondeterministic output."""
        first = scenarios.artifacts()
        self.assertEqual(first, scenarios.artifacts())
        self.assertIn(scenarios.PROVENANCE.encode(), first["fleet-scenarios.md"])
        self.assertEqual(first["fleet-scenarios.tsv"].splitlines()[0].split(b"\t"),
                         [field.encode() for field in scenarios.FIELDS])
        self.assertEqual(len(scenarios.FIELDS), 7)


if __name__ == "__main__":
    unittest.main()
