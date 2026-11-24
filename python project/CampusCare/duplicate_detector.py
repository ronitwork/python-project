"""
CampusCare 2.0 - Duplicate detection and campus-wide issue grouping.

Layer 1: exact duplicate - same student, same normalised title, still open.
Layer 2: similarity - same category + location and Jaccard word overlap above
a threshold. Similar reports are linked into an issue group (Suggested) that an
administrator confirms. Nothing is ever discarded automatically.
"""
import string

from priority_engine import fmt, now

SIMILARITY_THRESHOLD = 0.45
PREVENTIVE_MIN_REPORTS = 3

STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "in", "on", "at", "of",
    "and", "or", "to", "for", "it", "this", "that", "my", "our", "very",
    "not", "no", "has", "have", "had", "be", "been", "with", "from", "by",
}

_PUNCT_TABLE = str.maketrans("", "", string.punctuation)


def normalize(text):
    """Lowercase, remove punctuation, collapse whitespace."""
    return " ".join(text.lower().translate(_PUNCT_TABLE).split())


def tokenize(text):
    return {w for w in normalize(text).split() if w and w not in STOPWORDS}


def jaccard(set_a, set_b):
    if not set_a and not set_b:
        return 0.0
    union = set_a | set_b
    if not union:
        return 0.0
    return len(set_a & set_b) / len(union)


def similarity(text_a, text_b):
    return jaccard(tokenize(text_a), tokenize(text_b))


def find_exact_duplicate(conn, student_id, title):
    """Same student + same normalised title + not Resolved/Closed."""
    target = normalize(title)
    rows = conn.execute(
        "SELECT * FROM complaints WHERE student_id = ? AND status NOT IN ('Resolved', 'Closed')",
        (student_id,),
    ).fetchall()
    for row in rows:
        if normalize(row["title"]) == target:
            return row
    return None


def find_similar(conn, category, location, title, description,
                 exclude_id=None, threshold=SIMILARITY_THRESHOLD):
    """Open complaints in the same category + location with similar text."""
    loc = normalize(location)
    text = title + " " + description
    rows = conn.execute(
        "SELECT * FROM complaints WHERE category = ? AND status NOT IN ('Resolved', 'Closed')",
        (category,),
    ).fetchall()
    matches = []
    for row in rows:
        if exclude_id and row["complaint_id"] == exclude_id:
            continue
        if normalize(row["location"]) != loc:
            continue
        score = similarity(text, row["title"] + " " + row["description"])
        if score >= threshold:
            matches.append((row, round(score, 3)))
    matches.sort(key=lambda pair: pair[1], reverse=True)
    return matches


def _next_group_id(conn):
    count = conn.execute("SELECT COUNT(*) AS c FROM issue_groups").fetchone()["c"]
    while True:
        count += 1
        gid = f"IG-{count:04d}"
        if not conn.execute("SELECT 1 FROM issue_groups WHERE group_id = ?", (gid,)).fetchone():
            return gid


def group_of(conn, complaint_id):
    row = conn.execute(
        "SELECT group_id FROM group_links WHERE complaint_id = ?", (complaint_id,)
    ).fetchone()
    return row["group_id"] if row else None


def suggest_grouping(conn, complaint_row, current=None):
    """Link a new complaint to similar open reports. Returns group_id or None."""
    current = current or now()
    matches = find_similar(
        conn, complaint_row["category"], complaint_row["location"],
        complaint_row["title"], complaint_row["description"],
        exclude_id=complaint_row["complaint_id"],
    )
    if not matches:
        return None

    # Join an existing group if any similar report already belongs to one.
    for row, _score in matches:
        gid = group_of(conn, row["complaint_id"])
        if gid:
            conn.execute(
                "INSERT OR IGNORE INTO group_links (group_id, complaint_id) VALUES (?, ?)",
                (gid, complaint_row["complaint_id"]),
            )
            conn.commit()
            return gid

    # Otherwise create a new suggested group holding all related reports.
    gid = _next_group_id(conn)
    summary = f"Recurring {complaint_row['category']} issue at {complaint_row['location']}"
    conn.execute(
        "INSERT INTO issue_groups (group_id, category, location, summary, created_at, group_status) "
        "VALUES (?, ?, ?, ?, ?, 'Suggested')",
        (gid, complaint_row["category"], complaint_row["location"], summary, fmt(current)),
    )
    conn.execute(
        "INSERT OR IGNORE INTO group_links (group_id, complaint_id) VALUES (?, ?)",
        (gid, complaint_row["complaint_id"]),
    )
    for row, _score in matches:
        conn.execute(
            "INSERT OR IGNORE INTO group_links (group_id, complaint_id) VALUES (?, ?)",
            (gid, row["complaint_id"]),
        )
    conn.commit()
    return gid


def confirm_group(conn, group_id):
    conn.execute(
        "UPDATE issue_groups SET group_status = 'Confirmed' WHERE group_id = ?", (group_id,)
    )
    conn.commit()


def group_details(conn):
    """All groups with their linked complaint counts and ids."""
    groups = conn.execute(
        "SELECT * FROM issue_groups ORDER BY created_at DESC"
    ).fetchall()
    result = []
    for g in groups:
        links = conn.execute(
            "SELECT complaint_id FROM group_links WHERE group_id = ?", (g["group_id"],)
        ).fetchall()
        ids = [r["complaint_id"] for r in links]
        open_count = 0
        if ids:
            placeholders = ",".join("?" for _ in ids)
            open_count = conn.execute(
                f"SELECT COUNT(*) AS c FROM complaints WHERE complaint_id IN ({placeholders}) "
                "AND status NOT IN ('Resolved', 'Closed')",
                ids,
            ).fetchone()["c"]
        result.append({
            "group_id": g["group_id"],
            "category": g["category"],
            "location": g["location"],
            "summary": g["summary"],
            "group_status": g["group_status"],
            "created_at": g["created_at"],
            "complaint_ids": ids,
            "count": len(ids),
            "open_count": open_count,
        })
    result.sort(key=lambda g: g["count"], reverse=True)
    return result


def preventive_suggestions(conn, min_reports=PREVENTIVE_MIN_REPORTS):
    """Confirmed recurring groups that warrant a preventive inspection."""
    return [
        g for g in group_details(conn)
        if g["group_status"] == "Confirmed" and g["count"] >= min_reports
    ]
