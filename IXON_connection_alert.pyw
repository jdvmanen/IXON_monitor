#Tool to monitor IXON adapter connection state. It shows a banner on top of your screen with the IXON adapter status. It shows the client device name in the banner as well.

# How to install
# Make sure your IXON network adapter is called 'IXON'.
# winget install python
# pip install tkinter
# pip install psutil
# place script (with extension .pyw) in shell:startup
# How to use
# Shows a little 'Not actief' (White) indicator on top of your screen if no IXON connection is active. shows up as soon as the IXON adapter is active with a banner red/white alterating. If you click on it, it moves 500 pixels to the right or to the left (to prevent something being behind the indicator that has to be read)

import tkinter as tk
import psutil
import os
import re

def is_vpn_active(vpn_adapter_name):
    adapters = psutil.net_if_addrs()

    if vpn_adapter_name in adapters:
        adapter_status = psutil.net_if_stats().get(vpn_adapter_name, None)
        if adapter_status is not None and adapter_status.isup:
            return True
    return False

def get_connected_client():
    log_path = "C:\\ProgramData\\IXON\\VPN Client\\Logs"
    # Search newest logfile
    log_files = [f for f in os.listdir(log_path) if f.endswith(".log")]
    latest_log = max(log_files, key=lambda f: os.path.getctime(os.path.join(log_path, f)))

    # Open the newest log and search for last row having 'Name:'
    client_pattern = re.compile(r'Name:\s+(.*?)(?:\r\n|\n)', re.DOTALL)
    with open(os.path.join(log_path, latest_log), 'r') as file:
        lines = file.readlines()
        for line in reversed(lines):
            match = client_pattern.search(line)
            if match:
                return match.group(1)
    return "Unknown client"

def on_click(event):
    global moved
    if not moved:
        root.geometry(f'+{(screen_width - root.winfo_reqwidth()) // 2 + 500}+0')
    else:
        root.geometry(f'+{(screen_width - root.winfo_reqwidth()) // 2}+0')
    moved = not moved

def update_window():
    global blink_color_index
    if is_vpn_active('IXON'):
        root.title('IXON active')
        connected_client = get_connected_client()
        status_label.config(text=f'IXON ACTIVE - {connected_client}', bg=blink_colors[blink_color_index])
        blink_color_index = 1 - blink_color_index  # Toggle between 0 en 1
    else:
        root.title('ixon not active')
        status_label.config(text='not active', bg='white')  # Empty textfield

    root.after(1000, update_window)  # Repeat every 1000 milliseconds

blink_color_index = 0
blink_colors = ['red', 'white']
moved = False

root = tk.Tk()
root.title('IXON Status')

# Show screen on top
root.attributes('-topmost', True)

# Hide taskbar buttons
root.overrideredirect(True)

# Center on homescreen
screen_width = root.winfo_screenwidth()
root.geometry(f'+{(screen_width - root.winfo_reqwidth()) // 2}+0')

# Add label to show status
status_label = tk.Label(root, text='', bg='lightgray')
status_label.pack(pady=0)

# Add click event to move screen
root.bind('<Button-1>', on_click)

# Start update function
update_window()

root.mainloop()
