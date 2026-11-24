"""
CampusCare 2.0 - Automated test suite (unittest).

Covers: priority scoring, age bonus, emergency override, priority bands,
department routing, deadlines, text similarity, duplicate rejection,
complaint lifecycle, overdue escalation, feedback/review, reopening,
authentication, persistence, anonymity, issue grouping and CSV export.

Run:  python -m unittest discover -s tests -v
"""
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import analytics
import auth
import complaints
import database
import duplicate_detector as dup
import escalation
import notifications
import priority_engine as pe


class CampusCareTestBase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp.name, "test.db")
        self.conn = database.connect(self.db_path)
        auth.ensure_admin(self.conn)
        auth.register_user(self.conn, "STU001", "Test Student", "secret123", role="student")
        auth.register_user(self.conn, "STU002", "Other Student", "secret123", role="student")
        auth.register_user(self.conn, "STF-IT", "IT Technician", "staff123",
                           role="staff", department="IT Support")

    def tearDown(self):
        self.conn.close()
        self.tmp.cleanup()

    def make_complaint(self, student="STU001", title="Wi-Fi not working in Hostel A",
                       description="The Wi-Fi in Hostel A room 204 keeps disconnecting every evening.",
                       category="Internet", location="Hostel A", severity=3, impact=4,
                       safety_risk=0, current=None, **kw):
        return complaints.create_complaint(
            self.conn, student, title, description, category, location,
            severity, impact, safety_risk, current=current, **kw)


class PriorityEngineTests(CampusCareTestBase):
    def test_weighted_score_max(self):
        created = datetime(2026, 1, 1)
        self.assertEqual(pe.calculate_score(5, 5, 5, created, created), 60)

    def test_age_bonus(self):
        created = datetime(2026, 1, 1)
        current = created + timedelta(days=6)
        self.assertEqual(pe.calculate_score(1, 1, 0, created, current), 11)

    def test_no_age_bonus_when_resolved(self):
        created = datetime(2026, 1, 1)
        current = created + timedelta(days=30)
        self.assertEqual(pe.calculate_score(1, 1, 0, created, current, resolved=True), 9)

    def test_emergency_override(self):
        self.assertEqual(pe.priority_from_score(10, emergency=True), "Critical")

    def test_emergency_keywords(self):
        self.assertTrue(pe.is_emergency("Exposed live wire near stairwell", "sparking seen"))
        self.assertFalse(pe.is_emergency("Slow fan", "fan makes noise"))

    def test_priority_band_boundaries(self):
        self.assertEqual(pe.priority_from_score(20), "Low")
        self.assertEqual(pe.priority_from_score(21), "Medium")
        self.assertEqual(pe.priority_from_score(40), "Medium")
        self.assertEqual(pe.priority_from_score(41), "High")
        self.assertEqual(pe.priority_from_score(55), "High")
        self.assertEqual(pe.priority_from_score(56), "Critical")

    def test_department_routing(self):
        self.assertEqual(pe.route_department("Internet"), "IT Support")
        self.assertEqual(pe.route_department("Electricity"), "Electrical Maintenance")
        self.assertEqual(pe.route_department("Unknown"), "Administrator Review")

    def test_deadline_targets(self):
        created = datetime(2026, 1, 1)
        self.assertEqual(pe.calculate_due_date(created, "Critical"), created)
        self.assertEqual(pe.calculate_due_date(created, "High"), created + timedelta(days=1))
        self.assertEqual(pe.calculate_due_date(created, "Medium"), created + timedelta(days=3))
        self.assertEqual(pe.calculate_due_date(created, "Low"), created + timedelta(days=7))

    def test_score_refresh_grows_with_age(self):
        created = pe.now() - timedelta(days=9)
        cid = self.make_complaint(current=created)["complaint"]["complaint_id"]
        before = complaints.get_complaint(self.conn, cid)["priority_score"]
        pe.refresh_score(self.conn, cid)
        after = complaints.get_complaint(self.conn, cid)["priority_score"]
        self.assertEqual(after, before + 3)  # 9 days // 3


