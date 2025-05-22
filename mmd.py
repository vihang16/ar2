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
    if not df.empty and "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors='coerce')
    return df

# Save matches
def save_matches(df):
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d %H:%M:%S")
    matches_sheet.clear()
    matches_sheet.update([df.columns.tolist()] + df.astype(str).values.tolist())

# Compute stats
def compute_stats(matches):
    stats = defaultdict(lambda: {"points": 0, "wins": 0, "losses": 0, "matches": 0, "partners": defaultdict(int)})
    for _, row in matches.iterrows():
        t1 = [row["team1_player1"], row["team1_player2"]]
        t2 = [row["team2_player1"], row["team2_player2"]]
        winner = row["winner"]

        for p1, p2 in [(t1[0], t1[1]), (t1[1], t1[0]), (t2[0], t2[1]), (t2[1], t2[0])]:
            stats[p1]["partners"][p2] += 1

        if winner == "Team 1":
            for p in t1:
                stats[p]["points"] += 3
                stats[p]["wins"] += 1
            for p in t2:
                stats[p]["points"] += 1
                stats[p]["losses"] += 1
        else:
            for p in t2:
                stats[p]["points"] += 3
                stats[p]["wins"] += 1
            for p in t1:
                stats[p]["points"] += 1
                stats[p]["losses"] += 1

        for p in t1 + t2:
            stats[p]["matches"] += 1

    return stats

# Font
st.markdown('''
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Offside&display=swap');
    html, body, [class*="st-"], [class^="css"] {
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

# Match entry
st.header("Enter Match Result")

available_players = players.copy()
p1 = st.selectbox("Team 1 - Player 1", available_players, key="t1p1")
available_players.remove(p1)
p2 = st.selectbox("Team 1 - Player 2", available_players, key="t1p2")
available_players.remove(p2)
p3 = st.selectbox("Team 2 - Player 1", available_players, key="t2p1")
available_players.remove(p3)
p4 = st.selectbox("Team 2 - Player 2", available_players, key="t2p2")

# Tennis score dropdown options
score_options = ["6-0", "6-1", "6-2", "6-3", "6-4", "7-5", "7-6"]
set1 = st.selectbox("Set 1", score_options, index=4, key="set1")
set2 = st.selectbox("Set 2", score_options, index=4, key="set2")
set3 = st.selectbox("Set 3 (if played)", ["", *score_options], key="set3")

winner = st.radio("Winner", ["Team 1", "Team 2"])

if st.button("Submit Match"):
    match_id = f"MIRA-{datetime.now().strftime('%y%m%d%H%M%S')}-{str(uuid.uuid4())[:6]}"
    new_match = {
        "match_id": match_id,
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

# Match Records
st.header("Match Records")
if not matches.empty:
    matches["Date"] = pd.to_datetime(matches["date"], errors='coerce').dt.strftime("%d %b %Y")
    def format_winner(row):
        if row["winner"] == "Team 1":
            return f"🏆 {row['team1_player1']} & {row['team1_player2']}"
        else:
            return f"🏆 {row['team2_player1']} & {row['team2_player2']}"
    matches["Winner"] = matches.apply(format_winner, axis=1)
    matches["Match"] = matches.apply(
        lambda r: f"{r['team1_player1']} & {r['team1_player2']} vs {r['team2_player1']} & {r['team2_player2']}", axis=1)
    display = matches[["Date", "Match", "set1", "set2", "set3", "Winner", "match_id"]].copy()
    display.columns = ["Date", "Match", "Set 1", "Set 2", "Set 3", "Winner", "Match ID"]
    st.dataframe(display, use_container_width=True)

# Rankings
st.header("Player Rankings")
stats = compute_stats(matches)
if stats:
    rankings = pd.DataFrame([
        {
            "Player": p,
            "Points": d["points"],
            "Wins": d["wins"],
            "Losses": d["losses"],
            "Matches": d["matches"],
            "Win %": f"{(d['wins']/d['matches']*100):.1f}%" if d["matches"] else "0%"
        }
        for p, d in stats.items()
    ])
    rankings = rankings.sort_values(by=["Points", "Wins"], ascending=False)
    rankings.index = range(1, len(rankings) + 1)
    rankings.index.name = "Rank"
    st.dataframe(rankings, use_container_width=True)

# Player Stats with dropdown
st.header("Player Stats")

selected_player = st.selectbox("Select a player to view details", sorted(stats.keys()))
if selected_player:
    d = stats[selected_player]
    st.subheader(f"Stats for {selected_player}")
    st.markdown(f"""
    - **Total Matches:** {d['matches']}
    - **Wins:** {d['wins']}
    - **Losses:** {d['losses']}
    - **Points:** {d['points']}
    - **Win %:** {(d["wins"] / d["matches"] * 100):.1f}%
    """)

    if d["partners"]:
        sorted_partners = sorted(d["partners"].items(), key=lambda x: -x[1])
        partner_list = [f"{p} ({n}x)" for p, n in sorted_partners]
        best_partner = sorted_partners[0][0]
        st.markdown(f"- **Partners Played With:** {', '.join(partner_list)}")
        st.markdown(f"- **Most Effective Partner:** 🏆 {best_partner} ({d['partners'][best_partner]} matches)")
    else:
        st.markdown("No partner data available.")
