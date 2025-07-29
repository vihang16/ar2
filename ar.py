import streamlit as st
import pandas as pd
import uuid
from datetime import datetime
from collections import defaultdict, Counter
from supabase import create_client, Client
import plotly.express as px

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

st.set_page_config(layout="wide")

# Theme Toggle
if "theme_mode" not in st.session_state:
    st.session_state.theme_mode = "light"
if st.sidebar.button("🌙 Toggle Dark/Light Mode"):
    st.session_state.theme_mode = "dark" if st.session_state.theme_mode == "light" else "light"

st.markdown(f"""
    <style>
    html, body, [class*="st-"] {{
        font-family: 'Offside', sans-serif !important;
        background-color: {'#0e1117' if st.session_state.theme_mode == 'dark' else 'white'};
        color: {'white' if st.session_state.theme_mode == 'dark' else 'black'};
    }}
    </style>
""", unsafe_allow_html=True)

st.title("AR2 Tennis Group 🎾")

players = load_players()
matches = load_matches()

if not matches.empty and ("match_id" not in matches.columns or matches["match_id"].isnull().any()):
    for i in matches.index:
        if pd.isna(matches.at[i, "match_id"]):
            matches.at[i, "match_id"] = f"AR2-{datetime.now().strftime('%y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}"
    save_matches(matches)

tab1, tab2, tab3 = st.tabs(["Post Match", "Match Records", "Rankings"])

# POST MATCH
with tab1:
    st.header("Enter Match Result")

    match_type = st.radio("Match Type", ["Doubles", "Singles"], horizontal=True)
    date_input = st.date_input("Match Date", value=datetime.today())
    available_players = players.copy()

    if match_type == "Doubles":
        p1 = st.selectbox("Team 1 - Player 1", available_players, key="t1p1")
        available_players.remove(p1)
        p2 = st.selectbox("Team 1 - Player 2", available_players, key="t1p2")
        available_players.remove(p2)
        p3 = st.selectbox("Team 2 - Player 1", available_players, key="t2p1")
        available_players.remove(p3)
        p4 = st.selectbox("Team 2 - Player 2", available_players, key="t2p2")
    else:
        p1 = st.selectbox("Player 1", available_players, key="s1p1")
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
            "date": date_input.strftime("%Y-%m-%d"),
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

# MATCH RECORDS
with tab2:
    st.header("Match History")

    with st.expander("🔎 Filters"):
        col1, col2, col3 = st.columns(3)
        with col1:
            match_filter = st.radio("Filter by Type", ["All", "Singles", "Doubles"], horizontal=True)
        with col2:
            selected_players = st.multiselect("Filter by Players", players)
        with col3:
            date_range = st.date_input("Date Range", [])

    filtered = matches.copy()
    if match_filter != "All":
        filtered = filtered[filtered["match_type"] == match_filter]
    if selected_players:
        filtered = filtered[filtered.apply(lambda row: any(p in selected_players for p in [row['team1_player1'], row['team1_player2'], row['team2_player1'], row['team2_player2']]), axis=1)]
    if len(date_range) == 2:
        filtered = filtered[(pd.to_datetime(filtered["date"]) >= pd.to_datetime(date_range[0])) &
                            (pd.to_datetime(filtered["date"]) <= pd.to_datetime(date_range[1]))]

    if not filtered.empty:
        filtered_display = filtered[["date", "match_type", "team1_player1", "team1_player2", "team2_player1", "team2_player2", "set1", "set2", "set3", "winner", "match_id"]]
        st.dataframe(filtered_display.sort_values("date", ascending=False), use_container_width=True)
    else:
        st.info("No matches found for the selected filters.")

# RANKINGS
with tab3:
    st.header("Player Rankings")
    scores = defaultdict(int)
    partners = defaultdict(list)

    for _, row in matches.iterrows():
        t1 = [row['team1_player1']]
        t2 = [row['team2_player1']]
        if row['match_type'] == 'Doubles':
            t1.append(row['team1_player2'])
            t2.append(row['team2_player2'])

        if row['winner'] == 'Tie':
            for p in t1 + t2:
                scores[p] += 1.5
        elif row['winner'] == 'Team 1':
            for p in t1:
                scores[p] += 3
            for p in t2:
                scores[p] += 1
        elif row['winner'] == 'Team 2':
            for p in t2:
                scores[p] += 3
            for p in t1:
                scores[p] += 1

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
    st.subheader("Top 3 Players 🏆")
    for i in range(min(3, len(rank_df))):
        badge = ["🥇", "🥈", "🥉"][i]
        st.metric(label=f"#{i+1} {rank_df.iloc[i]['Player']}", value=f"{rank_df.iloc[i]['Points']} pts", delta=badge)

    st.subheader("Ranking Progression")
    if len(rank_df) > 0:
        fig = px.bar(rank_df, x="Player", y="Points", color="Player", title="Current Rankings", text="Points")
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Player Insights")
    selected = st.selectbox("Select a player", players)
    if selected:
        st.markdown(f"**Partners Played With**: {dict(Counter(partners[selected]))}")
        if partners[selected]:
            best = Counter(partners[selected]).most_common(1)[0][0]
            st.markdown(f"**Most Frequent Partner**: {best}")

# Footer
st.markdown("<br><br><hr style='border-top: 1px solid #fff500;'>", unsafe_allow_html=True)
st.markdown(
    "<div style='text-align: center; color: #ffffff;'>"
    "Built with ❤️ using <a href='https://streamlit.io/' target='_blank' style='color: #fff500;'>Streamlit</a> — free and open source. "
    "<a href='https://devs-scripts.streamlit.app/' target='_blank' style='color: #fff500;'>Other Scripts by dev</a>"
    "</div>",
    unsafe_allow_html=True
)
