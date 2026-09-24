import unittest
from xml.etree import ElementTree

from scripts.update_activity import render_heatmap, render_monthly, summarize_calendar


SAMPLE = {
    "totalContributions": 3,
    "weeks": [
        {"contributionDays": [
            {"date": "2025-12-31", "contributionCount": 2, "color": "#40c463"},
            {"date": "2026-01-01", "contributionCount": 1, "color": "#9be9a8"},
        ]},
    ],
}


class ActivityGraphTests(unittest.TestCase):
    def test_monthly_counts_cross_year_boundary(self):
        summary = summarize_calendar(SAMPLE)
        self.assertEqual(summary["total"], 3)
        self.assertEqual(summary["monthly"]["2025-12"], 2)
        self.assertEqual(summary["monthly"]["2026-01"], 1)

    def test_both_graphs_are_valid_svg_with_accessible_summary(self):
        for render in (render_heatmap, render_monthly):
            svg = render(SAMPLE)
            root = ElementTree.fromstring(svg)
            self.assertEqual(root.tag, "{http://www.w3.org/2000/svg}svg")
            self.assertIn("3 contributions", svg)
            self.assertIn("<title>", svg)
            self.assertIn("<desc>", svg)


if __name__ == "__main__":
    unittest.main()
