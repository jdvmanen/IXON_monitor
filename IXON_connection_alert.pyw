#######################################################
# Tool to monitor IXON adapter connection state. It shows a banner on top of your screen with the IXON adapter status.
# 
#### How to install ####
# Make sure your IXON network adapter is called 'IXON'.
# winget install python
# pip install tkinter
# pip install psutil
# pip install screeninfo
# place script (with extension .pyw) in shell:startup


#### How to use ####
# Shows a little 'Niet actief' (White) indicator on top of your screen if no IXON connection is active.
# shows up as soon as the IXON adapter is active with a banner red/white alterating.
# If you click on it, it moves to the right or to the left (to prevent something
# being behind the indicator that has to be read)

import tkinter as tk
import psutil
import datetime
import os
import re
from screeninfo import get_monitors

class Banner:
    def __init__(self, master, screen):
        self.master = master
        self.screen = screen
        self.moved_right = False

        width, height = 1, 1
        x_center = screen.x + (screen.width) // 2
        y_top = screen.y

        self.top = tk.Toplevel(master)
        self.top.geometry(f"{width}x{height}+{x_center}+{y_top}")
        self.top.overrideredirect(True)
        self.top.attributes("-topmost", True)  # Make screen always on top

        self.frame = tk.Frame(self.top, bg="white")
        if (self.screen.height > 1440):
            self.label = tk.Label(self.frame, text="", font=("Helvetica", 20), bg="white")
        else:
            self.label = tk.Label(self.frame, text="", font=("Helvetica", 12), bg="white")

        self.label.pack(pady=0, padx=0)

        self.frame.pack()

        # Add a variable to track the previous state of the VPN
        self.previous_vpn_state = False
        self.connected_client = ""

        # Bind the function to clicking on the banner
        self.label.bind("<Button-1>", self.move_banner)

        # Start the UpdateBanner function every 1000 ms (1 second)
        self.UpdateBanner()

    def move_banner(self, event):
        width = self.label.winfo_reqwidth()
        height = self.label.winfo_reqheight()
        if not self.moved_right:
            x_center = self.screen.x + (self.screen.width - width) - 300
            y_top = self.screen.y
            self.top.geometry(f"{width}x{height}+{x_center}+{y_top}")
        else:
            x_center = self.screen.x + (self.screen.width - width) // 2
            y_top = self.screen.y
            self.top.geometry(f"{width}x{height}+{x_center}+{y_top}")

        # Toggle the movement status
        self.moved_right = not self.moved_right

    def UpdateBanner(self):
        blink_colors = ['red', 'white']
        blink_color_index = (datetime.datetime.now().second % 2 != 0)
        
        # Check if the VPN is active

        # Update the banner text based on the VPN status
        if is_vpn_active("IXON"):
            if not self.previous_vpn_state:
                self.connected_client = get_connected_client()
            self.label.config(text=f'VPN ACTIVE - {self.connected_client}')
            self.label.config(bg=blink_colors[blink_color_index]) 
            # Update the previous VPN state
            self.previous_vpn_state = True
                
            # Call the function again after 1000 ms (1 second)
            self.master.after(1000, self.UpdateBanner)
        else:
            self.label.config(text="Not active", bg='white')
            
            # Update the previous VPN state
            self.previous_vpn_state = False
            
            # Call the function again after 1000 ms (1 second)
            self.master.after(10000, self.UpdateBanner)

        # Adjust height based on the updated banner text
        width = self.label.winfo_reqwidth()
        height = self.label.winfo_reqheight()
        if not self.moved_right:
            x_center = self.screen.x + (self.screen.width - width) // 2
            y_top = self.screen.y
            self.top.geometry(f"{width}x{height}+{x_center}+{y_top}")
        else:
            x_center = self.screen.x + (self.screen.width - width) - 300
            y_top = self.screen.y
            self.top.geometry(f"{width}x{height}+{x_center}+{y_top}")


def is_vpn_active(vpn_adapter_name):
    adapters = psutil.net_if_addrs()

    if vpn_adapter_name in adapters:
        adapter_status = psutil.net_if_stats().get(vpn_adapter_name, None)
        if adapter_status is not None and adapter_status.isup:
            return True
    return False

def get_connected_client():
    log_path = "C:\\ProgramData\\IXON\\VPN Client\\Logs"
    # Look for the newest log file in the folder
    log_files = [f for f in os.listdir(log_path) if f.endswith(".log")]
    latest_log = max(log_files, key=lambda f: os.path.getctime(os.path.join(log_path, f)))

    # Open the newest log file and search for the last line with 'Name:'
    client_pattern = re.compile(r'Name:\s+(.*?)(?:\r\n|\n)', re.DOTALL)
    with open(os.path.join(log_path, latest_log), 'r') as file:
        lines = file.readlines()
        for line in reversed(lines):
            match = client_pattern.search(line)
            if match:
                return match.group(1)
    return "Unknown client"

def create_banners(master, screens):
    banners = [Banner(master, screen) for screen in screens]

def main():
    root = tk.Tk()
    root.title('IXON status')
    root.withdraw()
    root.overrideredirect(True)

    screens = get_monitors()

    create_banners(root, screens)

    root.mainloop()

if __name__ == "__main__":
    main()
