"""
CampusCare 2.0 - Complaint lifecycle: submission, validation, assignment,
status updates, feedback and reopening. Every change is written to SQLite and
recorded in the timestamped status history.
"""
import auth
import duplicate_detector as dup
import notifications
import priority_engine as pe
from priority_engine import fmt, now, parse_dt

STATUSES = ["Pending", "Assigned", "In Progress", "Resolved", "Reopened", "Closed"]
OPEN_STATUSES = ("Pending", "Assigned", "In Progress", "Reopened")
LOW_RATING_THRESHOLD = 2


class ValidationError(Exception):
    """Raised when complaint input fails validation."""


class DuplicateError(Exception):
    """Raised when the same student repeats an identical open complaint."""


def next_complaint_id(conn, current=None):
    today = (current or now()).strftime("%Y%m%d")
    prefix = f"CC-{today}-"
    count = conn.execute(
        "SELECT COUNT(*) AS c FROM complaints WHERE complaint_id LIKE ?", (prefix + "%",)
    ).fetchone()["c"]
    while True:
        count += 1
        cid = f"{prefix}{count:04d}"
        if not conn.execute("SELECT 1 FROM complaints WHERE complaint_id = ?", (cid,)).fetchone():
            return cid


def validate_fields(title, description, category, location, severity, impact, safety_risk):
    if not (5 <= len(title.strip()) <= 100):
        raise ValidationError("Title must be 5-100 characters.")
    if not (10 <= len(description.strip()) <= 1000):
        raise ValidationError("Description must be 10-1000 characters.")
    if category not in pe.CATEGORIES:
        raise ValidationError("Please choose a valid category.")
    if not (2 <= len(location.strip()) <= 100):
        raise ValidationError("Location must be 2-100 characters.")
    if not (1 <= int(severity) <= 5):
        raise ValidationError("Severity must be 1-5.")
    if not (1 <= int(impact) <= 5):
        raise ValidationError("Impact must be 1-5.")
    if not (0 <= int(safety_risk) <= 5):
        raise ValidationError("Safety risk must be 0-5.")


def create_complaint(conn, student_id, title, description, category, location,
                     severity, impact, safety_risk, emergency_confirmed=False,
                     anonymous=False, current=None):
    """Validate, score, route, store and notify. Returns a result dict."""
    current = current or now()
    title, description, location = title.strip(), description.strip(), location.strip()
    validate_fields(title, description, category, location, severity, impact, safety_risk)
    severity, impact, safety_risk = int(severity), int(impact), int(safety_risk)

    exact = dup.find_exact_duplicate(conn, student_id, title)
    if exact:
        raise DuplicateError(
            f"You already have an open complaint with this title: {exact['complaint_id']}. "
            "It was not saved again."
        )

    emergency = pe.is_emergency(title, description, emergency_confirmed)
    score = pe.calculate_score(severity, impact, safety_risk, current, current)
    priority = pe.priority_from_score(score, emergency)
    due = pe.calculate_due_date(current, priority)
    department = pe.route_department(category)
    cid = next_complaint_id(conn, current)

    conn.execute(
        "INSERT INTO complaints (complaint_id, student_id, title, description, category, location, "
        "severity, impact, safety_risk, priority_score, priority, emergency, department, "
        "assigned_staff, status, created_at, due_at, resolved_at, overdue, anonymous) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '', 'Pending', ?, ?, '', 0, ?)",
        (cid, student_id, title, description, category, location, severity, impact,
         safety_risk, score, priority, int(emergency), department, fmt(current), fmt(due),
         int(anonymous)),
    )
    conn.execute(
        "INSERT INTO status_history (complaint_id, old_status, new_status, changed_by, note, changed_at) "
        "VALUES (?, '', 'Pending', ?, 'Complaint submitted', ?)",
        (cid, student_id, fmt(current)),
    )
    conn.commit()

    row = get_complaint(conn, cid)
    similar = dup.find_similar(conn, category, location, title, description, exclude_id=cid)
    group_id = dup.suggest_grouping(conn, row, current)

    label = "Anonymous student" if anonymous else student_id
    notifications.notify_admins(
        conn, cid,
        f"New {priority} complaint {cid} ({category}, {location}) from {label}.",
        current,
    )
    if emergency:
        notifications.notify_department(
            conn, department, cid,
            f"EMERGENCY: {cid} at {location} needs immediate review.", current,
        )
    return {
        "complaint": row,
        "similar": similar,
        "group_id": group_id,
        "emergency": emergency,
    }


def get_complaint(conn, complaint_id):
    return conn.execute(
        "SELECT * FROM complaints WHERE complaint_id = ?", (complaint_id.strip(),)
    ).fetchone()


def list_complaints(conn, student_id=None, department=None, status=None,
                    priority=None, category=None, search=None, open_only=False):
    query = "SELECT * FROM complaints WHERE 1=1"
    params = []
    if student_id:
        query += " AND student_id = ?"
        params.append(student_id)
    if department:
        query += " AND department = ?"
        params.append(department)
    if status:
        query += " AND status = ?"
        params.append(status)
    if priority:
        query += " AND priority = ?"
        params.append(priority)
    if category:
        query += " AND category = ?"
        params.append(category)
    if open_only:
        query += " AND status IN ('Pending', 'Assigned', 'In Progress', 'Reopened')"
    if search:
        query += " AND (title LIKE ? OR location LIKE ? OR complaint_id LIKE ?)"
        like = f"%{search}%"
        params.extend([like, like, like])
    rows = conn.execute(query, params).fetchall()
    rows = sorted(
        rows,
        key=lambda r: (pe.priority_rank(r["priority"]), r["priority_score"], r["created_at"]),
        reverse=True,
    )
    return rows


