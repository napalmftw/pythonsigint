import streamlit as st
import pandas as pd
import os
import re
import plotly.express as px
from datetime import datetime, timedelta
from streamlit_autorefresh import st_autorefresh

# ==============================================================================
# CONFIGURATION: Update these paths to match your local DSDPlus environment
# ==============================================================================
# Example: r'C:\DSDPlus\CC-DSDPlus.event'
LOG_FILE_PATH = "path/to/your/CC-DSDPlus.event"
RADIOS_FILE_PATH = "path/to/your/DSDPlus.radios"
GROUPS_FILE_PATH = "path/to/your/DSDPlus.groups"
WATCHLIST_FILE = "watchlist.txt"  # Local file for monitored RIDs
IGNORE_FILE = "ignore_list.txt"    # Local file for muted TGIDs

st.set_page_config(
    page_title="LakeOps Intel Hub", 
    layout="wide", 
    page_icon="📡",
    initial_sidebar_state="expanded"
)

# --- 1. DATA PROCESSING ---
def load_watchlist():
    """Reads the local watchlist.txt for flagged Radio IDs."""
    if not os.path.exists(WATCHLIST_FILE): return {}
    watch = {}
    try:
        with open(WATCHLIST_FILE, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                if ':' in line:
                    rid, reason = line.strip().split(':', 1)
                    watch[rid.strip()] = reason.strip()
    except Exception as e:
        st.sidebar.error(f"Watchlist Load Error: {e}")
    return watch

@st.cache_data(ttl=60)
def load_metadata():
    """Parses DSDPlus .radios and .groups for Aliases and TG Names."""
    rids, tgs = {}, {}
    try:
        if os.path.exists(RADIOS_FILE_PATH):
            with open(RADIOS_FILE_PATH, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    parts = line.split(',')
                    if len(parts) >= 9: rids[parts[3].strip()] = parts[8].strip().strip('"')
        if os.path.exists(GROUPS_FILE_PATH):
            with open(GROUPS_FILE_PATH, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    parts = line.split(',')
                    if len(parts) >= 8: tgs[parts[2].strip()] = parts[7].strip().strip('"')
    except Exception as e:
        st.sidebar.error(f"Metadata Error: {e}")
    return rids, tgs

def parse_logs():
    """Main engine: Scans DSDPlus event logs and applies filters/logic."""
    rid_aliases, tg_aliases = load_metadata()
    watchlist = load_watchlist()
    all_data = []
    tactical_rids = set()
    
    # Standard P25 Group Call Regex Pattern
    pattern = re.compile(
        r"(\d{4}/\d{2}/\d{2})\s+(\d{2}:\d{2}:\d{2}).*?(Enc Group call|Group call|P-Group call); TG=(\d+).*?RID=(\d+)"
    )

    if os.path.exists(LOG_FILE_PATH):
        with open(LOG_FILE_PATH, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                match = pattern.search(line)
                if match:
                    date, timestamp, ctype, tg, rid = match.groups()
                    
                    is_enc = "Enc" in ctype
                    if is_enc: tactical_rids.add(rid)
                    
                    tg_name = tg_aliases.get(tg, f"TG {tg}")
                    
                    all_data.append({
                        'Timestamp': f"{date} {timestamp}",
                        'dt': datetime.strptime(f"{date} {timestamp}", "%Y/%m/%d %H:%M:%S"),
                        'Type': "🔒 ENC" if is_enc else "🔊 CLEAR",
                        'TG': tg,
                        'TG Name': tg_name,
                        'RID': rid,
                        'Unit Alias': rid_aliases.get(rid, "UNID"),
                        'IsWatched': rid in watchlist
                    })
    return pd.DataFrame(all_data), tactical_rids

# --- 2. UI INITIALIZATION ---
rid_map, tg_map = load_metadata()
df, tac_set = parse_logs()
watchlist = load_watchlist()

st.sidebar.header("📡 System Controls")
if st.sidebar.checkbox("Enable Live Feed Refresh", value=False):
    st_autorefresh(interval=15000, key="hub_refresh_timer")

st.title("🛰️ Radio Intelligence Dashboard")
st.markdown("---")

# --- 3. TACTICAL DASHBOARD TABS ---
tabs = st.tabs(["🔒 Tactical ENC", "👤 Unit Deep-Dive", "📊 TGID Intel", "📜 Live Feed"])

def color_watchlist(val): 
    return 'background-color: #8B0000; color: white' if val in watchlist else ''

# --- TAB: TGID INTEL (The Dual Pie/Table View) ---
with tabs[2]:
    st.header("Talkgroup Traffic Analysis")
    if not df.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🔊 Clear Traffic Share")
            clear_df = df[df['Type'] == "🔊 CLEAR"]
            if not clear_df.empty:
                clear_tg_counts = clear_df['TG Name'].value_counts().reset_index()
                clear_tg_counts.columns = ['Talkgroup', 'Hits']
                fig_clear = px.pie(clear_tg_counts.head(10), values='Hits', names='Talkgroup', 
                                  hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
                st.plotly_chart(fig_clear, use_container_width=True)
            
        with col2:
            st.subheader("🔒 Encrypted Traffic Share")
            enc_df = df[df['Type'] == "🔒 ENC"]
            if not enc_df.empty:
                enc_tg_counts = enc_df['Agency'].value_counts().reset_index() if 'Agency' in df else enc_df['TG Name'].value_counts().reset_index()
                enc_tg_counts.columns = ['Talkgroup', 'Hits']
                fig_enc = px.pie(enc_tg_counts.head(10), values='Hits', names='Talkgroup', 
                                hole=0.4, color_discrete_sequence=px.colors.qualitative.Safe)
                st.plotly_chart(fig_enc, use_container_width=True)

        st.divider()
        
        # Dual Dataframes for detailed volume
        t1, t2 = st.columns(2)
        with t1:
            st.write("### 🔊 Busiest Clear Channels")
            if not clear_df.empty:
                st.dataframe(clear_df.groupby('TG Name').size().reset_index(name='Hits').sort_values('Hits', ascending=False), hide_index=True)
        with t2:
            st.write("### 🔒 Busiest Tactical Channels")
            if not enc_df.empty:
                st.dataframe(enc_df.groupby('TG Name').size().reset_index(name='Hits').sort_values('Hits', ascending=False), hide_index=True)
    else:
        st.warning("No log data detected. Verify your file paths in the script configuration.")

# (Other logic for Deep-Dive and Live Feed follows same pattern...)
