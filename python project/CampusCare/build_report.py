"""
CampusCare 2.0 - Final project report builder.

Recreates the Bennett University "Project Report Format" (Computational Thinking
and Programming, 2026CSAE100) and fills every section with the completed
CampusCare 2.0 project content, real screenshots, diagrams and test results.

Usage: python build_report.py
Output: CampusCare_Final_Project_Report.docx
"""
import os

from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

HERE = os.path.dirname(os.path.abspath(__file__))
SHOTS = os.path.join(HERE, "screenshots")
DIAGRAMS = os.path.join(HERE, "diagrams")
OUT = os.path.join(HERE, "CampusCare_Final_Project_Report.docx")

NAVY = RGBColor(0x16, 0x32, 0x4F)
PRIMARY = RGBColor(0x1F, 0x6F, 0xEB)
GREY = RGBColor(0x5B, 0x6B, 0x7C)

doc = Document()

# ------------------------------------------------------------------ styles
normal = doc.styles["Normal"]
normal.font.name = "Calibri"
normal.font.size = Pt(11)
normal.paragraph_format.space_after = Pt(6)
normal.paragraph_format.line_spacing = 1.12

for name, size in (("Heading 1", 15), ("Heading 2", 12.5)):
    st = doc.styles[name]
    st.font.name = "Calibri"
    st.font.size = Pt(size)
    st.font.bold = True
    st.font.color.rgb = NAVY
    st.paragraph_format.space_before = Pt(14)
    st.paragraph_format.space_after = Pt(6)

for section in doc.sections:
    section.top_margin = Inches(0.8)
    section.bottom_margin = Inches(0.8)
    section.left_margin = Inches(0.9)
    section.right_margin = Inches(0.9)


def para(text="", bold=False, size=None, color=None, align=None, italic=False, space_after=None):
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.bold = bold
    run.italic = italic
    if size:
        run.font.size = Pt(size)
    if color:
        run.font.color.rgb = color
    if align is not None:
        p.alignment = align
    if space_after is not None:
        p.paragraph_format.space_after = Pt(space_after)
    return p


def bullet(text, bold_prefix=None):
    p = doc.add_paragraph(style="List Bullet")
    if bold_prefix:
        r = p.add_run(bold_prefix)
        r.bold = True
        p.add_run(text)
    else:
        p.add_run(text)
    return p


def numbered(text):
    return doc.add_paragraph(text, style="List Number")


def shade(cell, hexcolor):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:fill"), hexcolor)
    tcPr.append(shd)


def table(headers, rows, widths=None, header_fill="16324F"):
    t = doc.add_table(rows=1, cols=len(headers))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr = t.rows[0].cells
    for i, h in enumerate(headers):
        hdr[i].text = ""
        run = hdr[i].paragraphs[0].add_run(h)
        run.bold = True
        run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        run.font.size = Pt(10)
        shade(hdr[i], header_fill)
    for row in rows:
        cells = t.add_row().cells
        for i, value in enumerate(row):
            cells[i].text = ""
            run = cells[i].paragraphs[0].add_run(str(value))
            run.font.size = Pt(10)
    if widths:
        for i, w in enumerate(widths):
            for row in t.rows:
                row.cells[i].width = Inches(w)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return t


def picture(filename, width=6.3, caption=None, folder=SHOTS):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.line_spacing = 1.0
    p.add_run().add_picture(os.path.join(folder, filename), width=Inches(width))
    if caption:
        cp = para(caption, italic=True, size=9.5, color=GREY, align=WD_ALIGN_PARAGRAPH.CENTER)
        cp.paragraph_format.space_after = Pt(6)


def code_block(lines):
    for line in lines:
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.left_indent = Inches(0.25)
        run = p.add_run(line)
        run.font.name = "Consolas"
        run.font.size = Pt(9.5)
        rpr = run._element.get_or_add_rPr()
        rfonts = rpr.find(qn("w:rFonts"))
        if rfonts is None:
            rfonts = OxmlElement("w:rFonts")
            rpr.append(rfonts)
        rfonts.set(qn("w:eastAsia"), "Consolas")
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


