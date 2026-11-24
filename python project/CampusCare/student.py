"""
CampusCare 2.0 - Student interface: submit complaints, track progress,
give feedback and read notifications.
"""
import tkinter as tk
from tkinter import ttk

import complaints
import notifications
import priority_engine as pe
from ui_common import (BG, CARD, MUTED, RED, GREEN, AMBER, NAVY, card, make_tree,
                       complaint_tags, ComplaintDetailDialog, NotificationPanel,
                       ScrollableFrame, error)


class SubmitView(ttk.Frame):
    """Validated complaint form with instant priority result (scrollable)."""

    def __init__(self, parent, conn, user, on_submitted=None):
        super().__init__(parent)
        self.conn, self.user, self.on_submitted = conn, user, on_submitted
        scroll = ScrollableFrame(self)
        scroll.pack(fill="both", expand=True)
        body = scroll.body
        body.configure(padding=14)
        ttk.Label(body, text="Submit a Campus Complaint", style="Title.TLabel").pack(anchor="w")
        ttk.Label(body, text="Fields are validated. Priority is calculated from severity, impact, "
                             "safety risk and complaint age.", style="Muted.TLabel").pack(anchor="w", pady=(2, 10))

        form = card(body)
        form.pack(fill="x")
        self.vars = {}
        rows = [
            ("Title", "title", "entry", "Short summary, e.g. Wi-Fi not working in Hostel A room 204"),
            ("Category", "category", "combo", None),
            ("Location", "location", "entry", "Building / room / hostel / area"),
        ]
        r = 0
        for label, key, kind, placeholder in rows:
            ttk.Label(form, text=label + ":", style="Card.TLabel").grid(row=r, column=0, sticky="w", pady=5)
            var = tk.StringVar()
            self.vars[key] = var
            if kind == "combo":
                widget = ttk.Combobox(form, textvariable=var, values=pe.CATEGORIES,
                                      state="readonly", width=42)
                widget.current(0)
            else:
                widget = ttk.Entry(form, textvariable=var, width=70)
            widget.grid(row=r, column=1, columnspan=3, sticky="w", padx=8, pady=5)
            r += 1

        ttk.Label(form, text="Description:", style="Card.TLabel").grid(row=r, column=0, sticky="nw", pady=5)
        self.desc_text = tk.Text(form, height=3, width=68, font=("Segoe UI", 10),
                                 highlightbackground="#d7dee8", highlightthickness=1)
        self.desc_text.grid(row=r, column=1, columnspan=3, sticky="w", padx=8, pady=5)
        r += 1

        scales = ttk.Frame(form, style="Card.TFrame")
        scales.grid(row=r, column=0, columnspan=4, sticky="w", pady=6)
        for col, (label, key, lo, hi, hint) in enumerate([
            ("Severity", "severity", 1, 5, "1 minor - 5 severe"),
            ("Impact", "impact", 1, 5, "1 one person - 5 campus-wide"),
            ("Safety risk", "safety_risk", 0, 5, "0 none - 5 extreme"),
        ]):
            box = ttk.Frame(scales, style="Card.TFrame")
            box.grid(row=0, column=col, padx=(0, 28), sticky="w")
            ttk.Label(box, text=label + ":", style="Card.TLabel").pack(anchor="w")
            var = tk.StringVar(value=str(lo))
            self.vars[key] = var
            ttk.Spinbox(box, from_=lo, to=hi, textvariable=var, width=5).pack(anchor="w")
            ttk.Label(box, text=hint, style="CardMuted.TLabel").pack(anchor="w")
        r += 1

        checks = ttk.Frame(form, style="Card.TFrame")
        checks.grid(row=r, column=0, columnspan=4, sticky="w", pady=6)
        self.emergency_var = tk.BooleanVar(value=False)
        self.anonymous_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(checks, text="This is an emergency safety incident",
                        variable=self.emergency_var, style="Card.TCheckbutton").pack(side="left", padx=(0, 24))
        ttk.Checkbutton(checks, text="Report anonymously (hide my identity from staff/admin views)",
                        variable=self.anonymous_var, style="Card.TCheckbutton").pack(side="left")
        r += 1

        btns = ttk.Frame(form, style="Card.TFrame")
        btns.grid(row=r, column=0, columnspan=4, sticky="w", pady=(8, 2))
        ttk.Button(btns, text="Submit Complaint", style="Primary.TButton",
                   command=self.submit).pack(side="left")
        ttk.Button(btns, text="Clear form", command=self.clear).pack(side="left", padx=8)
        self.form_msg = tk.Label(form, text="", bg=CARD, fg=RED, font=("Segoe UI", 9),
                                 wraplength=780, justify="left")
        self.form_msg.grid(row=r + 1, column=0, columnspan=4, sticky="w")

        self.result_area = ttk.Frame(body)
        self.result_area.pack(fill="x", pady=12)

    def clear(self):
        for key, var in self.vars.items():
            var.set("1" if key in ("severity", "impact") else ("0" if key == "safety_risk" else ""))
        self.vars["category"].set(pe.CATEGORIES[0])
        self.desc_text.delete("1.0", "end")
        self.emergency_var.set(False)
        self.anonymous_var.set(False)
        self.form_msg.config(text="")
        for child in self.result_area.winfo_children():
            child.destroy()

    def submit(self):
        self.form_msg.config(text="")
        for child in self.result_area.winfo_children():
            child.destroy()
        try:
            result = complaints.create_complaint(
                self.conn, self.user["user_id"],
                self.vars["title"].get(), self.desc_text.get("1.0", "end").strip(),
                self.vars["category"].get(), self.vars["location"].get(),
                self.vars["severity"].get(), self.vars["impact"].get(),
                self.vars["safety_risk"].get(),
                emergency_confirmed=self.emergency_var.get(),
                anonymous=self.anonymous_var.get(),
            )
        except complaints.DuplicateError as exc:
            self.form_msg.config(text=str(exc), fg=AMBER)
            return
        except complaints.ValidationError as exc:
            self.form_msg.config(text=str(exc))
            return
        except ValueError:
            self.form_msg.config(text="Severity, impact and safety risk must be whole numbers.")
            return
        self.show_result(result)
        if self.on_submitted:
            self.on_submitted()

    def show_result(self, result):
        row = result["complaint"]
        box = card(self.result_area)
        box.pack(fill="x")
        color = {"Critical": RED, "High": "#d97706", "Medium": AMBER, "Low": GREEN}[row["priority"]]
        head = tk.Label(box, text=f"Complaint submitted: {row['complaint_id']}", bg=CARD, fg=NAVY,
                        font=("Segoe UI Semibold", 13))
        head.pack(anchor="w")
        tk.Label(box, text=f"Priority: {row['priority']}   |   Score: {row['priority_score']}   |   "
                           f"Department: {row['department']}", bg=CARD, fg=color,
                 font=("Segoe UI Semibold", 11)).pack(anchor="w", pady=2)
        tk.Label(box, text=f"Response target: {row['due_at']}   |   Status: {row['status']}",
                 bg=CARD, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w")
        if result["emergency"]:
            tk.Label(box, text=pe.EMERGENCY_NOTICE, bg="#fdecec", fg=RED,
                     font=("Segoe UI Semibold", 9), wraplength=840, justify="left",
                     padx=8, pady=6).pack(fill="x", pady=6)
        if result["group_id"]:
            ids = ", ".join(r["complaint_id"] for r, _ in result["similar"])
            tk.Label(box, text=f"Possible duplicate / recurring issue: similar open report(s) {ids}. "
                               f"Linked to issue group {result['group_id']} for administrator review.",
                     bg="#f3edff", fg="#8250df", font=("Segoe UI", 9),
                     wraplength=840, justify="left", padx=8, pady=6).pack(fill="x", pady=4)


class MyComplaintsView(ttk.Frame):
    """Student's own complaints with priority, status, timeline and feedback."""

    def __init__(self, parent, conn, user):
        super().__init__(parent, padding=14)
        self.conn, self.user = conn, user
        bar = ttk.Frame(self)
        bar.pack(fill="x")
        ttk.Label(bar, text="My Complaints", style="Title.TLabel").pack(side="left")
        ttk.Button(bar, text="Refresh", command=self.refresh).pack(side="right")
        ttk.Button(bar, text="Open selected", style="Primary.TButton",
                   command=self.open_selected).pack(side="right", padx=6)
        ttk.Label(self, text="Sorted by priority. Double-click a row for the full record, timeline, "
                             "feedback and reopen options.", style="Muted.TLabel").pack(anchor="w", pady=(2, 8))
        wrap, self.tree = make_tree(
            self, ["ID", "Title", "Category", "Priority", "Score", "Status", "Due", "Overdue"],
            [130, 300, 90, 80, 55, 95, 130, 70], height=15)
        wrap.pack(fill="both", expand=True)
        self.tree.bind("<Double-1>", lambda e: self.open_selected())
        self.refresh()

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        for row in complaints.list_complaints(self.conn, student_id=self.user["user_id"]):
            self.tree.insert("", "end", iid=row["complaint_id"], tags=complaint_tags(row),
                             values=(row["complaint_id"], row["title"], row["category"],
                                     row["priority"], row["priority_score"], row["status"],
                                     row["due_at"], "Yes" if row["overdue"] else "No"))

    def open_selected(self):
        sel = self.tree.selection()
        if not sel:
            error(self, "Please select a complaint first.")
            return
        ComplaintDetailDialog(self, self.conn, self.user, sel[0], "student", on_change=self.refresh)


class StudentHome(ttk.Frame):
    """Container switching between the student views (used by the sidebar shell)."""

    def __init__(self, parent, conn, user):
        super().__init__(parent)
        self.conn, self.user = conn, user
        self.submit_view = SubmitView(self, conn, user, on_submitted=self.refresh_all)
        self.my_view = MyComplaintsView(self, conn, user)
        self.notifications_view = NotificationPanel(self, conn, user)
        self.views = {
            "Submit Complaint": self.submit_view,
            "My Complaints": self.my_view,
            "Notifications": self.notifications_view,
        }
        self.current = None

    def show(self, name):
        if self.current:
            self.current.pack_forget()
        self.current = self.views[name]
        self.current.pack(fill="both", expand=True)
        if name == "My Complaints":
            self.my_view.refresh()
        if name == "Notifications":
            self.notifications_view.refresh()

    def refresh_all(self):
        self.my_view.refresh()
        self.notifications_view.refresh()
