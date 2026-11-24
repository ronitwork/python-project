"""
CampusCare 2.0 - Campus-level analytics, charts and report exports.

Metrics: status totals, critical/overdue counts, average resolution time,
category/location patterns, staff workload, student satisfaction and weekly
trends. Charts are built with matplotlib; exports are written to reports/.
"""
import csv
import os
from datetime import timedelta

import matplotlib
matplotlib.use("Agg")  # safe default; the GUI switches to TkAgg when embedding
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

import duplicate_detector as dup
import priority_engine as pe
from priority_engine import now, parse_dt

EXPORT_FIELDS = [
    "complaint_id", "student_id", "anonymous", "title", "description", "category",
    "location", "severity", "impact", "safety_risk", "priority_score", "priority",
    "emergency", "department", "assigned_staff", "status", "created_at", "due_at",
    "resolved_at", "overdue",
]

CHART_COLORS = ["#1f6feb", "#2da44e", "#bf8700", "#cf222e", "#8250df", "#0e7490", "#d97706", "#64748b"]


def summary(conn):
    rows = conn.execute("SELECT * FROM complaints").fetchall()
    total = len(rows)
    by_status = {s: sum(1 for r in rows if r["status"] == s)
                 for s in ("Pending", "Assigned", "In Progress", "Resolved", "Reopened", "Closed")}
    critical = sum(1 for r in rows if r["priority"] == "Critical")
    overdue = sum(1 for r in rows if r["overdue"] and r["status"] not in ("Resolved", "Closed"))
    emergencies = sum(1 for r in rows if r["emergency"])

    durations = []
    for r in rows:
        if r["resolved_at"]:
            hours = (parse_dt(r["resolved_at"]) - parse_dt(r["created_at"])).total_seconds() / 3600
            durations.append(max(0.0, hours))
    avg_hours = sum(durations) / len(durations) if durations else 0.0

    fb = conn.execute("SELECT rating FROM feedback").fetchall()
    ratings = [r["rating"] for r in fb]
    satisfaction = sum(ratings) / len(ratings) if ratings else 0.0

    return {
        "total": total,
        "by_status": by_status,
        "open": sum(by_status[s] for s in ("Pending", "Assigned", "In Progress", "Reopened")),
        "critical": critical,
        "overdue": overdue,
        "emergencies": emergencies,
        "resolved_count": len(durations),
        "avg_resolution_hours": round(avg_hours, 1),
        "avg_resolution_days": round(avg_hours / 24, 1),
        "feedback_count": len(ratings),
        "satisfaction": round(satisfaction, 2),
    }


def by_category(conn):
    rows = conn.execute(
        "SELECT category, COUNT(*) AS c FROM complaints GROUP BY category ORDER BY c DESC"
    ).fetchall()
    return [(r["category"], r["c"]) for r in rows]


def by_location(conn, top=8):
    rows = conn.execute(
        "SELECT location, COUNT(*) AS c FROM complaints GROUP BY location ORDER BY c DESC LIMIT ?",
        (top,),
    ).fetchall()
    return [(r["location"], r["c"]) for r in rows]


def by_department(conn):
    rows = conn.execute(
        "SELECT department, COUNT(*) AS c FROM complaints GROUP BY department ORDER BY c DESC"
    ).fetchall()
    return [(r["department"], r["c"]) for r in rows]


def staff_workload(conn):
    rows = conn.execute(
        "SELECT assigned_staff, COUNT(*) AS c FROM complaints "
        "WHERE assigned_staff != '' AND status NOT IN ('Resolved', 'Closed') "
        "GROUP BY assigned_staff ORDER BY c DESC"
    ).fetchall()
    result = []
    for r in rows:
        user = conn.execute("SELECT name FROM users WHERE user_id = ?", (r["assigned_staff"],)).fetchone()
        name = user["name"] if user else r["assigned_staff"]
        result.append((f"{name} ({r['assigned_staff']})", r["c"]))
    return result


