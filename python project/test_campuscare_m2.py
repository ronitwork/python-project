"""Basic automated tests for CampusCare Milestone 2 logic."""
import unittest
from datetime import datetime, timedelta
import campuscare_m2 as cc


class Milestone2Tests(unittest.TestCase):
    def test_weighted_score(self):
        created = datetime(2026, 1, 1)
        self.assertEqual(cc.calculate_score(5, 5, 5, created, created), 60)

    def test_age_bonus(self):
        created = datetime(2026, 1, 1)
        current = created + timedelta(days=6)
        self.assertEqual(cc.calculate_score(1, 1, 0, created, current), 11)

    def test_emergency_override(self):
        self.assertEqual(cc.priority_from_score(10, emergency=True), "Critical")

    def test_priority_bands(self):
        self.assertEqual(cc.priority_from_score(20), "Low")
        self.assertEqual(cc.priority_from_score(21), "Medium")
        self.assertEqual(cc.priority_from_score(41), "High")
        self.assertEqual(cc.priority_from_score(56), "Critical")

    def test_department_routing(self):
        self.assertEqual(cc.route_department("Internet"), "IT Support")
        self.assertEqual(cc.route_department("Electricity"), "Electrical Maintenance")

    def test_deadline_targets(self):
        created = datetime(2026, 1, 1)
        self.assertEqual(cc.calculate_due_date(created, "High"), created + timedelta(days=1))
        self.assertEqual(cc.calculate_due_date(created, "Low"), created + timedelta(days=7))


if __name__ == "__main__":
    unittest.main()