class DuplicateDetectionTests(CampusCareTestBase):
    def test_normalize_and_tokens(self):
        self.assertEqual(dup.normalize("  Slow   Wi-Fi!! "), "slow wifi")
        self.assertIn("wifi", dup.tokenize("The Wi-Fi is slow"))
        self.assertNotIn("the", dup.tokenize("The Wi-Fi is slow"))

    def test_jaccard_values(self):
        self.assertEqual(dup.jaccard({"a", "b"}, {"a", "b"}), 1.0)
        self.assertEqual(dup.jaccard({"a"}, {"b"}), 0.0)
        self.assertAlmostEqual(dup.jaccard({"a", "b"}, {"b", "c"}), 1 / 3)

    def test_exact_duplicate_rejected(self):
        self.make_complaint()
        with self.assertRaises(complaints.DuplicateError):
            self.make_complaint(title="wi-fi NOT working in hostel a!!")

    def test_same_title_different_student_allowed(self):
        self.make_complaint(student="STU001")
        result = self.make_complaint(student="STU002")
        self.assertIsNotNone(result["complaint"])

    def test_similarity_requires_same_category_and_location(self):
        self.make_complaint()
        matches = dup.find_similar(self.conn, "Internet", "Hostel A",
                                   "Wi-Fi not working in Hostel A",
                                   "The Wi-Fi in Hostel A room 204 keeps disconnecting every evening.")
        self.assertTrue(matches)
        other_loc = dup.find_similar(self.conn, "Internet", "Hostel B",
                                     "Wi-Fi not working in Hostel A",
                                     "The Wi-Fi in Hostel A room 204 keeps disconnecting every evening.")
        self.assertFalse(other_loc)
        other_cat = dup.find_similar(self.conn, "Electricity", "Hostel A",
                                     "Wi-Fi not working in Hostel A",
                                     "The Wi-Fi in Hostel A room 204 keeps disconnecting every evening.")
        self.assertFalse(other_cat)

    def test_grouping_and_preventive_suggestion(self):
        desc = "Wi-Fi in Hostel A is very slow and disconnects frequently during evening study hours."
        r1 = self.make_complaint(student="STU001", title="Slow Wi-Fi in Hostel A", description=desc)
        self.assertIsNone(r1["group_id"])
        r2 = self.make_complaint(student="STU002", title="Hostel A Wi-Fi slow again",
                                 description=desc + " Same problem every day.")
        self.assertIsNotNone(r2["group_id"])
        gid = r2["group_id"]
        details = next(g for g in dup.group_details(self.conn) if g["group_id"] == gid)
        self.assertEqual(details["count"], 2)
        self.assertEqual(details["group_status"], "Suggested")
        self.assertFalse(dup.preventive_suggestions(self.conn))
        dup.confirm_group(self.conn, gid)
        r3 = self.make_complaint(student="STU001", title="Wi-Fi problem Hostel A",
                                 description="Wi-Fi in Hostel A very slow, disconnects frequently during evening study hours.",
                                 location="Hostel A")
        self.assertEqual(r3["group_id"], gid)
        suggestions = dup.preventive_suggestions(self.conn)
        self.assertEqual(len(suggestions), 1)
        self.assertEqual(suggestions[0]["count"], 3)


class ValidationTests(CampusCareTestBase):
    def test_empty_title_rejected(self):
        with self.assertRaises(complaints.ValidationError):
            self.make_complaint(title="")

    def test_short_description_rejected(self):
        with self.assertRaises(complaints.ValidationError):
            self.make_complaint(description="too short")

    def test_out_of_range_severity_rejected(self):
        with self.assertRaises(complaints.ValidationError):
            self.make_complaint(severity=9)

    def test_invalid_category_rejected(self):
        with self.assertRaises(complaints.ValidationError):
            self.make_complaint(category="Swimming Pool")

    def test_invalid_rating_rejected(self):
        cid = self.make_complaint()["complaint"]["complaint_id"]
        complaints.update_status(self.conn, cid, "Resolved", "STF-IT", "fixed")
        with self.assertRaises(complaints.ValidationError):
            complaints.add_feedback(self.conn, cid, 7, "great")
        with self.assertRaises(complaints.ValidationError):
            complaints.add_feedback(self.conn, cid, "abc", "great")