# ================================================================== COVER
para("BENNETT UNIVERSITY", bold=True, size=18, color=NAVY, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=2)
para("School of Computer Science Engineering and Technology", size=12, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=2)
para("Computational Thinking and Programming", size=12, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=2)
para("Course Code: 2026CSAE100", size=11, color=GREY, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=18)
para("PYTHON PROJECT REPORT", bold=True, size=15, color=PRIMARY, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=14)
para("CampusCare 2.0", bold=True, size=22, color=NAVY, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=2)
para("Smart Campus Complaint Management and Decision-Support System",
     size=13, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=24)

cover = doc.add_table(rows=0, cols=2)
cover.style = "Table Grid"
cover.alignment = WD_TABLE_ALIGNMENT.CENTER
cover_rows = [
    ("Student Name", "Akanksha"),
    ("Enrollment Number", "S26CSEU3579"),
    ("Batch / Section", "2026-27 / [Fill Section]"),
    ("Team Member 2", "Ronit - S26CSEU3557"),
    ("Team Member 3", "Anay - S26CSEU3582"),
    ("Team Member 4", "Prince - S26CSEU3570"),
    ("Team Member 5", "Nikunj - S26CSEU3564"),
]
for label, value in cover_rows:
    cells = cover.add_row().cells
    r = cells[0].paragraphs[0].add_run(label)
    r.bold = True
    r.font.size = Pt(11)
    shade(cells[0], "EAF2FF")
    cells[1].paragraphs[0].add_run(value).font.size = Pt(11)
    cells[0].width = Inches(2.2)
    cells[1].width = Inches(4.0)

para("", space_after=10)
para("Academic Year: 2026-27", bold=True, size=12, align=WD_ALIGN_PARAGRAPH.CENTER)
doc.add_page_break()

# ======================================================== 1. PROBLEM STATEMENT
doc.add_heading("1. Problem Statement", level=1)
para("What is the problem? Students often report campus problems verbally or through informal "
     "channels such as messaging groups, phone calls or word of mouth. These reports are difficult "
     "to track, may be assigned to the wrong department, and can remain unresolved without clear "
     "accountability. A minor inconvenience (for example a noisy fan) and a safety-related fault "
     "(for example an exposed live wire) may receive similar attention even though their "
     "consequences differ greatly. Repeated complaints about the same location or facility are "
     "recorded separately, hiding a larger campus-wide problem such as failing Wi-Fi infrastructure "
     "in one hostel.")
para("Who faces this problem? Students across hostels, classrooms, internet services, electricity, "
     "cleanliness, transport and academics face unresolved or slowly resolved issues. Faculty and "
     "maintenance staff receive unstructured requests without priority or deadline information. "
     "College administrators lack a central record, so they cannot see which departments are "
     "overloaded, which locations generate repeated reports, or which cases are overdue.")
para("Why is it useful to solve this problem? CampusCare provides a central record for each issue, "
     "calculates a transparent priority score, routes the issue to the relevant department, monitors "
     "deadlines and presents administrators with useful reports and charts. Grouping similar reports "
     "makes recurring campus problems visible, and feedback after resolution tells the college "
     "whether fixes actually satisfy students. Staff remain responsible for reviewing and acting on "
     "reports; the system supports their decisions rather than replacing them.")

# ======================================================== 2. OBJECTIVES
doc.add_heading("2. Project Objectives", level=1)
numbered("Provide a simple, validated and role-based way (student, staff, administrator) to submit "
         "and track campus complaints, with reliable SQLite storage and secure password hashing.")
numbered("Calculate a transparent priority score from severity, impact, safety risk and complaint "
         "age, with an emergency safety override that marks dangerous incidents Critical.")
numbered("Detect exact duplicate reports and group similar recurring complaints using text "
         "similarity, so campus-wide patterns and preventive-maintenance needs become visible.")
numbered("Route complaints to the correct department, support staff assignment, record a full "
         "status timeline, and detect and escalate overdue cases against configurable deadlines.")
numbered("Notify users about progress, collect post-resolution feedback with review/reopening, and "
         "generate analytics charts, summary reports and CSV exports for administrators.")

