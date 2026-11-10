# IXON Monitor

Windows utility that shows an always-on-top IXON connection banner on every monitor. It highlights potentially unsafe routing situations and can activate an existing IXON Portal tab in Microsoft Edge.

## Features

- Shows IXON connection status and client name on every monitor.
- Warns when IXON and a direct `192.168.200.0/24` LAN connection are active simultaneously.
- Blinks the border only for a TIA Portal main window with a project-path title when the IXON and TIA project context is unsafe or incomplete.
- Rebuilds the overlays after monitor changes and runs a watchdog that repairs/restarts lost banner windows.
- Right-clicking the banner activates an existing `portal.ixon.cloud` tab through the included Edge extension, or opens the IXON devices portal when none exists.

## Install on a Windows PC

1. Install Python 3.13 or later.
2. Install dependencies:

   ```powershell
   py -3.13 -m pip install --user -r requirements.txt
   ```

3. Copy `IXON_connection_alert.pyw` to the user's Startup folder:

   ```text
   %APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
   ```

4. In Edge, open `edge://extensions`, turn on **Developer mode**, choose **Load unpacked**, and select the `edge-extension` folder.

The extension requires only the `tabs` permission. Its fixed local ID is `ebhkggkoccabjalpldedaffeljnjjkgd`; the Python tool uses this ID when the banner is right-clicked.

## Usage

- Left-click the banner to move it between centre and right.
- Double-click the banner to restart the monitor tool.
- Right-click the banner to activate the existing IXON Portal tab in Edge.

## Notes

- The IXON adapter must be named `IXON`.
- `tkinter` is included with the normal Windows Python installer and is not a pip dependency.
- Python bytecode caches are ignored by Git.