class WorkflowTests(CampusCareTestBase):
    def test_submission_stores_history_and_notifies_admin(self):
        result = self.make_complaint()
        row = result["complaint"]
        self.assertTrue(row["complaint_id"].startswith("CC-"))
        self.assertEqual(row["status"], "Pending")
        self.assertEqual(row["department"], "IT Support")
        events = complaints.timeline(self.conn, row["complaint_id"])
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["new_status"], "Pending")
        admin_unread = notifications.unread(self.conn, "admin")
        self.assertTrue(any(row["complaint_id"] in n["message"] for n in admin_unread))

    def test_assignment_updates_status_and_notifies(self):
        cid = self.make_complaint()["complaint"]["complaint_id"]
        complaints.assign(self.conn, cid, "STF-IT", "admin")
        row = complaints.get_complaint(self.conn, cid)
        self.assertEqual(row["status"], "Assigned")
        self.assertEqual(row["assigned_staff"], "STF-IT")
        self.assertTrue(notifications.unread(self.conn, "STU001"))
        self.assertTrue(notifications.unread(self.conn, "STF-IT"))

    def test_resolution_sets_timestamp_and_notifies_student(self):
        cid = self.make_complaint()["complaint"]["complaint_id"]
        complaints.update_status(self.conn, cid, "Resolved", "STF-IT", "Router replaced")
        row = complaints.get_complaint(self.conn, cid)
        self.assertEqual(row["status"], "Resolved")
        self.assertTrue(row["resolved_at"])
        msgs = [n["message"] for n in notifications.unread(self.conn, "STU001")]
        self.assertTrue(any("Resolved" in m for m in msgs))

    def test_overdue_detection_and_escalation(self):
        created = pe.now() - timedelta(days=10)
        cid = self.make_complaint(severity=1, impact=1, safety_risk=0,
                                  current=created)["complaint"]["complaint_id"]
        result = escalation.run_checks(self.conn)
        self.assertIn(cid, result["newly_overdue"])
        row = complaints.get_complaint(self.conn, cid)
        self.assertEqual(row["overdue"], 1)
        admin_msgs = [n["message"] for n in notifications.unread(self.conn, "admin")]
        self.assertTrue(any("overdue" in m.lower() and cid in m for m in admin_msgs))
        # Resolved complaints are never flagged.
        complaints.update_status(self.conn, cid, "Resolved", "STF-IT", "fixed")
        result2 = escalation.run_checks(self.conn)
        self.assertNotIn(cid, result2["newly_overdue"])
        self.assertEqual(complaints.get_complaint(self.conn, cid)["overdue"], 0)

    def test_low_feedback_requests_review_and_reopen(self):
        cid = self.make_complaint()["complaint"]["complaint_id"]
        complaints.update_status(self.conn, cid, "Resolved", "STF-IT", "fixed")
        result = complaints.add_feedback(self.conn, cid, 2, "Not actually fixed")
        self.assertTrue(result["review_requested"])
        admin_msgs = [n["message"] for n in notifications.unread(self.conn, "admin")]
        self.assertTrue(any("Low feedback" in m for m in admin_msgs))
        complaints.request_reopen(self.conn, cid, "STU001", "Problem persists")
        self.assertEqual(complaints.get_complaint(self.conn, cid)["status"], "Reopened")
        with self.assertRaises(complaints.ValidationError):
            complaints.request_reopen(self.conn, cid, "STU002", "not mine")

    def test_feedback_only_after_resolution_and_only_once(self):
        cid = self.make_complaint()["complaint"]["complaint_id"]
        with self.assertRaises(complaints.ValidationError):
            complaints.add_feedback(self.conn, cid, 5, "great")
        complaints.update_status(self.conn, cid, "Resolved", "STF-IT", "fixed")
        complaints.add_feedback(self.conn, cid, 5, "great")
        with self.assertRaises(complaints.ValidationError):
            complaints.add_feedback(self.conn, cid, 4, "again")

    def test_anonymous_identity_hidden(self):
        cid = self.make_complaint(anonymous=True)["complaint"]["complaint_id"]
        row = complaints.get_complaint(self.conn, cid)
        self.assertEqual(complaints.student_label(row, "STF-IT"), "Anonymous")
        self.assertEqual(complaints.student_label(row, "admin"), "Anonymous")
        self.assertEqual(complaints.student_label(row, "STU001"), "STU001")


