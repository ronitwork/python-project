"""
CampusCare 2.0 - Automated screenshot capture for the project report.

Runs the real Tkinter application against a COPY of the demo database,
drives it through the main workflows and captures window screenshots.

Usage:  python capture_screenshots.py
Output: screenshots/*.png
"""
import ctypes
import os
import shutil
import sys
import traceback

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass

from PIL import Image
import ctypes
from ctypes import windll, wintypes

user32 = windll.user32
gdi32 = windll.gdi32
user32.GetAncestor.restype = wintypes.HWND
user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
user32.GetWindowDC.restype = wintypes.HDC
user32.GetWindowDC.argtypes = [wintypes.HWND]
user32.PrintWindow.restype = wintypes.BOOL
user32.PrintWindow.argtypes = [wintypes.HWND, wintypes.HDC, wintypes.UINT]
user32.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
gdi32.CreateCompatibleDC.restype = wintypes.HDC
gdi32.CreateCompatibleDC.argtypes = [wintypes.HDC]
gdi32.CreateCompatibleBitmap.restype = wintypes.HANDLE
gdi32.CreateCompatibleBitmap.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int]
gdi32.SelectObject.restype = wintypes.HANDLE
gdi32.SelectObject.argtypes = [wintypes.HDC, wintypes.HANDLE]
gdi32.GetDIBits.restype = ctypes.c_int
gdi32.GetDIBits.argtypes = [wintypes.HDC, wintypes.HANDLE, wintypes.UINT, wintypes.UINT,
                            ctypes.c_void_p, ctypes.c_void_p, wintypes.UINT]
gdi32.DeleteObject.argtypes = [wintypes.HANDLE]
gdi32.DeleteDC.argtypes = [wintypes.HDC]


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG), ("biHeight", wintypes.LONG),
        ("biPlanes", wintypes.WORD), ("biBitCount", wintypes.WORD),
        ("biCompression", wintypes.DWORD), ("biSizeImage", wintypes.DWORD),
        ("biXPelsPerMeter", wintypes.LONG), ("biYPelsPerMeter", wintypes.LONG),
        ("biClrUsed", wintypes.DWORD), ("biClrImportant", wintypes.DWORD),
    ]


def grab(name, widget=None):
    """Capture the widget's window via PrintWindow (immune to screen overlays)."""
    pump()
    w = widget or app
    try:
        w.lift()
    except Exception:
        pass
    pump(2)
    hwnd = user32.GetAncestor(w.winfo_id(), 2) or w.winfo_id()  # GA_ROOT
    rect = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    width, height = rect.right - rect.left, rect.bottom - rect.top
    window_dc = user32.GetWindowDC(hwnd)
    mem_dc = gdi32.CreateCompatibleDC(window_dc)
    bitmap = gdi32.CreateCompatibleBitmap(window_dc, width, height)
    gdi32.SelectObject(mem_dc, bitmap)
    ok = user32.PrintWindow(hwnd, mem_dc, 2)  # PW_RENDERFULLCONTENT
    bmi = BITMAPINFOHEADER()
    bmi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    bmi.biWidth, bmi.biHeight = width, -height
    bmi.biPlanes, bmi.biBitCount, bmi.biCompression = 1, 32, 0
    buffer = ctypes.create_string_buffer(width * height * 4)
    gdi32.GetDIBits(mem_dc, bitmap, 0, height, buffer, ctypes.byref(bmi), 0)
    img = Image.frombuffer("RGB", (width, height), buffer, "raw", "BGRX", 0, 1)
    gdi32.DeleteObject(bitmap)
    gdi32.DeleteDC(mem_dc)
    user32.ReleaseDC(hwnd, window_dc)
    if not ok:
        raise RuntimeError(f"PrintWindow failed for {name}")
    path = os.path.join(SHOTS_DIR, name + ".png")
    img.save(path)
    saved.append(path)
    print("captured", name, img.size)

import complaints
import database
import duplicate_detector as dup
from main import CampusCareApp

HERE = os.path.dirname(os.path.abspath(__file__))
SHOTS_DIR = os.path.join(HERE, "screenshots")
WORK_DB = os.path.join(HERE, "data", "campuscare_screenshot.db")

os.makedirs(SHOTS_DIR, exist_ok=True)
shutil.copyfile(database.DEFAULT_DB_PATH, WORK_DB)

app = CampusCareApp(db_path=WORK_DB)
app.geometry("1280x920+80+40")
conn = app.conn
saved = []


