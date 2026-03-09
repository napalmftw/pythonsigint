# Fire Dispatch AI Transcriber & Telegram Alerter
# Created by: David John Pickard
#
# DESCRIPTION:
# This script is designed to be called by TwoToneDetect (TTD) when a fire tone is found.
# It waits for the audio file to be finalized, transcribes the dispatch using the 
# Faster-Whisper AI model, applies phonetic corrections for computer-aided dispatch (Locution),
# and sends the transcript and audio file to a designated Telegram bot.
#
# USAGE:
# 1. Place this script in your TTD folder.
# 2. Update 'TOKEN', 'CHAT_ID', and 'AUDIO_DIR' in the configuration section.
# 3. Configure TTD to run this script as an 'alert_command':
#    python tg_alert.py "[description]" "[mp3]"
# -----------------------------------------------------------------------------------

import sys
import os
import requests
import time
import re
import random
from datetime import datetime
from faster_whisper import WhisperModel

# --- CONFIGURATION ---
TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
CHAT_ID = "YOUR_TELEGRAM_CHAT_ID"
AUDIO_DIR = r"C:\Path\To\Your\TTD\audio"
MAX_WAIT = 120 

# Initialize AI Model (Base model provides good balance of speed and accuracy)
print("Loading AI Transcription Model...")
model = WhisperModel("base", device="cpu", compute_type="int8")
# ---------------------

def fix_locution_dispatch(text):
    """Clean up computer-generated dispatch errors and force proper capitalization."""
    # 1. Fix Time: Updated regex to handle 3 or 4 digits (e.g., 861 hours -> 8:61)
    text = re.sub(r'(\d{1,2})[- ](\d{2})\s*hours', r'\1:\2', text, flags=re.IGNORECASE)
    
    # 2. Fix Unit Numbers (e.g., 15-11 -> 1511)
    text = re.sub(r'(\d{2})-(\d{2})', r'\1\2', text)
    
    # 3. Comprehensive Phonetic Corrections (Original List Preserved)
    corrections = {
        "ten four": "10-4", "signal 37": "Signal 37 (Any Messages?)",
        "merrill ville": "Merrillville", "cereville": "Schererville",
        "francescan": "Franciscan Health", "6 person": "Sick Person",
        "timeout": "Time Out", "cesar": "Seizure", "pabahawk": "Tomahawk",
        "fjprk": "St John Truck", "ground point": "Crown Point",
        "hovered": "Hobart", "for street": "Fir Street",
        "high mountain": "Time out", "referred": "refer",
        "MTC": "MDC", "dire": "Dyer", "6%": "Sick Person",
        "test pain": "Chest Pain", "6th person": "Sick Person",
        "D.R.I.S": "Drive:", "6-person": "Sick Person", "begin": "beacon",
        "multimor": "Baltimore", "test pane": "chest pain", "drives": "drive",
        "Cherville": "Schererville", "Ambul of Art": "Boulevard", "Drys": "Drive", 
        "Gas League": "Gas Leak", "polaski": "Pulaski", "Chromatic injury": "Traumatic Injury", 
        "Katalba": "Catalpa", "Dwaygan": "Wiggins", "hard problems": "heart problems", 
        "back pane": "back pain", "medicine street": "Madison Street","soul avenue": "Sohl Avenue", 
        "monster": "Munster", "six percent": "Sick Person", "glum": "Plum", "Chairvale": "Schererville",
        "st anthony": "Franciscan Health", "saint anthony": "Franciscan Health", 
        "melting": "Melton", "epidontinal pain": "Abdominal Pain", "brode": "Road"
    }
    
    for misheard, correct in corrections.items():
        text = re.sub(rf'\b{misheard}\b', correct, text, flags=re.IGNORECASE)

    # 4. Expanded Proper Noun List (Forces Capitalization)
    proper_nouns = [
        "Street", "Avenue", "Road", "Drive", "Court", "Lane", "North", "South", "East", "West", 
        "Boulevard", "Place", "Way", "Terrace", "Circle", "Highway", "St", "Ave", "Rd", "Dr", 
        "Ln", "Ct", "Blvd", "Main", "Engine", "Ambulance", "Station", "Unit"
    ]
    for word in proper_nouns:
        text = re.sub(rf'\b{word}\b', word, text, flags=re.IGNORECASE)

    # 5. Sentence Case Polisher
    parts = re.split('([.!?] *)', text)
    processed_parts = []
    for p in parts:
        if p and any(c.isalpha() for c in p):
            match = re.search(r'[a-zA-Z]', p)
            if match:
                idx = match.start()
                p = p[:idx] + p[idx].upper() + p[idx+1:]
        processed_parts.append(p)
        
    return "".join(processed_parts).strip()

def send_to_telegram():
    if len(sys.argv) < 3: return
    raw_name = sys.argv[1]
    mp3_filename = os.path.basename(sys.argv[2])
    full_mp3_path = os.path.join(AUDIO_DIR, mp3_filename)
    now = datetime.now().strftime("%H:%M:%S")

    # 1. Wait for file stability (TTD to finish writing)
    file_ready = False
    start_time = time.time()
    while (time.time() - start_time) < MAX_WAIT:
        if os.path.exists(full_mp3_path) and os.path.getsize(full_mp3_path) > 1024:
            size_1 = os.path.getsize(full_mp3_path)
            time.sleep(3) 
            if size_1 == os.path.getsize(full_mp3_path):
                file_ready = True
                break
        time.sleep(2)

    dept_name = mp3_filename.split('_202')[0].replace('_', ' ')

    # 2. AI TRANSCRIPTION (Staggered to prevent CPU resource clashes)
    transcript = "Transcription unavailable."
    if file_ready:
        time.sleep(random.uniform(2, 6)) 
        for attempt in range(7):
            try:
                print(f"Transcribing {dept_name}...")
                segments, _ = model.transcribe(full_mp3_path, beam_size=5)
                raw_text = " ".join([segment.text for segment in segments])
                transcript = fix_locution_dispatch(raw_text)
                break 
            except Exception as e:
                print(f"Transcription retry {attempt+1}: {e}")
                time.sleep(3)

    # 3. Send Telegram Message
    message_text = f"🚨 **FIRE DISPATCH: {dept_name}**\n🕒 **Time:** {now}\n📝 **Transcript:**\n_{transcript.strip()}_"
    requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", data={"chat_id": CHAT_ID, "text": message_text, "parse_mode": "Markdown"})

    # 4. Upload Audio and Persistent Delete Loop (Handles Windows File Locks)
    if file_ready:
        try:
            with open(full_mp3_path, 'rb') as audio:
                r = requests.post(f"https://api.telegram.org/bot{TOKEN}/sendAudio", data={"chat_id": CHAT_ID}, files={"audio": audio})
            
            if r.status_code == 200:
                print(f"Upload success. Attempting cleanup of {mp3_filename}...")
                for d_attempt in range(10):
                    try:
                        os.remove(full_mp3_path)
                        print(f"Successfully deleted {mp3_filename}")
                        break
                    except PermissionError:
                        time.sleep(2)
            else:
                print(f"Upload failed. Status: {r.status_code}")
        except Exception as e:
            print(f"Cleanup Error: {e}")

if __name__ == "__main__":
    send_to_telegram()
