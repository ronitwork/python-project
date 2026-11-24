# CampusCare 2.0

**Smart Campus Complaint Management and Decision-Support System**
Computational Thinking and Programming (2026CSAE100) — Bennett University, 2026–27

Team: Akanksha (S26CSEU3579), Ronit (S26CSEU3557), Anay (S26CSEU3582), Prince (S26CSEU3570), Nikunj (S26CSEU3564)

## What it does

Students submit campus problems (hostel, classroom, internet, electricity, cleanliness,
transport, academic, other), track progress and rate resolutions. Staff work a
department queue; administrators assign, monitor deadlines and see campus-level
analytics. The system:

- validates every submission and rejects exact duplicates;
- scores priority transparently: `P = S×5 + I×4 + R×3 + age bonus` with an
  emergency safety override (Critical);
- groups similar recurring reports (Jaccard similarity ≥ 0.45, same category +
  location) into issue groups and suggests preventive maintenance;
- routes complaints to departments, keeps a timestamped status timeline,
  flags and escalates overdue cases;
- sends in-app notifications, collects 1–5 feedback (low ratings request review,
  students can request reopening);
- shows dashboards and six matplotlib charts, and exports CSV + summary reports;
- stores everything in SQLite; passwords are PBKDF2-HMAC-SHA256 hashed with salts;
- supports anonymous reporting (identity hidden from staff/admin views).

## Requirements

- Python 3.10+ (developed on 3.12), Windows/macOS/Linux with Tk support
- `matplotlib` (only third-party runtime dependency): `pip install matplotlib`
- Optional for report tooling: `pillow`, `python-docx`

## Run

```bash
cd CampusCare
python seed_demo.py --reset   # optional: synthetic demo data (19 users, 30 complaints, 8 weeks)
python main.py                # launch the GUI
```

Demo logins (after seeding):

| Role    | User ID      | Password  |
|---------|--------------|-----------|
| Admin   | `admin`      | `admin123`|
| Staff   | `STF-IT` (or any `STF-*`) | `staff123` |
| Student | `S26CSEU3579` (or any seeded student) | `campus123` |

Without seeding, a default `admin / admin123` account is created on first run and
students can self-register from the login screen.

## Tests

```bash
python -m unittest discover -s tests -v   # 37 tests, all passing
```

## Project layout

```
main.py               entry point, login shell, role-based navigation
database.py           SQLite schema + connection
auth.py               registration/login, PBKDF2 hashing, roles
complaints.py         lifecycle: create, assign, status, feedback, reopen
priority_engine.py    scoring, bands, emergency override, deadlines
duplicate_detector.py normalisation, Jaccard similarity, issue groups
escalation.py         overdue checks + escalation notifications
notifications.py      in-app notification records
analytics.py          metrics, matplotlib charts, CSV/text exports
student.py staff.py admin.py ui_common.py   Tkinter views and dialogs
seed_demo.py          synthetic demo dataset
tests/                37 automated unit tests
data/campuscare.db    SQLite database (created at runtime)
reports/              CSV + summary report exports
screenshots/          GUI screenshots used in the report
diagrams/             flowchart + architecture diagrams
capture_screenshots.py  automated screenshot capture (needs pillow)
make_diagrams.py        report diagram generation
build_report.py         final report builder (needs python-docx)
CampusCare_Final_Project_Report.docx   completed project report
```

## Notes

- All demo data is **synthetic** (`seed_demo.py`); no real student data is used.
- Response targets (Critical immediate, High 1 day, Medium 3 days, Low 7 days)
  are demonstration values, configurable in `priority_engine.DEADLINE_DAYS`.
- A ticket is **not** a replacement for emergency help: emergency reports show a
  notice directing users to campus security/emergency services.
