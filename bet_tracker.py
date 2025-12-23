# Re-deploy after secrets fix
import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta

# Replace with your API keys
NBA_STATS_API_KEY = st.secrets["NBA_STATS_API_KEY"]
SOCCER_STATS_API_KEY = st.secrets["SOCCER_STATS_API_KEY"]
ODDS_API_KEY = st.secrets["ODDS_API_KEY"]


# Helper functions
def get_nba_past_records(team_id, last_n=5):
    url = "https://api.balldontlie.io/v1/games"
    headers = {"Authorization": NBA_STATS_API_KEY}
    params = {"team_ids[]": team_id, "per_page": last_n, "seasons[]": datetime.now().year - 1}
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        games = response.json()["data"]
        return pd.DataFrame([{
            "Date": g["date"],
            "Opponent": g["visitor_team"]["full_name"] if g["home_team"]["id"] == team_id else g["home_team"][
                "full_name"],
            "Result": "Win" if (g["home_team_score"] > g["visitor_team_score"] and g["home_team"]["id"] == team_id) or (
                        g["visitor_team_score"] > g["home_team_score"] and g["visitor_team"][
                    "id"] == team_id) else "Loss",
            "Score": f"{g['home_team_score']}-{g['visitor_team_score']}"
        } for g in games])
    return pd.DataFrame()


def get_soccer_past_records(team_id, league_id, last_n=5):
    url = "https://v3.football.api-sports.io/fixtures"
    headers = {"x-apisports-key": SOCCER_STATS_API_KEY}
    params = {"team": team_id, "league": league_id, "last": last_n}
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        fixtures = response.json()["response"]
        return pd.DataFrame([{
            "Date": f["fixture"]["date"],
            "Opponent": f["teams"]["away"]["name"] if f["teams"]["home"]["id"] == team_id else f["teams"]["home"][
                "name"],
            "Result": "Win" if (f["goals"]["home"] > f["goals"]["away"] and f["teams"]["home"]["id"] == team_id) or (
                        f["goals"]["away"] > f["goals"]["home"] and f["teams"]["away"]["id"] == team_id) else "Loss" if
            f["score"]["fulltime"]["home"] is not None else "Draw",
            "Score": f"{f['goals']['home']}-{f['goals']['away']}"
        } for f in fixtures])
    return pd.DataFrame()


def get_head_to_head(sport, team1_id, team2_id, league_id=None):
    if sport == "NBA":
        url = "https://api.balldontlie.io/v1/games"
        headers = {"Authorization": NBA_STATS_API_KEY}
        params = {"team_ids[]": [team1_id, team2_id], "per_page": 5}
        response = requests.get(url, headers=headers, params=params)
        games = response.json()["data"] if response.status_code == 200 else []
    else:  # Soccer
        url = "https://v3.football.api-sports.io/fixtures/headtohead"
        headers = {"x-apisports-key": SOCCER_STATS_API_KEY}
        params = {"h2h": f"{team1_id}-{team2_id}", "last": 5}
        response = requests.get(url, headers=headers, params=params)
        games = response.json()["response"] if response.status_code == 200 else []
    return games  # Process into DF or summary as needed


def get_odds(sport_key, regions="us"):  # FanDuel is in 'us' region
    url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds"
    params = {"apiKey": ODDS_API_KEY, "regions": regions, "markets": "h2h,spreads,totals", "bookmakers": "fanduel"}
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json()
    return []


def suggest_bet(odds, past_df, home_team):
    if past_df.empty:
        return "No data for suggestion."
    win_rate = (past_df["Result"] == "Win").mean()
    if win_rate > 0.6:
        return f"Suggest betting on {home_team} to win (high win rate: {win_rate:.0%}). Check FanDuel odds."
    return "No strong suggestion—teams are evenly matched."


# Streamlit App
st.title("Sports Bet Tracker: NBA & European Soccer")

sport = st.selectbox("Select Sport", ["NBA", "Soccer"])
if sport == "NBA":
    # Sample team IDs (expand as needed)
    team_id = st.selectbox("Select Team (ID)", {"Lakers": 14, "Warriors": 10})  # Add more
    past_df = get_nba_past_records(team_id)
    st.subheader("Past 5 Games")
    st.dataframe(past_df)

    opponent_id = st.selectbox("Opponent for H2H (ID)", {"Celtics": 2, "Bulls": 5})
    h2h = get_head_to_head("NBA", team_id, opponent_id)
    st.subheader("Head-to-Head Summary")
    st.write(h2h)  # Display raw or format

    odds = get_odds("basketball_nba")
    st.subheader("Upcoming Odds (FanDuel)")
    st.write(odds)  # Filter for relevant game

    suggestion = suggest_bet(odds, past_df, "Your Team")
    st.subheader("Bet Suggestion")
    st.write(suggestion)

else:  # Soccer
    league_id = st.selectbox("Select League (ID)", {"Premier League": 39, "La Liga": 140, "Bundesliga": 78})
    team_id = st.selectbox("Select Team (ID)", {"Manchester United": 33, "Real Madrid": 541})  # Add more
    past_df = get_soccer_past_records(team_id, league_id)
    st.subheader("Past 5 Games")
    st.dataframe(past_df)

    opponent_id = st.selectbox("Opponent for H2H (ID)", {"Liverpool": 40, "Barcelona": 529})
    h2h = get_head_to_head("Soccer", team_id, opponent_id, league_id)
    st.subheader("Head-to-Head Summary")
    st.write(h2h)

    sport_key = "soccer_epl" if league_id == 39 else "soccer_spain_la_liga" if league_id == 140 else "soccer_germany_bundesliga"
    odds = get_odds(sport_key)
    st.subheader("Upcoming Odds (FanDuel)")
    st.write(odds)

    suggestion = suggest_bet(odds, past_df, "Your Team")
    st.subheader("Bet Suggestion")
    st.write(suggestion)


st.warning("This is a basic tool using public APIs. For real bets, use FanDuel app. Gambling responsibly—set limits.")