def weekly_trend(conn, weeks=8, current=None):
    """Complaint counts per ISO week for the last `weeks` weeks."""
    current = current or now()
    start = (current - timedelta(weeks=weeks - 1)).date()
    start -= timedelta(days=start.weekday())  # Monday of that week
    buckets = []
    for i in range(weeks):
        week_start = start + timedelta(weeks=i)
        buckets.append([week_start, 0])
    rows = conn.execute("SELECT created_at FROM complaints").fetchall()
    for r in rows:
        d = parse_dt(r["created_at"]).date()
        for bucket in buckets:
            week_start = bucket[0]
            if week_start <= d < week_start + timedelta(days=7):
                bucket[1] += 1
                break
    return [(b[0].strftime("%d %b"), b[1]) for b in buckets]


def avg_resolution_by_category(conn):
    rows = conn.execute(
        "SELECT category, created_at, resolved_at FROM complaints WHERE resolved_at != ''"
    ).fetchall()
    data = {}
    for r in rows:
        hours = (parse_dt(r["resolved_at"]) - parse_dt(r["created_at"])).total_seconds() / 3600
        data.setdefault(r["category"], []).append(max(0.0, hours))
    return [(cat, round(sum(v) / len(v) / 24, 1)) for cat, v in
            sorted(data.items(), key=lambda kv: sum(kv[1]) / len(kv[1]), reverse=True)]


def build_charts(conn, current=None):
    """Return a dict of matplotlib figures for the analytics page."""
    plt.rcParams.update({"font.size": 9, "axes.titlesize": 11, "figure.facecolor": "white"})
    figures = {}

    cats = by_category(conn)
    if cats:
        fig, ax = plt.subplots(figsize=(5.0, 2.9), dpi=100)
        labels, values = zip(*cats)
        bars = ax.bar(labels, values, color=CHART_COLORS[:len(labels)])
        ax.bar_label(bars, padding=2)
        ax.set_title("Complaints by Category")
        ax.set_ylabel("Reports")
        ax.tick_params(axis="x", rotation=30)
        for label in ax.get_xticklabels():
            label.set_ha("right")
        ax.spines[["top", "right"]].set_visible(False)
        fig.tight_layout()
        figures["category"] = fig

    locs = by_location(conn)
    if locs:
        fig, ax = plt.subplots(figsize=(5.0, 2.9), dpi=100)
        labels, values = zip(*locs)
        bars = ax.barh(list(labels)[::-1], list(values)[::-1], color="#1f6feb")
        ax.bar_label(bars, padding=2)
        ax.set_title("Top Locations by Report Count")
        ax.set_xlabel("Reports")
        ax.spines[["top", "right"]].set_visible(False)
        fig.tight_layout()
        figures["location"] = fig

    trend = weekly_trend(conn, current=current)
    fig, ax = plt.subplots(figsize=(5.0, 2.9), dpi=100)
    labels, values = zip(*trend)
    ax.plot(labels, values, marker="o", color="#2da44e", linewidth=2)
    ax.fill_between(range(len(labels)), values, alpha=0.12, color="#2da44e")
    ax.set_title("Weekly Complaint Trend (last 8 weeks)")
    ax.set_ylabel("Reports")
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=30, ha="right")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    figures["trend"] = fig

    s = summary(conn)
    status_items = [(k, v) for k, v in s["by_status"].items() if v > 0]
    if status_items:
        fig, ax = plt.subplots(figsize=(5.0, 2.9), dpi=100)
        labels, values = zip(*status_items)
        colors = {"Pending": "#bf8700", "Assigned": "#1f6feb", "In Progress": "#8250df",
                  "Resolved": "#2da44e", "Reopened": "#cf222e", "Closed": "#64748b"}
        ax.pie(values, labels=labels, autopct="%1.0f%%",
               colors=[colors.get(l, "#999") for l in labels],
               textprops={"fontsize": 8}, startangle=90)
        ax.set_title("Complaint Status Distribution")
        fig.tight_layout()
        figures["status"] = fig

    workload = staff_workload(conn)
    if workload:
        fig, ax = plt.subplots(figsize=(5.0, 2.9), dpi=100)
        labels, values = zip(*workload)
        bars = ax.barh(list(labels)[::-1], list(values)[::-1], color="#8250df")
        ax.bar_label(bars, padding=2)
        ax.set_title("Open Cases per Staff Member")
        ax.set_xlabel("Open complaints")
        ax.spines[["top", "right"]].set_visible(False)
        fig.tight_layout()
        figures["workload"] = fig

    res_cat = avg_resolution_by_category(conn)
    if res_cat:
        fig, ax = plt.subplots(figsize=(5.0, 2.9), dpi=100)
        labels, values = zip(*res_cat)
        bars = ax.bar(labels, values, color="#0e7490")
        ax.bar_label(bars, padding=2, fmt="%.1f")
        ax.set_title("Average Resolution Time by Category (days)")
        ax.set_ylabel("Days")
        ax.tick_params(axis="x", rotation=30)
        for label in ax.get_xticklabels():
            label.set_ha("right")
        ax.spines[["top", "right"]].set_visible(False)
        fig.tight_layout()
        figures["resolution"] = fig

    return figures