def pump(n=6):
    for _ in range(n):
        app.update_idletasks()
        app.update()


def find_cid(title_like, student=None):
    q = "SELECT complaint_id FROM complaints WHERE title LIKE ?"
    params = [f"%{title_like}%"]
    if student:
        q += " AND student_id = ?"
        params.append(student)
    row = conn.execute(q, params).fetchone()
    return row["complaint_id"] if row else None


def toplevels():
    found = []

    def walk(w):
        for c in w.winfo_children():
            if c.winfo_class() == "Toplevel":
                found.append(c)
            walk(c)

    walk(app)
    return found


def close_dialogs():
    for t in toplevels():
        try:
            t.destroy()
        except Exception:
            pass
    pump()


try:
    # 1. Login screen
    grab("01_login")

    # 2. Student submission form (filled)
    app.login_as("S26CSEU3579", "campus123")
    pump()
    sv = app.home.submit_view
    sv.vars["title"].set("Slow Wi-Fi in Hostel A room 204")
    sv.desc_text.insert("1.0", "Wi-Fi in Hostel A is very slow and disconnects frequently "
                               "during evening study hours. Online classes keep buffering.")
    sv.vars["category"].set("Internet")
    sv.vars["location"].set("Hostel A")
    sv.vars["severity"].set("3")
    sv.vars["impact"].set("4")
    sv.vars["safety_risk"].set("0")
    grab("02_student_submit_form")

    # 3. Submission result with priority + issue-group link
    sv.submit()
    pump()
    grab("03_student_submit_result")

    # 4. My complaints list
    app.show("My Complaints")
    pump()
    grab("04_student_my_complaints")

    # 5. Student detail dialog (emergency complaint, resolved, feedback shown)
    cid_wire = find_cid("live wire", "S26CSEU3579")
    app.home.my_view.tree.selection_set(cid_wire)
    app.home.my_view.open_selected()
    pump()
    dialog = toplevels()[-1]
    grab("05_student_complaint_detail", dialog)
    close_dialogs()

    # 6. Student notifications
    app.show("Notifications")
    pump()
    grab("06_student_notifications")

    # 7. Staff queue
    app.logout()
    pump()
    app.login_as("STF-IT", "staff123")
    pump()
    grab("07_staff_queue")

    # 8. Admin dashboard
    app.logout()
    pump()
    app.login_as("admin", "admin123")
    pump()
    grab("08_admin_dashboard")

    # 9. Admin complaint detail (assignment + status + timeline)
    app.show("All Complaints")
    pump()
    cid_cooler = find_cid("Water cooler dirty")
    app.home.complaints_view.tree.selection_set(cid_cooler)
    app.home.complaints_view.open_selected()
    pump()
    dialog = toplevels()[-1]
    grab("09_admin_complaint_detail", dialog)
    close_dialogs()

    # Resolve the water cooler complaint so a feedback dialog can be shown later.
    complaints.assign(conn, cid_cooler, "STF-HK", "admin")
    complaints.update_status(conn, cid_cooler, "Resolved", "admin",
                             "Cooler cleaned, filters replaced and serviced.")

    # 10. Issue groups + preventive maintenance
    app.show("Issue Groups")
    pump()
    groups = dup.group_details(conn)
    wifi_group = next(g for g in groups if g["category"] == "Internet" and g["location"] == "Hostel A")
    app.home.groups_view.tree.selection_set(wifi_group["group_id"])
    pump()
    grab("10_admin_issue_groups")

    # 11. Analytics charts
    app.show("Analytics")
    pump(10)
    grab("11_admin_analytics")

    # 12. Admin notifications (escalations)
    app.show("Notifications")
    pump()
    grab("12_admin_notifications")

    # 13. Feedback dialog (student rates the just-resolved cooler complaint)
    app.logout()
    pump()
    app.login_as("S26CSEU0102", "campus123")
    app.show("My Complaints")
    pump()
    app.home.my_view.tree.selection_set(cid_cooler)
    app.home.my_view.open_selected()
    pump()
    detail = toplevels()[-1]
    detail.do_feedback()
    pump()
    fb = toplevels()[-1]
    fb.rating.set("4")
    fb.comments.insert("1.0", "Cooler is clean now, water tastes fine. Thank you!")
    pump()
    grab("13_student_feedback_dialog", fb)
    close_dialogs()

    print(f"\nDone. {len(saved)} screenshots saved to {SHOTS_DIR}")
except Exception:
    traceback.print_exc()
    sys.exit(1)
finally:
    try:
        app.destroy()
    except Exception:
        pass
