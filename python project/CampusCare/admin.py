"""
CampusCare 2.0 - Administrator interface: dashboard cards, complaint
management and assignment, issue groups, analytics charts and exports.
"""
import os
import tkinter as tk
from tkinter import ttk

import matplotlib
matplotlib.use("TkAgg", force=True)
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

import analytics
import auth
import complaints
import duplicate_detector as dup
import escalation
import notifications
import priority_engine as pe
from ui_common import (BG, CARD, MUTED, RED, GREEN, AMBER, PRIMARY, NAVY, BORDER,
                       card, stat_card, make_tree, complaint_tags,
                       ComplaintDetailDialog, NotificationPanel, ScrollableFrame,
                       error, info)


class DashboardView(ttk.Frame):
    def __init__(self, parent, conn, user, on_change=None):
        super().__init__(parent, padding=14)
        self.conn, self.user, self.on_change = conn, user, on_change
        bar = ttk.Frame(self)
        bar.pack(fill="x")
        ttk.Label(bar, text="Campus Dashboard", style="Title.TLabel").pack(side="left")
        ttk.Button(bar, text="Run overdue & priority checks", style="Primary.TButton",
                   command=self.run_checks).pack(side="right")
        ttk.Button(bar, text="Add staff user", command=self.add_staff).pack(side="right", padx=6)
        ttk.Button(bar, text="Refresh", command=self.refresh).pack(side="right", padx=6)

        self.cards = ttk.Frame(self)
        self.cards.pack(fill="x", pady=10)

        tables = ttk.Frame(self)
        tables.pack(fill="both", expand=True)
        ttk.Label(tables, text="Critical / emergency queue (open cases)",
                  style="CardTitle.TLabel").pack(anchor="w")
        wrap, self.critical_tree = make_tree(
            tables, ["ID", "Title", "Location", "Status", "Score", "Department", "Overdue"],
            [125, 280, 165, 90, 50, 200, 65], height=5)
        wrap.pack(fill="x", pady=(4, 10))
        self.critical_tree.bind("<Double-1>", lambda e: self.open_tree(self.critical_tree))

        ttk.Label(tables, text="Overdue escalations", style="CardTitle.TLabel").pack(anchor="w")
        wrap, self.overdue_tree = make_tree(
            tables, ["ID", "Title", "Priority", "Department", "Assigned", "Due"],
            [130, 300, 80, 220, 110, 130], height=6)
        wrap.pack(fill="x", pady=4)
        self.overdue_tree.bind("<Double-1>", lambda e: self.open_tree(self.overdue_tree))

        exports = ttk.Frame(self)
        exports.pack(fill="x", pady=8)
        ttk.Button(exports, text="Export complaints CSV", command=self.export_csv).pack(side="left")
        ttk.Button(exports, text="Export summary report", command=self.export_report).pack(side="left", padx=8)
        self.export_msg = ttk.Label(exports, text="", style="Muted.TLabel")
        self.export_msg.pack(side="left", padx=10)
        self.refresh()

    def refresh(self):
        for child in self.cards.winfo_children():
            child.destroy()
        s = analytics.summary(self.conn)
        items = [
            ("Total complaints", s["total"], PRIMARY),
            ("Open", s["open"], AMBER),
            ("Critical", s["critical"], RED),
            ("Overdue", s["overdue"], RED),
            ("Avg resolution (days)", s["avg_resolution_days"], NAVY),
            ("Satisfaction / 5", s["satisfaction"] or "-", GREEN),
        ]
        for i, (title, value, color) in enumerate(items):
            c = stat_card(self.cards, title, value, color)
            c.grid(row=0, column=i, padx=(0 if i == 0 else 8, 0), sticky="nsew")
            self.cards.columnconfigure(i, weight=1)

        self.critical_tree.delete(*self.critical_tree.get_children())
        rows = complaints.list_complaints(self.conn, open_only=True)
        for row in rows:
            if row["priority"] == "Critical" or row["emergency"]:
                self.critical_tree.insert("", "end", iid=row["complaint_id"], tags=complaint_tags(row),
                                          values=(row["complaint_id"], row["title"], row["location"],
                                                  row["status"], row["priority_score"],
                                                  "Yes" if row["overdue"] else "No"))
        self.overdue_tree.delete(*self.overdue_tree.get_children())
        for row in escalation.overdue_complaints(self.conn):
            self.overdue_tree.insert("", "end", iid=row["complaint_id"], tags=complaint_tags(row),
                                     values=(row["complaint_id"], row["title"], row["priority"],
                                             row["department"], row["assigned_staff"] or "-",
                                             row["due_at"]))

    def run_checks(self):
        result = escalation.run_checks(self.conn)
        self.refresh()
        if self.on_change:
            self.on_change()
        info(self, f"Checks complete. {result['total_overdue']} complaint(s) overdue; "
                   f"{len(result['newly_overdue'])} newly escalated to administrators and departments.")

    def open_tree(self, tree):
        sel = tree.selection()
        if sel:
            ComplaintDetailDialog(self, self.conn, self.user, sel[0], "admin", on_change=self.refresh)

    def add_staff(self):
        dialog = tk.Toplevel(self)
        dialog.title("Add staff user")
        dialog.configure(bg=BG)
        dialog.geometry("420x330")
        dialog.transient(self)
        dialog.grab_set()
        body = ttk.Frame(dialog, padding=16)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text="Register a staff account", style="Title.TLabel",
                  font=("Segoe UI Semibold", 12)).pack(anchor="w", pady=(0, 10))
        entries = {}
        for label, key in [("Staff ID", "user_id"), ("Full name", "name"), ("Password", "password")]:
            ttk.Label(body, text=label + ":").pack(anchor="w", pady=(6, 0))
            var = tk.StringVar()
            entries[key] = var
            ttk.Entry(body, textvariable=var, width=40,
                      show="*" if key == "password" else "").pack(anchor="w")
        ttk.Label(body, text="Department:").pack(anchor="w", pady=(6, 0))
        dept_var = tk.StringVar(value=pe.DEPARTMENT_ROUTING["Internet"])
        ttk.Combobox(body, textvariable=dept_var, values=sorted(set(pe.DEPARTMENT_ROUTING.values())),
                     state="readonly", width=40).pack(anchor="w")
        msg = ttk.Label(body, text="", foreground=RED)
        msg.pack(anchor="w", pady=4)

        def save():
            try:
                auth.register_user(self.conn, entries["user_id"].get(), entries["name"].get(),
                                   entries["password"].get(), role="staff", department=dept_var.get())
            except auth.AuthError as exc:
                msg.config(text=str(exc))
                return
            info(dialog, "Staff account created.")
            dialog.destroy()

        ttk.Button(body, text="Create account", style="Primary.TButton", command=save).pack(anchor="e", pady=8)

    def export_csv(self):
        from database import REPORTS_DIR
        path = analytics.export_csv(self.conn, REPORTS_DIR)
        self.export_msg.config(text=f"Saved: {os.path.basename(path)}")

    def export_report(self):
        from database import REPORTS_DIR
        path = analytics.export_summary_report(self.conn, REPORTS_DIR)
        self.export_msg.config(text=f"Saved: {os.path.basename(path)}")


