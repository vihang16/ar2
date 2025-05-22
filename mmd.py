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

# Compute points and stats
def compute_stats(matches):
    stats = defaultdict(lambda: {"points": 0, "wins": 0, "losses": 0, "matches": 0, "partners": defaultdict(int)})
    for _, row in matches.iterrows():
        team1 = [row["team1_player1"], row["team1_player2"]]
        team2 = [row["team2_player1"], row["team2_player2"]]
        winner = row["winner"]
        # Count partners
        for p in team1:
            for partner in team1:
                if partner != p:
                    stats[p]["partners"][partner] += 1
        for p in team2:
            for partner in team2:
                if partner != p:
                    stats[p]["partners"][partner] += 1
        if winner == "Team 1":
            for p in team1:
                stats[p]["points"] += 3
                stats[p]["wins"] += 1
            for p in team2:
                stats[p]["points"] += 1
                stats[p]["losses"] += 1
        elif winner == "Team 2":
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

# Load data
players = load_players()
matches = load_matches()

# Fix date parsing in matches
if not matches.empty and "date" in matches.columns:
    matches["date"] = pd.to_datetime(matches["date"], errors="coerce", dayfirst=False)
    # Try parsing manually entered mm/dd/yyyy format if initial parse fails
    mask = matches["date"].isna()
    if mask.any():
        original_dates = matches.loc[mask, "date"].astype(str)
        fallback_dates = pd.to_datetime(original_dates, format="%m/%d/%Y", errors="coerce")
        matches.loc[mask, "date"] = fallback_dates

# Sidebar - Manage Players
with st.sidebar:
    st.header("Manage Players")

    # Reload players here to stay updated
    players = load_players()

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

    st.markdown("---")

    # Edit or Delete Matches
    st.header("Edit or Delete Match")
    if not matches.empty:
        # Use id or if missing, create temp id for selection
        match_options = []
        for idx, row in matches.iterrows():
            mid = row["id"] if "id" in row and row["id"] else f"NO-ID-{idx}"
            match_desc = f"{mid} | {row['team1_player1']} & {row['team1_player2']} vs {row['team2_player1']} & {row['team2_player2']} | {row['date'] if pd.notnull(row['date']) else 'No Date'}"
            match_options.append(match_desc)
        selected_match = st.selectbox("Select Match to Edit/Delete", [""] + match_options)
        if selected_match and selected_match != "":
            selected_idx = match_options.index(selected_match)
            selected_row = matches.iloc[selected_idx]

            # Editing players
            st.write("### Edit Match Details")
            # Player selection options for editing
            p1 = st.selectbox("Team 1 - Player 1", players, index=players.index(selected_row["team1_player1"]) if selected_row["team1_player1"] in players else 0, key="edit_t1p1")
            p2 = st.selectbox("Team 1 - Player 2", [p for p in players if p != p1], index=[p for p in players if p != p1].index(selected_row["team1_player2"]) if selected_row["team1_player2"] in players else 0, key="edit_t1p2")
            p3 = st.selectbox("Team 2 - Player 1", [p for p in players if p not in [p1,p2]], index=[p for p in players if p not in [p1,p2]].index(selected_row["team2_player1"]) if selected_row["team2_player1"] in players else 0, key="edit_t2p1")
            p4 = st.selectbox("Team 2 - Player 2", [p for p in players if p not in [p1,p2,p3]], index=[p for p in players if p not in [p1,p2,p3]].index(selected_row["team2_player2"]) if selected_row["team2_player2"] in players else 0, key="edit_t2p2")

            # Score options for dropdown
            score_options = [
                "6-0", "6-1", "6-2", "6-3", "6-4", "7-5", "7-6",
                "0-6", "1-6", "2-6", "3-6", "4-6", "5-7", "6-7",
            ]

            set1 = st.selectbox("Set 1", score_options, index=score_options.index(selected_row["set1"]) if selected_row["set1"] in score_options else 0, key="edit_set1")
            set2 = st.selectbox("Set 2", score_options, index=score_options.index(selected_row["set2"]) if selected_row["set2"] in score_options else 0, key="edit_set2")
            set3 = st.selectbox("Set 3 (optional)", [""] + score_options, index=(score_options.index(selected_row["set3"]) + 1) if selected_row["set3"] in score_options else 0, key="edit_set3")

            winner = st.radio("Winner", ["Team 1", "Team 2"], index=0 if selected_row["winner"]=="Team 1" else 1, key="edit_winner")

            if st.button("Update Match"):
                matches.at[selected_idx, "team1_player1"] = p1
                matches.at[selected_idx, "team1_player2"] = p2
                matches.at[selected_idx, "team2_player1"] = p3
                matches.at[selected_idx, "team2_player2"] = p4
                matches.at[selected_idx, "set1"] = set1
                matches.at[selected_idx, "set2"] = set2
                matches.at[selected_idx, "set3"] = set3
                matches.at[selected_idx, "winner"] = winner
                save_matches(matches)
                st.success("Match updated.")
                st.experimental_rerun()

            if st.button("Delete Match"):
                matches = matches.drop(matches.index[selected_idx]).reset_index(drop=True)
                save_matches(matches)
                st.success("Match deleted.")
                st.experimental_rerun()

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

score_options = [
    "6-0", "6-1", "6-2", "6-3", "6-4", "7-5", "7-6",
    "0-6", "1-6", "2-6", "3-6", "4-6", "5-7", "6-7",
]

set1 = st.selectbox("Set 1", score_options, index=4)
set2 = st.selectbox("Set 2", score_options, index=4)
set3 = st.selectbox("Set 3 (optional)", [""] + score_options, index=0)

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

# Display Match Records
st.header("Match Records")
if not matches.empty:
    display = matches.copy()
    
    display["Players"] = display.apply(
        lambda row: f"{row['team1_player1']} & {row['team1_player2']} vs {row['team2_player1']} & {row['team2_player2']}",
        axis=1
    )
    
    def format_winner(row):
        if row["winner"] == "Team 1":
            return "🏆 " + f"{row['team1_player1']} & {row['team1_player2']}"
        elif row["winner"] == "Team 2":
            return "🏆 " + f"{row['team2_player1']} & {row['team2_player2']}"
        else:
            return row["winner"]

    display["Winner"] = display.apply(format_winner, axis=1)

    show_cols = ["date", "Players", "set1", "set2", "set3", "Winner", "id"]
    display = display[show_cols]

    display = display.rename(columns={
        "date": "Date",
        "set1": "Set 1",
        "set2": "Set 2",
        "set3": "Set 3",
        "id": "Match ID"
    })

    st.dataframe(display.style.format({"Date": lambda t: t.strftime("%d %b %Y") if pd.notnull(t) else ""}), use_container_width=True)

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
    st.dataframe(rankings)

# Player Partners and Best Partner
st.header("Player Partners and Best Partner")
for player, data in stats.items():
    partners = data["partners"]
    if partners:
        best_partner = max(partners, key=partners.get)
        st.write(f"**{player}** has played with: {', '.join(partners.keys())}. Most effective partner: {best_partner} ({partners[best_partner]} matches).")

