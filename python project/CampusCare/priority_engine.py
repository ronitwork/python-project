"""
CampusCare 2.0 - Intelligent priority engine.

Priority score:  P = (Severity x 5) + (Impact x 4) + (Safety risk x 3) + Age bonus
Age bonus: +1 for every 3 days a complaint stays unresolved.
Bands: 0-20 Low | 21-40 Medium | 41-55 High | 56+ Critical.
Emergency safety override: keyword-detected or confirmed emergencies are Critical
regardless of score.
"""
from datetime import datetime, timedelta

DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

CATEGORIES = [
    "Hostel", "Classroom", "Internet", "Electricity",
    "Cleanliness", "Transport", "Academic", "Other",
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

# Demonstration response targets (configurable to match college policy).
DEADLINE_DAYS = {
    "Critical": 0,   # immediate review
    "High": 1,
    "Medium": 3,
    "Low": 7,
}

EMERGENCY_KEYWORDS = (
    "fire", "smoke", "gas leak", "live wire", "exposed wire",
    "electrocution", "short circuit", "electric shock", "sparking",
)

EMERGENCY_NOTICE = (
    "EMERGENCY WARNING: This looks like a safety incident. Contact campus "
    "security / emergency services immediately. A CampusCare ticket is not a "
    "replacement for emergency help."
)


def now():
    return datetime.now()


def fmt(dt):
    return dt.strftime(DATE_FORMAT)


def parse_dt(value):
    return datetime.strptime(value, DATE_FORMAT)


def calculate_score(severity, impact, safety_risk, created_at, current=None, resolved=False):
    """Weighted score with an age bonus for unresolved complaints."""
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


def priority_rank(priority):
    return {"Low": 1, "Medium": 2, "High": 3, "Critical": 4}.get(priority, 0)


def calculate_due_date(created_at, priority):
    return created_at + timedelta(days=DEADLINE_DAYS[priority])


def route_department(category):
    return DEPARTMENT_ROUTING.get(category, "Administrator Review")


def is_emergency(title, description, explicit=False):
    text = " ".join((title + " " + description).lower().split())
    return bool(explicit) or any(keyword in text for keyword in EMERGENCY_KEYWORDS)


def refresh_score(conn, complaint_id, current=None):
    """Recalculate score/priority for one open complaint (age bonus grows over time)."""
    current = current or now()
    row = conn.execute(
        "SELECT * FROM complaints WHERE complaint_id = ?", (complaint_id,)
    ).fetchone()
    if row is None or row["status"] in ("Resolved", "Closed"):
        return None
    score = calculate_score(
        row["severity"], row["impact"], row["safety_risk"],
        parse_dt(row["created_at"]), current, resolved=False,
    )
    priority = priority_from_score(score, emergency=bool(row["emergency"]))
    conn.execute(
        "UPDATE complaints SET priority_score = ?, priority = ? WHERE complaint_id = ?",
        (score, priority, complaint_id),
    )
    conn.commit()
    return score, priority
