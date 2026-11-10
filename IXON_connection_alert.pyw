#######################################################
# Tool to monitor IXON adapter connection state.
# Shows a banner on top of each screen with the IXON adapter status.
# Additionally shows a subtle red border around each screen when IXON is active.
# Shows an explicit warning when IXON is active while a regular LAN adapter also
# has an address in 192.168.200.0/24; both routes would otherwise be ambiguous.
# Restarts itself after a monitor is connected/disconnected so the overlays are
# recreated for the new desktop layout.
# If the active TIA Portal main window (recognised by its path-bearing title) has
# an unsafe project-number match with IXON, the border blinks.
#
# Notes:
# - Windows only (uses WinAPI to read foreground window title and transparent color).
# - Multiple monitors with different resolutions/offsets supported.
#
#### How to install ####
# Make sure your IXON network adapter is called 'IXON'.
# winget install python
# pip install psutil
# pip install screeninfo
# place script (with extension .pyw) in shell:startup
#######################################################

import tkinter as tk
import psutil
import subprocess
import datetime
import os
import re
import sys
import ctypes
import ipaddress
import tkinter.font as tkfont
from ctypes import wintypes
from screeninfo import get_monitors

# -------- Project number helpers --------
PROJECT_RE = re.compile(r"C\d{6}")
WINDOWS_PATH_RE = re.compile(r"\b[A-Za-z]:\\")
LAN_200_NETWORK = ipaddress.ip_network("192.168.200.0/24")
EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
IXON_PORTAL_URL = "https://portal.ixon.cloud/portal/devices"
IXON_EXTENSION_ID = "ebhkggkoccabjalpldedaffeljnjjkgd"
IXON_EXTENSION_URL = f"chrome-extension://{IXON_EXTENSION_ID}/activate.html"

def get_foreground_window_title() -> str:
    """Return the title of the currently focused (foreground) window (Windows)."""
    user32 = ctypes.windll.user32
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return ""
    length = user32.GetWindowTextLengthW(hwnd)
    buf = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buf, length + 1)
    return buf.value or ""

def extract_project_number(text: str) -> str:
    """Extract C###### from text; returns '' if not found."""
    if not text:
        return ""
    m = PROJECT_RE.search(text)
    return m.group(0) if m else ""

def get_active_project_number() -> str:
    """Project number from active window title."""
    return extract_project_number(get_foreground_window_title())

def is_tia_portal_foreground() -> bool:
    """True only when the foreground window belongs to Siemens TIA Portal."""
    user32 = ctypes.windll.user32
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return False

    process_id = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(process_id))
    title = get_foreground_window_title().lower()
    try:
        process = psutil.Process(process_id.value)
        process_name = process.name().lower()
        process_path = process.exe().lower()
        return (
            "siemens.automation.portal" in process_name
            or "siemens.automation.portal" in process_path
            or "tia portal" in title
        )
    except (psutil.Error, OSError):
        # A title fallback covers Portal variants whose executable cannot be read.
        return "tia portal" in title

def is_tia_portal_main_window() -> bool:
    """A TIA main window has both the Portal process and a path in its title."""
    return bool(
        is_tia_portal_foreground()
        and WINDOWS_PATH_RE.search(get_foreground_window_title())
    )

def open_or_activate_ixon_portal():
    """Delegate IXON-tab activation to the explicitly installed Edge extension."""
    subprocess.Popen([EDGE_PATH, IXON_EXTENSION_URL], close_fds=True)

# -------- UI: red border overlay per monitor --------
class ScreenBorder:
    """
    A mostly transparent fullscreen overlay that draws a red border around one monitor.
    Uses 'transparentcolor' on Windows to make the background click-through.
    """
    def __init__(self, master, screen, thickness=3, color="#cc0000"):
        self.master = master
        self.screen = screen
        self.thickness = thickness
        self.color = color

        self.win = tk.Toplevel(master)
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)

        # Fullscreen on this monitor rect
        self.win.geometry(f"{screen.width}x{screen.height}+{screen.x}+{screen.y}")

        # Make background transparent/click-through (Windows)
        self.transparent_color = "magenta"
        self.win.configure(bg=self.transparent_color)
        try:
            self.win.wm_attributes("-transparentcolor", self.transparent_color)
        except tk.TclError:
            pass

        self.canvas = tk.Canvas(self.win, highlightthickness=0, bd=0, bg=self.transparent_color)
        self.canvas.pack(fill="both", expand=True)

        self.visible = False
        self.drawn_style = None
        self.hide()

    def _draw_border(self):
        self.canvas.delete("all")
        w = self.screen.width
        h = self.screen.height
        t = self.thickness

        # 4 rectangles so interior remains transparent
        self.canvas.create_rectangle(0, 0, w, t, fill=self.color, outline="")
        self.canvas.create_rectangle(0, h - t, w, h, fill=self.color, outline="")
        self.canvas.create_rectangle(0, 0, t, h, fill=self.color, outline="")
        self.canvas.create_rectangle(w - t, 0, w, h, fill=self.color, outline="")

    def show(self):
        if not self.visible:
            self.win.deiconify()
            self.visible = True

    def hide(self):
        self.win.withdraw()
        self.visible = False

    def set_state(self, active: bool, blink: bool = False, blink_on: bool = True):
        """
        active=False -> hidden
        active=True & blink=False -> always visible
        active=True & blink=True  -> visible only when blink_on=True
        """
        if not active:
            self.hide()
            return

        style = (self.screen.width, self.screen.height, self.thickness, self.color)
        if self.drawn_style != style:
            self._draw_border()
            self.drawn_style = style
        if blink:
            if blink_on:
                self.show()
            else:
                self.hide()
        else:
            self.show()