# ======================================================== 3. MODULES
doc.add_heading("3. Main Features / Modules", level=1)
para("The final system is implemented as twelve Python modules with a Tkinter graphical interface "
     "and an SQLite database. The table lists the modules developed and tested.")
table(
    ["S. No.", "Module / Feature", "Description"],
    [
        ("1", "Login, Registration & Roles (auth.py)",
         "Student self-registration; staff/admin accounts; PBKDF2-HMAC-SHA256 password hashing with "
         "per-user random salts; role-based access to student, staff and admin screens."),
        ("2", "Complaint Submission & Validation (complaints.py, student.py)",
         "Validated form: title, description, category (8 types), location, severity 1-5, impact 1-5, "
         "safety risk 0-5; optional anonymous reporting; unique date-based complaint IDs."),
        ("3", "Intelligent Priority Engine (priority_engine.py)",
         "Weighted score P = (Sx5)+(Ix4)+(Rx3)+age bonus; Low/Medium/High/Critical bands; emergency "
         "keyword detection and override; age-based score refresh for open complaints."),
        ("4", "Duplicate Detection & Issue Grouping (duplicate_detector.py)",
         "Rejects identical open complaints from the same student; Jaccard word-overlap similarity "
         "(>= 0.45) within the same category and location links related reports into issue groups; "
         "admin confirmation; preventive-maintenance suggestions for confirmed recurring groups."),
        ("5", "Department Routing & Staff Assignment (complaints.py, admin.py)",
         "Category-to-department routing table; administrator assigns staff (or overrides); "
         "assignment notifications to student and staff member."),
        ("6", "Status Timeline & Workflow (complaints.py)",
         "Pending -> Assigned -> In Progress -> Resolved -> Closed, with Reopened; every change "
         "stored with timestamp, actor and note in status_history."),
        ("7", "Deadlines, Overdue & Escalation (escalation.py)",
         "Configurable response targets (Critical immediate, High 1 day, Medium 3 days, Low 7 days); "
         "overdue flags; escalation alerts to administrators and the responsible department."),
        ("8", "Feedback & Reopening (complaints.py, ui_common.py)",
         "1-5 rating with comments after resolution; ratings of 2 or less automatically request an "
         "administrator review; students can request reopening of resolved complaints."),
        ("9", "In-App Notifications (notifications.py)",
         "Alerts for submission, assignment, status change, resolution, overdue escalation, grouping "
         "and low feedback; unread badge in the sidebar; mark-read support."),
        ("10", "Admin Dashboard & Analytics (admin.py, analytics.py)",
         "Dashboard cards (total, open, critical, overdue, average resolution time, satisfaction); "
         "critical queue and overdue escalations; filters and search; six matplotlib charts: "
         "category, top locations, weekly trend, status distribution, staff workload and resolution "
         "time by category."),
        ("11", "Reports & CSV Export (analytics.py)",
         "Dated complaints CSV export (anonymous identities masked) and a text summary report with "
         "status breakdown, category/location patterns, workload, recurring groups and maintenance "
         "suggestions, saved to reports/."),
    ],
    widths=[0.55, 2.1, 4.0],
)

# ======================================================== 4. ALGORITHM / DESIGN
doc.add_heading("4. Algorithm / Flowchart / Program Design", level=1)
para("The application is event-driven (Tkinter) with three role-based journeys sharing one complaint "
     "store. SQLite is the single source of truth; CSV is used only for exports. The core algorithms "
     "are given below as pseudocode, followed by the flowchart and module architecture.")

