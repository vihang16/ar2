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

# Load and save functions
def load_players():
    df = pd.DataFrame(players_sheet.get_all_records())
    return df["Player"].dropna().str.upper().tolist() if "Player" in df.columns else []

def save_players(players):
    df = pd.DataFrame({"Player": players})
    players_sheet.clear()
    players_sheet.update([df.columns.tolist()] + df.values.tolist())

def load_matches():
    df = pd.DataFrame(matches_sheet.get_all_records())
    return df

def save_matches(df):
    matches_sheet.clear()
    matches_sheet.update([df.columns.tolist()] + df.values.tolist())

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

        stats[team1[0]]["partners"][team1[1]] += 1
        stats[team1[1]]["partners"][team1[0]] += 1
        stats[team2[0]]["partners"][team2[1]] += 1
        stats[team2[1]]["partners"][team2[0]] += 1

    return stats

# Score options
def tennis_scores():
    scores = ["6-0", "6-1", "6-2", "6-3", "6-4", "7-5", "7-6"]
    return scores

players = load_players()
matches = load_matches()

# Sidebar: Manage players
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

# Sidebar: Edit/Delete Matches
with st.sidebar:
    st.header("Edit or Delete Match")
    match_ids = matches["match_id"].dropna().tolist() if "match_id" in matches.columns else []
    selected_match_id = st.selectbox("Select Match ID", [""] + match_ids)
    if selected_match_id:
        match_row = matches[matches["match_id"] == selected_match_id].iloc[0]
        if st.button("Delete Match"):
            matches = matches[matches["match_id"] != selected_match_id]
            save_matches(matches)
            st.success("Match deleted.")
            st.rerun()

# Enter Match Result
st.header("Enter Match Result")
available_players = players.copy()
p1 = st.selectbox("Team 1 - Player 1", available_players, key="t1p1")
available_players = [p for p in available_players if p != p1]
p2 = st.selectbox("Team 1 - Player 2", available_players, key="t1p2")
available_players = [p for p in available_players if p != p2]
p3 = st.selectbox("Team 2 - Player 1", available_players, key="t2p1")
available_players = [p for p in available_players if p != p3]
p4 = st.selectbox("Team 2 - Player 2", available_players, key="t2p2")

score_options = tennis_scores()
set1 = st.selectbox("Set 1", score_options, index=4, key="set1")
set2 = st.selectbox("Set 2", score_options, index=4, key="set2")
set3 = st.selectbox("Set 3 (optional)", ["", *score_options], index=0, key="set3")

winner = st.radio("Winner", ["Team 1", "Team 2"])

if st.button("Submit Match"):
    match_id = f"MIRA-{datetime.now().strftime('%y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}"
    new_match = {
        "match_id": match_id,
        "date": datetime.now().strftime("%Y-%m-%d"),
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

# Tabs
if not matches.empty:
    tab1, tab2, tab3 = st.tabs(["📖 Match Records", "🏆 Rankings", "🎾 Player Stats"])

    with tab1:
        matches["Date"] = pd.to_datetime(matches["date"], errors='coerce').dt.strftime("%d %b %Y")
        matches["Match"] = matches.apply(
            lambda row: f"{row['team1_player1']} & {row['team1_player2']} vs {row['team2_player1']} & {row['team2_player2']}", axis=1)
        matches["Winner"] = matches.apply(
            lambda row: f"\U0001F3C6 {row['team1_player1']} & {row['team1_player2']}" if row['winner'] == "Team 1"
            else f"\U0001F3C6 {row['team2_player1']} & {row['team2_player2']}", axis=1)

        display = matches[["Date", "Match", "set1", "set2", "set3", "Winner", "match_id"]].copy()
        st.dataframe(display, use_container_width=True)

    with tab2:
        stats = compute_stats(matches)
        if stats:
            rankings = pd.DataFrame([
                {"Player": p, "Points": d["points"], "Wins": d["wins"], "Losses": d["losses"], "Matches": d["matches"],
                 "Win %": f"{(d['wins']/d['matches']*100):.1f}%" if d['matches'] > 0 else "0.0%"}
                for p, d in stats.items()
            ])
            rankings = rankings.sort_values(by=["Points", "Wins"], ascending=False)
            rankings.index = range(1, len(rankings) + 1)
            rankings.index.name = "Rank"
            st.dataframe(rankings, use_container_width=True)

    with tab3:
        st.subheader("Player Insights")
        selected_player = st.selectbox("Select Player", players)
        if selected_player:
            data = stats.get(selected_player, {"points": 0, "wins": 0, "losses": 0, "matches": 0, "partners": {}})
            st.write(f"**Points:** {data['points']}")
            st.write(f"**Wins:** {data['wins']}")
            st.write(f"**Losses:** {data['losses']}")
            st.write(f"**Matches Played:** {data['matches']}")
            win_pct = (data["wins"] / data["matches"] * 100) if data["matches"] else 0
            st.write(f"**Win %:** {win_pct:.1f}%")

            if data["partners"]:
                st.write("**Partners Played With:**")
                partners_df = pd.DataFrame(
                    {"Partner": list(data["partners"].keys()), "Matches Together": list(data["partners"].values())}
                ).sort_values(by="Matches Together", ascending=False)
                st.dataframe(partners_df, use_container_width=True)
                st.write("**Most Effective Partner:**")
                st.write(partners_df.iloc[0]["Partner"] if not partners_df.empty else "None")
