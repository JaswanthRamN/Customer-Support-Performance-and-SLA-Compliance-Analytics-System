"""Static contracts for the Power BI model assets."""

from pathlib import Path
import unittest

from scripts.generate_synthetic_data import ROOT


class PowerBIAssetTests(unittest.TestCase):
    def setUp(self):
        self.query_dir = ROOT / "powerbi" / "power_query"

    def test_required_power_query_assets_exist(self):
        required = {
            "pServer.m", "pDatabase.m", "pAnalysisAsOfUtc.m", "StagingDatabase.m",
            "fnUtcDateTime.m", "FactTickets.m", "FactAssignmentHistory.m", "FactFeedback.m",
            "DimTeams.m", "DimAgents.m", "DimDate.m", "DimCurrentTeam.m",
            "DimHistoricalTeam.m", "DimCurrentAgent.m", "DimHistoricalAgent.m",
            "DimCreatedDate.m", "DimAssignmentDate.m", "DimFeedbackDate.m",
        }
        self.assertEqual(required, {path.name for path in self.query_dir.glob("*.m")})

    def test_ticket_query_preserves_grain_nulls_and_utc(self):
        query = (self.query_dir / "FactTickets.m").read_text(encoding="utf-8")
        self.assertNotIn("Table.NestedJoin", query)
        self.assertIn("if [first_response_at] = null then null", query)
        self.assertIn("if [resolved_at] = null then null", query)
        self.assertIn("unresolved_age_hours", query)
        function = (self.query_dir / "fnUtcDateTime.m").read_text(encoding="utf-8")
        self.assertIn("DateTimeZone.SwitchZone", function)
        self.assertIn("DateTimeZone.RemoveZone", function)

    def test_model_document_separates_current_and_historical_roles(self):
        guide = (ROOT / "docs" / "power_bi_model.md").read_text(encoding="utf-8")
        self.assertIn("DimCurrentTeam", guide)
        self.assertIn("DimHistoricalTeam", guide)
        self.assertIn("current backlog", guide)
        self.assertIn("cannot reconstruct backlog on a historical date", guide)
        self.assertIn("does **not** contain a `.pbix` file", guide)

    def test_dax_uses_distinct_ticket_counts(self):
        dax = (ROOT / "powerbi" / "dax" / "measures.dax").read_text(encoding="utf-8")
        self.assertIn("DISTINCTCOUNT(FactTickets[ticket_id])", dax)
        self.assertIn("DISTINCTCOUNT(FactAssignmentHistory[ticket_id])", dax)
        self.assertIn("DIVIDE([Response SLA Met]", dax)
        self.assertIn("AVERAGE(FactFeedback[csat_score])", dax)


if __name__ == "__main__":
    unittest.main()
