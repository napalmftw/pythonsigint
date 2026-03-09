import os
import shutil
import re
from datetime import datetime
from collections import defaultdict

# --- CONFIGURATION ---
dsd_path = r'C:\Users\HP Elitedesk 800\Downloads\DSDPlusFull'
# ---------------------

script_dir = os.path.dirname(os.path.abspath(__file__))
event_file = os.path.join(script_dir, 'CC-DSDPlus.event')
old_event_file = event_file + ".old"
groups_file = os.path.join(script_dir, 'DSDPlus.groups')
radios_file = os.path.join(script_dir, 'DSDPlus.radios')

current_date_str = datetime.now().strftime('%Y-%m-%d')
report_file = os.path.join(script_dir, f"Intel_Report_{current_date_str}.txt")

IGNORE_TGS = {'240'}

def load_aliases():
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

def get_detailed_ids(filename):
    tgs, rids = {}, {}
    if not os.path.exists(filename): return tgs, rids
    with open(filename, 'r', encoding='utf-8', errors='replace') as f:
        for line in f:
            date_m = re.search(r'(\d{4}/\d{2}/\d{2})', line)
            tg_m = re.search(r'TG=(\d+)', line)
            rid_m = re.search(r'RID=(\d+)', line)
            date_val = date_m.group(1) if date_m else "Unknown"
            tg_val = tg_m.group(1) if tg_m else None
            if tg_val and tg_val not in IGNORE_TGS:
                if tg_val not in tgs: tgs[tg_val] = date_val
                if rid_m:
                    rid_val = rid_m.group(1)
                    if rid_val not in rids: rids[rid_val] = date_val
    return tgs, rids

def run_intel():
    print(f"Generating Forensic Intel Report for {current_date_str}...")
    
    # 1. Sync & Rotate
    for f_name in ['CC-DSDPlus.event', 'DSDPlus.groups', 'DSDPlus.radios']:
        src = os.path.join(dsd_path, f_name)
        dst = os.path.join(script_dir, f_name)
        if f_name == 'CC-DSDPlus.event' and os.path.exists(dst):
            if os.path.exists(old_event_file): os.remove(old_event_file)
            os.rename(dst, old_event_file)
        if os.path.exists(src): shutil.copy2(src, dst)

    tg_names, rid_names = load_aliases()
    old_tgs, old_rids = get_detailed_ids(old_event_file)
    new_tgs, new_rids = get_detailed_ids(event_file)
    
    enc_entries = []
    unid_times = defaultdict(list)

    # 2. Extract Data for Timeline and UNID Analysis
    with open(event_file, 'r', encoding='utf-8', errors='replace') as ev:
        for line in ev:
            d_m = re.search(r'(\d{4}/\d{2}/\d{2})', line)
            t_m = re.search(r'(\d{2}:\d{2}:\d{2})', line)
            tg_m = re.search(r'TG=(\d+)', line)
            rid_m = re.search(r'RID=(\d+)', line)
            
            if not d_m or not t_m or not tg_m: continue
            
            date, time, tg = d_m.group(1), t_m.group(1), tg_m.group(1)
            rid = rid_m.group(1) if rid_m else "Unknown"
            
            # Store Encrypted Hits
            if 'Enc Group call' in line and tg not in IGNORE_TGS:
                enc_entries.append({
                    'dt': f"{date} {time}",
                    'tg': tg,
                    'rid': rid,
                    'line': f"  [{date} {time}] {tg_names.get(tg, 'Unidentified'):<20} (TG:{tg:<5}) | Unit: {rid_names.get(rid, 'New'):<18} (RID:{rid})"
                })
            
            # Track 455* UNID Timestamps
            if rid.startswith('455'):
                unid_times[rid].append(f"{date} {time}")

    # 3. Write Report
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(f"--- LAKECOPS NETWORK INTELLIGENCE REPORT ---\n")
        f.write(f"REPORT GENERATED: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        # Newest First Encrypted Timeline
        f.write("--- ENCRYPTED TIMELINE (Newest First) ---\n")
        enc_entries.sort(key=lambda x: x['dt'], reverse=True)
        for entry in enc_entries:
            f.write(entry['line'] + "\n")
        if not enc_entries: f.write("  No encrypted traffic found.\n")

        # Network Deltas
        f.write(f"\n--- NEW CHANNELS SPOTTED ---\n")
        for tg in sorted(list(set(new_tgs.keys()) - set(old_tgs.keys())), key=int):
            f.write(f"  [{new_tgs[tg]}] {tg_names.get(tg, 'NEW TALKGROUP'):<20} (TG: {tg})\n")

        f.write(f"\n--- NEW RADIO IDS SPOTTED ---\n")
        for rid in sorted(list(set(new_rids.keys()) - set(old_rids.keys())), key=int):
            f.write(f"  [{new_rids[rid]}] {rid_names.get(rid, 'NEW UNIT'):<20} (RID: {rid})\n")

        # 455* Block Activity Summary
        f.write(f"\n--- 455* UNID ACTIVITY SUMMARY (First/Last Seen) ---\n")
        for rid in sorted(unid_times.keys()):
            times = unid_times[rid]
            f.write(f"  RID: {rid:<8} | First: {times[0]} | Last: {times[-1]} | Hits: {len(times)}\n")

    print(f"Report complete: {os.path.basename(report_file)}")

try: run_intel()
except Exception as e: print(f"Error: {e}")
input("\nForensic audit finished. Press Enter to exit...")