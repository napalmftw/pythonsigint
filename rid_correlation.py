# DSDPlus Radio ID Correlation & Tactical De-Masking Tool
# Created by: David K3FTW
#
# DESCRIPTION:
# This script analyzes DSDPlus event logs to identify "cross-over" units.
# It finds Radio IDs (RIDs) that have appeared on a tactical/encrypted 
# talkgroup and then cross-references them against clear-voice dispatch 
# channels to reveal their identity or routine assignments.
#
# "ALL" MODE (GLOBAL DE-MASKING):
# If you leave the prompts blank (just hit Enter), the script will:
#   1. Scan for EVERY RID seen using encryption.
#   2. Match them against EVERY clear-voice transmission in the log.
#   3. Output a comprehensive report of all tactical units spotted in the clear.
#
# USAGE:
# 1. Place this script in your DSDPlus folder.
# 2. Run: python rid_correlation.py
# 3. Enter specific Talkgroups to narrow the search, or hit Enter for a global scan.
# -----------------------------------------------------------------------------------

import re
import os
import sys
from datetime import datetime

# Get the directory where the script is located to avoid path errors
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Link the data files to the script's home folder
LOG_FILE = os.path.join(SCRIPT_DIR, "CC-DSDPlus.event")
RADIOS_FILE = os.path.join(SCRIPT_DIR, "DSDPlus.radios")

def load_radio_aliases():
    """Reads DSDPlus.radios and returns a dictionary of {RID: Alias}"""
    aliases = {}
    if not os.path.exists(RADIOS_FILE):
        return aliases
    
    # Line format: protocol, networkID, group, radio, priority, override, hits, timestamp, "alias"
    with open(RADIOS_FILE, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            if line.startswith(';') or not line.strip():
                continue
            parts = line.split(',')
            if len(parts) >= 9:
                rid = parts[3].strip()
                alias = parts[8].strip().strip('"')
                if alias:
                    aliases[rid] = alias
    return aliases

def analyze_correlation():
    print("--- DSDPlus Talkgroup Correlation Tool ---")
    
    if not os.path.exists(LOG_FILE):
        print(f"Error: {LOG_FILE} not found!")
        print(f"Looked in: {SCRIPT_DIR}")
        input("\nPress Enter to exit...")
        return

    # 1. Load Aliases and Get User Input
    aliases = load_radio_aliases()
    
    tg_a = input("Enter Target Talkgroup [Enter for ALL ENCRYPTED]: ").strip()
    tg_b = input("Enter Second Talkgroup [Enter for ALL CLEAR]: ").strip()
    filter_date = input("Enter Date to scan (YYYY/MM/DD) [Enter for ALL]: ").strip()

    # Determine search logic flags
    is_all_a = not tg_a
    is_all_b = not tg_b
    is_all_date = (not filter_date or filter_date.upper() == "ALL")

    search_desc_a = "ANY ENCRYPTED" if is_all_a else f"TG {tg_a}"
    search_desc_b = "ANY CLEAR" if is_all_b else f"TG {tg_b}"
    search_desc_date = "ALL DATES" if is_all_date else filter_date

    print(f"\nScanning logs for correlation: {search_desc_a} -> {search_desc_b} ({search_desc_date})...")

    rids_on_tg_a = set()
    clear_hits = []

    # Regex to extract: Date, Time, Call Type, TG, and RID
    pattern = re.compile(r"(\d{4}/\d{2}/\d{2})\s+(\d{2}:\d{2}:\d{2}).*?(Enc Group call|Group call|P-Group call); TG=(\d+).*?RID=(\d+)")

    with open(LOG_FILE, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            match = pattern.search(line)
            if match:
                date, timestamp, call_type, tg, rid = match.groups()
                
                # Identify Tactical/Encrypted RIDs (A Side)
                if is_all_a:
                    if "Enc" in call_type: # Catch any RID using encryption
                        rids_on_tg_a.add(rid)
                elif tg == tg_a:
                    rids_on_tg_a.add(rid)
                
                # Identify Clear Voice Transmissions (B Side)
                if (is_all_date or date == filter_date) and "Enc" not in call_type:
                    if is_all_b or tg == tg_b:
                        clear_hits.append({
                            'date': date,
                            'time': timestamp,
                            'rid': rid,
                            'tg': tg,
                            'alias': aliases.get(rid, "No Alias")
                        })

    # 2. Filter hits: Keep clear transmissions from units seen on the encrypted side
    final_matches = [h for h in clear_hits if h['rid'] in rids_on_tg_a]

    # 3. Generate Unique Filename with Timestamp
    now = datetime.now()
    now_ts = now.strftime("%Y-%m-%d_%H-%M")
    filename = f"correlation_{'ALL' if is_all_a else tg_a}_to_{'ALL' if is_all_b else tg_b}_{now_ts}.txt"
    full_path = os.path.join(SCRIPT_DIR, filename)

    # 4. Prepare Output Content
    output_lines = []
    if not final_matches:
        output_lines.append(f"\nNo units from {search_desc_a} were found using clear voice on {search_desc_b}.")
    else:
        matched_rids = sorted(list(set(h['rid'] for h in final_matches)))
        output_lines.append(f"\nSUCCESS: Found {len(matched_rids)} cross-over units.")
        
        # Build unit summary with aliases
        unit_summary = [f"{rid} ({aliases.get(rid, 'No Alias')})" for rid in matched_rids]
        output_lines.append(f"Units identified: {', '.join(unit_summary)}")
        
        output_lines.append("-" * 95)
        output_lines.append(f"{'DATE':<12} {'TIME':<10} {'TG':<6} {'RADIO ID':<10} {'ALIAS':<30} {'STATUS'}")
        output_lines.append("-" * 95)
        for match in final_matches:
            output_lines.append(f"{match['date']:<12} {match['time']:<10} {match['tg']:<6} {match['rid']:<10} {match['alias']:<30} Clear Voice")
        output_lines.append("-" * 95)
        output_lines.append(f"Found {len(final_matches)} total clear-voice transmissions.")

    output_lines.append(f"\nReport generated on: {now.strftime('%Y/%m/%d at %H:%M:%S')}")

    # 5. Print results to console and save to unique file
    with open(full_path, "w", encoding='utf-8') as out_file:
        for line in output_lines:
            print(line)
            out_file.write(line + "\n")

    print(f"\nResults saved to: {full_path}")
    input("\nAnalysis Complete. Press Enter to close this window...")

if __name__ == "__main__":
    analyze_correlation()
