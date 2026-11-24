"""
CampusCare 2.0 - Authentication and role management.

Passwords are stored as PBKDF2-HMAC-SHA256 hashes with a per-user random salt
(hashlib + secrets). Plain-text passwords are never stored.
Roles: student, staff, admin.
"""
import hashlib
import secrets

from priority_engine import fmt, now

PBKDF2_ITERATIONS = 120_000


class AuthError(Exception):
    """Raised for registration/login validation problems."""


def hash_password(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt), PBKDF2_ITERATIONS
    )
    return digest.hex(), salt


def verify_password(password, password_hash, salt):
    digest, _ = hash_password(password, salt)
    return secrets.compare_digest(digest, password_hash)


def register_user(conn, user_id, name, password, role="student", department="", current=None):
    user_id = user_id.strip()
    name = name.strip()
    if not (3 <= len(user_id) <= 20):
        raise AuthError("User ID must be 3-20 characters.")
    if not (2 <= len(name) <= 60):
        raise AuthError("Name must be 2-60 characters.")
    if len(password) < 6:
        raise AuthError("Password must be at least 6 characters.")
    if role not in ("student", "staff", "admin"):
        raise AuthError("Invalid role.")
    if conn.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,)).fetchone():
        raise AuthError(f"User ID '{user_id}' is already registered.")
    password_hash, salt = hash_password(password)
    conn.execute(
        "INSERT INTO users (user_id, name, role, department, password_hash, salt, active, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, 1, ?)",
        (user_id, name, role, department, password_hash, salt, fmt(current or now())),
    )
    conn.commit()
    return get_user(conn, user_id)


def login(conn, user_id, password):
    row = conn.execute(
        "SELECT * FROM users WHERE user_id = ? AND active = 1", (user_id.strip(),)
    ).fetchone()
    if row is None:
        return None
    if not verify_password(password, row["password_hash"], row["salt"]):
        return None
    return row


def get_user(conn, user_id):
    return conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()


def list_staff(conn, department=None):
    if department:
        return conn.execute(
            "SELECT * FROM users WHERE role = 'staff' AND department = ? AND active = 1 ORDER BY name",
            (department,),
        ).fetchall()
    return conn.execute(
        "SELECT * FROM users WHERE role = 'staff' AND active = 1 ORDER BY name"
    ).fetchall()


def ensure_admin(conn):
    """Create the default administrator on first run (demo credentials)."""
    if conn.execute("SELECT 1 FROM users WHERE role = 'admin'").fetchone():
        return None
    return register_user(
        conn, "admin", "Campus Administrator", "admin123",
        role="admin", department="Administration",
    )
