import streamlit as st
import pandas as pd
import uuid
from datetime import datetime
from collections import defaultdict, Counter
from supabase import create_client, Client

# Supabase setup
supabase_url = st.secrets["supabase"]["supabase_url"]
supabase_key = st.secrets["supabase"]["supabase_key"]
supabase: Client = create_client(supabase_url, supabase_key)

# Table names
players_table_name = "players"
matches_table_name = "matches"
bookings_table_name = "bookings"

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
        expected_columns = ["match_id", "date", "match_type", "team1_player1", "team1_player2", "team2_player1", "team2_player2", "set1", "set2", "set3", "winner"]
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

#st.markdown("<div style='text-align: center;'><img src='https://raw.githubusercontent.com/mahadevbk/mmd/main/mmd.png' style='width: 150px;'/></div>", unsafe_allow_html=True)
st.title("AR2 Tennis Group 🎾")

players = load_players()
matches = load_matches()

if not matches.empty and ("match_id" not in matches.columns or matches["match_id"].isnull().any()):
    for i in matches.index:
        if pd.isna(matches.at[i, "match_id"]):
            matches.at[i, "match_id"] = f"AR2-{datetime.now().strftime('%y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}"
    save_matches(matches)

tab1, tab2, tab3 = st.tabs(["Post Match", "Match Records", "Rankings"])

# ----- POST MATCH -----
with tab1:
    st.header("Enter Match Result")

    match_type = st.radio("Match Type", ["Doubles", "Singles"], horizontal=True)

    available_players = players.copy()

    if match_type == "Doubles":
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
    else:
        p1 = st.selectbox("Player 1", available_players, key="s1p1")
        if p1 in available_players:
            available_players.remove(p1)
        p3 = st.selectbox("Player 2", available_players, key="s1p2")
        p2 = ""
        p4 = ""

    set1 = st.selectbox("Set 1", tennis_scores(), index=4)
    set2 = st.selectbox("Set 2", tennis_scores(), index=4)
    set3 = st.selectbox("Set 3 (optional)", [""] + tennis_scores())

    winner = st.radio("Winner", ["Team 1", "Team 2", "Tie"])

    if st.button("Submit Match"):
        new_match = {
            "match_id": f"AR2-{datetime.now().strftime('%y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "match_type": match_type,
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

# ----- MATCH RECORDS -----
with tab2:
    st.header("Match History")
    match_filter = st.radio("Filter by Type", ["All", "Singles", "Doubles"], horizontal=True)

    filtered_matches = matches.copy()
    if match_filter != "All":
        filtered_matches = filtered_matches[filtered_matches["match_type"] == match_filter]

    st.dataframe(filtered_matches.sort_values(by="date", ascending=False), use_container_width=True)

# ----- RANKINGS -----
with tab3:
    st.header("Player Rankings")
    scores = defaultdict(int)
    partners = defaultdict(list)
    results = []

    for _, row in matches.iterrows():
        if row['winner'] == 'Tie':
            continue
        t1 = [row['team1_player1']]
        t2 = [row['team2_player1']]
        if row['match_type'] == 'Doubles':
            t1.append(row['team1_player2'])
            t2.append(row['team2_player2'])

        if row['winner'] == 'Team 1':
            for p in t1:
                scores[p] += 3
            for p in t2:
                scores[p] -= 1
        else:
            for p in t2:
                scores[p] += 3
            for p in t1:
                scores[p] -= 1

        if row['match_type'] == 'Doubles':
            if row['team1_player1'] and row['team1_player2']:
                partners[row['team1_player1']].append(row['team1_player2'])
                partners[row['team1_player2']].append(row['team1_player1'])
            if row['team2_player1'] and row['team2_player2']:
                partners[row['team2_player1']].append(row['team2_player2'])
                partners[row['team2_player2']].append(row['team2_player1'])

    rank_df = pd.DataFrame(scores.items(), columns=["Player", "Points"])
    rank_df = rank_df.sort_values(by="Points", ascending=False).reset_index(drop=True)
    st.dataframe(rank_df, use_container_width=True)

    st.subheader("Player Insights")
    selected = st.selectbox("Select a player", players)
    if selected:
        st.markdown(f"**Partners Played With**: {dict(Counter(partners[selected]))}")
        if partners[selected]:
            best = Counter(partners[selected]).most_common(1)[0][0]
            st.markdown(f"**Most Frequent Partner**: {best}")

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

st.markdown("""
<div style='
    background-color: #292481;
    padding: 1rem;
    border-left: 5px solid #fff500;
    border-radius: 0.5rem;
    color: white;
    font-family: sans-serif;
'>
    Built with ❤️ using <a href='https://streamlit.io/' style='color: #fff500;'>Streamlit</a> — free and open source. 
    <a href='https://devs-scripts.streamlit.app/' style='color: #fff500;'>Other Scripts by dev</a> on Streamlit.
</div>
""", unsafe_allow_html=True)

