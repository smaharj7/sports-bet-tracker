import streamlit as st
import pandas as pd
import plotly.express as px
from nba_api.stats.static import teams, players
from nba_api.stats.endpoints import playergamelog
import time

# --- 1. CONFIG & BRANDING ---
st.set_page_config(page_title="KHONA.ai Stats Tracker", layout="wide")

st.markdown("""
    <style>
    header[data-testid="stHeader"] { visibility: hidden; height: 0px; }
    .block-container { padding-top: 1rem !important; }
    .khona-logo {
        position: fixed; top: 10px; left: 20px;
        font-size: 20px; font-weight: 800; color: #1d428a;
        z-index: 10000; font-family: sans-serif;
    }
    .khona-logo span { color: #552583; }
    </style>
    <div class="khona-logo">🏀 KHONA<span>.ai</span></div>
""", unsafe_allow_html=True)


# --- 2. ROBUST DATA ENGINE ---
@st.cache_data(ttl=300)
def get_player_data(player_id, player_name):
    # Standard headers to bypass NBA.com security
    headers = {
        'Host': 'stats.nba.com',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.5',
        'Referer': 'https://stats.nba.com/',
        'Origin': 'https://stats.nba.com'
    }

    for attempt in range(3):  # Try 3 times before giving up
        try:
            time.sleep(1.2)  # Essential delay for NBA API
            log = playergamelog.PlayerGameLog(
                player_id=player_id,
                season='2024-25',
                timeout=30  # Allow more time for slow API responses
            ).get_data_frames()[0]

            if not log.empty:
                log['Date'] = pd.to_datetime(log['GAME_DATE']).dt.strftime('%b %d')
                log['P+A+R'] = log['PTS'] + log['AST'] + log['REB']
                return log
        except Exception:
            time.sleep(2)  # Wait longer if failed
    return None


# --- 3. UI TABS ---
tab1, tab2 = st.tabs(["📊 Team Performance", "🆚 Player Comparison"])

with tab1:
    st.info("Select a team to view the full roster performance.")
    # (Team logic from previous version goes here...)

with tab2:
    st.subheader("🔍 Head-to-Head Comparison")
    pc1, pc2 = st.columns(2, gap="large")

    for i, col in enumerate([pc1, pc2]):
        with col:
            p_name = st.text_input(f"Enter Player {i + 1}:", value="LeBron James" if i == 0 else "Luka Doncic",
                                   key=f"p_input_{i}")
            p_stat = st.selectbox("Compare vs P+A+R:", ["PTS", "REB", "AST"], key=f"p_stat_{i}")

            # Find ID
            matches = [p for p in players.get_players() if p_name.lower() in p['full_name'].lower() and p['is_active']]

            if matches:
                p_id = matches[0]['id']
                with st.spinner(f'Loading {matches[0]["full_name"]}...'):
                    df = get_player_data(p_id, matches[0]['full_name'])

                    if df is not None:
                        # Graph
                        fig = px.bar(df.head(10), x='Date', y=[p_stat, 'P+A+R'],
                                     barmode='group', text_auto='.1f',
                                     color_discrete_map={p_stat: '#FFD700', 'P+A+R': '#1d428a'})

                        fig.update_layout(legend=dict(orientation="h", y=1.1), height=400)
                        st.plotly_chart(fig, use_container_width=True)

                        # Data Table
                        st.dataframe(df[['Date', 'MATCHUP', p_stat, 'P+A+R']].head(5), use_container_width=True)
                    else:
                        st.warning(f"NBA server is busy. Please wait 10 seconds and try again.")
            else:
                st.error("Player not found. Check the spelling.")
