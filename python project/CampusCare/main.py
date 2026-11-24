"""
CampusCare 2.0 - Smart Campus Complaint Management and Decision-Support System
Course: Computational Thinking and Programming (2026CSAE100)

Application entry point: login / registration, role-based navigation shell.
Run:  python main.py
Demo data (optional):  python seed_demo.py --reset
"""
import tkinter as tk
from tkinter import ttk

import auth
import database
import notifications
from student import StudentHome
from staff import StaffHome
from admin import AdminHome
from ui_common import (BG, CARD, NAVY, PRIMARY, MUTED, RED, BORDER,
                       apply_theme, card, error)

APP_TITLE = "CampusCare 2.0 - Smart Campus Complaint Management"

ROLE_VIEWS = {
    "student": ["Submit Complaint", "My Complaints", "Notifications"],
    "staff": ["My Queue", "Notifications"],
    "admin": ["Dashboard", "All Complaints", "Issue Groups", "Analytics", "Notifications"],
}


class LoginFrame(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, padding=20)
        self.app = app
        wrap = ttk.Frame(self)
        wrap.place(relx=0.5, rely=0.46, anchor="center")
        box = card(wrap, padding=30)
        box.pack()
        tk.Label(box, text="CampusCare 2.0", bg=CARD, fg=NAVY,
                 font=("Segoe UI Semibold", 24)).pack()
        tk.Label(box, text="Smart Campus Complaint Management & Decision-Support",
                 bg=CARD, fg=MUTED, font=("Segoe UI", 10)).pack(pady=(2, 18))
        tk.Label(box, text="User ID", bg=CARD, fg=NAVY, font=("Segoe UI Semibold", 10)).pack(anchor="w")
        self.user_var = tk.StringVar()
        user_entry = ttk.Entry(box, textvariable=self.user_var, width=36, font=("Segoe UI", 11))
        user_entry.pack(pady=(2, 10), ipady=3)
        tk.Label(box, text="Password", bg=CARD, fg=NAVY, font=("Segoe UI Semibold", 10)).pack(anchor="w")
        self.pass_var = tk.StringVar()
        pass_entry = ttk.Entry(box, textvariable=self.pass_var, width=36, show="*", font=("Segoe UI", 11))
        pass_entry.pack(pady=(2, 6), ipady=3)
        self.msg = tk.Label(box, text="", bg=CARD, fg=RED, font=("Segoe UI", 9))
        self.msg.pack(anchor="w")
        ttk.Button(box, text="Login", style="Primary.TButton", command=self.do_login).pack(fill="x", pady=(8, 4), ipady=4)
        ttk.Button(box, text="Register as student", command=self.do_register).pack(fill="x", pady=4)
        tk.Label(box, text="Demo logins:  admin / admin123   |   STF-IT / staff123\n"
                           "student: S26CSEU3579 / campus123  (see seed_demo.py)",
                 bg=CARD, fg=MUTED, font=("Segoe UI", 8), justify="center").pack(pady=(12, 0))
        user_entry.focus_set()
        self.bind_all("<Return>", lambda e: self.do_login())

    def do_login(self):
        user = auth.login(self.app.conn, self.user_var.get(), self.pass_var.get())
        if user is None:
            self.msg.config(text="Invalid user ID or password.")
            return
        self.app.on_login(user)

    def do_register(self):
        dialog = tk.Toplevel(self)
        dialog.title("Student registration")
        dialog.configure(bg=BG)
        dialog.geometry("430x360")
        dialog.transient(self)
        dialog.grab_set()
        body = ttk.Frame(dialog, padding=18)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text="Create a student account", style="Title.TLabel",
                  font=("Segoe UI Semibold", 13)).pack(anchor="w", pady=(0, 10))
        entries = {}
        for label, key in [("Enrollment / User ID", "user_id"), ("Full name", "name"),
                           ("Password (min 6 chars)", "password"), ("Confirm password", "confirm")]:
            ttk.Label(body, text=label + ":").pack(anchor="w", pady=(5, 0))
            var = tk.StringVar()
            entries[key] = var
            ttk.Entry(body, textvariable=var, width=42,
                      show="*" if "password" in key or key == "confirm" else "").pack(anchor="w")
        msg = ttk.Label(body, text="", foreground=RED)
        msg.pack(anchor="w", pady=4)

        def save():
            if entries["password"].get() != entries["confirm"].get():
                msg.config(text="Passwords do not match.")
                return
            try:
                auth.register_user(self.app.conn, entries["user_id"].get(),
                                   entries["name"].get(), entries["password"].get(), role="student")
            except auth.AuthError as exc:
                msg.config(text=str(exc))
                return
            dialog.destroy()
            self.user_var.set(entries["user_id"].get())
            self.msg.config(text="Registered. You can log in now.", fg="#2da44e")

        ttk.Button(body, text="Register", style="Primary.TButton", command=save).pack(anchor="e", pady=8)


