"""
CampusCare 2.0 - In-app notifications.

Alerts are created when a complaint is assigned, updated, resolved, escalated
as overdue, grouped, or when low feedback requests a review.
"""
from priority_engine import fmt, now


def notify(conn, user_id, complaint_id, message, current=None):
    if not user_id:
        return None
    cur = conn.execute(
        "INSERT INTO notifications (user_id, complaint_id, message, created_at, read) "
        "VALUES (?, ?, ?, ?, 0)",
        (user_id, complaint_id or "", message, fmt(current or now())),
    )
    conn.commit()
    return cur.lastrowid


def notify_admins(conn, complaint_id, message, current=None):
    admins = conn.execute("SELECT user_id FROM users WHERE role = 'admin' AND active = 1").fetchall()
    for admin in admins:
        notify(conn, admin["user_id"], complaint_id, message, current)


def notify_department(conn, department, complaint_id, message, current=None):
    staff = conn.execute(
        "SELECT user_id FROM users WHERE role = 'staff' AND department = ? AND active = 1",
        (department,),
    ).fetchall()
    for member in staff:
        notify(conn, member["user_id"], complaint_id, message, current)


def unread(conn, user_id):
    return conn.execute(
        "SELECT * FROM notifications WHERE user_id = ? AND read = 0 ORDER BY notification_id DESC",
        (user_id,),
    ).fetchall()


def all_for(conn, user_id, limit=100):
    return conn.execute(
        "SELECT * FROM notifications WHERE user_id = ? ORDER BY notification_id DESC LIMIT ?",
        (user_id, limit),
    ).fetchall()


def unread_count(conn, user_id):
    return conn.execute(
        "SELECT COUNT(*) AS c FROM notifications WHERE user_id = ? AND read = 0",
        (user_id,),
    ).fetchone()["c"]


def mark_read(conn, notification_id):
    conn.execute("UPDATE notifications SET read = 1 WHERE notification_id = ?", (notification_id,))
    conn.commit()


def mark_all_read(conn, user_id):
    conn.execute("UPDATE notifications SET read = 1 WHERE user_id = ?", (user_id,))
    conn.commit()