class ComplaintsView(ttk.Frame):
    def __init__(self, parent, conn, user):
        super().__init__(parent, padding=14)
        self.conn, self.user = conn, user
        ttk.Label(self, text="All Complaints", style="Title.TLabel").pack(anchor="w")
        filters = card(self)
        filters.pack(fill="x", pady=8)
        ttk.Label(filters, text="Search:", style="Card.TLabel").grid(row=0, column=0, sticky="w")
        self.search_var = tk.StringVar()
        ttk.Entry(filters, textvariable=self.search_var, width=24).grid(row=0, column=1, padx=6)
        self.filter_vars = {}
        for col, (label, key, values) in enumerate([
            ("Category", "category", ["All"] + pe.CATEGORIES),
            ("Status", "status", ["All"] + complaints.STATUSES),
            ("Priority", "priority", ["All", "Critical", "High", "Medium", "Low"]),
            ("Department", "department", ["All"] + sorted(set(pe.DEPARTMENT_ROUTING.values()))),
        ], start=2):
            ttk.Label(filters, text=label + ":", style="Card.TLabel").grid(row=0, column=col * 2, sticky="w", padx=(10, 0))
            var = tk.StringVar(value="All")
            self.filter_vars[key] = var
            ttk.Combobox(filters, textvariable=var, values=values, state="readonly",
                         width=22 if key == "department" else 13).grid(row=0, column=col * 2 + 1, padx=6)
        ttk.Button(filters, text="Apply", style="Primary.TButton",
                   command=self.refresh).grid(row=0, column=10, padx=8)
        ttk.Button(filters, text="Reset", command=self.reset).grid(row=0, column=11)

        wrap, self.tree = make_tree(
            self, ["ID", "Title", "Category", "Location", "Priority", "Score", "Status",
                   "Department", "Staff", "Student", "Overdue"],
            [120, 230, 85, 140, 70, 48, 92, 180, 90, 100, 62], height=15)
        wrap.pack(fill="both", expand=True)
        self.tree.bind("<Double-1>", lambda e: self.open_selected())
        ttk.Label(self, text="Double-click to open the record: assign staff, update status, "
                             "view timeline and issue-group links.", style="Muted.TLabel").pack(anchor="w", pady=6)
        self.refresh()

    def reset(self):
        self.search_var.set("")
        for var in self.filter_vars.values():
            var.set("All")
        self.refresh()

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        kwargs = {}
        for key, var in self.filter_vars.items():
            if var.get() != "All":
                kwargs[key] = var.get()
        if self.search_var.get().strip():
            kwargs["search"] = self.search_var.get().strip()
        for row in complaints.list_complaints(self.conn, **kwargs):
            student = complaints.student_label(row, self.user["user_id"])
            self.tree.insert("", "end", iid=row["complaint_id"], tags=complaint_tags(row),
                             values=(row["complaint_id"], row["title"], row["category"],
                                     row["location"], row["priority"], row["priority_score"],
                                     row["status"], row["department"], row["assigned_staff"] or "-",
                                     student, "Yes" if row["overdue"] else "No"))

    def open_selected(self):
        sel = self.tree.selection()
        if not sel:
            error(self, "Please select a complaint first.")
            return
        ComplaintDetailDialog(self, self.conn, self.user, sel[0], "admin", on_change=self.refresh)