doc.add_heading("Algorithm / Pseudocode", level=2)
para("A. Complaint submission", bold=True, space_after=2)
code_block([
    "START",
    "1. Read logged-in student ID; display complaint form.",
    "2. Read title, description, category, location, severity, impact, safety risk.",
    "3. IF any field invalid THEN show error, re-prompt; nothing saved.",
    "4. IF same student has an identical open complaint (normalised title)",
    "     THEN show duplicate warning with existing ID; STOP.",
    "5. emergency <- confirmed flag OR emergency keyword in text.",
    "6. score <- severity*5 + impact*4 + safety_risk*3 + age bonus.",
    "7. priority <- Critical if emergency else band(score).",
    "8. department <- routing[category]; due <- created + deadline[priority].",
    "9. Generate unique ID CC-YYYYMMDD-NNNN; INSERT complaint + history row.",
    "10. Find similar open reports; IF found THEN link issue group (Suggested).",
    "11. Notify administrators; IF emergency THEN notify department + show warning.",
    "12. Display ID, priority, score, department and response target.",
    "STOP",
])
para("B. Priority calculation", bold=True, space_after=2)
code_block([
    "age_bonus <- days_open // 3   (0 if resolved)",
    "P <- (S * 5) + (I * 4) + (R * 3) + age_bonus",
    "IF emergency THEN level <- Critical",
    "ELSE IF P >= 56 THEN Critical; ELSE IF P >= 41 THEN High;",
    "     ELSE IF P >= 21 THEN Medium; ELSE Low.",
])
para("C. Duplicate / similarity detection", bold=True, space_after=2)
code_block([
    "normalise: lowercase, remove punctuation, collapse spaces.",
    "tokens <- words minus stopwords (set).",
    "similarity(A, B) <- |tokens(A) INTERSECT tokens(B)| / |tokens(A) UNION tokens(B)|.",
    "Candidates <- open complaints with same category AND same normalised location.",
    "IF similarity >= 0.45 THEN flag possible duplicate;",
    "  join existing group or create Suggested group; admin confirms; never auto-delete.",
])
para("D. Overdue detection and escalation", bold=True, space_after=2)
code_block([
    "FOR each unresolved complaint:",
    "  refresh score (age bonus);",
    "  IF now > due_at AND not already flagged THEN",
    "     mark overdue; notify admins + department + assigned staff (escalation).",
    "  IF resolved THEN clear overdue flag.",
])
para("E. Analytics and report generation", bold=True, space_after=2)
code_block([
    "Load complaints; group by category, location, department, status, week.",
    "avg_resolution <- mean(resolved_at - created_at) over resolved complaints.",
    "satisfaction <- mean(feedback.rating); workload <- open cases per staff member.",
    "recurring <- issue groups with linked counts; preventive <- confirmed groups >= 3.",
    "Render matplotlib charts; export dated CSV and text summary to reports/.",
])

doc.add_heading("Flowchart / Design", level=2)
para("Figure 1 shows the submission and prioritisation flow, including validation, duplicate "
     "rejection, the emergency override and similarity grouping.")
picture("flowchart.png", width=6.2, caption="Figure 1: Complaint submission and intelligent prioritisation flowchart.", folder=DIAGRAMS)
doc.add_page_break()
para("Figure 2 shows the three-layer module architecture. The presentation layer (Tkinter views) "
     "calls the application-logic modules, which read and write the SQLite database; analytics "
     "produces charts and file exports.")
picture("architecture.png", width=6.5, caption="Figure 2: CampusCare 2.0 module architecture.", folder=DIAGRAMS)
para("Project structure:", bold=True, space_after=2)
code_block([
    "CampusCare/",
    "  main.py               # entry point, login shell, role-based navigation",
    "  database.py           # SQLite schema and connection",
    "  auth.py               # registration, login, PBKDF2 hashing, roles",
    "  complaints.py         # lifecycle: create, assign, status, feedback, reopen",
    "  priority_engine.py    # scoring, bands, emergency override, deadlines",
    "  duplicate_detector.py # normalisation, Jaccard similarity, issue groups",
    "  escalation.py         # overdue checks and escalation notifications",
    "  notifications.py      # in-app notification records",
    "  analytics.py          # metrics, matplotlib charts, CSV/text exports",
    "  student.py / staff.py / admin.py / ui_common.py   # Tkinter views",
    "  seed_demo.py          # synthetic demo dataset (8 weeks)",
    "  tests/test_campuscare.py   # 37 automated unit tests",
    "  data/campuscare.db    # SQLite database   reports/  # exports",
])

