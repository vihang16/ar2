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
                # track partners
                partner = [x for x in team1 if x != p][0]
                stats[p]["partners"][partner] += 1
            for p in team2:
                stats[p]["points"] += 1
                stats[p]["losses"] += 1
                partner = [x for x in team2 if x != p][0]
                stats[p]["partners"][partner] += 1
        else:
            for p in team2:
                stats[p]["points"] += 3
                stats[p]["wins"] += 1
                partner = [x for x in team2 if x != p][0]
                stats[p]["partners"][partner] += 1
            for p in team1:
                stats[p]["points"] += 1
                stats[p]["losses"] += 1
                partner = [x for x in team1 if x != p][0]
                stats[p]["partners"][partner] += 1
        for p in team1 + team2:
            stats[p]["matches"] += 1
    return stats

# Score options for dropdowns (common tennis set scores)
score_options = [
    "6-0", "6-1", "6-2", "6-3", "6-4", "7-5", "7-6",
    "0-6", "1-6", "2-6", "3-6", "4-6", "5-7", "6-7", ""
]

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
    new_player = st.text_input("Add New Player", key="sidebar_add_player").upper()
    if st.button("Add Player", key="sidebar_add_player_btn") and new_player and new_player not in players:
        players.append(new_player)
        save_players(players)
        st.experimental_rerun()

    remove_player = st.selectbox("Remove Player", [""] + players, key="sidebar_remove_player")
    if st.button("Remove Selected Player", key="sidebar_remove_player_btn") and remove_player:
        players.remove(remove_player)
        save_players(players)
        st.experimental_rerun()

    st.markdown("---")
    st.header("Edit/Delete Matches")

    if matches.empty:
        st.write("No matches to edit.")
    else:
        match_ids = matches["id"].tolist()
        selected_match_id = st.selectbox("Select Match to Edit/Delete", [""] + match_ids, key="sidebar_select_match")

        if selected_match_id:
            match_idx = matches.index[matches["id"] == selected_match_id][0]
            match_row = matches.loc[match_idx]

            # Show editable fields with unique keys
            t1p1 = st.selectbox("Team 1 - Player 1", players, index=players.index(match_row["team1_player1"]), key="edit_t1p1")
            t1p2 = st.selectbox("Team 1 - Player 2", [p for p in players if p != t1p1], index=[p for p in players if p != t1p1].index(match_row["team1_player2"]), key="edit_t1p2")
            t2p1 = st.selectbox("Team 2 - Player 1", [p for p in players if p not in [t1p1, t1p2]], index=[p for p in players if p not in [t1p1, t1p2]].index(match_row["team2_player1"]), key="edit_t2p1")
            t2p2 = st.selectbox("Team 2 - Player 2", [p for p in players if p not in [t1p1, t1p2, t2p1]], index=[p for p in players if p not in [t1p1, t1p2, t2p1]].index(match_row["team2_player2"]), key="edit_t2p2")

            set1 = st.selectbox("Set 1", score_options, index=score_options.index(match_row["set1"]) if match_row["set1"] in score_options else 0, key="edit_set1")
            set2 = st.selectbox("Set 2", score_options, index=score_options.index(match_row["set2"]) if match_row["set2"] in score_options else 0, key="edit_set2")
            set3 = st.selectbox("Set 3 (optional)", score_options, index=score_options.index(match_row["set3"]) if match_row["set3"] in score_options else 0, key="edit_set3")
            winner = st.radio("Winner", ["Team 1", "Team 2"], index=0 if match_row["winner"]=="Team 1" else 1, key="edit_winner")

            if st.button("Save Changes", key="save_match_changes"):
                matches.at[match_idx, "team1_player1"] = t1p1
                matches.at[match_idx, "team1_player2"] = t1p2
                matches.at[match_idx, "team2_player1"] = t2p1
                matches.at[match_idx, "team2_player2"] = t2p2
                matches.at[match_idx, "set1"] = set1
                matches.at[match_idx, "set2"] = set2
                matches.at[match_idx, "set3"] = set3
                matches.at[match_idx, "winner"] = winner
                save_matches(matches)
                st.success("Match updated.")
                st.experimental_rerun()

            if st.button("Delete Match", key="delete_match_btn"):
                matches = matches.drop(match_idx).reset_index(drop=True)
                save_matches(matches)
                st.success("Match deleted.")
                st.experimental_rerun()

