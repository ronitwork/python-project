"""
CampusCare 2.0 - Milestone 2: Intelligent Workflow
Course: Computational Thinking and Programming (2026CSAE100)

Features:
- Complaint creation and validation
- Weighted priority scoring: (severity*5) + (impact*4) + (safety_risk*3) + age_bonus
- Emergency safety override
- Department routing by category
- Status timeline stored in CSV
- Configurable response deadlines
- Overdue detection and escalation
- CSV persistence (no external libraries required)

Run: python campuscare_m2.py
"""
import csv
import os
from datetime import datetime, timedelta

COMPLAINTS_FILE = "complaints.csv"
HISTORY_FILE = "status_history.csv"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

CATEGORIES = [
    "Hostel", "Classroom", "Internet", "Electricity",
    "Cleanliness", "Transport", "Academic", "Other"
]

DEPARTMENT_ROUTING = {
    "Hostel": "Hostel Administration / Housekeeping",
    "Classroom": "Facilities / Maintenance",
    "Internet": "IT Support",
    "Electricity": "Electrical Maintenance",
    "Cleanliness": "Housekeeping",
    "Transport": "Transport Office",
    "Academic": "Academic Office / Faculty Coordinator",
    "Other": "Administrator Review",
}

# Demonstration targets. Change these to match college policy.
DEADLINE_DAYS = {
    "Critical": 0,   # immediate review
    "High": 1,
    "Medium": 3,
    "Low": 7,
}

EMERGENCY_KEYWORDS = (
    "fire", "smoke", "gas leak", "live wire", "exposed wire",
    "electrocution", "short circuit", "electric shock"
)

FIELDS = [
    "complaint_id", "student_id", "title", "description", "category", "location",
    "severity", "impact", "safety_risk", "priority_score", "priority",
    "emergency", "department", "assigned_staff", "status", "created_at",
    "due_at", "resolved_at", "overdue", "issue_group"
]
HISTORY_FIELDS = [
    "history_id", "complaint_id", "old_status", "new_status",
    "changed_by", "note", "changed_at"
]


def now():
    return datetime.now()


def fmt(dt):
    return dt.strftime(DATE_FORMAT)


def parse_dt(value):
    return datetime.strptime(value, DATE_FORMAT)