def student_label(row, viewer_id):
    """Anonymous reports hide the student's identity from other viewers."""
    if row["anonymous"] and row["student_id"] != viewer_id:
        return "Anonymous"
    return row["student_id"]


def assign(conn, complaint_id, staff_id, changed_by, current=None):
    current = current or now()
    row = get_complaint(conn, complaint_id)
    if row is None:
        raise ValidationError("Complaint ID not found.")
    staff = auth.get_user(conn, staff_id)
    if staff is None or staff["role"] not in ("staff", "admin"):
        raise ValidationError("Assigned user must be a staff member or admin.")
    old = row["status"]
    new = "Assigned" if old == "Pending" else old
    conn.execute(
        "UPDATE complaints SET assigned_staff = ?, status = ? WHERE complaint_id = ?",
        (staff_id, new, complaint_id),
    )
    conn.execute(
        "INSERT INTO status_history (complaint_id, old_status, new_status, changed_by, note, changed_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (complaint_id, old, new, changed_by,
         f"Assigned to {staff['name']} ({staff_id}); department: {row['department']}", fmt(current)),
    )
    conn.commit()
    notifications.notify(
        conn, row["student_id"], complaint_id,
        f"Your complaint {complaint_id} was assigned to {staff['name']} ({row['department']}).",
        current,
    )
    notifications.notify(
        conn, staff_id, complaint_id,
        f"Complaint {complaint_id} ({row['priority']}) assigned to you: {row['title']}",
        current,
    )
    return get_complaint(conn, complaint_id)


def update_status(conn, complaint_id, new_status, changed_by, note="", current=None):
    current = current or now()
    row = get_complaint(conn, complaint_id)
    if row is None:
        raise ValidationError("Complaint ID not found.")
    if new_status not in STATUSES:
        raise ValidationError("Invalid status.")
    old = row["status"]
    resolved_at = row["resolved_at"]
    overdue = row["overdue"]
    if new_status == "Resolved":
        resolved_at = fmt(current)
        overdue = 0
    elif new_status == "Reopened":
        resolved_at = ""
    conn.execute(
        "UPDATE complaints SET status = ?, resolved_at = ?, overdue = ? WHERE complaint_id = ?",
        (new_status, resolved_at, overdue, complaint_id),
    )
    conn.execute(
        "INSERT INTO status_history (complaint_id, old_status, new_status, changed_by, note, changed_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (complaint_id, old, new_status, changed_by, note or "Status updated", fmt(current)),
    )
    conn.commit()
    message = f"Complaint {complaint_id} status: {old} -> {new_status}."
    if new_status == "Resolved":
        message += " Please rate the resolution in My Complaints."
    notifications.notify(conn, row["student_id"], complaint_id, message, current)
    if new_status in ("Resolved", "Reopened"):
        notifications.notify_admins(conn, complaint_id, message, current)
    return get_complaint(conn, complaint_id)


def request_reopen(conn, complaint_id, student_id, reason="", current=None):
    current = current or now()
    row = get_complaint(conn, complaint_id)
    if row is None:
        raise ValidationError("Complaint ID not found.")
    if row["student_id"] != student_id:
        raise ValidationError("Only the reporting student can request a reopen.")
    if row["status"] not in ("Resolved", "Closed"):
        raise ValidationError("Only resolved or closed complaints can be reopened.")
    update_status(conn, complaint_id, "Reopened", student_id,
                  f"Reopen requested by student. {reason}".strip(), current)
    notifications.notify_admins(
        conn, complaint_id,
        f"Student requested reopening of {complaint_id}. Reason: {reason or 'not given'}",
        current,
    )
    if row["assigned_staff"]:
        notifications.notify(
            conn, row["assigned_staff"], complaint_id,
            f"Complaint {complaint_id} was reopened by the student.", current,
        )
    return get_complaint(conn, complaint_id)


def add_feedback(conn, complaint_id, rating, comments="", current=None):
    current = current or now()
    row = get_complaint(conn, complaint_id)
    if row is None:
        raise ValidationError("Complaint ID not found.")
    try:
        rating = int(rating)
    except (TypeError, ValueError):
        raise ValidationError("Rating must be a whole number from 1 to 5.")
    if not (1 <= rating <= 5):
        raise ValidationError("Rating must be 1-5.")
    if row["status"] not in ("Resolved", "Closed"):
        raise ValidationError("Feedback can only be given after resolution.")
    if get_feedback(conn, complaint_id):
        raise ValidationError("Feedback was already submitted for this complaint.")
    conn.execute(
        "INSERT INTO feedback (complaint_id, rating, comments, submitted_at) VALUES (?, ?, ?, ?)",
        (complaint_id, rating, comments.strip(), fmt(current)),
    )
    conn.commit()
    review_requested = rating <= LOW_RATING_THRESHOLD
    if review_requested:
        notifications.notify_admins(
            conn, complaint_id,
            f"Low feedback ({rating}/5) on {complaint_id}: review requested. "
            f"Comments: {comments.strip() or 'none'}",
            current,
        )
    return {"rating": rating, "review_requested": review_requested}


def get_feedback(conn, complaint_id):
    return conn.execute(
        "SELECT * FROM feedback WHERE complaint_id = ?", (complaint_id,)
    ).fetchone()


def timeline(conn, complaint_id):
    return conn.execute(
        "SELECT * FROM status_history WHERE complaint_id = ? ORDER BY history_id",
        (complaint_id,),
    ).fetchall()
