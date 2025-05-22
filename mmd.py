import streamlit as st
import pandas as pd
import uuid
from datetime import datetime
import gspread
from collections import defaultdict
from oauth2client.service_account import ServiceAccountCredentials

# Safely get secrets with fallback
creds_dict = st.secrets.get("gcp_service_account", None)
sheet_url = st.secrets.get("sheet_url", None)

if creds_dict is None or sheet_url is None:
    st.error(
        "Missing required secrets! Please ensure 'gcp_service_account' and 'sheet_url' "
        "are set in Streamlit Cloud Secrets."
    )
    st.stop()

# Google Sheets setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

spreadsheet = client.open_by_url(sheet_url)

# Worksheet names
players_sheet_name = "Mira Players"
matches_sheet_name = "Mira Matches"

def get_or_create_worksheet(sheet, name, rows=1000, cols=20):
    try:
        return sheet.worksheet(name)
    except gspread.exceptions.WorksheetNotFound:
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
        # Update partners
        stats[team1[0]]["partners"][team1[1]] += 1
        stats[team1[1]]["partners"][team1[0]] += 1
        stats[team2[0]]["partners"][team2[1]] += 1
        stats[team2[1]]["partners"][team2[0]] += 1
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

players = load_players()
matches = load_matches()

# --- Tabs for UI ---
tab1, tab2, tab3, tab4 = st.tabs(["📖 Match Records", "🏆 Rankings", "🎾 Player Stats", "➕ Post Match"])

# --- Tab 1: Match Records ---
with tab1:
    st.header("Match Records")

    if not matches.empty:
        matches = matches.copy()
        # Format Date to dd MMM yyyy if possible
        try:
            matches["Date"] = pd.to_datetime(matches["date"]).dt.strftime("%d %b %Y")
        except:
            matches["Date"] = matches["date"]

        matches["Match"] = matches.apply(
            lambda row: f"{row['team1_player1']} & {row['team1_player2']} vs {row['team2_player1']} & {row['team2_player2']}",
            axis=1
        )
        # Winner display with cup emoji + players names
        def winner_names(row):
            if row["winner"] == "Team 1":
                return "🏆 " + f"{row['team1_player1']} & {row['team1_player2']}"
            elif row["winner"] == "Team 2":
                return "🏆 " + f"{row['team2_player1']} & {row['team2_player2']}"
            else:
                return row["winner"]
        matches["Winner"] = matches.apply(winner_names, axis=1)

        display = matches[["Date", "Match", "set1", "set2", "set3", "Winner", "match_id"]]

        st.dataframe(display, use_container_width=True)
    else:
        st.info("No match records found.")

# --- Tab 2: Rankings ---
with tab2:
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
        st.dataframe(rankings, use_container_width=True)
    else:
        st.info("No rankings data available.")

# --- Tab 3: Player Stats ---
with tab3:
    st.header("Player Insights")
    if players:
        selected_player = st.selectbox("Select Player", players)
        if selected_player:
            data = stats.get(selected_player, {"points": 0, "wins": 0, "losses": 0, "matches": 0, "partners": {}})
            st.write(f"**Points:** {data['points']}")
            st.write(f"**Wins:** {data['wins']}")
            st.write(f"**Losses:** {data['losses']}")
            st.write(f"**Matches Played:** {data['matches']}")
            win_pct = (data["wins"] / data["matches"] * 100) if data["matches"] else 0
            st.write(f"**Win %:** {win_pct:.1f}%")

            # Show partner stats
            if data["partners"]:
                st.write("### Partners Played With:")
                partners_df = pd.DataFrame(
                    list(data["partners"].items()), columns=["Partner", "Matches Played Together"]
                ).sort_values(by="Matches Played Together", ascending=False)
                st.dataframe(partners_df, use_container_width=True)

                most_effective_partner = partners_df.iloc[0]["Partner"] if not partners_df.empty else None
                if most_effective_partner:
                    st.write(f"**Most Effective Partner:** {most_effective_partner}")
            else:
                st.write("No partners data available.")
    else:
        st.info("No players found. Please add players.")

# --- Tab 4: Post Match ---
with tab4:
    st.header("Enter Match Result")

    with st.form("post_match_form"):
        new_player_name = st.text_input("Add New Player (optional)").upper()
        if new_player_name and new_player_name not in players:
            players.append(new_player_name)
            save_players(players)
            st.experimental_rerun()

        if len(players) < 4:
            st.warning("At least 4 players are required to post a match.")
        else:
            # Player selectors
            available_players = players.copy()
            p1 = st.selectbox("Team 1 - Player 1", available_players, key="t1p1")
            available_players.remove(p1)
            p2 = st.selectbox("Team 1 - Player 2", available_players, key="t1p2")
            available_players.remove(p2)
            p3 = st.selectbox("Team 2 - Player 1", available_players, key="t2p1")
            available_players.remove(p3)
            p4 = st.selectbox("Team 2 - Player 2", available_players, key="t2p2")

            score_options = [
                "6-0", "6-1", "6-2", "6-3", "6-4", "7-5", "7-6",
                "0-6", "1-6", "2-6", "3-6", "4-6", "5-7", "6-7"
            ]

            set1 = st.selectbox("Set 1 Score", score_options, index=4)
            set2 = st.selectbox("Set 2 Score", score_options, index=4)
            set3 = st.selectbox("Set 3 Score (optional)", [""] + score_options)

            winner = st.radio("Winner", ["Team 1", "Team 2"])

            submitted = st.form_submit_button("Submit Match")

            if submitted:
                new_match = {
                    "match_id": f"MIRA-{datetime.now().strftime('%y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}",
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "team1_player1": p1,
                    "team1_player2": p2,
                    "team2_player1": p3,
                    "team2_player2": p4,
                    "set1": set1,
                    "set2": set2,
                    "set3": set3 if set3 else "",
                    "winner": winner,
                }
                matches = matches.append(new_match, ignore_index=True)
                save_matches(matches)
                st.success("Match recorded successfully!")
                st.experimental_rerun()
