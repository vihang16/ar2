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
bookings_sheet_name = "Mira Bookings"

spreadsheet = client.open(SHEET_NAME)

def get_or_create_worksheet(sheet, name, rows=1000, cols=20):
    try:
        return sheet.worksheet(name)
    except gspread.exceptions.WorksheetNotFound:
        return sheet.add_worksheet(title=name, rows=str(rows), cols=str(cols))
    except Exception as e:
        st.error(f"Error accessing Google Sheet: {str(e)}")
        return None

players_sheet = get_or_create_worksheet(spreadsheet, players_sheet_name)
matches_sheet = get_or_create_worksheet(spreadsheet, matches_sheet_name)
bookings_sheet = get_or_create_worksheet(spreadsheet, bookings_sheet_name)

# Initialize bookings sheet with headers
def initialize_bookings_sheet():
    headers = ["booking_id", "date", "time", "court", "players"]
    try:
        current_headers = bookings_sheet.row_values(1)
        if not current_headers:
            bookings_sheet.update([headers])
    except Exception as e:
        st.error(f"Error initializing bookings sheet: {str(e)}")

if bookings_sheet:
    initialize_bookings_sheet()

# Booking court list
court_list = [
    "Mira 2", "Mira 4", "Mira 5 A", "Mira 5 B",
    "Mira Oasis 1", "Mira Oasis 2", "Mira Oasis 3 A", "Mira Oasis 3 B", "Mira Oasis 3C",
    "AR Palmera 2", "AR Palmera 4", "AR Alvorada 1", "AR Alvorada 2",
    "AR Mirador La Collecion", "AR Hattan", "AR Saheel", "AR Alma", "AR Al Mahra", "AR Mirador",
    "AR Reem 1", "AR Reem 2", "AR Reem 3", "Mudon Main (Rahat)", "Mudon Arabella", "Mudon Arabella 3",
    "AR2 Rosa", "AR2 Palma", "AR2 Fitness First"
]

time_slots = [f"{h}:00 {'AM' if h < 12 else 'PM'}" for h in range(6, 22)]

def load_bookings():
    try:
        df = pd.DataFrame(bookings_sheet.get_all_records())
        # Define expected columns
        expected_columns = ["booking_id", "date", "time", "court", "players"]
        # If DataFrame is empty or missing columns, initialize with expected columns
        for col in expected_columns:
            if col not in df.columns:
                df[col] = ""
        # Generate booking_id if missing
        if not df.empty and "booking_id" not in df.columns:
            df["booking_id"] = [f"BOOK-{i}" for i in range(len(df))]
        return df
    except Exception as e:
        st.error(f"Error loading bookings: {str(e)}")
        return pd.DataFrame(columns=["booking_id", "date", "time", "court", "players"])

def save_bookings(df):
    try:
        bookings_sheet.clear()
        bookings_sheet.update([df.columns.tolist()] + df.values.tolist())
    except Exception as e:
        st.error(f"Error saving bookings: {str(e)}")

def load_players():
    try:
        df = pd.DataFrame(players_sheet.get_all_records())
        if "Player" not in df.columns:
            return []
        return df["Player"].dropna().str.upper().tolist()
    except Exception as e:
        st.error(f"Error loading players: {str(e)}")
        return []

def save_players(players):
    try:
        df = pd.DataFrame({"Player": players})
        players_sheet.clear()
        players_sheet.update([df.columns.tolist()] + df.values.tolist())
    except Exception as e:
        st.error(f"Error saving players: {str(e)}")

def load_matches():
    try:
        df = pd.DataFrame(matches_sheet.get_all_records())
        # Define expected columns
        expected_columns = ["match_id", "date", "team1_player1", "team1_player2", 
                           "team2_player1", "team2_player2", "set1", "set2", "set3", "winner"]
        # If DataFrame is empty or missing columns, initialize with expected columns
        for col in expected_columns:
            if col not in df.columns:
                df[col] = ""
        # Generate match_id if missing
        if not df.empty and "match_id" not in df.columns:
            df["match_id"] = [f"MIRA-OLD-{i}" for i in range(len(df))]
        return df
    except Exception as e:
        st.error(f"Error loading matches: {str(e)}")
        return pd.DataFrame(columns=expected_columns)

