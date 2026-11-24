"""
CampusCare 2.0 - Report diagrams (flowchart + architecture), drawn with matplotlib.
Usage: python make_diagrams.py
"""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Ellipse, Polygon

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "diagrams")
os.makedirs(OUT, exist_ok=True)

NAVY = "#16324f"
PRIMARY = "#1f6feb"
GREEN = "#2da44e"
AMBER = "#bf8700"
RED = "#cf222e"
PURPLE = "#8250df"
LIGHT = "#eaf2ff"
GREY = "#f2f5f9"


def box(ax, x, y, w, h, text, fc=LIGHT, ec=PRIMARY, fs=9, bold=False):
    patch = FancyBboxPatch((x - w / 2, y - h / 2), w, h,
                           boxstyle="round,pad=0.012,rounding_size=0.02",
                           fc=fc, ec=ec, lw=1.3)
    ax.add_patch(patch)
    ax.text(x, y, text, ha="center", va="center", fontsize=fs,
            color=NAVY, fontweight="bold" if bold else "normal", linespacing=1.35)


def diamond(ax, x, y, w, h, text, fs=8.5):
    pts = [(x, y + h / 2), (x + w / 2, y), (x, y - h / 2), (x - w / 2, y)]
    ax.add_patch(Polygon(pts, closed=True, fc="#fff6e0", ec=AMBER, lw=1.3))
    ax.text(x, y, text, ha="center", va="center", fontsize=fs, color=NAVY, linespacing=1.3)


def terminal(ax, x, y, w, h, text):
    ax.add_patch(Ellipse((x, y), w, h, fc=NAVY, ec=NAVY))
    ax.text(x, y, text, ha="center", va="center", fontsize=9.5, color="white", fontweight="bold")


def arrow(ax, x1, y1, x2, y2, label="", color=NAVY, lx=0.02, style="-|>"):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle=style,
                                 mutation_scale=13, color=color, lw=1.2,
                                 shrinkA=0, shrinkB=0))
    if label:
        ax.text((x1 + x2) / 2 + lx, (y1 + y2) / 2, label, fontsize=8, color=color,
                ha="left", va="center", fontweight="bold")


# ---------------------------------------------------------------- flowchart
fig, ax = plt.subplots(figsize=(10, 12.6), dpi=150)
ax.set_xlim(0, 1)
ax.set_ylim(0, 1)
ax.axis("off")
ax.text(0.5, 0.985, "CampusCare 2.0 - Complaint Submission & Intelligent Prioritisation Flowchart",
        ha="center", fontsize=12.5, fontweight="bold", color=NAVY)

X = 0.40          # main column
RX = 0.80         # branch column
W, H = 0.34, 0.045
DW, DH = 0.30, 0.062

terminal(ax, X, 0.95, 0.14, 0.035, "START")
arrow(ax, X, 0.9325, X, 0.9125)
box(ax, X, 0.895, W, H, "Student login (role check) and\nopen complaint form")
arrow(ax, X, 0.8725, X, 0.8525)
box(ax, X, 0.835, W, H, "Enter title, description, category,\nlocation, severity, impact, safety risk")
arrow(ax, X, 0.8125, X, 0.790)
diamond(ax, X, 0.762, DW, DH, "Input valid?")
arrow(ax, X + DW / 2, 0.762, RX - 0.13, 0.762, "No", RED, lx=0.01)
box(ax, RX, 0.762, 0.26, 0.045, "Show validation error,\nre-prompt (nothing saved)", fc="#fdecec", ec=RED, fs=8.5)
arrow(ax, RX, 0.7845, RX, 0.835, "", RED, style="-")
arrow(ax, RX, 0.835, X + W / 2, 0.835, "", RED)
arrow(ax, X, 0.731, X, 0.706, "Yes", GREEN)
diamond(ax, X, 0.678, DW, DH, "Identical open complaint\nby same student?")
arrow(ax, X + DW / 2, 0.678, RX - 0.13, 0.678, "Yes", RED, lx=0.01)
box(ax, RX, 0.678, 0.26, 0.045, "Duplicate warning with\nexisting ID - not saved", fc="#fdecec", ec=RED, fs=8.5)
arrow(ax, X, 0.647, X, 0.622, "No", GREEN)
box(ax, X, 0.60, W, H, "Calculate priority score\nP = (S x 5) + (I x 4) + (R x 3) + A", bold=True)
arrow(ax, X, 0.5775, X, 0.553)
diamond(ax, X, 0.525, DW, DH, "Emergency keyword\nor confirmed flag?")
arrow(ax, X + DW / 2, 0.525, RX - 0.13, 0.525, "Yes", RED, lx=0.01)
box(ax, RX, 0.525, 0.26, 0.05, "Priority = Critical\n+ emergency safety notice", fc="#fdecec", ec=RED, fs=8.5, bold=True)
arrow(ax, RX, 0.50, RX, 0.455, "", RED, style="-")
arrow(ax, RX, 0.455, X + W / 2, 0.455, "", RED)
arrow(ax, X, 0.494, X, 0.469, "No", GREEN)
box(ax, X, 0.447, W, H, "Map score to band: 0-20 Low, 21-40 Medium,\n41-55 High, 56+ Critical")
arrow(ax, X, 0.4245, X, 0.400)
box(ax, X, 0.378, W, H, "Route to department by category;\nset response deadline by priority")
arrow(ax, X, 0.3555, X, 0.331)
diamond(ax, X, 0.303, DW, DH, "Similar open reports?\n(same category + location,\nJaccard >= 0.45)")
arrow(ax, X + DW / 2, 0.303, RX - 0.13, 0.303, "Yes", PURPLE, lx=0.01)
box(ax, RX, 0.303, 0.26, 0.05, "Link to issue group (Suggested)\nfor administrator confirmation", fc="#f3edff", ec=PURPLE, fs=8.5)
arrow(ax, RX, 0.278, RX, 0.228, "", PURPLE, style="-")
arrow(ax, RX, 0.228, X + W / 2, 0.228, "", PURPLE)
arrow(ax, X, 0.266, X, 0.243, "No", GREEN)
box(ax, X, 0.221, W, H, "Save complaint to SQLite + status history;\nnotify administrators (and department if emergency)", bold=True)
arrow(ax, X, 0.1985, X, 0.174)
box(ax, X, 0.152, W, H, "Staff assignment / status updates / overdue checks\n-> feedback, analytics and reports (see lifecycle)")
arrow(ax, X, 0.1295, X, 0.105)
terminal(ax, X, 0.085, 0.14, 0.035, "END")

