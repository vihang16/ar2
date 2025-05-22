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
    if "match_id" not in df.columns:
        df["match_id"] = [f"MIRA-OLD-{i}" for i in range(len(df))]
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
        elif winner == "Team 2":
            for p in team2:
                stats[p]["points"] += 3
                stats[p]["wins"] += 1
            for p in team1:
                stats[p]["points"] += 1
                stats[p]["losses"] += 1
        elif winner == "Tie":
            for p in team1 + team2:
                stats[p]["points"] += 1.5

        for p in team1 + team2:
            stats[p]["matches"] += 1

        stats[team1[0]]["partners"][team1[1]] += 1
        stats[team1[1]]["partners"][team1[0]] += 1
        stats[team2[0]]["partners"][team2[1]] += 1
        stats[team2[1]]["partners"][team2[0]] += 1

    return stats

def tennis_scores():
    return ["6-0", "6-1", "6-2", "6-3", "6-4", "7-5", "7-6", "0-6", "1-6", "2-6", "3-6", "4-6", "5-7", "6-7"]

# Custom CSS and header
st.markdown('''
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Offside&display=swap');
    html, body, [class*="st-"], h1, h2, h3, h4, h5, h6 {
        font-family: 'Offside', sans-serif !important;
    }
    </style>
''', unsafe_allow_html=True)

image_url = "https://raw.githubusercontent.com/mahadevbk/mmd/main/mmd.png"
st.markdown(f"<div style='text-align: center;'><img src='{image_url}' style='width: 150px;'/></div>", unsafe_allow_html=True)

st.title("Mira Mixed Doubles Tennis Group 🎾")

players = load_players()
matches = load_matches()

# Ensure match_id exists
if "match_id" not in matches.columns or matches["match_id"].isnull().any():
    for i in matches.index:
        if pd.isna(matches.at[i, "match_id"]):
            matches.at[i, "match_id"] = f"MIRA-{datetime.now().strftime('%y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}"
    save_matches(matches)

# Tabs
tab1, tab2, tab3, tab4 = st.tabs(["Post Match", "Match Records", "Rankings", "Player Stats"])

