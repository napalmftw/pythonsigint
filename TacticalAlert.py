# Live Tactical Alert Tool for DSDPlus
# Created by: David K3FTW
#
# DESCRIPTION:
# This script monitors a DSDPlus event log in real-time and sends an 
# instant Telegram notification whenever encrypted activity is detected.
#
# USAGE:
# 1. Update the BOT_TOKEN and CHAT_ID with your Telegram bot credentials.
# 2. Set the 'live_event_file' path to your CC-DSDPlus.event file.
# 3. Run: python alerter.py
# -----------------------------------------------------------------------------------

import os
import time
import re
import requests

# --- CONFIGURATION ---
# 1. Your Telegram Credentials
BOT_TOKEN = 'YOUR_BOT_TOKEN_HERE'
CHAT_ID = 'YOUR_CHAT_ID_HERE'

# 2. Path to the LIVE log in your DSDPlus folder
live_event_file = r'C:\Path\To\Your\DSDPlus\CC-DSDPlus.event'

# 3. Filter Configuration (Talkgroups to ignore, e.g., routine data/jail traffic)
IGNORE_TGS = ['0'] 
# ---------------------

def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": f"🚨 TACTICAL ALERT: {message}"}
    try:
        requests.post(url, data=payload, timeout=5)
    except Exception as e:
        print(f"Failed to send Telegram: {e}")

def watch_log():
    print(f"Live Watcher Active. Monitoring for Encrypted Activity...")
    
    if not os.path.exists(live_event_file):
        print(f"ERROR: Cannot find {live_event_file}. Check your paths.")
        return

    # Open the file and jump to the end so we only see NEW activity
    with open(live_event_file, 'r', encoding='utf-8', errors='replace') as f:
        f.seek(0, os.SEEK_END)
        
        while True:
            line = f.readline()
            if not line:
                time.sleep(0.5) # Check for new lines every half-second
                continue

            # Scan for Encrypted calls
            if re.search(r'enc group call', line, re.IGNORECASE):
                tg_m = re.search(r'TG=(\d+)', line)
                if tg_m:
                    tg = tg_m.group(1)
                    
                    # Apply the Talkgroup Filter
                    if tg in IGNORE_TGS:
                        continue
                    
                    rid_m = re.search(r'RID=(\d+)', line)
                    rid = rid_m.group(1) if rid_m else "Unknown"
                    
                    # Extract timestamp from the log line
                    time_m = re.search(r'(\d{2}:\d{2}:\d{2})', line)
                    t_stamp = time_m.group(1) if time_m else "NOW"
                    
                    alert_msg = f"Encrypted traffic on TG {tg} by RID {rid} at {t_stamp}"
                    print(f"Alert Triggered: {alert_msg}")
                    send_telegram(alert_msg)

if __name__ == "__main__":
    try:
        watch_log()
    except KeyboardInterrupt:

        print("\nWatcher stopped by user.")
