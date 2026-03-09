🛰️ LakeOps Intelligence Dashboard
A real-time P25 radio intelligence suite for DSDPlus, designed to provide high-resolution tactical awareness. This dashboard parses .event logs to visualize traffic patterns, track priority units, and monitor encrypted tactical deployments.

🚀 Features
🔒 Tactical ENC Tab: Real-time feed of encrypted transmissions with target highlighting.

📊 TGID Intel: Dual Plotly charts for Clear vs. Encrypted traffic distribution by Talkgroup.

👤 Unit Deep-Dive: Filter activity by Radio ID (RID) to identify "Pattern of Life."

🚨 Watchlist: Instant visual alerts for flagged units using a custom watchlist.txt.

📝 Alias Editor: Modify the DSDPlus.radios database directly from the web interface.

🛠️ Installation & Setup
To get the Hub running on your machine, follow these steps:

1. Install Dependencies
Open your terminal (Command Prompt or PowerShell) and run:

Bash
pip install streamlit pandas plotly streamlit-autorefresh
2. Configure Your Paths
Open hub.py and update the DSD_DIR variable to point to your DSDPlus folder.

3. Run the App
Navigate to your script folder and launch the dashboard:

Bash
streamlit run hub.py
📂 Required Files
Ensure the following files exist in your script directory:

hub.py (The main script)

watchlist.txt (Format: RID:Note)

ignore_list.txt (List of TGIDs to hide, one per line)

⚖️ Disclaimer
This software is for educational and hobbyist radio monitoring purposes only. Ensure compliance with all local laws regarding radio communication monitoring.