class CampusCareApp(tk.Tk):
    def __init__(self, db_path=None):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1280x860+60+30")
        self.minsize(1120, 700)
        apply_theme(self)
        database.ensure_dirs()
        self.conn = database.connect(db_path)
        auth.ensure_admin(self.conn)
        self.user = None
        self.home = None
        self.sidebar_buttons = {}
        self.login_frame = LoginFrame(self, self)
        self.login_frame.pack(fill="both", expand=True)

    # ---- shell -------------------------------------------------------------
    def on_login(self, user):
        self.user = user
        self.login_frame.pack_forget()
        self.login_frame.destroy()
        self.unbind_all("<Return>")
        self.build_shell()

    def build_shell(self):
        self.header = tk.Frame(self, bg=NAVY, height=60)
        self.header.pack(fill="x")
        self.header.pack_propagate(False)
        tk.Label(self.header, text="  CampusCare 2.0", bg=NAVY, fg="white",
                 font=("Segoe UI Semibold", 14)).pack(side="left", padx=10)
        tk.Label(self.header, text=f"{self.user['name']}  |  {self.user['role'].upper()}"
                                  + (f"  |  {self.user['department']}" if self.user["department"] else ""),
                 bg=NAVY, fg="#c9d8ea", font=("Segoe UI", 10)).pack(side="right", padx=14)
        ttk.Button(self.header, text="Logout", command=self.logout).pack(side="right", pady=10)

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True)
        self.sidebar = tk.Frame(body, bg="#ffffff", width=210, highlightbackground=BORDER, highlightthickness=1)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)
        tk.Label(self.sidebar, text="NAVIGATION", bg="white", fg=MUTED,
                 font=("Segoe UI Semibold", 8)).pack(anchor="w", padx=16, pady=(16, 6))
        self.content = ttk.Frame(body)
        self.content.pack(side="left", fill="both", expand=True)

        role = self.user["role"]
        if role == "student":
            self.home = StudentHome(self.content, self.conn, self.user)
        elif role == "staff":
            self.home = StaffHome(self.content, self.conn, self.user)
        else:
            self.home = AdminHome(self.content, self.conn, self.user)
            self.home.on_badge_change = self.update_badges
        self.home.pack(fill="both", expand=True)

        for name in ROLE_VIEWS[role]:
            btn = tk.Button(self.sidebar, text=name, anchor="w", bd=0, bg="white", fg=NAVY,
                            activebackground="#eaf2ff", activeforeground=PRIMARY,
                            font=("Segoe UI", 10), padx=16, pady=10, cursor="hand2",
                            command=lambda n=name: self.show(n))
            btn.pack(fill="x")
            self.sidebar_buttons[name] = btn
        self.show(ROLE_VIEWS[role][0])

    def show(self, name):
        for n, btn in self.sidebar_buttons.items():
            btn.configure(bg="#eaf2ff" if n == name else "white",
                          fg=PRIMARY if n == name else NAVY,
                          font=("Segoe UI Semibold", 10) if n == name else ("Segoe UI", 10))
        self.home.show(name)
        self.update_badges()

    def update_badges(self):
        if not self.user or "Notifications" not in self.sidebar_buttons:
            return
        count = notifications.unread_count(self.conn, self.user["user_id"])
        btn = self.sidebar_buttons["Notifications"]
        base = "Notifications"
        btn.configure(text=f"{base}  ({count})" if count else base)

    def logout(self):
        self.user = None
        for child in self.winfo_children():
            child.destroy()
        self.sidebar_buttons = {}
        self.home = None
        self.login_frame = LoginFrame(self, self)
        self.login_frame.pack(fill="both", expand=True)

    # ---- helpers for automation / testing ----------------------------------
    def login_as(self, user_id, password):
        user = auth.login(self.conn, user_id, password)
        if user is None:
            raise RuntimeError(f"Login failed for {user_id}")
        self.on_login(user)
        return user


def main():
    app = CampusCareApp()
    app.mainloop()


if __name__ == "__main__":
    main()