fig.tight_layout()
fig.savefig(os.path.join(OUT, "flowchart.png"), bbox_inches="tight", facecolor="white")
plt.close(fig)
print("flowchart.png saved")

# ------------------------------------------------------------- architecture
fig, ax = plt.subplots(figsize=(11, 7.2), dpi=150)
ax.set_xlim(0, 1)
ax.set_ylim(0, 1)
ax.axis("off")
ax.text(0.5, 0.975, "CampusCare 2.0 - Module Architecture", ha="center",
        fontsize=13, fontweight="bold", color=NAVY)


def layer(y, h, title, color):
    ax.add_patch(FancyBboxPatch((0.03, y), 0.94, h,
                                boxstyle="round,pad=0.008,rounding_size=0.015",
                                fc="white", ec=color, lw=1.6))
    ax.text(0.05, y + h - 0.028, title, fontsize=10.5, fontweight="bold", color=color)


layer(0.70, 0.22, "PRESENTATION LAYER  -  Tkinter GUI (main.py)", PRIMARY)
for x, w, t in [
    (0.165, 0.20, "Login / Registration\n(auth views)"),
    (0.395, 0.20, "Student views\nsubmit | track | feedback"),
    (0.625, 0.20, "Staff views\ndepartment queue | updates"),
    (0.855, 0.20, "Admin views\ndashboard | groups | analytics"),
]:
    box(ax, x, 0.79, w, 0.075, t, fc=LIGHT, ec=PRIMARY, fs=8.5)

layer(0.36, 0.28, "APPLICATION LOGIC LAYER  -  Python modules", GREEN)
mods = [
    (0.145, "auth.py\nroles + PBKDF2 hashing"),
    (0.375, "complaints.py\nlifecycle + validation"),
    (0.605, "priority_engine.py\nscoring + override"),
    (0.835, "duplicate_detector.py\nJaccard + grouping"),
    (0.145, "escalation.py\ndeadlines + overdue"),
    (0.375, "notifications.py\nin-app alerts"),
    (0.605, "analytics.py\nmetrics + charts + exports"),
    (0.835, "ui_common.py\nshared widgets + dialogs"),
]
for i, (x, t) in enumerate(mods):
    y = 0.545 if i < 4 else 0.435
    box(ax, x, y, 0.21, 0.075, t, fc="#e9f6ec", ec=GREEN, fs=8)

layer(0.06, 0.24, "DATA LAYER  -  SQLite (database.py) + file exports", PURPLE)
box(ax, 0.26, 0.155, 0.40, 0.085,
    "data/campuscare.db\nusers | complaints | status_history | issue_groups\ngroup_links | feedback | notifications",
    fc="#f3edff", ec=PURPLE, fs=8.5)
box(ax, 0.72, 0.155, 0.40, 0.085,
    "reports/\ncomplaints_export_*.csv (csv module)\nsummary_report_*.txt  |  matplotlib charts",
    fc="#f3edff", ec=PURPLE, fs=8.5)

arrow(ax, 0.5, 0.70, 0.5, 0.645, "", PRIMARY)
arrow(ax, 0.5, 0.64, 0.5, 0.70, "", PRIMARY)
ax.text(0.515, 0.672, "role-based actions / queries", fontsize=8, color=PRIMARY)
arrow(ax, 0.5, 0.36, 0.5, 0.305, "", GREEN)
arrow(ax, 0.5, 0.30, 0.5, 0.36, "", GREEN)
ax.text(0.515, 0.332, "SQL reads / writes (single source of truth)", fontsize=8, color=GREEN)

fig.tight_layout()
fig.savefig(os.path.join(OUT, "architecture.png"), bbox_inches="tight", facecolor="white")
plt.close(fig)
print("architecture.png saved")