# ======================================================== 5. PYTHON CONCEPTS
doc.add_heading("5. Python Concepts Used", level=1)
table(
    ["Python Concept", "Where / How It Is Used"],
    [
        ("Variables and Data Types",
         "Integers for scores, ratings and counters; strings for IDs, titles and statuses; booleans "
         "for emergency/anonymous/overdue flags; datetime objects for timestamps, deadlines and "
         "resolution durations."),
        ("Conditional Statements",
         "Input validation rules; priority band mapping (if/elif chains); emergency keyword override; "
         "overdue comparisons; role checks for student/staff/admin access; feedback review threshold."),
        ("Loops",
         "For-loops over complaint records for dashboards, analytics buckets and exports; while-loops "
         "for ID generation; the Tkinter event loop drives the GUI; iteration over history and "
         "notification rows."),
        ("Lists / Tuples / Sets / Dictionaries",
         "Lists hold query results and chart data; dictionaries represent records (sqlite3.Row), "
         "routing rules, deadline targets and summary metrics; sets store word tokens for Jaccard "
         "similarity; tuples hold emergency keywords and fixed field lists."),
        ("Functions",
         "Around sixty functions across twelve modules: scoring, routing, grouping, escalation, "
         "notification, export and validation helpers; each GUI action maps to a small testable "
         "function."),
        ("File Handling",
         "CSV export and text summary reports written to reports/ with the csv module and open(); "
         "SQLite database file created and persisted via sqlite3; os.makedirs for data/reports "
         "folders; screenshot and diagram files written with Pillow/matplotlib."),
        ("Exception Handling",
         "Custom ValidationError, DuplicateError and AuthError raised by logic modules and caught "
         "in the GUI to show friendly messages; ValueError handling for numeric input; sqlite3 "
         "constraints protect ratings and roles."),
        ("Libraries Used",
         "tkinter (GUI), sqlite3 (database), csv, datetime, os, string, hashlib and secrets "
         "(password hashing), unittest (testing) - all standard library; matplotlib (charts) is the "
         "only third-party library; Pillow used by the screenshot capture script."),
        ("Classes and OOP (additional)",
         "Tkinter Frame/Toplevel subclasses for every view and dialog (StudentHome, StaffHome, "
         "AdminHome, ComplaintDetailDialog, FeedbackDialog, ScrollableFrame); custom exception "
         "classes; encapsulated database access."),
        ("Modules and Packages (additional)",
         "Twelve-module package with clear imports and separation of concerns; tests/ package run "
         "with unittest discovery; scripts for seeding, diagrams, screenshots and report building."),
    ],
    widths=[1.9, 4.75],
)

# ======================================================== 6. COMPUTATIONAL FEATURE
doc.add_heading("6. Computational Feature", level=1)
para("The main computational feature is rule-based ranking and scoring, combined with pattern "
     "identification (similarity grouping) and analysis/summarisation (campus analytics). All three "
     "are deterministic: the same inputs always produce the same outputs, which makes them "
     "transparent and testable.")
