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
    
    with open(RADIOS_FILE, 'r') as f:
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
    tg_a = input("Enter Target Talkgroup (e.g., Tactical TG): ").strip()
    tg_b = input("Enter Second Talkgroup to check (e.g., Dispatch TG): ").strip()
    filter_date = input("Enter Date to scan (YYYY/MM/DD) or type 'ALL': ").strip()

    print(f"\nScanning logs for correlation between {tg_a} and {tg_b}...")

    rids_on_tg_a = set()
    clear_hits = []

    # Regex to extract: Date, Time, Call Type, TG, and RID
    pattern = re.compile(r"(\d{4}/\d{2}/\d{2})\s+(\d{2}:\d{2}:\d{2}).*?(Enc Group call|Group call|P-Group call); TG=(\d+).*?RID=(\d+)")

    with open(LOG_FILE, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            match = pattern.search(line)
            if match:
                date, timestamp, call_type, tg, rid = match.groups()
                
                if tg == tg_a:
                    rids_on_tg_a.add(rid)
                
                if tg == tg_b:
                    if filter_date.upper() == "ALL" or date == filter_date:
                        if "Enc" not in call_type:
                            clear_hits.append({
                                'date': date,
                                'time': timestamp,
                                'rid': rid,
                                'alias': aliases.get(rid, "No Alias")
                            })

    # 2. Filter hits: Only keep TG_B hits from units seen on TG_A
    final_matches = [h for h in clear_hits if h['rid'] in rids_on_tg_a]

    # 3. Generate Unique Filename
    now = datetime.now()
    now_ts = now.strftime("%Y-%m-%d_%H-%M")
    filename = f"correlation_{tg_a}_to_{tg_b}_{now_ts}.txt"
    full_path = os.path.join(SCRIPT_DIR, filename)

    # 4. Prepare Output Content
    output_lines = []
    if not final_matches:
        msg = f"\nNo units from TG {tg_a} were found using clear voice on TG {tg_b} on {filter_date}."
        output_lines.append(msg)
    else:
        matched_rids = sorted(list(set(h['rid'] for h in final_matches)))
        output_lines.append(f"\nSUCCESS: Found {len(matched_rids)} cross-over units.")
        unit_summary = [f"{rid} ({aliases.get(rid, 'No Alias')})" for rid in matched_rids]
        output_lines.append(f"Units identified: {', '.join(unit_summary)}")
        output_lines.append("-" * 80)
        output_lines.append(f"{'DATE':<12} {'TIME':<10} {'RADIO ID':<10} {'ALIAS':<25} {'STATUS'}")
        output_lines.append("-" * 80)
        for match in final_matches:
            output_lines.append(f"{match['date']:<12} {match['time']:<10} {match['rid']:<10} {match['alias']:<25} Clear Voice")
        output_lines.append("-" * 80)
        output_lines.append(f"Found {len(final_matches)} total clear-voice transmissions.")

    # 5. Add execution timestamp to the end of the file
    execution_time = now.strftime("%Y/%MM/%DD at %H:%M:%S")
    output_lines.append(f"\nReport generated on: {execution_time}")

    # 6. Print results and save
    with open(full_path, "w", encoding='utf-8') as out_file:
        for line in output_lines:
            print(line)
            out_file.write(line + "\n")

    print(f"\nResults saved to: {full_path}")
    input("\nAnalysis Complete. Press Enter to close this window...")

if __name__ == "__main__":
    analyze_correlation()