with tab1:
    st.header("Enter Match Result")
    available_players = players.copy()
    p1 = st.selectbox("Team 1 - Player 1", available_players, key="t1p1")
    available_players.remove(p1)
    p2 = st.selectbox("Team 1 - Player 2", available_players, key="t1p2")
    available_players.remove(p2)
    p3 = st.selectbox("Team 2 - Player 1", available_players, key="t2p1")
    available_players.remove(p3)
    p4 = st.selectbox("Team 2 - Player 2", available_players, key="t2p2")

    set1 = st.selectbox("Set 1", tennis_scores(), index=4)
    set2 = st.selectbox("Set 2", tennis_scores(), index=4)
    set3 = st.selectbox("Set 3 (optional)", [""] + tennis_scores())

    winner = st.radio("Winner", ["Team 1", "Team 2", "Tie"])

    if st.button("Submit Match"):
        new_match = {
            "match_id": f"MIRA-{datetime.now().strftime('%y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}",
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

with tab2:
    st.header("Match Records & Edit/Delete")

    matches["Date"] = pd.to_datetime(matches["date"], errors='coerce')
    matches = matches.sort_values(by="Date", ascending=False)
    matches["Date"] = matches["Date"].dt.strftime("%d %b %Y")

    def format_winner(row):
        if row["winner"] == "Team 1":
            return f"🏆 {row['team1_player1']} & {row['team1_player2']}"
        elif row["winner"] == "Team 2":
            return f"🏆 {row['team2_player1']} & {row['team2_player2']}"
        else:
            return "🤝 Tie"

    matches["Winner"] = matches.apply(format_winner, axis=1)
    matches["Match"] = matches.apply(lambda r: f"{r['team1_player1']} & {r['team1_player2']} vs {r['team2_player1']} & {r['team2_player2']}", axis=1)

    display = matches[["Date", "Match", "set1", "set2", "set3", "Winner", "match_id"]].copy()
    display.columns = ["Date", "Match", "Set 1", "Set 2", "Set 3", "Winner", "Match ID"]
    st.dataframe(display.style.hide(axis="index"), use_container_width=True)

    st.subheader("Edit/Delete Match")
    match_ids = matches["match_id"].dropna().tolist()
    selected_id = st.selectbox("Select Match ID", [""] + match_ids)

    if selected_id:
        selected_row = matches[matches["match_id"] == selected_id].iloc[0]
        st.markdown("### Edit Match Details")

        available_players = players.copy()
        p1 = st.selectbox("Team 1 - Player 1", available_players, index=available_players.index(selected_row["team1_player1"]))
        available_players.remove(p1)
        p2 = st.selectbox("Team 1 - Player 2", available_players, index=available_players.index(selected_row["team1_player2"]))
        available_players.remove(p2)
        p3 = st.selectbox("Team 2 - Player 1", available_players, index=available_players.index(selected_row["team2_player1"]))
        available_players.remove(p3)
        p4 = st.selectbox("Team 2 - Player 2", available_players, index=available_players.index(selected_row["team2_player2"]))

        set1 = st.selectbox("Set 1", tennis_scores(), index=tennis_scores().index(selected_row["set1"]))
        set2 = st.selectbox("Set 2", tennis_scores(), index=tennis_scores().index(selected_row["set2"]))
        set3 = st.selectbox("Set 3 (optional)", [""] + tennis_scores(), index=([""] + tennis_scores()).index(selected_row["set3"] if selected_row["set3"] else ""))

        winner = st.radio("Winner", ["Team 1", "Team 2", "Tie"], index=["Team 1", "Team 2", "Tie"].index(selected_row["winner"]))

        if st.button("Update Match"):
            match_index = matches[matches["match_id"] == selected_id].index[0]
            matches.at[match_index, "team1_player1"] = p1
            matches.at[match_index, "team1_player2"] = p2
            matches.at[match_index, "team2_player1"] = p3
            matches.at[match_index, "team2_player2"] = p4
            matches.at[match_index, "set1"] = set1
            matches.at[match_index, "set2"] = set2
            matches.at[match_index, "set3"] = set3
            matches.at[match_index, "winner"] = winner
            save_matches(matches)
            st.success("Match updated.")
            st.rerun()

        if st.button("Delete Match"):
            matches = matches[matches["match_id"] != selected_id]
            save_matches(matches)
            st.success("Match deleted.")
            st.rerun()

with tab3:
    st.header("Player Rankings")
    stats = compute_stats(matches)
    if stats:
        rankings = pd.DataFrame([
            {"Player": p, "Points": d["points"], "Wins": d["wins"], "Losses": d["losses"], "Matches": d["matches"]}
            for p, d in stats.items()
        ])
        rankings["Win %"] = rankings.apply(lambda r: round((r["Wins"] / r["Matches"] * 100), 1) if r["Matches"] else 0.0, axis=1)
        rankings = rankings.sort_values(by=["Points", "Wins"], ascending=False)
        rankings.index = range(1, len(rankings) + 1)
        rankings.index.name = "Rank"
        st.dataframe(rankings)

with tab4:
    st.header("Player Insights")
    selected_player = st.selectbox("Select Player", players)

    if selected_player:
        stats = compute_stats(matches)
        player_stats = stats.get(selected_player, {"points": 0, "wins": 0, "losses": 0, "matches": 0, "partners": {}})

        rankings_df = pd.DataFrame([
            {"Player": p, "Points": d["points"], "Wins": d["wins"], "Matches": d["matches"]}
            for p, d in stats.items()
        ])
        rankings_df["RankKey"] = rankings_df.apply(lambda r: (-r["Points"], -r["Wins"]), axis=1)
        rankings_df = rankings_df.sort_values(by="RankKey").reset_index(drop=True)
        rankings_df["Rank"] = rankings_df.index + 1
        player_rank = rankings_df[rankings_df["Player"] == selected_player]["Rank"].values[0]

        st.write(f"**🏅 Player Ranking:** #{player_rank}")
        st.write(f"**Points:** {player_stats['points']}")
        st.write(f"**Wins:** {player_stats['wins']}")
        st.write(f"**Losses:** {player_stats['losses']}")
        st.write(f"**Matches Played:** {player_stats['matches']}")
        win_pct = (player_stats["wins"] / player_stats["matches"] * 100) if player_stats["matches"] else 0
        st.write(f"**Win %:** {win_pct:.1f}%")

        if player_stats['partners']:
            st.write("**Partners Played With:**")
            for partner, count in sorted(player_stats['partners'].items(), key=lambda x: -x[1]):
                st.write(f"- {partner} ({count} matches)")
            best_partner = max(player_stats['partners'], key=player_stats['partners'].get)
            st.write(f"**Most Effective Partner:** {best_partner}")

with st.sidebar:
    st.header("Manage Players")
    new_player = st.text_input("Add Player").strip().upper()
    if st.button("Add Player"):
        if new_player and new_player not in players:
            players.append(new_player)
            players = sorted(set(players))
            save_players(players)
            st.success(f"{new_player} added.")
            st.rerun()
        elif new_player in players:
            st.warning(f"{new_player} is already in the list.")

    remove_player = st.selectbox("Remove Player", [""] + players)
    if st.button("Remove Selected Player"):
        if remove_player:
            players = [p for p in players if p != remove_player]
            save_players(players)
            st.success(f"{remove_player} removed.")
            st.rerun()
