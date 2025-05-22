import streamlit as st
import pandas as pd
import uuid
from datetime import datetime

# Google Sheet URL and loading
sheet_url = st.secrets["sheet_url"]

@st.cache_data(ttl=60)
def load_data():
    df = pd.read_csv(sheet_url)
    return df

# Load match data
matches = load_data()

# Clean and normalize column names
matches.columns = matches.columns.str.strip().str.lower()

# Ensure necessary columns exist
required_columns = ["match_id", "date", "team1_player1", "team1_player2", "team2_player1", "team2_player2",
                    "set1", "set2", "set3", "winner"]
for col in required_columns:
    if col not in matches.columns:
        matches[col] = ""

# Convert and normalize date
matches["date"] = pd.to_datetime(matches["date"], errors="coerce")

# Tabs
st.title("🎾 Tennis Match Dashboard")
tab_post, tab_records, tab_rankings, tab_stats = st.tabs(["➕ Post Match", "📖 Match Records", "🏆 Rankings", "🎾 Player Stats"])

# ---------------------- TAB 1: Post Match ----------------------
with tab_post:
    st.subheader("➕ Enter New Match Result")

    with st.form("match_form"):
        date = st.date_input("Match Date", value=datetime.today())

        col1, col2 = st.columns(2)
        with col1:
            p1 = st.text_input("Team 1 - Player 1")
            p2 = st.text_input("Team 1 - Player 2")
        with col2:
            p3 = st.text_input("Team 2 - Player 1")
            p4 = st.text_input("Team 2 - Player 2")

        score_options = ["6-0", "6-1", "6-2", "6-3", "6-4", "7-5", "7-6"]
        set1 = st.selectbox("Set 1", score_options, index=0)
        set2 = st.selectbox("Set 2", score_options, index=1)
        set3 = st.selectbox("Set 3 (if played)", ["", *score_options], index=0)

        winner = st.radio("Winner", ("Team 1", "Team 2"))
        submit = st.form_submit_button("Submit Match")

    if submit:
        new_match = {
            "match_id": f"MIRA-{datetime.now().strftime('%y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}",
            "date": date.strftime("%Y-%m-%d"),
            "team1_player1": p1,
            "team1_player2": p2,
            "team2_player1": p3,
            "team2_player2": p4,
            "set1": set1,
            "set2": set2,
            "set3": set3,
            "winner": winner
        }
        matches = matches.append(new_match, ignore_index=True)
        st.success("Match submitted successfully!")

# ---------------------- TAB 2: Match Records ----------------------
with tab_records:
    st.subheader("📖 Match Records")

    if not matches.empty:
        matches["Date"] = matches["date"].dt.strftime("%d %b %Y")
        matches["Match"] = matches.apply(lambda row: f"{row['team1_player1']} & {row['team1_player2']} vs {row['team2_player1']} & {row['team2_player2']}", axis=1)
        matches["Winner"] = matches.apply(lambda row: "🏆 " + f"{row['team1_player1']} & {row['team1_player2']}" if row["winner"] == "Team 1" else "🏆 " + f"{row['team2_player1']} & {row['team2_player2']}", axis=1)

        display = matches[["Date", "Match", "set1", "set2", "set3", "Winner", "match_id"]].copy()
        st.dataframe(display, use_container_width=True)
    else:
        st.info("No matches recorded yet.")

# ---------------------- TAB 3: Rankings ----------------------
with tab_rankings:
    st.subheader("🏆 Rankings")
    from collections import defaultdict

    win_count = defaultdict(int)
    match_count = defaultdict(int)

    for _, row in matches.iterrows():
        t1 = [row["team1_player1"], row["team1_player2"]]
        t2 = [row["team2_player1"], row["team2_player2"]]
        for player in t1 + t2:
            match_count[player] += 1
        if row["winner"] == "Team 1":
            for player in t1:
                win_count[player] += 1
        elif row["winner"] == "Team 2":
            for player in t2:
                win_count[player] += 1

    ranking_data = []
    for player in match_count:
        wins = win_count[player]
        total = match_count[player]
        win_rate = round((wins / total) * 100, 1) if total else 0
        ranking_data.append((player, wins, total, win_rate))

    ranking_df = pd.DataFrame(ranking_data, columns=["Player", "Wins", "Matches", "Win Rate (%)"])
    ranking_df = ranking_df.sort_values(by="Wins", ascending=False).reset_index(drop=True)
    st.dataframe(ranking_df, use_container_width=True)

# ---------------------- TAB 4: Player Stats ----------------------
with tab_stats:
    st.subheader("🎾 Player Statistics")
    all_players = pd.unique(matches[["team1_player1", "team1_player2", "team2_player1", "team2_player2"]].values.ravel('K'))
    selected_player = st.selectbox("Select a player", sorted(all_players))

    if selected_player:
        total_matches = 0
        wins = 0
        partners = defaultdict(int)

        for _, row in matches.iterrows():
            if selected_player in [row["team1_player1"], row["team1_player2"]]:
                total_matches += 1
                partners[row["team1_player1"] if row["team1_player2"] == selected_player else row["team1_player2"]] += 1
                if row["winner"] == "Team 1":
                    wins += 1
            elif selected_player in [row["team2_player1"], row["team2_player2"]]:
                total_matches += 1
                partners[row["team2_player1"] if row["team2_player2"] == selected_player else row["team2_player2"]] += 1
                if row["winner"] == "Team 2":
                    wins += 1

        win_rate = round((wins / total_matches) * 100, 1) if total_matches else 0
        most_effective = max(partners.items(), key=lambda x: x[1])[0] if partners else "-"

        st.markdown(f"**Total Matches:** {total_matches}")
        st.markdown(f"**Wins:** {wins}")
        st.markdown(f"**Win Rate:** {win_rate}%")
        st.markdown(f"**Partners Played With:** {', '.join(partners.keys())}")
        st.markdown(f"**Most Frequent Partner:** {most_effective}")
