"""
CampusCare 2.0 - Faculty / maintenance staff interface: department queue,
progress updates and resolution notes.
"""
import tkinter as tk
from tkinter import ttk

import complaints
from ui_common import (card, make_tree, complaint_tags, ComplaintDetailDialog,
                       NotificationPanel, error, MUTED)


class StaffQueueView(ttk.Frame):
    def __init__(self, parent, conn, user):
        super().__init__(parent, padding=14)
        self.conn, self.user = conn, user
        bar = ttk.Frame(self)
        bar.pack(fill="x")
        ttk.Label(bar, text=f"Department Queue - {user['department']}", style="Title.TLabel").pack(side="left")
        ttk.Button(bar, text="Refresh", command=self.refresh).pack(side="right")
        ttk.Button(bar, text="Open / update selected", style="Primary.TButton",
                   command=self.open_selected).pack(side="right", padx=6)

        filters = ttk.Frame(self)
        filters.pack(fill="x", pady=8)
        ttk.Label(filters, text="Status:", style="Muted.TLabel").pack(side="left")
        self.status_var = tk.StringVar(value="Open cases")
        choices = ["Open cases", "All"] + complaints.STATUSES
        combo = ttk.Combobox(filters, textvariable=self.status_var, values=choices,
                             state="readonly", width=16)
        combo.pack(side="left", padx=6)
        combo.bind("<<ComboboxSelected>>", lambda e: self.refresh())
        self.mine_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(filters, text="Only assigned to me", variable=self.mine_var,
                        command=self.refresh).pack(side="left", padx=12)

        wrap, self.tree = make_tree(
            self, ["ID", "Title", "Location", "Priority", "Score", "Status", "Assigned", "Due", "Overdue"],
            [120, 250, 140, 70, 45, 90, 90, 120, 60], height=15)
        wrap.pack(fill="both", expand=True)
        self.tree.bind("<Double-1>", lambda e: self.open_selected())
        ttk.Label(self, text="Open a complaint to add progress notes and change its status. "
                             "Every change is recorded in the timeline and the student is notified.",
                  style="Muted.TLabel").pack(anchor="w", pady=6)
        self.refresh()

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        choice = self.status_var.get()
        if choice == "Open cases":
            rows = complaints.list_complaints(self.conn, department=self.user["department"], open_only=True)
        elif choice == "All":
            rows = complaints.list_complaints(self.conn, department=self.user["department"])
        else:
            rows = complaints.list_complaints(self.conn, department=self.user["department"], status=choice)
        if self.mine_var.get():
            rows = [r for r in rows if r["assigned_staff"] == self.user["user_id"]]
        for row in rows:
            self.tree.insert("", "end", iid=row["complaint_id"], tags=complaint_tags(row),
                             values=(row["complaint_id"], row["title"], row["location"],
                                     row["priority"], row["priority_score"], row["status"],
                                     row["assigned_staff"] or "-", row["due_at"],
                                     "Yes" if row["overdue"] else "No"))

    def open_selected(self):
        sel = self.tree.selection()
        if not sel:
            error(self, "Please select a complaint first.")
            return
        ComplaintDetailDialog(self, self.conn, self.user, sel[0], "staff", on_change=self.refresh)


class StaffHome(ttk.Frame):
    def __init__(self, parent, conn, user):
        super().__init__(parent)
        self.conn, self.user = conn, user
        self.queue_view = StaffQueueView(self, conn, user)
        self.notifications_view = NotificationPanel(self, conn, user)
        self.views = {"My Queue": self.queue_view, "Notifications": self.notifications_view}
        self.current = None

    def show(self, name):
        if self.current:
            self.current.pack_forget()
        self.current = self.views[name]
        self.current.pack(fill="both", expand=True)
        if name == "My Queue":
            self.queue_view.refresh()
        if name == "Notifications":
            self.notifications_view.refresh()
