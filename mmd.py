import streamlit as st
import pandas as pd
import uuid
from datetime import datetime
import gspread
from collections import defaultdict
from oauth2client.service_account import ServiceAccountCredentials

# Google Sheets setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_dict = st.secrets["gcp_service_account"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

SHEET_NAME = "RLTG Data"
players_sheet_name = "Mira Players"
matches_sheet_name = "Mira Matches"

# Ensure worksheets exist
spreadsheet = client.open(SHEET_NAME)
def get_or_create_worksheet(sheet, name, rows=1000, cols=20):
    try:
        return sheet.worksheet(name)
    except:
        return sheet.add_worksheet(title=name, rows=str(rows), cols=str(cols))

players_sheet = get_or_create_worksheet(spreadsheet, players_sheet_name)
matches_sheet = get_or_create_worksheet(spreadsheet, matches_sheet_name)

# Load players
def load_players():
    df = pd.DataFrame(players_sheet.get_all_records())
    if "Player" not in df.columns:
        return []
    return df["Player"].dropna().str.upper().tolist()

# Save players
def save_players(players):
    df = pd.DataFrame({"Player": players})
    players_sheet.clear()
    players_sheet.update([df.columns.tolist()] + df.values.tolist())

# Load matches
def load_matches():
    df = pd.DataFrame(matches_sheet.get_all_records())
    return df

# Save matches
def save_matches(df):
    matches_sheet.clear()
    matches_sheet.update([df.columns.tolist()] + df.values.tolist())

# Compute points
def compute_stats(matches):
    stats = defaultdict(lambda: {"points": 0, "wins": 0, "losses": 0, "matches": 0})
    for _, row in matches.iterrows():
        team1 = [row["team1_player1"], row["team1_player2"]]
        team2 = [row["team2_player1"], row["team2_player2"]]
        winner = row["winner"]
        if winner == "Team 1":
            for p in team1:
                stats[p]["points"] += 3
                stats[p]["wins"] += 1
            for p in team2:
                stats[p]["points"] += 1
                stats[p]["losses"] += 1
        else:
            for p in team2:
                stats[p]["points"] += 3
                stats[p]["wins"] += 1
            for p in team1:
                stats[p]["points"] += 1
                stats[p]["losses"] += 1
        for p in team1 + team2:
            stats[p]["matches"] += 1
    return stats

# Font styling
st.markdown('''
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Offside&display=swap');
    html, body, [class*="st-"], [class^="css"], h1, h2, h3, h4, h5, h6, .stText, .stMarkdown {
        font-family: 'Offside', sans-serif !important;
    }
    </style>
''', unsafe_allow_html=True)

st.title("Mira Mixed Doubles Tennis Group 🎾")

players = load_players()
matches = load_matches()

# Sidebar for managing players
with st.sidebar:
    st.header("Manage Players")
    new_player = st.text_input("Add New Player").upper()
    if st.button("Add Player") and new_player and new_player not in players:
        players.append(new_player)
        save_players(players)
        st.rerun()

    remove_player = st.selectbox("Remove Player", [""] + players)
    if st.button("Remove Selected Player") and remove_player:
        players.remove(remove_player)
        save_players(players)
        st.rerun()

# Match Entry Section
st.header("Enter Match Result")

p1 = st.selectbox("Team 1 - Player 1", players, key="t1p1")
p2 = st.selectbox("Team 1 - Player 2", [p for p in players if p != p1], key="t1p2")
p3 = st.selectbox("Team 2 - Player 1", [p for p in players if p not in [p1, p2]], key="t2p1")
p4 = st.selectbox("Team 2 - Player 2", [p for p in players if p not in [p1, p2, p3]], key="t2p2")

# Score inputs
st.markdown("**Enter Set Scores (Format: 6-4)**")
set1 = st.text_input("Set 1", value="6-4")
set2 = st.text_input("Set 2", value="6-4")
set3 = st.text_input("Set 3 (optional)", value="")

winner = st.radio("Winner", ["Team 1", "Team 2"])

if st.button("Submit Match"):
    new_match = {
        "id": f"MIRA-{datetime.now().strftime('%y%m%d%H%M%S')}",
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "team1_player1": p1,
        "team1_player2": p2,
        "team2_player1": p3,
        "team2_player2": p4,
        "set1": set1,
        "set2": set2,
        "set3": set3,
        "winner": winner
    }
    matches = pd.concat([matches, pd.DataFrame([new_match])], ignore_index=True)
    save_matches(matches)
    st.success("Match submitted.")
    st.rerun()

# Match Records Display
st.header("Match Records")
if not matches.empty:
    display = matches.copy()
    display["Players"] = display.apply(
        lambda row: f"{row['team1_player1']} & {row['team1_player2']} vs {row['team2_player1']} & {row['team2_player2']}",
        axis=1
    )
    display["Date"] = pd.to_datetime(display["date"]).dt.strftime("%d %b %Y")
    display = display[["Date", "Players", "set1", "set2", "set3", "winner"]]
    st.dataframe(display)

# Player Rankings
st.header("Player Rankings")
stats = compute_stats(matches)
if stats:
    rankings = pd.DataFrame([
        {"Player": p, "Points": d["points"], "Wins": d["wins"], "Losses": d["losses"], "Matches": d["matches"]}
        for p, d in stats.items()
    ])
    rankings = rankings.sort_values(by=["Points", "Wins"], ascending=False)
    rankings.index = range(1, len(rankings) + 1)
    rankings.index.name = "Rank"
    st.dataframe(rankings)

# Player Insights
st.header("Player Insights")
selected_player = st.selectbox("Select Player", players)
if selected_player:
    data = stats.get(selected_player, {"points": 0, "wins": 0, "losses": 0, "matches": 0})
    st.write(f"**Points:** {data['points']}")
    st.write(f"**Wins:** {data['wins']}")
    st.write(f"**Losses:** {data['losses']}")
    st.write(f"**Matches Played:** {data['matches']}")
    win_pct = (data["wins"] / data["matches"] * 100) if data["matches"] else 0
    st.write(f"**Win %:** {win_pct:.1f}%")
