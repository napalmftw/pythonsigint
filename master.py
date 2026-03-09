# Master Network Intelligence & Log Rotation Tool for DSDPlus
# Created by: David K3FTW
#
# DESCRIPTION:
# This script parses DSDPlus event logs to generate a daily "Intelligence Report."
# It identifies:
#   1. A chronological timeline of all encrypted transmissions.
#   2. "Network Deltas" - New Talkgroups and Radio IDs seen since the last baseline.
#   3. Automatic mapping of IDs to aliases using DSDPlus.groups and DSDPlus.radios.
#
# LOG ROTATION:
# Every Sunday, the script automatically archives the previous week's baseline (.old file)
# with a timestamp and establishes a new baseline from the current activity log.
#
# USAGE:
# 1. Place this script in your DSDPlus folder.
# 2. Update the 'dsd_path' variable below if your logs are in a specific sub-folder.
# 3. Run: python master.py
# -----------------------------------------------------------------------------------

import os
import shutil
import re
from datetime import datetime
from collections import defaultdict

# --- CONFIGURATION ---
# Replace with your actual DSDPlus directory path
dsd_path = r'C:\Path\To\Your\DSDPlus\Folder'
# Talkgroups to ignore in the "New Spotted" reports (e.g., data/status channels)
IGNORE_TGS = {'0'} 
# ---------------------

script_dir = os.path.dirname(os.path.abspath(__file__))
event_file = os.path.join(script_dir, 'CC-DSDPlus.event')
old_event_file = event_file + ".old"
groups_file = os.path.join(script_dir, 'DSDPlus.groups')
radios_file = os.path.join(script_dir, 'DSDPlus.radios')

current_date_str = datetime.now().strftime('%Y-%m-%d')
report_file = os.path.join(script_dir, f"Intel_Report_{current_date_str}.txt")

def load_aliases():
    """Maps IDs to user-defined aliases from DSDPlus data files."""
    tg_map, rid_map = {}, {}
    if os.path.exists(groups_file):
        with open(groups_file, 'r', encoding='utf-8', errors='replace') as f:
            for line in f:
                parts = [p.strip() for p in line.split(',')]
                if len(parts) >= 8: tg_map[parts[2]] = parts[7].strip('"')
    if os.path.exists(radios_file):
        with open(radios_file, 'r', encoding='utf-8', errors='replace') as f:
            for line in f:
                parts = [p.strip() for p in line.split(',')]
                if len(parts) >= 9: rid_map[parts[3]] = parts[8].strip('"')
    return tg_map, rid_map

def parse_logs(file_path):
    """Scans logs for unique Talkgroups, Radio IDs, and encrypted traffic."""
    tgs, rids = {}, {}
    enc_calls = []
    if not os.path.exists(file_path): return tgs, rids, enc_calls
    
    # Standard P25/DMR Group Call Regex
    pattern = re.compile(r"(\d{4}/\d{2}/\d{2})\s+(\d{2}:\d{2}:\d{2}).*?(Enc Group call|Group call|P-Group call); TG=(\d+).*?RID=(\d+)")
    
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            match = pattern.search(line)
            if match:
                date, time, ctype, tg, rid = match.groups()
                if tg in IGNORE_TGS: continue
                
                if tg not in tgs: tgs[tg] = f"{date} {time}"
                if rid not in rids: rids[rid] = f"{date} {time}"
                
                if "Enc" in ctype:
                    enc_calls.append({
                        'dt': datetime.strptime(f"{date} {time}", '%Y/%m/%d %H:%M:%S'),
                        'line': f"[{date} {time}] TG: {tg:<6} RID: {rid:<8} (ENCRYPTED)"
                    })
    return tgs, rids, enc_calls

def rotate_logs():
    """Archives the old baseline and sets a new one every Sunday."""
    # 6 = Sunday
    if datetime.now().weekday() == 6:
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M')
        archived_name = f"CC-DSDPlus.event.old.{timestamp}.archived"
        archived_path = os.path.join(script_dir, archived_name)
        
        if os.path.exists(old_event_file):
            print(f"--- Archiving previous baseline: {archived_name} ---")
            os.rename(old_event_file, archived_path)
            
        print("--- Establishing new weekly baseline ---")
        shutil.copy2(event_file, old_event_file)
    else:
        print("--- Skipping weekly rotation (Not Sunday) ---")

def run_report():
    """Main execution loop for Intel Report generation."""
    print(f"--- Generating Network Intel Report ---")
    tg_names, rid_names = load_aliases()
    old_tgs, old_rids, _ = parse_logs(old_event_file)
    new_tgs, new_rids, enc_entries = parse_logs(event_file)

    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(f"--- SYSTEM NETWORK INTELLIGENCE REPORT ---\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        # Section 1: Encrypted Hits
        f.write("--- ENCRYPTED TIMELINE (Recent First) ---\n")
        enc_entries.sort(key=lambda x: x['dt'], reverse=True)
        for entry in enc_entries:
            f.write(entry['line'] + "\n")
        if not enc_entries: f.write("  No encrypted traffic found.\n")

        # Section 2: New Talkgroups (Comparison)
        f.write(f"\n--- NEW CHANNELS SPOTTED ---\n")
        new_ch_count = 0
        for tg in sorted(list(set(new_tgs.keys()) - set(old_tgs.keys())), key=int):
            f.write(f"  [{new_tgs[tg]}] {tg_names.get(tg, 'NEW TALKGROUP'):<20} (TG: {tg})\n")
            new_ch_count += 1
        if new_ch_count == 0: f.write("  No new talkgroups identified.\n")

        # Section 3: New Radio IDs (Comparison)
        f.write(f"\n--- NEW RADIO IDS SPOTTED ---\n")
        new_rid_count = 0
        for rid in sorted(list(set(new_rids.keys()) - set(old_rids.keys())), key=int):
            f.write(f"  [{new_rid_count+1:02}] {rid_names.get(rid, 'NEW UNIT'):<20} (RID: {rid})\n")
            new_rid_count += 1
        if new_rid_count == 0: f.write("  No new Radio IDs identified.\n")

    print(f"Success! Report saved as: {os.path.basename(report_file)}")
    
    # Process log rotation
    rotate_logs()

if __name__ == "__main__":
    run_report()
    input("\nProcess Complete. Press Enter to close...")