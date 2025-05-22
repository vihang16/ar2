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

st.header("Enter Match Result")

available_players = players.copy()
p1 = st.selectbox("Team 1 - Player 1", available_players, key="t1p1")
available_players = [p for p in available_players if p != p1]
p2 = st.selectbox("Team 1 - Player 2", available_players, key="t1p2")
available_players = [p for p in available_players if p != p2]
p3 = st.selectbox("Team 2 - Player 1", available_players, key="t2p1")
available_players = [p for p in available_players if p != p3]
p4 = st.selectbox("Team 2 - Player 2", available_players, key="t2p2")

valid_scores = [
    "6-0", "6-1", "6-2", "6-3", "6-4", "7-5", "7-6",
    "0-6", "1-6", "2-6", "3-6", "4-6", "5-7", "6-7"
]

st.markdown("**Select Set Scores**")
set1 = st.selectbox("Set 1", valid_scores, index=4)
set2 = st.selectbox("Set 2", valid_scores, index=4)
set3 = st.selectbox("Set 3 (optional)", [""] + valid_scores, index=0)

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

    # Partner stats
    partner_matches = []
    for _, row in matches.iterrows():
        if selected_player in [row["team1_player1"], row["team1_player2"]]:
            teammate = row["team1_player2"] if selected_player == row["team1_player1"] else row["team1_player1"]
            same_team = "Team 1"
        elif selected_player in [row["team2_player1"], row["team2_player2"]]:
            teammate = row["team2_player2"] if selected_player == row["team2_player1"] else row["team2_player1"]
            same_team = "Team 2"
        else:
            continue
        won = row["winner"] == same_team
        partner_matches.append((teammate, won))

    partner_stats = defaultdict(lambda: {"matches": 0, "wins": 0})
    for partner, won in partner_matches:
        partner_stats[partner]["matches"] += 1
        if won:
            partner_stats[partner]["wins"] += 1

    if partner_stats:
        st.subheader("Partner History")
        for partner, stat in partner_stats.items():
            pct = (stat["wins"] / stat["matches"] * 100) if stat["matches"] else 0
            st.markdown(f"- {partner}: {stat['wins']} Wins / {stat['matches']} Matches ({pct:.1f}%)")

        best_partner = max(partner_stats.items(), key=lambda x: (x[1]["wins"] / x[1]["matches"] if x[1]["matches"] > 0 else 0))
        best_partner_name = best_partner[0]
        win_pct = (best_partner[1]["wins"] / best_partner[1]["matches"]) * 100
        st.markdown(f"**Most Effective Partner:** {best_partner_name} ({win_pct:.1f}% win rate)")