class GroupsView(ttk.Frame):
    def __init__(self, parent, conn, user):
        super().__init__(parent, padding=14)
        self.conn, self.user = conn, user
        bar = ttk.Frame(self)
        bar.pack(fill="x")
        ttk.Label(bar, text="Recurring Issue Groups", style="Title.TLabel").pack(side="left")
        ttk.Button(bar, text="Refresh", command=self.refresh).pack(side="right")
        ttk.Button(bar, text="Confirm selected group", style="Primary.TButton",
                   command=self.confirm).pack(side="right", padx=6)
        ttk.Label(self, text="Similar reports (same category + location, Jaccard word overlap >= "
                             f"{dup.SIMILARITY_THRESHOLD}) are grouped automatically as suggestions. "
                             "Confirming a group marks it as a verified campus-wide pattern.",
                  style="Muted.TLabel", wraplength=1000, justify="left").pack(anchor="w", pady=(2, 8))
        wrap, self.tree = make_tree(
            self, ["Group", "State", "Category", "Location", "Reports", "Open", "Summary"],
            [80, 90, 90, 170, 65, 55, 380], height=9)
        wrap.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", lambda e: self.show_links())

        bottom = ttk.Frame(self)
        bottom.pack(fill="both", expand=True, pady=8)
        left = ttk.Frame(bottom)
        left.pack(side="left", fill="both", expand=True, padx=(0, 8))
        ttk.Label(left, text="Linked complaints", style="CardTitle.TLabel").pack(anchor="w")
        wrap, self.links_tree = make_tree(left, ["ID", "Title", "Student", "Status", "Priority"],
                                          [120, 250, 100, 90, 75], height=6)
        wrap.pack(fill="both", expand=True, pady=4)
        right = ttk.Frame(bottom)
        right.pack(side="left", fill="both", expand=True)
        ttk.Label(right, text="Preventive maintenance suggestions", style="CardTitle.TLabel").pack(anchor="w")
        self.suggest_box = tk.Text(right, height=8, font=("Segoe UI", 9), bg=CARD,
                                   highlightbackground=BORDER, highlightthickness=1, wrap="word")
        self.suggest_box.pack(fill="both", expand=True, pady=4)
        self.refresh()

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        self.groups = dup.group_details(self.conn)
        for g in self.groups:
            self.tree.insert("", "end", iid=g["group_id"],
                             values=(g["group_id"], g["group_status"], g["category"],
                                     g["location"], g["count"], g["open_count"], g["summary"]))
        self.suggest_box.delete("1.0", "end")
        suggestions = dup.preventive_suggestions(self.conn)
        if suggestions:
            for g in suggestions:
                self.suggest_box.insert("end",
                    f"- Inspect {g['location']} ({g['category']}): {g['count']} recurring reports "
                    f"in confirmed group {g['group_id']} suggest a preventive inspection.\n\n")
        else:
            self.suggest_box.insert("end",
                "No confirmed group has reached the inspection threshold "
                f"({dup.PREVENTIVE_MIN_REPORTS} reports) yet.\n\n"
                "Confirm a suggested group with enough linked reports to generate a suggestion.")
        self.links_tree.delete(*self.links_tree.get_children())

    def show_links(self):
        sel = self.tree.selection()
        self.links_tree.delete(*self.links_tree.get_children())
        if not sel:
            return
        group = next((g for g in self.groups if g["group_id"] == sel[0]), None)
        if not group:
            return
        for cid in group["complaint_ids"]:
            row = complaints.get_complaint(self.conn, cid)
            if row:
                self.links_tree.insert("", "end", values=(
                    cid, row["title"], complaints.student_label(row, self.user["user_id"]),
                    row["status"], row["priority"]))

    def confirm(self):
        sel = self.tree.selection()
        if not sel:
            error(self, "Please select a group first.")
            return
        dup.confirm_group(self.conn, sel[0])
        notifications.notify_admins(self.conn, "", f"Issue group {sel[0]} confirmed as a recurring campus problem.")
        self.refresh()


