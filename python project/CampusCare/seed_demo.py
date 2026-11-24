"""
CampusCare 2.0 - Demo data seeder.

Creates demo users and ~28 realistic complaints spread over the last 8 weeks:
recurring Wi-Fi reports in Hostel A (issue group), an emergency electrical
fault, overdue cases, anonymous reports, feedback (including a low rating and
a reopen), and resolved cases for resolution-time analytics.

Usage:
    python seed_demo.py           # seed only if database is empty
    python seed_demo.py --reset   # delete the database and reseed
"""
import os
import sys
from datetime import timedelta

import auth
import complaints
import database
import duplicate_detector as dup
import escalation
import priority_engine as pe
from priority_engine import now

STAFF = [
    ("STF-HOSTEL", "Rakesh Verma", "Hostel Administration / Housekeeping"),
    ("STF-FAC", "Sunita Deshpande", "Facilities / Maintenance"),
    ("STF-IT", "Imran Qureshi", "IT Support"),
    ("STF-ELEC", "Mahesh Patil", "Electrical Maintenance"),
    ("STF-HK", "Lakshmi Iyer", "Housekeeping"),
    ("STF-TRANS", "Joseph D'Souza", "Transport Office"),
    ("STF-ACAD", "Dr. Kavita Menon", "Academic Office / Faculty Coordinator"),
]

TEAM_STUDENTS = [
    ("S26CSEU3579", "Akanksha"),
    ("S26CSEU3557", "Ronit"),
    ("S26CSEU3582", "Anay"),
    ("S26CSEU3570", "Prince"),
    ("S26CSEU3564", "Nikunj"),
]

EXTRA_STUDENTS = [
    ("S26CSEU0101", "Aarav Mehta"),
    ("S26CSEU0102", "Diya Sharma"),
    ("S26CSEU0103", "Kabir Singh"),
    ("S26CSEU0104", "Ananya Rao"),
    ("S26CSEU0105", "Vivaan Gupta"),
    ("S26CSEU0106", "Ishita Nair"),
]


