"""
CampusCare 2.0 - SQLite database layer.
Course: Computational Thinking and Programming (2026CSAE100)

SQLite is the single source of truth for users, complaints, status history,
issue groups, feedback and notifications. CSV is used only for exports.
"""
import os
import sqlite3

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
REPORTS_DIR = os.path.join(PROJECT_ROOT, "reports")
DEFAULT_DB_PATH = os.path.join(DATA_DIR, "campuscare.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id       TEXT PRIMARY KEY,
    name          TEXT NOT NULL,
    role          TEXT NOT NULL CHECK (role IN ('student', 'staff', 'admin')),
    department    TEXT NOT NULL DEFAULT '',
    password_hash TEXT NOT NULL,
    salt          TEXT NOT NULL,
    active        INTEGER NOT NULL DEFAULT 1,
    created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS complaints (
    complaint_id   TEXT PRIMARY KEY,
    student_id     TEXT NOT NULL,
    title          TEXT NOT NULL,
    description    TEXT NOT NULL,
    category       TEXT NOT NULL,
    location       TEXT NOT NULL,
    severity       INTEGER NOT NULL,
    impact         INTEGER NOT NULL,
    safety_risk    INTEGER NOT NULL,
    priority_score INTEGER NOT NULL,
    priority       TEXT NOT NULL,
    emergency      INTEGER NOT NULL DEFAULT 0,
    department     TEXT NOT NULL,
    assigned_staff TEXT NOT NULL DEFAULT '',
    status         TEXT NOT NULL DEFAULT 'Pending',
    created_at     TEXT NOT NULL,
    due_at         TEXT NOT NULL,
    resolved_at    TEXT NOT NULL DEFAULT '',
    overdue        INTEGER NOT NULL DEFAULT 0,
    anonymous      INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS status_history (
    history_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    complaint_id TEXT NOT NULL,
    old_status   TEXT NOT NULL DEFAULT '',
    new_status   TEXT NOT NULL,
    changed_by   TEXT NOT NULL,
    note         TEXT NOT NULL DEFAULT '',
    changed_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS issue_groups (
    group_id     TEXT PRIMARY KEY,
    category     TEXT NOT NULL,
    location     TEXT NOT NULL,
    summary      TEXT NOT NULL,
    created_at   TEXT NOT NULL,
    group_status TEXT NOT NULL DEFAULT 'Suggested'
);

CREATE TABLE IF NOT EXISTS group_links (
    group_id     TEXT NOT NULL,
    complaint_id TEXT NOT NULL,
    PRIMARY KEY (group_id, complaint_id)
);

CREATE TABLE IF NOT EXISTS feedback (
    feedback_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    complaint_id TEXT NOT NULL UNIQUE,
    rating       INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    comments     TEXT NOT NULL DEFAULT '',
    submitted_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS notifications (
    notification_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         TEXT NOT NULL,
    complaint_id    TEXT NOT NULL DEFAULT '',
    message         TEXT NOT NULL,
    created_at      TEXT NOT NULL,
    read            INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_complaints_student ON complaints (student_id);
CREATE INDEX IF NOT EXISTS idx_complaints_status  ON complaints (status);
CREATE INDEX IF NOT EXISTS idx_history_complaint  ON status_history (complaint_id);
CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications (user_id, read);
"""


def connect(path=None):
    """Open (and initialise) the database. Returns a connection with Row access."""
    path = path or DEFAULT_DB_PATH
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    init_db(conn)
    return conn


def init_db(conn):
    conn.executescript(SCHEMA)
    conn.commit()


def ensure_dirs():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(REPORTS_DIR, exist_ok=True)
