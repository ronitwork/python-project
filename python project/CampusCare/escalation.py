"""
CampusCare 2.0 - Deadlines, overdue detection and escalation.

Each complaint stores a due date derived from its priority. The check runs
when the admin dashboard loads and on demand. Newly overdue cases escalate to
the administrator and the assigned department/staff member.
"""
import notifications
import priority_engine as pe
from priority_engine import now, parse_dt

ESCALATION_TEXT = {
    "Critical": "IMMEDIATE ESCALATION: critical complaint missed its review target.",
    "High": "Escalation: high-priority complaint missed its 1-day target.",
    "Medium": "Overdue: medium-priority complaint missed its 3-day target.",
    "Low": "Overdue flag: low-priority complaint missed its 7-day target.",
}


def run_checks(conn, current=None):
    """Refresh age-based scores, then flag and escalate overdue complaints."""
    current = current or now()
    rows = conn.execute(
        "SELECT * FROM complaints WHERE status NOT IN ('Resolved', 'Closed')"
    ).fetchall()

    for row in rows:
        pe.refresh_score(conn, row["complaint_id"], current)

    newly_overdue = []
    total_overdue = 0
    for row in rows:
        due = parse_dt(row["due_at"])
        is_overdue = current > due
        if is_overdue:
            total_overdue += 1
        if is_overdue and not row["overdue"]:
            conn.execute(
                "UPDATE complaints SET overdue = 1 WHERE complaint_id = ?",
                (row["complaint_id"],),
            )
            message = (
                f"{ESCALATION_TEXT.get(row['priority'], 'Overdue complaint.')} "
                f"{row['complaint_id']} | {row['title']} | {row['location']} | "
                f"department: {row['department']} | due: {row['due_at']}"
            )
            notifications.notify_admins(conn, row["complaint_id"], message, current)
            notifications.notify_department(conn, row["department"], row["complaint_id"], message, current)
            if row["assigned_staff"]:
                notifications.notify(conn, row["assigned_staff"], row["complaint_id"], message, current)
            newly_overdue.append(row["complaint_id"])
        elif not is_overdue and row["overdue"]:
            conn.execute(
                "UPDATE complaints SET overdue = 0 WHERE complaint_id = ?",
                (row["complaint_id"],),
            )
    conn.commit()
    return {"newly_overdue": newly_overdue, "total_overdue": total_overdue}


def overdue_complaints(conn):
    return conn.execute(
        "SELECT * FROM complaints WHERE overdue = 1 AND status NOT IN ('Resolved', 'Closed') "
        "ORDER BY priority_score DESC"
    ).fetchall()
