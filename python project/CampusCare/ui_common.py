"""
CampusCare 2.0 - Shared Tkinter theme, widgets and dialogs.
"""
import tkinter as tk
from tkinter import ttk, messagebox

import auth
import complaints
import duplicate_detector as dup
import notifications
import priority_engine as pe

# Palette
BG = "#eef2f7"
CARD = "#ffffff"
NAVY = "#16324f"
PRIMARY = "#1f6feb"
TEXT = "#1c2733"
MUTED = "#5b6b7c"
GREEN = "#2da44e"
RED = "#cf222e"
AMBER = "#bf8700"
BORDER = "#d7dee8"

PRIORITY_COLORS = {"Critical": RED, "High": "#d97706", "Medium": AMBER, "Low": GREEN}
STATUS_COLORS = {"Pending": AMBER, "Assigned": PRIMARY, "In Progress": "#8250df",
                 "Resolved": GREEN, "Reopened": RED, "Closed": MUTED}


def apply_theme(root):
    root.configure(bg=BG)
    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure(".", background=BG, foreground=TEXT, font=("Segoe UI", 10))
    style.configure("TFrame", background=BG)
    style.configure("Card.TFrame", background=CARD, relief="flat", borderwidth=1)
    style.configure("TLabel", background=BG, foreground=TEXT)
    style.configure("Card.TLabel", background=CARD, foreground=TEXT)
    style.configure("Muted.TLabel", background=BG, foreground=MUTED, font=("Segoe UI", 9))
    style.configure("CardMuted.TLabel", background=CARD, foreground=MUTED, font=("Segoe UI", 9))
    style.configure("Title.TLabel", background=BG, foreground=NAVY, font=("Segoe UI Semibold", 16))
    style.configure("CardTitle.TLabel", background=CARD, foreground=NAVY, font=("Segoe UI Semibold", 11))
    style.configure("Header.TLabel", background=NAVY, foreground="white", font=("Segoe UI Semibold", 13))
    style.configure("HeaderUser.TLabel", background=NAVY, foreground="#c9d8ea", font=("Segoe UI", 10))
    style.configure("TButton", font=("Segoe UI", 10), padding=(12, 6))
    style.configure("Primary.TButton", background=PRIMARY, foreground="white", font=("Segoe UI Semibold", 10))
    style.map("Primary.TButton", background=[("active", "#1a5fd0")])
    style.configure("Danger.TButton", background=RED, foreground="white")
    style.map("Danger.TButton", background=[("active", "#b01d28")])
    style.configure("Sidebar.TButton", anchor="w", padding=(16, 10), font=("Segoe UI", 10))
    style.configure("Treeview", background=CARD, fieldbackground=CARD, foreground=TEXT,
                    rowheight=27, font=("Segoe UI", 9), borderwidth=0)
    style.configure("Treeview.Heading", background="#e6ecf4", foreground=NAVY,
                    font=("Segoe UI Semibold", 9), padding=4)
    style.map("Treeview", background=[("selected", "#cfe0ff")], foreground=[("selected", TEXT)])
    style.configure("TNotebook", background=BG, borderwidth=0)
    style.configure("TNotebook.Tab", padding=(14, 7), font=("Segoe UI", 10))
    style.configure("TCheckbutton", background=BG)
    style.configure("Card.TCheckbutton", background=CARD)
    style.configure("TLabelframe", background=CARD, borderwidth=1)
    style.configure("TLabelframe.Label", background=CARD, foreground=NAVY, font=("Segoe UI Semibold", 10))
    style.configure("Vertical.TScrollbar", background="#c4cedb")


def bind_mousewheel(canvas):
    """Scroll only while the pointer is over this canvas."""
    def _wheel(event):
        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
    canvas.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", _wheel))
    canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))


