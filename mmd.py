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

def load_players():
    df = pd.DataFrame(players_sheet.get_all_records())
    if "Player" not in df.columns:
        return []
    return df["Player"].dropna().str.upper().tolist()

def save_players(players):
    df = pd.DataFrame({"Player": players})
    players_sheet.clear()
    players_sheet.update([df.columns.tolist()] + df.values.tolist())

def load_matches():
    df = pd.DataFrame(matches_sheet.get_all_records())
    if df.empty:
        return df

    # Ensure 'id' column exists and fill missing ids with generated ones
    if "id" not in df.columns:
        df["id"] = ""

    missing_id_mask = df["id"].isna() | (df["id"] == "")
    if missing_id_mask.any():
        for idx in df[missing_id_mask].index:
            new_id = f"MIRA-{datetime.now().strftime('%y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}"
            df.at[idx, "id"] = new_id

        # Save back updated IDs to the sheet to keep it persistent
        save_matches(df)
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
        # Track partners
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

# --- Edit Match UI (always visible) ---
st.sidebar.header("Edit or Delete Match")

if not matches.empty:
    match_options = [f"{row['id']} - {row['team1_player1']} & {row['team1_player2']} vs {row['team2_player1']} & {row['team2_player2']} ({pd.to_datetime(row['date']).strftime('%d %b %Y')})"
                     for _, row in matches.iterrows()]
    selected_match_str = st.sidebar.selectbox("Select Match to Edit/Delete", [""] + match_options)
    if selected_match_str:
        selected_match_id = selected_match_str.split(" - ")[0]
        selected_match = matches[matches["id"] == selected_match_id].iloc[0]

        # Editable fields
        st.sidebar.markdown("### Edit Match Details")
        p1 = st.sidebar.selectbox("Team 1 - Player 1", players, index=players.index(selected_match["team1_player1"]))
        p2 = st.sidebar.selectbox("Team 1 - Player 2", [p for p in players if p != p1], index=[p for p in players if p != p1].index(selected_match["team1_player2"]))
        p3 = st.sidebar.selectbox("Team 2 - Player 1", [p for p in players if p not in [p1, p2]], index=[p for p in players if p not in [p1, p2]].index(selected_match["team2_player1"]))
        p4 = st.sidebar.selectbox("Team 2 - Player 2", [p for p in players if p not in [p1, p2, p3]], index=[p for p in players if p not in [p1, p2, p3]].index(selected_match["team2_player2"]))

        score_options = [
            "6-0", "6-1", "6-2", "6-3", "6-4", "7-5", "7-6",
            "0-6", "1-6", "2-6", "3-6", "4-6", "5-7", "6-7",
            ""
        ]

        set1 = st.sidebar.selectbox("Set 1", score_options, index=score_options.index(selected_match.get("set1", "") if selected_match.get("set1", "") in score_options else ""))
        set2 = st.sidebar.selectbox("Set 2", score_options, index=score_options.index(selected_match.get("set2", "") if selected_match.get("set2", "") in score_options else ""))
        set3 = st.sidebar.selectbox("Set 3 (optional)", score_options, index=score_options.index(selected_match.get("set3", "") if selected_match.get("set3", "") in score_options else ""))

        winner = st.sidebar.radio("Winner", ["Team 1", "Team 2"], index=0 if selected_match.get("winner", "Team 1") == "Team 1" else 1)

        if st.sidebar.button("Save Changes"):
            matches.loc[matches["id"] == selected_match_id, ["team1_player1", "team1_player2", "team2_player1", "team2_player2", "set1", "set2", "set3", "winner"]] = [
                p1, p2, p3, p4, set1, set2, set3, winner
            ]
            save_matches(matches)
            st.sidebar.success("Match updated!")
            st.experimental_rerun()

        if st.sidebar.button("Delete Match"):
            matches = matches[matches["id"] != selected_match_id]
            save_matches(matches)
            st.sidebar.success("Match deleted!")
            st.experimental_rerun()
else:
    st.sidebar.write("No matches available for edit/delete.")

# Main app continues with adding new matches and displaying tables (same as before)

st.header("Enter Match Result")

available_players = players.copy()
p1 = st.selectbox("Team 1 - Player 1", available_players, key="t1p1")
available_players = [p for p in available_players if p != p1]
p2 = st.selectbox("Team 1 - Player 2", available_players, key="t1p2")
available_players = [p for p in available_players if p != p2]
p3 = st.selectbox("Team 2 - Player 1", available_players, key="t2p1")
available_players = [p for p in available_players if p != p3]
p4 = st.selectbox("Team 2 - Player 2", available_players, key="t2p2")

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
        "id": f"MIRA-{datetime.now().strftime('%y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}",
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

# Display match records with winner names and cup emoji, and match id at end

st.header("Match Records")
if not matches.empty:
    display = matches.copy()

    display["Players"] = display.apply(
        lambda row: f"{row['team1_player1']} & {row['team1_player2']} vs {row['team2_player1']} & {row['team2_player2']}",
        axis=1
    )
    
    def winner_names(row):
        if row["winner"] == "Team 1":
            return f"🏆 {row['team1_player1']} & {row['team1_player2']}"
        else:
            return f"🏆 {row['team2_player1']} & {row['team2_player2']}"
    display["Winner"] = display.apply(winner_names, axis=1)

    display["Date"] = pd.to_datetime(display["date"]).dt.strftime("%d %b %Y")

    show_cols = ["Date", "Players", "set1", "set2", "set3", "Winner", "id"]
    display = display[show_cols]
    display = display.reset_index(drop=True)

    st.dataframe(display)
else:
    st.write("No matches recorded yet.")

# Rankings and player insights code (same as before)...
# (Omitted here to keep the focus on your request; you can re-add from previous snippet)

