import streamlit as st
import pandas as pd
import uuid
from datetime import datetime
from collections import defaultdict
from supabase import create_client, Client

# Supabase setup
supabase_url = st.secrets["supabase"]["supabase_url"]
supabase_key = st.secrets["supabase"]["supabase_key"]
supabase: Client = create_client(supabase_url, supabase_key)

# Table names
players_table_name = "players"
matches_table_name = "matches"
bookings_table_name = "bookings"

court_list = [
    "Mira 2", "Mira 4", "Mira 5 A", "Mira 5 B",
    "Mira Oasis 1", "Mira Oasis 2", "Mira Oasis 3 A", "Mira Oasis 3 B", "Mira Oasis 3C",
    "AR Palmera 2", "AR Palmera 4", "AR Alvorada 1", "AR Alvorada 2",
    "AR Mirador La Collecion", "AR Hattan", "AR Saheel", "AR Alma", "AR Al Mahra", "AR Mirador",
    "AR Reem 1", "AR Reem 2", "AR Reem 3", "Mudon Main (Rahat)", "Mudon Arabella", "Mudon Arabella 3",
    "AR2 Rosa", "AR2 Palma", "AR2 Fitness First"
]

time_slots = [f"{h}:00 {'AM' if h < 12 else 'PM'}" for h in range(6, 22)]

def load_players():
    try:
        response = supabase.table(players_table_name).select("name").execute()
        df = pd.DataFrame(response.data)
        return df["name"].dropna().tolist() if "name" in df.columns else []
    except Exception as e:
        st.error(f"Error loading players: {str(e)}")
        return []

def save_players(players):
    try:
        supabase.table(players_table_name).delete().neq("name", "").execute()
        data = [{"name": player} for player in players]
        supabase.table(players_table_name).insert(data).execute()
    except Exception as e:
        st.error(f"Error saving players: {str(e)}")

def load_matches():
    try:
        response = supabase.table(matches_table_name).select("*").execute()
        df = pd.DataFrame(response.data)
        expected_columns = ["match_id", "date", "team1_player1", "team1_player2", 
                            "team2_player1", "team2_player2", "set1", "set2", "set3", "winner"]
        for col in expected_columns:
            if col not in df.columns:
                df[col] = ""
        return df
    except Exception as e:
        st.error(f"Error loading matches: {str(e)}")
        return pd.DataFrame(columns=expected_columns)

def save_matches(df):
    try:
        supabase.table(matches_table_name).delete().neq("match_id", "").execute()
        supabase.table(matches_table_name).insert(df.to_dict("records")).execute()
    except Exception as e:
        st.error(f"Error saving matches: {str(e)}")

def load_bookings():
    try:
        response = supabase.table(bookings_table_name).select("*").execute()
        df = pd.DataFrame(response.data)
        expected_columns = ["booking_id", "date", "time", "court", "players"]
        for col in expected_columns:
            if col not in df.columns:
                df[col] = ""
        return df
    except Exception as e:
        st.error(f"Error loading bookings: {str(e)}")
        return pd.DataFrame(columns=["booking_id", "date", "time", "court", "players"])

def save_bookings(df):
    try:
        supabase.table(bookings_table_name).delete().neq("booking_id", "").execute()
        supabase.table(bookings_table_name).insert(df.to_dict("records")).execute()
    except Exception as e:
        st.error(f"Error saving bookings: {str(e)}")

def compute_stats(matches):
    stats = defaultdict(lambda: {"points": 0, "wins": 0, "losses": 0, "matches": 0, "partners": defaultdict(int)})
    if matches.empty:
        return stats
    for _, row in matches.iterrows():
        if not all(row.get(col) for col in ["team1_player1", "team1_player2", "team2_player1", "team2_player2"]):
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

# --- UI Code ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Offside&display=swap');
    html, body, [class*="st-"], h1, h2, h3, h4, h5, h6 {
        font-family: 'Offside', sans-serif !important;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown("<div style='text-align: center;'><img src='https://raw.githubusercontent.com/mahadevbk/mmd/main/mmd.png' style='width: 150px;'/></div>", unsafe_allow_html=True)
st.title("Mira Mixed Doubles Tennis Group 🎾")

players = load_players()
matches = load_matches()

# Assign match ID if missing
if not matches.empty and ("match_id" not in matches.columns or matches["match_id"].isnull().any()):
    for i in matches.index:
        if pd.isna(matches.at[i, "match_id"]):
            matches.at[i, "match_id"] = f"MIRA-{datetime.now().strftime('%y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}"
    save_matches(matches)

tab1, tab2, tab3, tab4, tab5 = st.tabs(["Post Match", "Match Records", "Rankings", "Player Stats", "Game Bookings"])

# ----- POST MATCH -----
with tab1:
    st.header("Enter Match Result")
    available_players = players.copy()
    p1 = st.selectbox("Team 1 - Player 1", available_players, key="t1p1")
    if p1 in available_players:
        available_players.remove(p1)
    p2 = st.selectbox("Team 1 - Player 2", available_players, key="t1p2")
    if p2 in available_players:
        available_players.remove(p2)
    p3 = st.selectbox("Team 2 - Player 1", available_players, key="t2p1")
    if p3 in available_players:
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

# You can continue using the same pattern for other tabs (Match Records, Rankings, Stats, Bookings, etc.)

# ----- SIDEBAR -----
with st.sidebar:
    st.header("🎾 Manage Players")

    new_player = st.text_input("Add Player").strip()
    if st.button("Add Player"):
        if new_player:
            if new_player not in players:
                players.append(new_player)
                players = sorted(set(players))
                save_players(players)
                st.success(f"{new_player} added.")
                st.rerun()
            else:
                st.warning(f"{new_player} is already in the list.")
        else:
            st.warning("Please enter a valid player name.")

    st.markdown("---")

    remove_player = st.selectbox("Remove Player", [""] + players)
    if st.button("Remove Selected Player"):
        if remove_player:
            players = [p for p in players if p != remove_player]
            save_players(players)
            st.success(f"{remove_player} removed.")
            st.rerun()