def save_matches(df):
    try:
        matches_sheet.clear()
        matches_sheet.update([df.columns.tolist()] + df.values.tolist())
    except Exception as e:
        st.error(f"Error saving matches: {str(e)}")

def compute_stats(matches):
    stats = defaultdict(lambda: {"points": 0, "wins": 0, "losses": 0, "matches": 0, "partners": defaultdict(int)})
    if matches.empty:
        return stats
    # Ensure required columns exist
    required_columns = ["team1_player1", "team1_player2", "team2_player1", "team2_player2", "winner"]
    if not all(col in matches.columns for col in required_columns):
        return stats
    for _, row in matches.iterrows():
        # Skip rows with missing player data
        if not all(row.get(col) for col in required_columns[:-1]):
            continue
        team1 = [row["team1_player1"], row["team1_player2"]]
        team2 = [row["team2_player1"], row["team2_player2"]]
        winner = row["winner"]
        if not winner:
            continue
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
if not matches.empty and ("match_id" not in matches.columns or matches["match_id"].isnull().any()):
    for i in matches.index:
        if pd.isna(matches.at[i, "match_id"]):
            matches.at[i, "match_id"] = f"MIRA-{datetime.now().strftime('%y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}"
    save_matches(matches)

# Tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs(["Post a Match", "Match Records", "Rankings", "Player Stats", "Game Bookings"])

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
    if matches.empty:
        st.write("No match records available.")
    else:
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
            p1 = st.selectbox("Team 1 - Player 1", available_players, 
                             index=available_players.index(selected_row["team1_player1"]) if selected_row["team1_player1"] in available_players else 0)
            available_players.remove(p1)
            p2 = st.selectbox("Team 1 - Player 2", available_players, 
                             index=available_players.index(selected_row["team1_player2"]) if selected_row["team1_player2"] in available_players else 0)
            available_players.remove(p2)
            p3 = st.selectbox("Team 2 - Player 1", available_players, 
                             index=available_players.index(selected_row["team2_player1"]) if selected_row["team2_player1"] in available_players else 0)
            available_players.remove(p3)
            p4 = st.selectbox("Team 2 - Player 2", available_players, 
                             index=available_players.index(selected_row["team2_player2"]) if selected_row["team2_player2"] in available_players else 0)

            set1 = st.selectbox("Set 1", tennis_scores(), 
                               index=tennis_scores().index(selected_row["set1"]) if selected_row["set1"] in tennis_scores() else 0)
            set2 = st.selectbox("Set 2", tennis_scores(), 
                               index=tennis_scores().index(selected_row["set2"]) if selected_row["set2"] in tennis_scores() else 0)
            set3 = st.selectbox("Set 3 (optional)", [""] + tennis_scores(), 
                               index=([""] + tennis_scores()).index(selected_row["set3"] if selected_row["set3"] else ""))

            winner = st.radio("Winner", ["Team 1", "Team 2", "Tie"], 
                             index=["Team 1", "Team 2", "Tie"].index(selected_row["winner"]) if selected_row["winner"] in ["Team 1", "Team 2", "Tie"] else 0)

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
    else:
        st.write("No rankings available. Add matches to generate rankings.")

with tab4:
    st.header("Player Insights")
    selected_player = st.selectbox("Select Player", players)

    if selected_player:
        stats = compute_stats(matches)
        default_stats = {"points": 0, "wins": 0, "losses": 0, "matches": 0, "partners": defaultdict(int)}
        player_stats = stats.get(selected_player, default_stats)

        rankings_df = pd.DataFrame([
            {"Player": p, "Points": d["points"], "Wins": d["wins"], "Matches": d["matches"]}
            for p, d in stats.items()
        ])
        if not rankings_df.empty:
            rankings_df["RankKey"] = rankings_df.apply(lambda r: (-r["Points"], -r["Wins"]), axis=1)
            rankings_df = rankings_df.sort_values(by="RankKey").reset_index(drop=True)
            rankings_df["Rank"] = rankings_df.index + 1
            player_rank = rankings_df[rankings_df["Player"] == selected_player]["Rank"].values[0] if not rankings_df[rankings_df["Player"] == selected_player].empty else "N/A"
        else:
            player_rank = "N/A"

        if player_stats["matches"] == 0:
            st.write(f"No match data available for {selected_player}.")
        else:
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