class AnalyticsView(ttk.Frame):
    def __init__(self, parent, conn, user):
        super().__init__(parent, padding=14)
        self.conn, self.user = conn, user
        bar = ttk.Frame(self)
        bar.pack(fill="x")
        ttk.Label(bar, text="Campus Analytics & Trends", style="Title.TLabel").pack(side="left")
        ttk.Button(bar, text="Refresh charts", style="Primary.TButton",
                   command=self.refresh).pack(side="right")
        self.summary_label = ttk.Label(self, text="", style="Muted.TLabel")
        self.summary_label.pack(anchor="w", pady=(2, 8))

        container = ScrollableFrame(self)
        container.pack(fill="both", expand=True)
        self.inner = container.body
        self.refresh()

    def refresh(self):
        for child in self.inner.winfo_children():
            child.destroy()
        s = analytics.summary(self.conn)
        self.summary_label.config(
            text=f"Average resolution: {s['avg_resolution_days']} days across {s['resolved_count']} resolved "
                 f"complaints   |   Satisfaction: {s['satisfaction']}/5 ({s['feedback_count']} ratings)   |   "
                 f"Emergencies: {s['emergencies']}   |   Recurring groups: {len(dup.group_details(self.conn))}")
        figures = analytics.build_charts(self.conn)
        order = ["category", "location", "trend", "status", "workload", "resolution"]
        for i, key in enumerate(order):
            fig = figures.get(key)
            if fig is None:
                continue
            r, c = divmod(i, 2)
            cell = card(self.inner, padding=6)
            cell.grid(row=r, column=c, padx=6, pady=6, sticky="nsew")
            canvas = FigureCanvasTkAgg(fig, master=cell)
            canvas.draw()
            canvas.get_tk_widget().pack()
            self.inner.columnconfigure(c, weight=1)


class AdminHome(ttk.Frame):
    def __init__(self, parent, conn, user):
        super().__init__(parent)
        self.conn, self.user = conn, user
        self.dashboard = DashboardView(self, conn, user, on_change=self.refresh_badges)
        self.complaints_view = ComplaintsView(self, conn, user)
        self.groups_view = GroupsView(self, conn, user)
        self.analytics_view = AnalyticsView(self, conn, user)
        self.notifications_view = NotificationPanel(self, conn, user)
        self.views = {
            "Dashboard": self.dashboard,
            "All Complaints": self.complaints_view,
            "Issue Groups": self.groups_view,
            "Analytics": self.analytics_view,
            "Notifications": self.notifications_view,
        }
        self.current = None
        self.on_badge_change = None

    def show(self, name):
        if self.current:
            self.current.pack_forget()
        self.current = self.views[name]
        self.current.pack(fill="both", expand=True)
        if name == "Dashboard":
            escalation.run_checks(self.conn)
            self.dashboard.refresh()
        if name == "All Complaints":
            self.complaints_view.refresh()
        if name == "Issue Groups":
            self.groups_view.refresh()
        if name == "Analytics":
            self.analytics_view.refresh()
        if name == "Notifications":
            self.notifications_view.refresh()
        self.refresh_badges()

    def refresh_badges(self):
        if self.on_badge_change:
            self.on_badge_change()
