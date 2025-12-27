import streamlit as st
import pandas as pd
import plotly.express as px
from nba_api.stats.static import teams, players
from nba_api.stats.endpoints import playergamelog, commonteamroster
import time

# --- 1. CONFIG & BRANDING (Header at the very top) ---
st.set_page_config(page_title="KHONA.ai Stats Tracker", layout="wide")

# CSS to fix the header to the top and remove default padding
st.markdown("""
    <style>
    .block-container { padding-top: 0rem !important; }
    .khona-header {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        background: linear-gradient(90deg, #1d428a, #552583);
        color: white;
        padding: 15px;
        text-align: center;
        font-size: 28px;
        font-weight: bold;
        z-index: 9999;
        box-shadow: 0px 4px 10px rgba(0,0,0,0.3);
    }
    /* Spacer to push content below fixed header */
    .content-spacer { margin-top: 80px; }
    </style>
    <div class="khona-header">🏀 NBA Stats Tracker by KHONA.ai</div>
    <div class="content-spacer"></div>
""", unsafe_allow_html=True)


# --- 2. DATA ENGINE ---
@st.cache_data(ttl=600)
def get_recent_stats(id_val, is_team=True):
    logs = []
    try:
        if is_team:
            roster = commonteamroster.CommonTeamRoster(team_id=id_val, season='2025-26').get_data_frames()[0]
            for _, p in roster.head(12).iterrows():
                time.sleep(0.1)
                log = playergamelog.PlayerGameLog(player_id=p['PLAYER_ID'], season='2025-26').get_data_frames()[0]
                if not log.empty:
                    log['Player'] = p['PLAYER']
                    logs.append(log)
        else:
            log = playergamelog.PlayerGameLog(player_id=id_val, season='2025-26').get_data_frames()[0]
            if not log.empty: logs.append(log)

        if not logs: return None
        df = pd.concat(logs)
        df['Date'] = pd.to_datetime(df['GAME_DATE']).dt.strftime('%b %d')
        df['P+R+A'] = df['PTS'] + df['REB'] + df['AST']
        return df
    except:
        return None


# --- 3. NAVIGATION ---
tab1, tab2 = st.tabs(["📊 Team Performance", "🆚 Player Comparison"])

# --- TAB 1: TEAM PERFORMANCE (Horizontal & Max Visibility) ---
with tab1:
    c1, c2 = st.columns(2, gap="medium")
    for i, col in enumerate([c1, c2]):
        with col:
            side = "Left" if i == 0 else "Right"
            sc1, sc2, sc3, sc4 = st.columns([2, 2, 1, 1])
            t_query = sc1.text_input(f"{side} Team:", value="Lakers" if i == 0 else "Mavericks", key=f"t{i}")
            stat = sc2.selectbox("Stat:", ["PTS", "REB", "AST", "P+R+A"], key=f"s{i}")
            line = sc3.number_input("Line:", value=25.5, step=0.5, key=f"l{i}")
            games = sc4.number_input("Last N:", value=5, min_value=1, key=f"n{i}")

            t_id = [t for t in teams.get_teams() if t_query.lower() in t['full_name'].lower()]
            if t_id:
                df = get_recent_stats(t_id[0]['id'], is_team=True)
                if df is not None:
                    recent_dates = df['Date'].unique()[:games]
                    df_filtered = df[df['Date'].isin(recent_dates)]
                    top_players = df_filtered.groupby('Player')[stat].mean().nlargest(10).index

                    fig = px.bar(df_filtered[df_filtered['Player'].isin(top_players)],
                                 y='Player', x=stat, color='Date', barmode='group',
                                 text_auto='.1f', height=700, orientation='h')

                    # LARGE VALUES: Increased to 22 for immediate readability
                    fig.update_traces(
                        textfont_size=22,
                        textfont_weight='bold',
                        textposition='outside',
                        cliponaxis=False
                    )

                    fig.add_vline(x=line, line_dash="dash", line_color="red", line_width=2)
                    fig.update_layout(
                        yaxis={'categoryorder': 'total ascending', 'tickfont': {'size': 14}},
                        margin=dict(l=10, r=60, t=30, b=10)
                    )

                    st.plotly_chart(fig, use_container_width=True)
                    st.dataframe(
                        df_filtered.sort_values('Player').pivot(index='Player', columns='Date', values=stat).fillna(0),
                        use_container_width=True)

# --- TAB 2: PLAYER COMPARISON (Comparison Stat Selection) ---
with tab2:
    st.markdown("### 🔍 Head-to-Head Comparison")
    pc1, pc2 = st.columns(2, gap="large")

    for i, col in enumerate([pc1, pc2]):
        with col:
            side = f"Player {i + 1}"
            psc1, psc2, psc3 = st.columns([2, 2, 1])
            p_name = psc1.text_input(f"{side}:", value="Luka Doncic" if i == 0 else "Kyrie Irving", key=f"pn{i}")
            # ADDED: Stat selector to choose what to compare against P+R+A
            p_stat_choice = psc2.selectbox("Compare against P+R+A:", ["PTS", "REB", "AST"], key=f"psel{i}")
            p_games = psc3.number_input("Games:", value=10, key=f"pg{i}")

            p_match = [p for p in players.get_players() if p_name.lower() in p['full_name'].lower() and p['is_active']]
            if p_match:
                p_df = get_recent_stats(p_match[0]['id'], is_team=False)
                if p_df is not None:
                    p_df = p_df.head(p_games)

                    # Display both the chosen stat and P+R+A side-by-side
                    fig_p = px.bar(p_df, x='Date', y=[p_stat_choice, 'P+R+A'],
                                   barmode='group',
                                   text_auto='.1f',
                                   title=f"{p_match[0]['full_name']}: {p_stat_choice} vs P+R+A",
                                   color_discrete_map={p_stat_choice: '#FFD700', 'P+R+A': '#1d428a'})

                    fig_p.update_traces(textfont_size=15, textfont_weight='bold', textposition='outside')
                    fig_p.update_layout(
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                        yaxis_title="Value"
                    )

                    st.plotly_chart(fig_p, use_container_width=True)
                    st.dataframe(p_df[['Date', 'MATCHUP', p_stat_choice, 'P+R+A']].set_index('Date'),
                                 use_container_width=True)