def export_csv(conn, folder, current=None):
    os.makedirs(folder, exist_ok=True)
    stamp = (current or now()).strftime("%Y%m%d_%H%M%S")
    path = os.path.join(folder, f"complaints_export_{stamp}.csv")
    rows = conn.execute("SELECT * FROM complaints ORDER BY created_at").fetchall()
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=EXPORT_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            record = dict(row)
            record["student_id"] = "Anonymous" if record["anonymous"] else record["student_id"]
            writer.writerow(record)
    return path


def export_summary_report(conn, folder, current=None):
    os.makedirs(folder, exist_ok=True)
    current = current or now()
    stamp = current.strftime("%Y%m%d_%H%M%S")
    path = os.path.join(folder, f"summary_report_{stamp}.txt")
    s = summary(conn)
    lines = [
        "CAMPUSCARE 2.0 - CAMPUS COMPLAINT SUMMARY REPORT",
        f"Generated: {pe.fmt(current)}",
        "=" * 64,
        "",
        f"Total complaints:        {s['total']}",
        f"Open complaints:         {s['open']}",
        f"Critical complaints:     {s['critical']}",
        f"Overdue complaints:      {s['overdue']}",
        f"Emergency reports:       {s['emergencies']}",
        f"Average resolution time: {s['avg_resolution_days']} days ({s['avg_resolution_hours']} hours)",
        f"Student satisfaction:    {s['satisfaction']}/5 from {s['feedback_count']} rating(s)",
        "",
        "STATUS BREAKDOWN",
    ]
    lines += [f"  {k:<12} {v}" for k, v in s["by_status"].items()]
    lines += ["", "COMPLAINTS BY CATEGORY"]
    lines += [f"  {cat:<14} {count}" for cat, count in by_category(conn)]
    lines += ["", "TOP LOCATIONS"]
    lines += [f"  {loc:<36} {count}" for loc, count in by_location(conn)]
    lines += ["", "STAFF WORKLOAD (OPEN CASES)"]
    workload = staff_workload(conn)
    lines += [f"  {name:<36} {count}" for name, count in workload] or ["  No open assigned cases."]
    lines += ["", "RECURRING ISSUE GROUPS"]
    groups = dup.group_details(conn)
    if groups:
        for g in groups:
            lines.append(
                f"  {g['group_id']} [{g['group_status']}] {g['summary']} - "
                f"{g['count']} linked report(s), {g['open_count']} open"
            )
    else:
        lines.append("  No issue groups recorded.")
    lines += ["", "PREVENTIVE MAINTENANCE SUGGESTIONS"]
    suggestions = dup.preventive_suggestions(conn)
    if suggestions:
        for g in suggestions:
            lines.append(
                f"  Inspect {g['location']} ({g['category']}): {g['count']} recurring reports "
                f"in group {g['group_id']} suggest a preventive inspection."
            )
    else:
        lines.append("  No confirmed recurring groups above the inspection threshold yet.")
    lines += ["", "Note: demonstration targets and sample data; not official college statistics."]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return path