class ScrollableFrame(ttk.Frame):
    """A vertically scrollable container; put content in self.body."""

    def __init__(self, parent, **kw):
        super().__init__(parent, **kw)
        self.canvas = tk.Canvas(self, bg=BG, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.body = ttk.Frame(self.canvas)
        self.body.bind("<Configure>",
                       lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self._win = self.canvas.create_window((0, 0), window=self.body, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        self.canvas.bind("<Configure>",
                         lambda e: self.canvas.itemconfigure(self._win, width=e.width))
        bind_mousewheel(self.canvas)


def card(parent, padding=12, **kw):
    frame = ttk.Frame(parent, style="Card.TFrame", padding=padding, **kw)
    return frame


def stat_card(parent, title, value, color=PRIMARY):
    frame = tk.Frame(parent, bg=CARD, highlightbackground=BORDER, highlightthickness=1, padx=14, pady=10)
    tk.Label(frame, text=str(value), bg=CARD, fg=color, font=("Segoe UI Semibold", 22)).pack(anchor="w")
    tk.Label(frame, text=title, bg=CARD, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w")
    return frame


def make_tree(parent, columns, widths, height=10):
    wrap = ttk.Frame(parent)
    tree = ttk.Treeview(wrap, columns=columns, show="headings", height=height)
    for col, width in zip(columns, widths):
        tree.heading(col, text=col)
        tree.column(col, width=width, anchor="w", stretch=True)
    scroll = ttk.Scrollbar(wrap, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scroll.set)
    tree.pack(side="left", fill="both", expand=True)
    scroll.pack(side="right", fill="y")
    for priority, color in PRIORITY_COLORS.items():
        tree.tag_configure(f"p_{priority}", foreground=color)
    tree.tag_configure("overdue", background="#fdecec")
    tree.tag_configure("resolved", foreground=MUTED)
    return wrap, tree


def complaint_tags(row):
    tags = [f"p_{row['priority']}"]
    if row["overdue"] and row["status"] not in ("Resolved", "Closed"):
        tags.append("overdue")
    if row["status"] in ("Resolved", "Closed"):
        tags.append("resolved")
    return tuple(tags)


def error(parent, message):
    messagebox.showerror("CampusCare", message, parent=parent)


def info(parent, message):
    messagebox.showinfo("CampusCare", message, parent=parent)


class FeedbackDialog(tk.Toplevel):
    """1-5 rating + comments after resolution. Low ratings request a review."""

    def __init__(self, parent, conn, user, complaint_id, on_done=None):
        super().__init__(parent)
        self.conn, self.user, self.cid, self.on_done = conn, user, complaint_id, on_done
        self.title(f"Resolution Feedback - {complaint_id}")
        self.configure(bg=BG)
        self.geometry("480x400")
        self.resizable(False, False)
        self.transient(parent)
        body = ttk.Frame(self, padding=16)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text=f"How well was complaint {complaint_id} resolved?",
                  style="Title.TLabel", font=("Segoe UI Semibold", 12),
                  wraplength=430, justify="left").pack(anchor="w")
        ttk.Label(body, text="1 = very dissatisfied, 5 = fully satisfied", style="Muted.TLabel").pack(anchor="w", pady=(2, 10))
        row = ttk.Frame(body)
        row.pack(anchor="w", pady=4)
        ttk.Label(row, text="Rating:").pack(side="left")
        self.rating = tk.StringVar(value="5")
        ttk.Spinbox(row, from_=1, to=5, textvariable=self.rating, width=5).pack(side="left", padx=8)
        ttk.Label(body, text="Comments (optional):").pack(anchor="w", pady=(8, 2))
        self.comments = tk.Text(body, height=5, width=48, font=("Segoe UI", 10),
                                highlightbackground=BORDER, highlightthickness=1)
        self.comments.pack(fill="x")
        self.msg = ttk.Label(body, text="", foreground=RED)
        self.msg.pack(anchor="w", pady=4)
        ttk.Button(body, text="Submit Feedback", style="Primary.TButton",
                   command=self.submit).pack(anchor="e", pady=6)
        self.grab_set()

    def submit(self):
        try:
            result = complaints.add_feedback(
                self.conn, self.cid, self.rating.get(),
                self.comments.get("1.0", "end").strip(),
            )
        except complaints.ValidationError as exc:
            self.msg.config(text=str(exc))
            return
        if result["review_requested"]:
            info(self, "Thank you. Your low rating has been flagged for administrator review.")
        else:
            info(self, "Thank you for your feedback!")
        if self.on_done:
            self.on_done()
        self.destroy()


class ComplaintDetailDialog(tk.Toplevel):
    """Full complaint record: fields, timeline, feedback and role-based actions."""

    def __init__(self, parent, conn, user, complaint_id, mode, on_change=None):
        super().__init__(parent)
        self.conn, self.user, self.cid, self.mode = conn, user, complaint_id, mode
        self.on_change = on_change
        self.title(f"Complaint {complaint_id}")
        self.configure(bg=BG)
        self.geometry("900x660")
        self.transient(parent)
        self.body = ttk.Frame(self, padding=14)
        self.body.pack(fill="both", expand=True)
        self.render()
        self.grab_set()

    def render(self):
        for child in self.body.winfo_children():
            child.destroy()
        row = complaints.get_complaint(self.conn, self.cid)
        if row is None:
            self.destroy()
            return
        owner_view = row["student_id"] == self.user["user_id"]
        student = complaints.student_label(row, self.user["user_id"])

        top = ttk.Frame(self.body)
        top.pack(fill="x")
        ttk.Label(top, text=row["title"], style="Title.TLabel", wraplength=640).pack(side="left", anchor="w")
        tk.Label(top, text=f" {row['priority']} ({row['priority_score']}) ",
                 bg=PRIORITY_COLORS.get(row["priority"], MUTED), fg="white",
                 font=("Segoe UI Semibold", 10), padx=8, pady=3).pack(side="right")

        meta = card(self.body)
        meta.pack(fill="x", pady=8)
        fields = [
            ("ID", row["complaint_id"]), ("Status", row["status"]),
            ("Category", row["category"]), ("Location", row["location"]),
            ("Student", student), ("Department", row["department"]),
            ("Assigned staff", row["assigned_staff"] or "Unassigned"),
            ("Severity / Impact / Risk", f"{row['severity']} / {row['impact']} / {row['safety_risk']}"),
            ("Created", row["created_at"]), ("Response target", row["due_at"]),
            ("Resolved at", row["resolved_at"] or "-"),
            ("Overdue", "Yes" if row["overdue"] else "No"),
            ("Emergency", "Yes" if row["emergency"] else "No"),
            ("Anonymous", "Yes" if row["anonymous"] else "No"),
        ]
        for i, (label, value) in enumerate(fields):
            r, c = divmod(i, 2)
            cell = ttk.Frame(meta)
            cell.grid(row=r, column=c, sticky="w", padx=(0, 30), pady=2)
            ttk.Label(cell, text=f"{label}: ", style="CardMuted.TLabel").pack(side="left")
            ttk.Label(cell, text=str(value), style="Card.TLabel",
                      font=("Segoe UI Semibold", 9)).pack(side="left")
        desc = ttk.Frame(meta)
        desc.grid(row=len(fields) // 2, column=0, columnspan=2, sticky="w", pady=(6, 0))
        ttk.Label(desc, text="Description: ", style="CardMuted.TLabel").pack(side="left", anchor="n")
        ttk.Label(desc, text=row["description"], style="Card.TLabel", wraplength=760,
                  justify="left").pack(side="left")

        gid = dup.group_of(self.conn, self.cid)
        if gid:
            g = next((x for x in dup.group_details(self.conn) if x["group_id"] == gid), None)
            if g:
                ttk.Label(self.body,
                          text=f"Linked issue group {gid} [{g['group_status']}]: {g['count']} related report(s) "
                               f"at {g['location']} - campus-wide pattern detected.",
                          foreground="#8250df").pack(anchor="w", pady=(0, 6))

        fb = complaints.get_feedback(self.conn, self.cid)
        if fb:
            ttk.Label(self.body, text=f"Student feedback: {fb['rating']}/5 - {fb['comments'] or 'no comments'}",
                      foreground=GREEN if fb["rating"] >= 3 else RED).pack(anchor="w", pady=(0, 6))

        actions = card(self.body)
        actions.pack(fill="x", pady=6)
        if self.mode == "admin":
            ttk.Label(actions, text="Assign staff:", style="Card.TLabel").grid(row=0, column=0, sticky="w")
            staff_rows = auth.list_staff(self.conn)
            choices = [f"{s['name']} ({s['user_id']})" for s in staff_rows]
            self.staff_var = tk.StringVar()
            combo = ttk.Combobox(actions, textvariable=self.staff_var, values=choices, width=30, state="readonly")
            combo.grid(row=0, column=1, padx=8, sticky="w")
            if row["assigned_staff"]:
                for choice in choices:
                    if row["assigned_staff"] in choice:
                        combo.set(choice)
                        break
            ttk.Button(actions, text="Assign", style="Primary.TButton",
                       command=self.do_assign).grid(row=0, column=2, padx=6)
        if self.mode in ("admin", "staff"):
            ttk.Label(actions, text="Update status:", style="Card.TLabel").grid(row=1, column=0, sticky="w", pady=6)
            self.status_var = tk.StringVar(value=row["status"])
            ttk.Combobox(actions, textvariable=self.status_var, values=complaints.STATUSES,
                         width=16, state="readonly").grid(row=1, column=1, sticky="w", padx=8, pady=6)
            self.note_var = tk.StringVar()
            ttk.Entry(actions, textvariable=self.note_var, width=26).grid(row=1, column=2, sticky="w", pady=6)
            ttk.Button(actions, text="Save status + note", style="Primary.TButton",
                       command=self.do_status).grid(row=1, column=3, padx=6)
            ttk.Label(actions, text="note (optional)", style="CardMuted.TLabel").grid(row=2, column=2, sticky="w")
        if self.mode == "student" and owner_view:
            if row["status"] in ("Resolved", "Closed") and not fb:
                ttk.Button(actions, text="Give feedback", style="Primary.TButton",
                           command=self.do_feedback).pack(side="left", padx=4)
            if row["status"] in ("Resolved", "Closed"):
                ttk.Button(actions, text="Request reopen", style="Danger.TButton",
                           command=self.do_reopen).pack(side="left", padx=4)
            if fb:
                ttk.Label(actions, text="Feedback submitted - thank you.", style="CardMuted.TLabel").pack(side="left")

        ttk.Label(self.body, text="Status timeline", style="Title.TLabel",
                  font=("Segoe UI Semibold", 11)).pack(anchor="w", pady=(8, 2))
        wrap, tree = make_tree(self.body, ["When", "From", "To", "By", "Note"],
                               [140, 85, 85, 105, 350], height=6)
        wrap.pack(fill="both", expand=True)
        for event in complaints.timeline(self.conn, self.cid):
            tree.insert("", "end", values=(event["changed_at"], event["old_status"] or "New",
                                           event["new_status"], event["changed_by"], event["note"]))

    def _changed(self):
        self.render()
        if self.on_change:
            self.on_change()

    def do_assign(self):
        value = self.staff_var.get()
        if not value or "(" not in value:
            error(self, "Please select a staff member.")
            return
        staff_id = value.rsplit("(", 1)[1].rstrip(")")
        try:
            complaints.assign(self.conn, self.cid, staff_id, self.user["user_id"])
        except complaints.ValidationError as exc:
            error(self, str(exc))
            return
        self._changed()

    def do_status(self):
        try:
            complaints.update_status(self.conn, self.cid, self.status_var.get(),
                                     self.user["user_id"], self.note_var.get().strip())
        except complaints.ValidationError as exc:
            error(self, str(exc))
            return
        self._changed()

    def do_feedback(self):
        FeedbackDialog(self, self.conn, self.user, self.cid, on_done=self._changed)

    def do_reopen(self):
        from tkinter import simpledialog
        reason = simpledialog.askstring("Reopen complaint", "Why should this be reopened?", parent=self)
        if reason is None:
            return
        try:
            complaints.request_reopen(self.conn, self.cid, self.user["user_id"], reason)
        except complaints.ValidationError as exc:
            error(self, str(exc))
            return
        self._changed()


class NotificationPanel(ttk.Frame):
    """In-app notification list with unread highlighting and mark-read."""

    def __init__(self, parent, conn, user):
        super().__init__(parent, padding=10)
        self.conn, self.user = conn, user
        bar = ttk.Frame(self)
        bar.pack(fill="x", pady=(0, 8))
        ttk.Label(bar, text="Notifications", style="Title.TLabel").pack(side="left")
        ttk.Button(bar, text="Mark all read", command=self.mark_all).pack(side="right")
        ttk.Button(bar, text="Refresh", command=self.refresh).pack(side="right", padx=6)
        wrap, self.tree = make_tree(self, ["When", "Complaint", "Message", "State"],
                                    [130, 130, 640, 70], height=16)
        wrap.pack(fill="both", expand=True)
        self.tree.tag_configure("unread", font=("Segoe UI Semibold", 9), background="#eaf2ff")
        self.tree.bind("<Double-1>", self.open_selected)
        ttk.Label(self, text="Double-click a notification to mark it read and open the complaint.",
                  style="Muted.TLabel").pack(anchor="w", pady=4)
        self.refresh()

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        for n in notifications.all_for(self.conn, self.user["user_id"]):
            tags = () if n["read"] else ("unread",)
            self.tree.insert("", "end", iid=str(n["notification_id"]),
                             values=(n["created_at"], n["complaint_id"] or "-", n["message"],
                                     "Read" if n["read"] else "NEW"), tags=tags)

    def mark_all(self):
        notifications.mark_all_read(self.conn, self.user["user_id"])
        self.refresh()

    def open_selected(self, _event=None):
        sel = self.tree.selection()
        if not sel:
            return
        nid = int(sel[0])
        notifications.mark_read(self.conn, nid)
        values = self.tree.item(sel[0], "values")
        cid = values[1]
        self.refresh()
        if cid and cid != "-":
            row = complaints.get_complaint(self.conn, cid)
            if row is None:
                return
            mode = self.user["role"]
            if mode == "student" and row["student_id"] != self.user["user_id"]:
                return
            ComplaintDetailDialog(self, self.conn, self.user, cid, mode, on_change=self.refresh)