# -------- Banner per monitor --------
class Banner:
    def __init__(self, master, screen):
        self.master = master
        self.screen = screen
        self.moved_right = False
        self.click_time = None

        # Border thickness: +2px when monitor is > 2560x1440
        thickness = 3
        if self.screen.width > 2560 and self.screen.height > 1440:
            thickness += 2
        self.border = ScreenBorder(master, screen, thickness=thickness, color="#cc0000")

        width, height = 1, 1
        x_center = screen.x + (screen.width) // 2
        y_top = screen.y

        self.top = tk.Toplevel(master)
        self.top.geometry(f"{width}x{height}+{x_center}+{y_top}")
        self.top.overrideredirect(True)
        self.top.attributes("-topmost", True)
        self.transparent_color = "magenta"
        self.top.configure(bg=self.transparent_color)
        try:
            self.top.wm_attributes("-transparentcolor", self.transparent_color)
        except tk.TclError:
            pass

        font_size = 20 if self.screen.height > 1440 else 12
        self.font = tkfont.Font(family="Helvetica", size=font_size)
        self.canvas = tk.Canvas(
            self.top, highlightthickness=0, bd=0, bg=self.transparent_color
        )
        self.canvas.pack(fill="both", expand=True)
        self.banner_width = width
        self.banner_height = height
        self.banner_style = None

        self.canvas.bind("<Button-1>", self.banner_click_left)
        self.canvas.bind("<Button-3>", self.banner_click_right)
        self.canvas.bind("<Double-1>", self.restart_script)

        self.UpdateBanner()

    def restart_script(self, event=None):
        restart_application(self.master)

    def banner_click_left(self, event):
        if self.click_time and (datetime.datetime.now() - self.click_time).total_seconds() < 0.3:
            self.restart_script(event)
            return

        self.click_time = datetime.datetime.now()
        self.master.after(300, self.process_single_click)

    def process_single_click(self):
        if (datetime.datetime.now() - self.click_time).total_seconds() >= 0.3:
            width = self.banner_width
            height = self.banner_height
            if not self.moved_right:
                x_center = self.screen.x + (self.screen.width - width) - 300
                y_top = self.screen.y
                self.top.geometry(f"{width}x{height}+{x_center}+{y_top}")
            else:
                x_center = self.screen.x + (self.screen.width - width) // 2
                y_top = self.screen.y
                self.top.geometry(f"{width}x{height}+{x_center}+{y_top}")

            self.moved_right = not self.moved_right

    def _draw_rounded_rectangle(self, width, height, radius, color):
        """Draw a pill-shaped banner while leaving its corners transparent."""
        self.canvas.create_rectangle(radius, 0, width - radius, height, fill=color, outline="")
        self.canvas.create_rectangle(0, radius, width, height - radius, fill=color, outline="")
        self.canvas.create_arc(0, 0, radius * 2, radius * 2, start=90, extent=90, fill=color, outline="")
        self.canvas.create_arc(width - radius * 2, 0, width, radius * 2, start=0, extent=90, fill=color, outline="")
        self.canvas.create_arc(width - radius * 2, height - radius * 2, width, height, start=270, extent=90, fill=color, outline="")
        self.canvas.create_arc(0, height - radius * 2, radius * 2, height, start=180, extent=90, fill=color, outline="")

    def set_banner(self, text, background, foreground="#202020"):
        """Render the banner only when its visible state has changed."""
        style = (text, background, foreground)
        if self.banner_style == style:
            return

        horizontal_padding = 18
        vertical_padding = 7
        self.banner_width = self.font.measure(text) + horizontal_padding * 2
        self.banner_height = self.font.metrics("linespace") + vertical_padding * 2
        radius = min(self.banner_height // 2, 16)

        self.canvas.config(width=self.banner_width, height=self.banner_height)
        self.canvas.delete("all")
        self._draw_rounded_rectangle(self.banner_width, self.banner_height, radius, background)
        self.canvas.create_text(
            self.banner_width // 2,
            self.banner_height // 2,
            text=text,
            font=self.font,
            fill=foreground,
        )
        self.banner_style = style

    def position_banner(self):
        """Keep the pill aligned at the top centre or user-selected right side."""
        width = self.banner_width
        height = self.banner_height
        if not self.moved_right:
            x_center = self.screen.x + (self.screen.width - width) // 2
            y_top = self.screen.y
            self.top.geometry(f"{width}x{height}+{x_center}+{y_top}")
        else:
            x_center = self.screen.x + (self.screen.width - width) - 300
            y_top = self.screen.y
            self.top.geometry(f"{width}x{height}+{x_center}+{y_top}")

    def restore_overlay(self):
        """Reassert and redraw this banner after a Windows display hiccup."""
        try:
            if not self.top.winfo_exists() or not self.canvas.winfo_exists():
                return False

            self.top.deiconify()
            self.top.attributes("-topmost", True)
            self.top.lift()
            if not self.top.winfo_ismapped():
                return False

            # Force a fresh Canvas paint: a mapped window can occasionally lose
            # its drawn contents after a monitor/DPI change without being closed.
            if self.banner_style:
                style = self.banner_style
                self.banner_style = None
                self.set_banner(*style)
            self.position_banner()
            return self.border.win.winfo_exists() and self.border.canvas.winfo_exists()
        except tk.TclError:
            return False

    def UpdateBanner(self):
        # Banner blink (red/white) each second
        blink_colors = ['red', 'white']
        blink_on = (datetime.datetime.now().second % 2 != 0)  # True/False

        status = self.master.ixon_status
        vpn_active = status["vpn_active"]
        lan_200_connections = status["lan_200_connections"]

        if vpn_active:
            active_proj = status["active_project"]
            ixon_proj = extract_project_number(status["connected_client"])

            # Only TIA Portal's path-bearing main window can trigger a blink.
            # This deliberately excludes TIA popups, whose title normally has
            # no project path and therefore no reliable project context.
            different_projects = bool(ixon_proj and active_proj and ixon_proj != active_proj)
            missing_project_on_one_side = bool(ixon_proj) != bool(active_proj)
            mismatch = status["is_tia_main_window"] and (
                different_projects or missing_project_on_one_side
            )

            if lan_200_connections:
                connections = ", ".join(f"{name}: {address}" for name, address in lan_200_connections)
                self.set_banner(
                    f"WARNING: IXON ACTIVE + LAN 192.168.200.x ({connections}) - {status['connected_client']}",
                    "#ff9900" if blink_on else "#ffdddd",
                )
                self.border.color = "#ff8c00"
            else:
                self.set_banner(f"VPN ACTIVE - {status['connected_client']}", blink_colors[blink_on])
                self.border.color = "#cc0000"

            # Border: on when active, blink only on mismatch
            # bij mismatch: 3x dikte + knipperen
            base = 3 + (2 if (self.screen.width > 2560 and self.screen.height > 1440) else 0)
            if mismatch:
                self.border.thickness = base * 2
                self.border.set_state(True, blink=True, blink_on=blink_on)
            else:
                # Restore the normal border thickness for this screen.
                self.border.thickness = base
                self.border.set_state(True, blink=False, blink_on=True)

            self.master.after(1000, self.UpdateBanner)
        else:
            if lan_200_connections:
                ip_address = lan_200_connections[0][1]
                self.set_banner(
                    f"Connected to 200.0 network with IP address {ip_address}",
                    "#e4f6e8",
                    "#28623d",
                )
            else:
                self.set_banner("Not active", "#ffffff")
            self.border.set_state(False)

            self.master.after(10000, self.UpdateBanner)

        self.position_banner()

    def banner_click_right(self, event):
        open_or_activate_ixon_portal()

# -------- IXON VPN detection + client extraction --------
def get_ixon_network_state(vpn_adapter_name):
    """Read all adapter data once and return IXON plus conflicting LAN state."""
    adapters = psutil.net_if_addrs()
    adapter_stats = psutil.net_if_stats()
    vpn_status = adapter_stats.get(vpn_adapter_name)
    vpn_active = vpn_adapter_name in adapters and vpn_status is not None and vpn_status.isup

    connections = []
    for adapter_name, addresses in adapters.items():
        if adapter_name.lower() == vpn_adapter_name.lower():
            continue
        status = adapter_stats.get(adapter_name)
        if status is None or not status.isup:
            continue
        for address in addresses:
            if address.family != 2:  # socket.AF_INET
                continue
            try:
                if ipaddress.ip_address(address.address) in LAN_200_NETWORK:
                    connections.append((adapter_name, address.address))
            except ValueError:
                continue
    return vpn_active, connections

def get_connected_client():
    log_path = r"C:\ProgramData\IXON\VPN Client\Logs"
    try:
        log_files = [f for f in os.listdir(log_path) if f.endswith(".log")]
        if not log_files:
            return "Unknown client"

        latest_log = max(log_files, key=lambda f: os.path.getctime(os.path.join(log_path, f)))

        client_pattern = re.compile(r'Name:\s+(.*?)(?:\r\n|\n)', re.DOTALL)
        with open(os.path.join(log_path, latest_log), 'r', errors="ignore") as file:
            lines = file.readlines()
            for line in reversed(lines):
                match = client_pattern.search(line)
                if match:
                    return match.group(1).strip()
    except Exception:
        pass

    return "Unknown client"

def get_foreground_alert_context():
    """Collect the active project and main-window flag once for every cycle."""
    return {
        "active_project": get_active_project_number(),
        "is_tia_main_window": is_tia_portal_main_window(),
    }

def read_ixon_status(previous_status):
    """Build the one shared status snapshot consumed by every screen banner."""
    vpn_active, lan_200_connections = get_ixon_network_state("IXON")
    connected_client = ""
    active_project = ""
    is_tia_main_window = False

    if vpn_active:
        connected_client = previous_status.get("connected_client", "")
        if not previous_status.get("vpn_active"):
            connected_client = get_connected_client()
        context = get_foreground_alert_context()
        active_project = context["active_project"]
        is_tia_main_window = context["is_tia_main_window"]

    return {
        "vpn_active": vpn_active,
        "lan_200_connections": lan_200_connections,
        "connected_client": connected_client,
        "active_project": active_project,
        "is_tia_main_window": is_tia_main_window,
    }

def refresh_ixon_status(root):
    """Refresh shared state once, irrespective of the number of monitors."""
    root.ixon_status = read_ixon_status(root.ixon_status)
    delay = 1000 if root.ixon_status["vpn_active"] else 10000
    root.after(delay, refresh_ixon_status, root)

def create_banners(master, screens):
    return [Banner(master, screen) for screen in screens]

def get_monitor_signature():
    """Stable representation of the current desktop layout."""
    return tuple(sorted(
        (screen.x, screen.y, screen.width, screen.height, getattr(screen, "name", ""))
        for screen in get_monitors()
    ))

def restart_application(root, reason=""):
    """Start a clean replacement process, then immediately stop this one."""
    try:
        subprocess.Popen([sys.executable, os.path.abspath(sys.argv[0])], close_fds=True)
    finally:
        try:
            root.destroy()
        finally:
            os._exit(0)

def watch_monitor_layout(root, previous_signature):
    """Restart to rebuild all Tk overlays whenever Windows changes monitor layout."""
    try:
        current_signature = get_monitor_signature()
    except Exception:
        restart_application(root, "Unable to read monitor layout")
        return

    if current_signature != previous_signature:
        restart_application(root, "Monitor layout changed")
        return

    root.after(2000, watch_monitor_layout, root, previous_signature)

def watch_banner_windows(root):
    """Repair banner drawing/topmost state; restart if a Tk window was lost."""
    for banner in root.banners:
        if not banner.restore_overlay():
            restart_application(root, "Banner window was lost")
            return
    root.after(5000, watch_banner_windows, root)

def main():
    root = tk.Tk()
    root.title('IXON status')
    root.withdraw()
    root.overrideredirect(True)

    root.ixon_status = read_ixon_status({"vpn_active": False})
    status_delay = 1000 if root.ixon_status["vpn_active"] else 10000
    root.after(status_delay, refresh_ixon_status, root)

    screens = get_monitors()
    root.banners = create_banners(root, screens)

    # A screen change can also surface as a Tcl callback error; recover by
    # replacing the process rather than leaving a broken or missing overlay.
    root.report_callback_exception = lambda *_: restart_application(root, "Tk callback error")
    sys.excepthook = lambda *_: restart_application(root, "Unhandled error")
    root.after(2000, watch_monitor_layout, root, get_monitor_signature())
    root.after(5000, watch_banner_windows, root)

    root.mainloop()

if __name__ == "__main__":
    main()