st.header("Enter Match Result")

available_players = players.copy()
p1 = st.selectbox("Team 1 - Player 1", available_players, key="new_t1p1")
available_players = [p for p in available_players if p != p1]
p2 = st.selectbox("Team 1 - Player 2", available_players, key="new_t1p2")
available_players = [p for p in available_players if p != p2]
p3 = st.selectbox("Team 2 - Player 1", available_players, key="new_t2p1")
available_players = [p for p in available_players if p != p3]
p4 = st.selectbox("Team 2 - Player 2", available_players, key="new_t2p2")

set1 = st.selectbox("Set 1", score_options, index=4, key="new_set1")  # default 6-4
set2 = st.selectbox("Set 2", score_options, index=4, key="new_set2")  # default 6-4
set3 = st.selectbox("Set 3 (optional)", score_options, index=8, key="new_set3")  # default ""

winner = st.radio("Winner", ["Team 1", "Team 2"], key="new_winner")

if st.button("Submit Match", key="submit_new_match"):
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

# Prepare match records display
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

    # Select columns to show - exclude the default unnamed index column from gspread load
    show_cols = ["Date", "Players", "set1", "set2", "set3", "Winner"]
    display = display[show_cols]

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
else:
    st.write("No rankings available yet.")

# Player insights including partners
st.header("Player Insights")
selected_player = st.selectbox("Select Player", players, key="player_insights")
if selected_player:
    data = stats.get(selected_player, {"points": 0, "wins": 0, "losses": 0, "matches": 0, "partners": {}})
    st.write(f"**Points:** {data['points']}")
    st.write(f"**Wins:** {data['wins']}")
    st.write(f"**Losses:** {data['losses']}")
    st.write(f"**Matches Played:** {data['matches']}")
    win_pct = (data["wins"] / data["matches"] * 100) if data["matches"] else 0
    st.write(f"**Win %:** {win_pct:.1f}%")

    # Show partners and most effective partner
    partners = data.get("partners", {})
    if partners:
        st.write("### Partners Played With:")
        partners_df = pd.DataFrame(list(partners.items()), columns=["Partner", "Matches Together"])
        partners_df = partners_df.sort_values(by="Matches Together", ascending=False)
        st.table(partners_df)

        # Most effective partner by win ratio
        partner_stats = []
        for partner in partners.keys():
            # Count wins together
            wins_together = 0
            matches_together = 0
            for _, row in matches.iterrows():
                team = [row["team1_player1"], row["team1_player2"]] if selected_player in [row["team1_player1"], row["team1_player2"]] else [row["team2_player1"], row["team2_player2"]]
                if partner in team and selected_player in team:
                    matches_together += 1
                    if (row["winner"] == "Team 1" and selected_player in [row["team1_player1"], row["team1_player2"]]) or \
                       (row["winner"] == "Team 2" and selected_player in [row["team2_player1"], row["team2_player2"]]):
                        wins_together += 1
            win_ratio = wins_together / matches_together if matches_together else 0
            partner_stats.append((partner, win_ratio, matches_together))
        if partner_stats:
            partner_stats.sort(key=lambda x: x[1], reverse=True)
            best_partner = partner_stats[0]
            st.write(f"**Most Effective Partner:** {best_partner[0]} with a win rate of {best_partner[1]*100:.1f}% over {best_partner[2]} matches")
    else:
        st.write("No partner data available yet.")