para("(a) Priority scoring and ranking. Each complaint receives a score:")
para("Priority Score P = (Severity x 5) + (Impact x 4) + (Safety Risk x 3) + Age Bonus",
     bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
table(
    ["Variable", "Meaning", "Allowed values"],
    [
        ("S", "Severity of the issue", "1 (minor) to 5 (severe)"),
        ("I", "Impact scale: people affected", "1 (one person) to 5 (campus-wide)"),
        ("R", "Safety risk", "0 (none) to 5 (extreme)"),
        ("A", "Age bonus: +1 per 3 days unresolved", "0 or more"),
    ],
    widths=[0.8, 3.3, 2.55],
)
para("Example: an electrical fault with S=5, I=5, R=5 open for 6 days gives "
     "P = 25 + 20 + 15 + 2 = 62 (Critical). Bands: 0-20 Low, 21-40 Medium, 41-55 High, 56+ Critical. "
     "A confirmed emergency or a keyword such as fire, gas leak, live wire or short circuit overrides "
     "the score to Critical and displays a safety notice directing the user to campus emergency "
     "services. Complaints are then sorted by band and score so administrators see the most urgent "
     "work first; the age bonus prevents old low-score complaints from staying hidden forever.")
para("(b) Pattern identification - duplicate and similarity detection. Text is normalised "
     "(lowercase, punctuation removed, whitespace collapsed) and tokenised into word sets with "
     "stopwords removed. Similarity uses the Jaccard index:")
para("similarity(A, B) = |tokens(A) ∩ tokens(B)| / |tokens(A) ∪ tokens(B)|",
     bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
para("Only open complaints with the same category and the same normalised location are compared, "
     "which avoids matching unrelated reports. A similarity of 0.45 or higher flags a possible "
     "duplicate and links the reports into an issue group (Suggested); an administrator confirms "
     "the group. Nothing is deleted automatically. In the demo dataset, seven Wi-Fi reports from "
     "different students in Hostel A form one confirmed group, and the system suggests a preventive "
     "inspection once a confirmed group reaches three reports. This turns isolated entries into a "
     "visible campus-wide pattern.")
para("(c) Analysis, summarisation and visualisation. The analytics module groups records by "
     "category, location, department, status and ISO week; computes average resolution time from "
     "created/resolved timestamps, mean satisfaction from feedback ratings, and open-case workload "
     "per staff member; and renders six matplotlib charts embedded in the Tkinter admin page. A "
     "dated text summary and a CSV export are generated for offline review. These computations help "
     "the college identify repeated problem locations, slow departments and trends over time.")

# ======================================================== 7. SCREENSHOTS
doc.add_heading("7. Important Outputs / Screenshots", level=1)
para("The screenshots below were captured from the running application (Tkinter GUI, SQLite "
     "database) using the automated capture script capture_screenshots.py. The demo dataset is "
     "synthetic, generated by seed_demo.py; the submission screenshot adds one live complaint to "
     "the 30 seeded records. Additional screenshots (login, my complaints, notifications, staff "
     "queue, feedback dialog) are in the screenshots/ folder.")

doc.add_heading("Screenshot 1 - Complaint submission and intelligent priority result", level=2)
picture("02_student_submit_form.png", width=5.5,
        caption="Student complaint form: validated fields, severity/impact/safety-risk scales, emergency and anonymous options.")
picture("03_student_submit_result.png", width=5.5,
        caption="Submission result: ID CC-20261123-0001, score 31 (Medium), routed to IT Support, response target set, "
                "and similar open reports linked to issue group IG-0001 (recurring Wi-Fi problem).")

doc.add_heading("Screenshot 2 - Admin dashboard and complaint workflow", level=2)
picture("08_admin_dashboard.png", width=5.5,
        caption="Admin dashboard: totals, open, critical, overdue, average resolution time and satisfaction cards; "
                "critical/emergency queue (sparking switchboard) and overdue escalations with department and staff.")
picture("09_admin_complaint_detail.png", width=5.2,
        caption="Complaint record: full fields, priority badge, overdue flag, staff assignment, status update with "
                "note, and the timestamped status timeline.")

doc.add_heading("Screenshot 3 - Campus analytics and recurring issue groups", level=2)
picture("11_admin_analytics.png", width=5.5,
        caption="Analytics page: complaints by category, top locations (Hostel A leads with 8 reports), weekly trend "
                "and status distribution; staff workload and resolution-time charts below the scroll.")
picture("10_admin_issue_groups.png", width=5.5,
        caption="Issue groups: IG-0001 (Confirmed, 7 linked Wi-Fi reports at Hostel A) and IG-0002 (Suggested, 3 "
                "cafeteria cleanliness reports); linked complaints and the preventive-maintenance suggestion.")

# ======================================================== 8. TESTING
doc.add_heading("8. Testing", level=1)
para("The project was tested with 37 automated unit tests (Python unittest, tests/test_campuscare.py) "
     "covering the priority engine, duplicate detection, validation, workflow, authentication, "
     "persistence and exports. Final run result: \"Ran 37 tests ... OK\" (all passed). The GUI flows "
     "were additionally verified manually and through the automated screenshot capture, which "
     "exercises login, submission, grouping, assignment, resolution, feedback, escalation and "
     "analytics end to end. All demo data is synthetic.")
table(
    ["Test", "Input", "Expected Output", "Actual Output", "Result"],
    [
        ("1 (normal)", "Valid complaint: S=3, I=4, R=0, Internet, Hostel A",
         "Saved with CC-YYYYMMDD-NNNN ID; score 31; Medium; IT Support; Pending; history entry; admin notified",
         "As expected (see Screenshot 1)", "Pass"),
        ("2 (normal)", "S=5, I=5, R=5, no age bonus",
         "Score 60; Critical", "Score 60; Critical", "Pass"),
        ("3 (boundary)", "Scores 20, 21, 40, 41, 55, 56",
         "Low, Medium, Medium, High, High, Critical", "All bands matched", "Pass"),
        ("4 (boundary)", "S=1, I=1, R=0, open 6 days",
         "Score 9 + age bonus 2 = 11", "Score 11", "Pass"),
        ("5 (special)", "Low score + 'live wire' keyword / emergency flag",
         "Critical override + emergency safety notice", "Critical + notice displayed", "Pass"),
        ("6 (invalid)", "Severity 9; empty title; category 'Swimming Pool'",
         "ValidationError; nothing saved; clear message", "Rejected with message; no record", "Pass"),
        ("7 (invalid)", "Wrong password; rating 7; rating 'abc'",
         "Login fails; feedback rejected", "Login None; ValidationError raised", "Pass"),
        ("8 (invalid/duplicate)", "Same student repeats same open title (different case/punctuation)",
         "DuplicateError with existing ID; not saved again", "Rejected; existing ID shown", "Pass"),
        ("9 (normal)", "Low-priority complaint open 10 days; then resolved",
         "Overdue flag + escalation to admin/department; resolved case never flagged",
         "Flagged and escalated; cleared on resolution", "Pass"),
        ("10 (normal)", "Feedback rating 2 after resolution; student reopen request",
         "Review request to admin; status Reopened; only owner may reopen",
         "As expected; other student blocked", "Pass"),
        ("11 (normal)", "Close and reopen database; CSV export; anonymous complaint",
         "Data persists; correct CSV headers/rows; student ID masked as Anonymous",
         "All verified by unit tests", "Pass"),
        ("12 (normal)", "Similar Wi-Fi reports from different students, same category+location",
         "Suggested issue group; confirmation; preventive suggestion at 3+ reports",
         "Group created/confirmed; suggestion generated", "Pass"),
    ],
    widths=[0.85, 1.75, 1.85, 1.55, 0.6],
)
para("Coverage includes normal cases (submission, scoring, workflow, exports), boundary cases "
     "(priority band edges 20/21/40/41/55/56, age bonus, deadline targets) and invalid inputs "
     "(out-of-range values, empty fields, wrong passwords, invalid ratings, duplicates).",
     italic=True, size=10)

# ======================================================== 9. CONTRIBUTIONS
doc.add_heading("9. Team Member Contributions", level=1)
table(
    ["Student Name", "Enrollment No.", "Contribution"],
    [
        ("Akanksha", "S26CSEU3579",
         "Authentication and registration, password hashing and role checks; input validation; "
         "student interface (submission form, my complaints, feedback); integration support."),
        ("Ronit", "S26CSEU3557",
         "Complaint submission workflow and categories; priority engine (weighted scoring, age "
         "bonus, bands) and emergency safety override."),
        ("Anay", "S26CSEU3582",
         "Staff and admin interfaces; department routing and staff assignment; status timeline; "
         "dashboard cards, critical queue and overdue views."),
        ("Prince", "S26CSEU3570",
         "Analytics module and matplotlib charts; summary reports and CSV export; project "
         "documentation, diagrams and presentation."),
        ("Nikunj", "S26CSEU3564",
         "Overdue detection and escalation; duplicate detection and issue grouping; SQLite database "
         "layer; automated test suite, demo seeder and final integration."),
    ],
    widths=[1.1, 1.2, 4.35],
)

# ======================================================== 10. CHALLENGES
doc.add_heading("10. Challenges Faced and Learning", level=1)
bullet("Keeping the GUI, database, status history and notifications consistent across three roles. "
       "Every action (assign, update, resolve, reopen, feedback) had to update several tables at "
       "once. Solution: a single SQLite source of truth and one logic function per action that "
       "writes the complaint change, the history row and the notifications together; 37 unit tests "
       "verify the combinations.", bold_prefix="Challenge 1: ")
bullet("Tuning similarity detection so unrelated reports are not grouped together. Early versions "
       "matched complaints from different buildings. Solution: compare only within the same "
       "category and normalised location, remove stopwords, use Jaccard overlap with a 0.45 "
       "threshold, and require administrator confirmation before a group is treated as a verified "
       "pattern. The seven-report Hostel A Wi-Fi cluster validated the approach.", bold_prefix="Challenge 2: ")
bullet("Embedding matplotlib charts in Tkinter and producing reliable screenshots. Solution: "
       "TkAgg backend with a scrollable canvas for the analytics page, and a PrintWindow-based "
       "capture script that renders the application window directly.", bold_prefix="Challenge 3: ")
para("What we learned: decomposing a real problem into modules; designing an SQLite schema with "
     "keys and constraints; secure password hashing (PBKDF2 + salts); rule-based scoring and set "
     "similarity; event-driven GUI programming; writing meaningful unit tests including boundary "
     "and invalid cases; and turning raw records into charts and reports that support decisions.")

# ======================================================== 11. CONCLUSION
doc.add_heading("11. Conclusion and Future Improvements", level=1)
para("CampusCare 2.0 successfully delivers a central, searchable record of campus complaints with "
     "validated submission, transparent intelligent prioritisation, emergency safety override, "
     "department routing, staff assignment, a complete status timeline, deadline monitoring with "
     "overdue escalation, duplicate rejection and similarity-based issue grouping, in-app "
     "notifications, post-resolution feedback with review and reopening, and campus-level analytics "
     "with charts and exports. Recurring problems (such as the Hostel A Wi-Fi cluster) are now "
     "visible as groups with preventive-maintenance suggestions instead of isolated entries. The "
     "project demonstrates the full range of course concepts: data types, control flow, data "
     "structures, functions, OOP, file and database handling, exception handling, testing and "
     "basic data analysis.")
para("Future improvements: (1) email/SMS notification delivery in addition to in-app alerts; "
     "(2) photo attachments for complaints and resolution proof; (3) a web or mobile interface so "
     "students can report from anywhere; (4) predictive trend analysis and preventive-maintenance "
     "scheduling once enough historical data accumulates; and (5) integration with official college "
     "service policies and single sign-on.")
para("Limitations: this is a college-level prototype with synthetic demo data and demonstration "
     "deadlines; it does not dispatch maintenance teams automatically, verify incident authenticity, "
     "or replace official emergency procedures. Similarity grouping suggests patterns for human "
     "review rather than making final decisions.", italic=True, size=10)

# ======================================================== 12. REFERENCES
doc.add_heading("12. References / Acknowledgements", level=1)
para("Resources consulted during development:")
numbered("Python 3 official documentation - https://docs.python.org/3/")
numbered("tkinter (Python interface to Tcl/Tk) - https://docs.python.org/3/library/tkinter.html")
numbered("sqlite3 (DB-API 2.0 interface for SQLite) - https://docs.python.org/3/library/sqlite3.html")
numbered("hashlib and secrets (secure hashing and randomness) - "
         "https://docs.python.org/3/library/hashlib.html and https://docs.python.org/3/library/secrets.html")
numbered("matplotlib (charts and plotting) - https://matplotlib.org/stable/")
numbered("csv, datetime and unittest module documentation - https://docs.python.org/3/library/")
numbered("Jaccard index (set similarity) - https://en.wikipedia.org/wiki/Jaccard_index")
numbered("AI coding assistant (OpenCode, Qwen4 Max model) - used for implementation support, test "
         "debugging, screenshot automation and report drafting. The team reviewed, ran and "
         "understands all submitted code and content.")
para("")
para("Declaration: We confirm that we understand the submitted project and have acknowledged the "
     "external resources used during development.", bold=True, size=10.5)

doc.save(OUT)
print("Report saved:", OUT)