class AuthTests(CampusCareTestBase):
    def test_register_and_login(self):
        user = auth.login(self.conn, "STU001", "secret123")
        self.assertIsNotNone(user)
        self.assertEqual(user["role"], "student")

    def test_wrong_password_fails(self):
        self.assertIsNone(auth.login(self.conn, "STU001", "wrong"))

    def test_duplicate_registration_fails(self):
        with self.assertRaises(auth.AuthError):
            auth.register_user(self.conn, "STU001", "Clone", "secret123")

    def test_short_password_fails(self):
        with self.assertRaises(auth.AuthError):
            auth.register_user(self.conn, "STU003", "New", "123")

    def test_password_not_stored_plain(self):
        row = auth.get_user(self.conn, "STU001")
        self.assertNotIn("secret123", row["password_hash"])
        self.assertNotIn("secret123", row["salt"])
        self.assertTrue(auth.verify_password("secret123", row["password_hash"], row["salt"]))


class PersistenceAndExportTests(CampusCareTestBase):
    def test_data_survives_reopen(self):
        cid = self.make_complaint()["complaint"]["complaint_id"]
        self.conn.close()
        self.conn = database.connect(self.db_path)
        self.assertIsNotNone(complaints.get_complaint(self.conn, cid))
        self.assertIsNotNone(auth.login(self.conn, "STU001", "secret123"))

    def test_csv_export_headers_and_rows(self):
        self.make_complaint()
        self.make_complaint(student="STU002", title="Fan noisy in Room 210",
                            description="Ceiling fan in Room 210 wobbles and makes loud noise.",
                            category="Classroom", location="Academic Block 1 - Room 210",
                            severity=1, impact=2)
        folder = os.path.join(self.tmp.name, "reports")
        path = analytics.export_csv(self.conn, folder)
        import csv as csvmod
        with open(path, newline="", encoding="utf-8") as f:
            reader = csvmod.DictReader(f)
            rows = list(reader)
            self.assertEqual(reader.fieldnames, analytics.EXPORT_FIELDS)
        self.assertEqual(len(rows), 2)

    def test_anonymous_csv_export_masks_id(self):
        self.make_complaint(anonymous=True)
        folder = os.path.join(self.tmp.name, "reports")
        path = analytics.export_csv(self.conn, folder)
        with open(path, encoding="utf-8") as f:
            content = f.read()
        self.assertNotIn("STU001", content)
        self.assertIn("Anonymous", content)

    def test_summary_report_and_metrics(self):
        created = pe.now() - timedelta(days=2)
        cid = self.make_complaint(current=created)["complaint"]["complaint_id"]
        complaints.update_status(self.conn, cid, "Resolved", "STF-IT", "fixed",
                                 current=created + timedelta(days=1))
        complaints.add_feedback(self.conn, cid, 4, "good", current=created + timedelta(days=1))
        s = analytics.summary(self.conn)
        self.assertEqual(s["total"], 1)
        self.assertEqual(s["resolved_count"], 1)
        self.assertAlmostEqual(s["avg_resolution_days"], 1.0, places=1)
        self.assertEqual(s["satisfaction"], 4.0)
        folder = os.path.join(self.tmp.name, "reports")
        path = analytics.export_summary_report(self.conn, folder)
        with open(path, encoding="utf-8") as f:
            text = f.read()
        self.assertIn("CAMPUSCARE 2.0", text)
        self.assertIn("STATUS BREAKDOWN", text)

    def test_charts_build_without_errors(self):
        self.make_complaint()
        figures = analytics.build_charts(self.conn)
        self.assertIn("category", figures)
        self.assertIn("trend", figures)
        for fig in figures.values():
            fig.clf()


if __name__ == "__main__":
    unittest.main(verbosity=2)
