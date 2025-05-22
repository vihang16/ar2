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
    stats = defaultdict(lambda: {"points": 0, "wins": 0, "losses": 0, "matches": 0, "partners": defaultdict(int)})
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
        # Track partners played with
        for p, partner in [(team1[0], team1[1]), (team1[1], team1[0]), (team2[0], team2[1]), (team2[1], team2[0])]:
            stats[p]["partners"][partner] += 1
    return stats

# Font style
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
        st.experimental_rerun()

    remove_player = st.selectbox("Remove Player", [""] + players)
    if st.button("Remove Selected Player") and remove_player:
        players.remove(remove_player)
        save_players(players)
        st.experimental_rerun()

st.header("Enter Match Result")

available_players = players.copy()
p1 = st.selectbox("Team 1 - Player 1", available_players, key="t1p1")
available_players = [p for p in available_players if p != p1]
p2 = st.selectbox("Team 1 - Player 2", available_players, key="t1p2")
available_players = [p for p in available_players if p != p2]
p3 = st.selectbox("Team 2 - Player 1", available_players, key="t2p1")
available_players = [p for p in available_players if p != p3]
p4 = st.selectbox("Team 2 - Player 2", available_players, key="t2p2")

# Possible tennis scores dropdown options (typical set scores)
score_options = [
    "6-0", "6-1", "6-2", "6-3", "6-4", "7-5", "7-6",
    "0-6", "1-6", "2-6", "3-6", "4-6", "5-7", "6-7",
    ""
]

set1 = st.selectbox("Set 1", score_options, index=4, key="set1")
set2 = st.selectbox("Set 2", score_options, index=4, key="set2")
set3 = st.selectbox("Set 3 (optional)", score_options, index=0, key="set3")

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
    st.experimental_rerun()

# Display match records
st.header("Match Records")
if not matches.empty:
    display = matches.copy()

    # Compose player strings
    display["Players"] = display.apply(
        lambda row: f"{row['team1_player1']} & {row['team1_player2']} vs {row['team2_player1']} & {row['team2_player2']}",
        axis=1
    )
    
    # Show winner players with cup emoji
    def winner_names(row):
        if row["winner"] == "Team 1":
            return f"🏆 {row['team1_player1']} & {row['team1_player2']}"
        else:
            return f"🏆 {row['team2_player1']} & {row['team2_player2']}"
    display["Winner"] = display.apply(winner_names, axis=1)

    display["Date"] = pd.to_datetime(display["date"]).dt.strftime("%d %b %Y")

    # Select columns to show - add 'id' as last column
    show_cols = ["Date", "Players", "set1", "set2", "set3", "Winner", "id"]
    display = display[show_cols]

    # Reset index to avoid unnamed column showing up
    display = display.reset_index(drop=True)

    st.dataframe(display)
else:
    st.write("No matches recorded yet.")

# Rankings
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

# Player insights
st.header("Player Insights")
selected_player = st.selectbox("Select Player", players)
if selected_player:
    data = stats.get(selected_player, {"points": 0, "wins": 0, "losses": 0, "matches": 0, "partners": {}})
    st.write(f"**Points:** {data['points']}")
    st.write(f"**Wins:** {data['wins']}")
    st.write(f"**Losses:** {data['losses']}")
    st.write(f"**Matches Played:** {data['matches']}")
    win_pct = (data["wins"] / data["matches"] * 100) if data["matches"] else 0
    st.write(f"**Win %:** {win_pct:.1f}%")

    partners = data.get("partners", {})
    if partners:
        st.write("**Partners Played With:**")
        partner_list = sorted(partners.items(), key=lambda x: x[1], reverse=True)
        for partner, count in partner_list:
            st.write(f"- {partner} ({count} match{'es' if count > 1 else ''})")

        most_effective_partner = partner_list[0][0]
        st.write(f"**Most Effective Partner:** {most_effective_partner}")
    else:
        st.write("No partners recorded.")