with tab5:
    st.header("🎾 Game Bookings")
    bookings = load_bookings()

    st.subheader("New Booking")
    selected_court = st.selectbox("Select Court", court_list)
    selected_date = st.date_input("Select Date")
    selected_time = st.selectbox("Select Time Slot", time_slots)
    selected_players = st.multiselect("Select Players", players)

    if st.button("Submit Booking"):
        if not selected_players:
            st.warning("Please select at least one player.")
        else:
            # Check for conflicting bookings
            conflict = bookings[
                (bookings["date"] == selected_date.strftime("%Y-%m-%d")) &
                (bookings["time"] == selected_time) &
                (bookings["court"] == selected_court)
            ]
            if not conflict.empty:
                st.error("This court is already booked for the selected date and time.")
            else:
                new_booking = {
                    "booking_id": f"BOOK-{datetime.now().strftime('%y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}",
                    "date": selected_date.strftime("%Y-%m-%d"),
                    "time": selected_time,
                    "court": selected_court,
                    "players": ", ".join(selected_players)
                }
                bookings = pd.concat([bookings, pd.DataFrame([new_booking])], ignore_index=True)
                save_bookings(bookings)
                st.success("Booking submitted.")
                st.rerun()

    st.subheader("📅 Manage Bookings")
    if bookings.empty:
        st.write("No bookings available.")
    else:
        bookings["date"] = pd.to_datetime(bookings["date"], errors='coerce')
        bookings = bookings.sort_values(by=["date", "time"])
        bookings["Date"] = bookings["date"].dt.strftime("%d %b %Y")
        bookings["Players"] = bookings["players"]
        bookings_display = bookings[["Date", "time", "court", "Players", "booking_id"]]
        bookings_display.columns = ["Date", "Time", "Court", "Players", "Booking ID"]
        st.dataframe(bookings_display.style.hide(axis="index"), use_container_width=True)

    st.subheader("Edit/Delete Booking")
    booking_ids = bookings["booking_id"].dropna().tolist()
    selected_booking_id = st.selectbox("Select Booking ID", [""] + booking_ids)

    if selected_booking_id:
        row = bookings[bookings["booking_id"] == selected_booking_id].iloc[0]
        edit_court = st.selectbox("Edit Court", court_list, 
                                 index=court_list.index(row["court"]) if row["court"] in court_list else 0)
        edit_date = st.date_input("Edit Date", 
                                 pd.to_datetime(row["date"]) if pd.notnull(row["date"]) else datetime.now())
        edit_time = st.selectbox("Edit Time", time_slots, 
                                index=time_slots.index(row["time"]) if row["time"] in time_slots else 0)
        current_players = row["players"].split(", ") if row["players"] else []
        edit_players = st.multiselect("Edit Players", players, 
                                    default=[p for p in current_players if p in players])

        if st.button("Update Booking"):
            index = bookings[bookings["booking_id"] == selected_booking_id].index[0]
            bookings.at[index, "court"] = edit_court
            bookings.at[index, "date"] = edit_date.strftime("%Y-%m-%d")
            bookings.at[index, "time"] = edit_time
            bookings.at[index, "players"] = ", ".join(edit_players)
            save_bookings(bookings)
            st.success("Booking updated.")
            st.rerun()

        if st.button("Delete Booking"):
            bookings = bookings[bookings["booking_id"] != selected_booking_id]
            save_bookings(bookings)
            st.success("Booking deleted.")
            st.rerun()

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
        else:
            st.warning("Please enter a valid player name.")

    remove_player = st.selectbox("Remove Player", [""] + players)
    if st.button("Remove Selected Player"):
        if remove_player:
            players = [p for p in players if p != remove_player]
            save_players(players)
            st.success(f"{remove_player} removed.")
            st.rerun()