def read_csv(path, fields):
    if not os.path.exists(path):
        return []
    with open(path, "r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path, fields, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def save_complaints(rows):
    write_csv(COMPLAINTS_FILE, FIELDS, rows)


def save_history(rows):
    write_csv(HISTORY_FILE, HISTORY_FIELDS, rows)


def valid_text(prompt, min_len=1, max_len=200):
    while True:
        value = input(prompt).strip()
        if min_len <= len(value) <= max_len:
            return value
        print(f"Please enter {min_len}-{max_len} characters.")


def valid_number(prompt, low, high):
    while True:
        try:
            value = int(input(prompt).strip())
            if low <= value <= high:
                return value
        except ValueError:
            pass
        print(f"Enter a whole number from {low} to {high}.")


def yes_no(prompt):
    while True:
        answer = input(prompt + " (y/n): ").strip().lower()
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no"):
            return False
        print("Please enter y or n.")


def normalize(text):
    return " ".join(text.lower().strip().split())


def is_emergency(title, description, explicit):
    text = normalize(title + " " + description)
    return explicit or any(keyword in text for keyword in EMERGENCY_KEYWORDS)


def calculate_score(severity, impact, safety_risk, created_at, current=None, resolved=False):
    """Score = severity*5 + impact*4 + safety_risk*3 + age bonus."""
    current = current or now()
    age_bonus = 0
    if not resolved:
        days_open = max(0, (current - created_at).days)
        age_bonus = days_open // 3
    return severity * 5 + impact * 4 + safety_risk * 3 + age_bonus


def priority_from_score(score, emergency=False):
    if emergency:
        return "Critical"
    if score >= 56:
        return "Critical"
    if score >= 41:
        return "High"
    if score >= 21:
        return "Medium"
    return "Low"


def calculate_due_date(created_at, priority):
    days = DEADLINE_DAYS[priority]
    # Critical is due immediately; other targets are calendar-day demo targets.
    return created_at + timedelta(days=days)


def route_department(category):
    return DEPARTMENT_ROUTING.get(category, "Administrator Review")


def next_complaint_id(rows):
    today = now().strftime("%Y%m%d")
    existing = [r["complaint_id"] for r in rows if r.get("complaint_id", "").startswith("CC-" + today)]
    sequence = len(existing) + 1
    return f"CC-{today}-{sequence:04d}"


def add_history(complaint_id, old_status, new_status, changed_by, note):
    history = read_csv(HISTORY_FILE, HISTORY_FIELDS)
    history.append({
        "history_id": f"H-{len(history)+1:05d}",
        "complaint_id": complaint_id,
        "old_status": old_status,
        "new_status": new_status,
        "changed_by": changed_by,
        "note": note,
        "changed_at": fmt(now()),
    })
    save_history(history)


def create_complaint():
    rows = read_csv(COMPLAINTS_FILE, FIELDS)
    student_id = valid_text("Student ID: ", 3, 15)
    title = valid_text("Complaint title: ", 5, 100)
    description = valid_text("Description: ", 10, 1000)
    print("\nCategories:")
    for i, category in enumerate(CATEGORIES, 1):
        print(f"{i}. {category}")
    category = CATEGORIES[valid_number("Select category: ", 1, len(CATEGORIES)) - 1]
    location = valid_text("Location (building/room/hostel): ", 2, 100)
    severity = valid_number("Severity (1=minor, 5=severe): ", 1, 5)
    impact = valid_number("Impact (1=one person, 5=campus-wide): ", 1, 5)
    safety_risk = valid_number("Safety risk (0=none, 5=extreme): ", 0, 5)
    emergency_confirmed = yes_no("Is this an emergency safety incident?")
    emergency = is_emergency(title, description, emergency_confirmed)

    # Prevent an identical open complaint from the same student.
    for row in rows:
        if (row["student_id"] == student_id
                and normalize(row["title"]) == normalize(title)
                and row["status"] not in ("Resolved", "Closed")):
            print(f"Duplicate open complaint found: {row['complaint_id']}. Not saved.")
            return

    created = now()
    score = calculate_score(severity, impact, safety_risk, created)
    priority = priority_from_score(score, emergency)
    due = calculate_due_date(created, priority)
    complaint_id = next_complaint_id(rows)

    complaint = {
        "complaint_id": complaint_id,
        "student_id": student_id,
        "title": title,
        "description": description,
        "category": category,
        "location": location,
        "severity": severity,
        "impact": impact,
        "safety_risk": safety_risk,
        "priority_score": score,
        "priority": priority,
        "emergency": "Yes" if emergency else "No",
        "department": route_department(category),
        "assigned_staff": "",
        "status": "Pending",
        "created_at": fmt(created),
        "due_at": fmt(due),
        "resolved_at": "",
        "overdue": "No",
        "issue_group": "",
    }
    rows.append(complaint)
    save_complaints(rows)
    add_history(complaint_id, "", "Pending", student_id, "Complaint submitted")
    print(f"\nComplaint submitted successfully. ID: {complaint_id}")
    print(f"Priority: {priority} (score {score}) | Department: {complaint['department']}")
    print(f"Response target: {fmt(due)}")
    if emergency:
        print("\n*** EMERGENCY WARNING ***")
        print("Contact campus security/emergency services immediately. This ticket is not a replacement for emergency help.")


def show_complaint(row):
    print("-" * 78)
    print(f"{row['complaint_id']} | {row['priority']} ({row['priority_score']}) | {row['status']}")
    print(f"Title: {row['title']} | Category: {row['category']} | Location: {row['location']}")
    print(f"Student: {row['student_id']} | Department: {row['department']} | Staff: {row['assigned_staff'] or 'Unassigned'}")
    print(f"Created: {row['created_at']} | Due: {row['due_at']} | Overdue: {row['overdue']}")
    print(f"Emergency: {row['emergency']}")
    print(f"Description: {row['description']}")


def view_complaints():
    rows = read_csv(COMPLAINTS_FILE, FIELDS)
    if not rows:
        print("No complaints recorded.")
        return
    rows.sort(key=lambda r: (priority_rank(r["priority"]), -int(r["priority_score"])), reverse=True)
    for row in rows:
        show_complaint(row)


def priority_rank(priority):
    return {"Low": 1, "Medium": 2, "High": 3, "Critical": 4}.get(priority, 0)


def view_student_complaints():
    student_id = valid_text("Student ID: ", 3, 15)
    rows = [r for r in read_csv(COMPLAINTS_FILE, FIELDS) if r["student_id"] == student_id]
    if not rows:
        print("No complaints found for this student.")
        return
    rows.sort(key=lambda r: priority_rank(r["priority"]), reverse=True)
    for row in rows:
        show_complaint(row)
        history = read_csv(HISTORY_FILE, HISTORY_FIELDS)
        events = [h for h in history if h["complaint_id"] == row["complaint_id"]]
        print("Timeline:")
        for event in events:
            print(f"  {event['changed_at']} | {event['old_status'] or 'New'} -> {event['new_status']} | {event['note']}")


def find_complaint(rows, complaint_id):
    return next((r for r in rows if r["complaint_id"].lower() == complaint_id.lower()), None)


def assign_complaint():
    rows = read_csv(COMPLAINTS_FILE, FIELDS)
    complaint_id = valid_text("Complaint ID: ", 5, 30)
    row = find_complaint(rows, complaint_id)
    if not row:
        print("Complaint ID not found.")
        return
    staff = valid_text("Assigned staff name/ID: ", 2, 80)
    old = row["status"]
    row["assigned_staff"] = staff
    if row["status"] == "Pending":
        row["status"] = "Assigned"
    save_complaints(rows)
    add_history(row["complaint_id"], old, row["status"], "Admin", f"Assigned to {staff}; department: {row['department']}")
    print(f"Assigned to {staff} in {row['department']}.")


def update_status():
    rows = read_csv(COMPLAINTS_FILE, FIELDS)
    complaint_id = valid_text("Complaint ID: ", 5, 30)
    row = find_complaint(rows, complaint_id)
    if not row:
        print("Complaint ID not found.")
        return
    statuses = ["Assigned", "In Progress", "Resolved", "Reopened", "Closed"]
    print("Status choices:")
    for i, status in enumerate(statuses, 1):
        print(f"{i}. {status}")
    new_status = statuses[valid_number("Choose status: ", 1, len(statuses)) - 1]
    note = input("Update/resolution note (optional): ").strip()
    old_status = row["status"]
    row["status"] = new_status
    if new_status == "Resolved":
        row["resolved_at"] = fmt(now())
        row["overdue"] = "No"
    elif new_status == "Reopened":
        row["resolved_at"] = ""
    save_complaints(rows)
    add_history(complaint_id, old_status, new_status, "Staff/Admin", note or "Status updated")
    print(f"Status changed: {old_status} -> {new_status}")


def check_overdue():
    rows = read_csv(COMPLAINTS_FILE, FIELDS)
    current = now()
    overdue_count = 0
    for row in rows:
        if row["status"] not in ("Resolved", "Closed"):
            due = parse_dt(row["due_at"])
            if current > due:
                row["overdue"] = "Yes"
                overdue_count += 1
            else:
                row["overdue"] = "No"
    save_complaints(rows)
    print(f"Overdue check complete. {overdue_count} complaint(s) overdue.")
    for row in rows:
        if row["overdue"] == "Yes":
            print(f"ESCALATION: {row['complaint_id']} | {row['priority']} | {row['department']} | assigned: {row['assigned_staff'] or 'Unassigned'}")
    return overdue_count


def show_timeline():
    complaint_id = valid_text("Complaint ID: ", 5, 30)
    history = read_csv(HISTORY_FILE, HISTORY_FIELDS)
    events = [h for h in history if h["complaint_id"].lower() == complaint_id.lower()]
    if not events:
        print("No timeline entries found.")
        return
    for event in events:
        print(f"{event['changed_at']} | {event['old_status'] or 'New'} -> {event['new_status']} | By: {event['changed_by']} | {event['note']}")


def dashboard():
    rows = read_csv(COMPLAINTS_FILE, FIELDS)
    total = len(rows)
    counts = {status: sum(1 for r in rows if r["status"] == status)
              for status in ("Pending", "Assigned", "In Progress", "Resolved", "Reopened", "Closed")}
    critical = sum(1 for r in rows if r["priority"] == "Critical")
    overdue = sum(1 for r in rows if r["overdue"] == "Yes")
    print("\n=== CAMPUSCARE WORKFLOW DASHBOARD ===")
    print(f"Total: {total} | Critical: {critical} | Overdue: {overdue}")
    for status, count in counts.items():
        print(f"{status}: {count}")


def menu():
    while True:
        print("\n=== CAMPUSCARE 2.0 | MILESTONE 2 ===")
        print("1. Submit complaint")
        print("2. View all complaints (admin)")
        print("3. View my complaints and timeline")
        print("4. Assign department staff")
        print("5. Update complaint status")
        print("6. Check overdue and escalation")
        print("7. View complaint timeline")
        print("8. Dashboard summary")
        print("9. Exit")
        choice = input("Choose: ").strip()
        if choice == "1":
            create_complaint()
        elif choice == "2":
            view_complaints()
        elif choice == "3":
            view_student_complaints()
        elif choice == "4":
            assign_complaint()
        elif choice == "5":
            update_status()
        elif choice == "6":
            check_overdue()
        elif choice == "7":
            show_timeline()
        elif choice == "8":
            dashboard()
        elif choice == "9":
            print("Goodbye.")
            break
        else:
            print("Invalid choice. Please choose 1-9.")


if __name__ == "__main__":
    menu()