def seed(conn):
    current = now()
    auth.ensure_admin(conn)
    for uid, name, dept in STAFF:
        if not auth.get_user(conn, uid):
            auth.register_user(conn, uid, name, "staff123", role="staff", department=dept)
    for uid, name in TEAM_STUDENTS + EXTRA_STUDENTS:
        if not auth.get_user(conn, uid):
            auth.register_user(conn, uid, name, "campus123", role="student")

    def mk(days_ago, student, title, desc, cat, loc, sev, imp, risk,
           anonymous=False, emergency=False, steps=(), feedback=None, reopen=None):
        """Create a backdated complaint, then walk it through workflow steps.

        steps: list of (hours_after_creation, status, staff_id_or_None, note)
        feedback: (hours_after_creation, rating, comments)
        reopen: (hours_after_creation, reason)
        """
        created = current - timedelta(days=days_ago)
        result = complaints.create_complaint(
            conn, student, title, desc, cat, loc, sev, imp, risk,
            emergency_confirmed=emergency, anonymous=anonymous, current=created,
        )
        cid = result["complaint"]["complaint_id"]
        for hours, status, staff, note in steps:
            when = created + timedelta(hours=hours)
            if staff:
                complaints.assign(conn, cid, staff, "admin", current=when)
            if status:
                complaints.update_status(conn, cid, status, staff or "admin", note, current=when)
        if feedback:
            hours, rating, comments = feedback
            complaints.add_feedback(conn, cid, rating, comments,
                                    current=created + timedelta(hours=hours))
        if reopen:
            hours, reason = reopen
            complaints.request_reopen(conn, cid, student, reason,
                                      current=created + timedelta(hours=hours))
        return cid

    wifi_desc = ("Wi-Fi in Hostel A is very slow and disconnects frequently "
                 "during evening study hours.")
    wifi = [
        (26, "S26CSEU0101", "Slow Wi-Fi in Hostel A", wifi_desc),
        (24, "S26CSEU0102", "Hostel A Wi-Fi slow again",
         wifi_desc + " Same problem every day this week."),
        (21, "S26CSEU3557", "Slow Wi-Fi Hostel A block",
         "Hostel A Wi-Fi is very slow and disconnects frequently in evening study hours, online classes impossible."),
        (17, "S26CSEU0103", "Wi-Fi problem Hostel A",
         "Wi-Fi in Hostel A very slow, disconnects frequently during evening study hours."),
        (12, "S26CSEU0104", "Slow internet Wi-Fi Hostel A", wifi_desc),
        (5, "S26CSEU3564", "Hostel A Wi-Fi keeps disconnecting", wifi_desc),
    ]
    wifi_ids = []
    for days, student, title, desc in wifi:
        steps = [(30, "Assigned", "STF-IT", "Router logs requested")] if days > 15 else []
        if days > 20:
            steps.append((70, "In Progress", None, "Checking access-point load in Hostel A"))
        wifi_ids.append(mk(days, student, title, desc, "Internet", "Hostel A", 3, 4, 0, steps=steps))

    garbage = [
        (16, "S26CSEU0105", "Garbage not collected near Cafeteria",
         "Garbage bins near the cafeteria are overflowing and not collected for three days, bad smell."),
        (13, "S26CSEU0106", "Cafeteria garbage overflowing",
         "Garbage bins near the cafeteria overflowing, not collected for days, bad smell around eating area."),
        (9, "S26CSEU0101", "Garbage dump near Cafeteria",
         "Garbage near cafeteria not collected for three days, bins overflowing with bad smell."),
    ]
    for days, student, title, desc in garbage:
        mk(days, student, title, desc, "Cleanliness", "Cafeteria", 3, 3, 1,
           steps=[(20, "Assigned", "STF-HK", "Housekeeping team informed")])

    # Emergency electrical fault - Critical, fast resolution, happy feedback.
    mk(20, "S26CSEU3579", "Exposed live wire near Hostel B stairwell",
       "An exposed live wire is hanging near the Hostel B stairwell landing. Sparking was seen yesterday.",
       "Electricity", "Hostel B - Stairwell", 5, 4, 5, emergency=True,
       steps=[(1, "Assigned", "STF-ELEC", "Emergency: electrician dispatched"),
              (3, "In Progress", None, "Area cordoned off"),
              (6, "Resolved", None, "Wire replaced and insulated; area checked safe")],
       feedback=(20, 5, "Fixed within hours, thank you!"))

    mk(12, "S26CSEU3582", "Power outage in Academic Block 1",
       "Frequent power cuts in Academic Block 1 during afternoon lectures, classes disrupted.",
       "Electricity", "Academic Block 1", 4, 4, 2,
       steps=[(8, "Assigned", "STF-ELEC", "Load inspection scheduled"),
              (48, "Resolved", None, "Faulty breaker replaced, supply stable")],
       feedback=(60, 4, "Power is stable now."))

    mk(9, "S26CSEU3570", "Projector not working in Room 305",
       "The ceiling projector in Room 305 does not power on, lectures need the board only.",
       "Classroom", "Academic Block 1 - Room 305", 3, 3, 0,
       steps=[(26, "Assigned", "STF-FAC", "Technician visit planned"),
              (50, "In Progress", None, "Replacement lamp ordered")])

    mk(15, "S26CSEU0102", "Water cooler dirty in Library",
       "The library water cooler tray is dirty and water tastes stale, many students use it daily.",
       "Cleanliness", "Library - 2nd Floor", 3, 3, 1)

    mk(6, "S26CSEU0103", "Bus route 7 always late",
       "Route 7 college bus arrives 20-30 minutes late every morning, students miss first lecture.",
       "Transport", "Bus Stop - Gate 2", 2, 4, 0,
       steps=[(12, "Assigned", "STF-TRANS", "Driver and route timing under review")])

    mk(2, "S26CSEU0104", "Mess food quality poor",
       "Hostel A mess food quality has dropped this week, meals are often cold and undercooked.",
       "Hostel", "Hostel A - Mess", 3, 4, 1,
       steps=[(10, "Assigned", "STF-HOSTEL", "Mess committee meeting scheduled"),
              (20, "In Progress", None, "Vendor warned, menu revised")])

    mk(1, "S26CSEU0105", "AC not cooling in Computer Lab",
       "Air conditioning in Computer Lab AB2 is not cooling, lab becomes unusable by afternoon.",
       "Classroom", "Computer Lab - AB2", 3, 3, 0,
       steps=[(6, "Assigned", "STF-FAC", "Gas refill requested")])

    mk(10, "S26CSEU0106", "Leaking tap in Hostel B bathroom",
       "A tap in the Hostel B second floor bathroom leaks continuously, water wastage and slippery floor.",
       "Hostel", "Hostel B - 2nd Floor", 2, 2, 0)

    mk(5, "S26CSEU3557", "Street light broken near Gate 2",
       "The street light near Gate 2 is broken, the path is dark and unsafe after evening classes.",
       "Electricity", "Gate 2 Pathway", 2, 2, 1,
       steps=[(10, "Assigned", "STF-ELEC", "Replacement bulb issued"),
              (24, "Resolved", None, "Street light repaired and tested")],
       feedback=(40, 3, "Light works but took a day."))

    mk(2, "S26CSEU3582", "Library reference books misplaced",
       "Reference books in the library second floor are misplaced, shelf labels do not match.",
       "Other", "Library - 2nd Floor", 1, 2, 0)

    mk(1, "S26CSEU3570", "Wi-Fi down in Academic Block 2",
       "Wi-Fi in Academic Block 2 first floor is completely down since morning, lab sessions affected.",
       "Internet", "Academic Block 2", 4, 4, 0,
       steps=[(4, "Assigned", "STF-IT", "Switch reboot attempted, checking uplink")])

    # Low feedback -> review request -> student reopen.
    mk(8, "S26CSEU3564", "Classroom benches broken in Room 210",
       "Two benches in Room 210 are broken and wobble, students cannot sit safely.",
       "Classroom", "Academic Block 1 - Room 210", 2, 3, 1,
       steps=[(20, "Assigned", "STF-FAC", "Carpenter assigned"),
              (72, "Resolved", None, "Benches repaired")],
       feedback=(90, 2, "Repair was temporary, one bench broke again next day."),
       reopen=(100, "Bench broke again after repair, needs proper replacement."))

    mk(7, "S26CSEU0101", "Garbage dump smell near Sports Complex",
       "A garbage dump near the sports complex entrance smells badly, players are affected.",
       "Cleanliness", "Sports Complex", 3, 3, 1,
       steps=[(12, "Assigned", "STF-HK", "Clearance scheduled"),
              (48, "Resolved", None, "Dump cleared, bins installed")],
       feedback=(60, 4, "Area is clean now."))

    # Anonymous safety report.
    mk(3, "S26CSEU0102", "Unsafe broken railing on Hostel C terrace",
       "The terrace railing in Hostel C is broken at two places, serious fall risk for students.",
       "Hostel", "Hostel C - Terrace", 4, 3, 4, anonymous=True)

    mk(6, "S26CSEU0103", "Exam timetable clash for electives",
       "Two elective exams are scheduled in the same slot, students cannot appear for both.",
       "Academic", "Academic Office", 3, 3, 0,
       steps=[(16, "Assigned", "STF-ACAD", "Coordinator reviewing slots"),
              (40, "In Progress", None, "Revised draft timetable circulated")])

    mk(11, "S26CSEU0104", "Transport bus AC not working",
       "AC in route 3 bus is not working, students travelling long distance are affected.",
       "Transport", "Bus Route 3", 2, 3, 0,
       steps=[(18, "Assigned", "STF-TRANS", "Workshop visit booked"),
              (96, "Resolved", None, "AC compressor repaired")],
       feedback=(110, 5, "Bus AC works fine now."))

    mk(2, "S26CSEU0105", "Lab computers very slow",
       "Computers in Lab AB2 take ten minutes to boot and freeze during practical sessions.",
       "Internet", "Computer Lab - AB2", 3, 3, 0)

    mk(1, "S26CSEU0106", "Drinking water taste strange Hostel A",
       "Drinking water on Hostel A ground floor has a strange taste since yesterday.",
       "Hostel", "Hostel A", 3, 3, 2)

    mk(13, "S26CSEU3579", "Ceiling fan noisy in Room 210",
       "Ceiling fan in Room 210 makes loud noise and wobbles, distracting during lectures.",
       "Classroom", "Academic Block 1 - Room 210", 1, 2, 0,
       steps=[(30, "Assigned", "STF-FAC", "Electrician scheduled"),
              (120, "Resolved", None, "Fan bearings replaced")],
       feedback=(130, 4, "Fan is quiet now."))

    mk(4, "S26CSEU3557", "Stray dogs near Hostel B gate",
       "A pack of stray dogs gathers near Hostel B gate at night, students feel unsafe returning late.",
       "Other", "Hostel B - Gate", 3, 3, 2,
       steps=[(14, "Assigned", "admin", "Municipal animal control contacted"),
              (30, "In Progress", None, "Awaiting municipal pickup schedule")])

    # Open Critical emergency - shows in the critical queue and escalates immediately.
    mk(1, "S26CSEU0106", "Sparking switchboard near Hostel C mess",
       "The main switchboard near Hostel C mess is sparking and smells of burning plastic, staff saw smoke.",
       "Electricity", "Hostel C - Mess", 5, 4, 5, emergency=True,
       steps=[(2, "Assigned", "STF-ELEC", "Emergency: electrician dispatched, area cordoned"),
              (5, "In Progress", None, "Awaiting replacement board from stores")])

    # Confirm the large Wi-Fi group so preventive maintenance can suggest an inspection.
    groups = dup.group_details(conn)
    wifi_group = next((g for g in groups if g["location"] == "Hostel A" and g["category"] == "Internet"), None)
    if wifi_group:
        dup.confirm_group(conn, wifi_group["group_id"])

    checks = escalation.run_checks(conn, current)
    return checks


def main():
    reset = "--reset" in sys.argv
    if reset and os.path.exists(database.DEFAULT_DB_PATH):
        os.remove(database.DEFAULT_DB_PATH)
        print("Existing database removed.")
    conn = database.connect()
    existing = conn.execute("SELECT COUNT(*) AS c FROM complaints").fetchone()["c"]
    if existing and not reset:
        print(f"Database already has {existing} complaints. Use --reset to reseed.")
        return
    checks = seed(conn)
    s = conn.execute("SELECT COUNT(*) AS c FROM complaints").fetchone()["c"]
    users = conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"]
    groups = dup.group_details(conn)
    print(f"Seeded {users} users and {s} complaints.")
    print(f"Issue groups: {len(groups)} | Overdue after checks: {checks['total_overdue']}")
    print("\nDemo logins:")
    print("  Admin:   admin / admin123")
    print("  Staff:   STF-IT / staff123  (any STF-* id)")
    print("  Student: S26CSEU3579 / campus123  (any listed student id)")
    conn.close()


if __name__ == "__main__":
    main()
