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
        if winner == "Team 1":
            for p in team1:
                stats[p]["points"] += 3
                stats[p]["wins"] += 1
                # Count partners
                partner = [x for x in team1 if x != p][0]
                stats[p]["partners"][partner] += 1
            for p in team2:
                stats[p]["points"] += 1
                stats[p]["losses"] += 1
        else:
            for p in team2:
                stats[p]["points"] += 3
                stats[p]["wins"] += 1
                partner = [x for x in team2 if x != p][0]
                stats[p]["partners"][partner] += 1
            for p in team1:
                stats[p]["points"] += 1
                stats[p]["losses"] += 1
        for p in team1 + team2:
            stats[p]["matches"] += 1
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

# Date parsing fix: normalize date column
if not matches.empty and "date" in matches.columns:
    # First try generic parse
    matches["date"] = pd.to_datetime(matches["date"], errors="coerce", dayfirst=False)
    # For unparsed dates (NaT), try MM/DD/YYYY format
    mask = matches["date"].isna()
    if mask.any():
        # Use original string column for fallback parsing
        original_dates = matches.loc[mask, "date"].astype(str)
        fallback_dates = pd.to_datetime(original_dates, format="%m/%d/%Y", errors="coerce")
        matches.loc[mask, "date"] = fallback_dates

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

# Tennis possible set scores dropdown options
score_options = ["6-0", "6-1", "6-2", "6-3", "6-4", "7-5", "7-6", "0-6", "1-6", "2-6", "3-6", "4-6", "5-7", "6-7"]

st.markdown("**Enter Set Scores (Best of 3 sets)**")
set1 = st.selectbox("Set 1", score_options, index=4)
set2 = st.selectbox("Set 2", score_options, index=4)
set3 = st.selectbox("Set 3 (optional)", [""] + score_options, index=0)

winner = st.radio("Winner", ["Team 1", "Team 2"])

if st.button("Submit Match"):
    new_match = {
        "id": f"MIRA-{datetime.now().strftime('%y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}",
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
    st.experimental_rerun()

# --- Edit and Delete Matches ---
st.sidebar.header("Edit or Delete Match")

if not matches.empty:
    # Show matches with match id and players for selection
    matches["display_name"] = matches.apply(
        lambda r: f"{r['team1_player1']} & {r['team1_player2']} vs {r['team2_player1']} & {r['team2_player2']} ({r.get('id', 'No ID')})",
        axis=1
    )
    selected_match_str = st.sidebar.selectbox("Select Match to Edit/Delete", [""] + matches["display_name"].tolist())
    
    if selected_match_str:
        # Extract match id from selected string
        selected_id = selected_match_str.split("(")[-1].replace(")", "")
        selected_match = matches[matches.get("id", pd.Series()).fillna("").astype(str) == selected_id]
        
        if not selected_match.empty:
            sm = selected_match.iloc[0]

            with st.sidebar.form("edit_match_form"):
                e_p1 = st.selectbox("Team 1 - Player 1", players, index=players.index(sm["team1_player1"]))
                e_p2 = st.selectbox("Team 1 - Player 2", players, index=players.index(sm["team1_player2"]))
                e_p3 = st.selectbox("Team 2 - Player 1", players, index=players.index(sm["team2_player1"]))
                e_p4 = st.selectbox("Team 2 - Player 2", players, index=players.index(sm["team2_player2"]))
                e_set1 = st.selectbox("Set 1", score_options, index=score_options.index(sm["set1"]) if sm["set1"] in score_options else 0)
                e_set2 = st.selectbox("Set 2", score_options, index=score_options.index(sm["set2"]) if sm["set2"] in score_options else 0)
                e_set3 = st.selectbox("Set 3 (optional)", [""] + score_options, index=(score_options.index(sm["set3"]) + 1) if sm["set3"] in score_options else 0)
                e_winner = st.radio("Winner", ["Team 1", "Team 2"], index=0 if sm["winner"] == "Team 1" else 1)
                
                submitted = st.form_submit_button("Update Match")
                if submitted:
                    matches.loc[matches.index == sm.name, ["team1_player1","team1_player2","team2_player1","team2_player2","set1","set2","set3","winner"]] = [
                        e_p1, e_p2, e_p3, e_p4, e_set1, e_set2, e_set3, e_winner
                    ]
                    save_matches(matches)
                    st.success("Match updated.")
                    st.experimental_rerun()

            if st.sidebar.button("Delete Match"):
                matches = matches[matches.index != sm.name]
                save_matches(matches)
                st.success("Match deleted.")
                st.experimental_rerun()

# Show match records
st.header("Match Records")
if not matches.empty:
    display = matches.copy()

    # Format date nicely or blank if NaT
    display["Date"] = display["date"].dt.strftime("%d %b %Y").fillna("")
    
    # Construct player pairs
    display["Players"] = display.apply(
        lambda row: f"{row['team1_player1']} & {row['team1_player2']} vs {row['team2_player1']} & {row['team2_player2']}",
        axis=1
    )
    
    # Show winner names with cup emoji prefix
    def format_winner(row):
        if row["winner"] == "Team 1":
            return "🏆 " + f"{row['team1_player1']} & {row['team1_player2']}"
        elif row["winner"] == "Team 2":
            return "🏆 " + f"{row['team2_player1']} & {row['team2_player2']}"
        else:
            return row["winner"]

    display["Winner"] = display.apply(format_winner, axis=1)

    # Select columns to show and order, add match id at end
    show_cols = ["Date", "Players", "set1", "set2", "set3", "Winner", "id"]
    display = display[show_cols]

    # Rename columns for display
    display = display.rename(columns={
        "set1": "Set 1",
        "set2": "Set 2",
        "set3": "Set 3",
        "id": "Match ID"
    })

    st.dataframe(display, use_container_width=True)

# Show player rankings
st.header("Player Rankings")
stats = compute_stats(matches)
if stats:
    rankings = pd.DataFrame([
        {"Player": p, 
         "Points": d["points"], 
         "Wins": d["wins"], 
         "Losses": d["losses"], 
         "Matches": d["matches"],
         "Most Effective Partner": max(d["partners"], key=d["partners"].get) if d["partners"] else "N/A",
         "Partners Played With": ", ".join(f"{partner} ({count})" for partner, count in d["partners"].items())
        }
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
    # Show partners info
    st.write(f"**Partners Played With:**")
    if data["partners"]:
        for partner, count in data["partners"].items():
            st.write(f"- {partner}: {count} match{'es' if count > 1 else ''}")
        most_eff = max(data["partners"], key=data["partners"].get)
        st.write(f"**Most Effective Partner:** {most_eff} ({data['partners'][most_eff]} matches)")
    else:
        st.write("No partners data available.")

