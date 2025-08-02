import streamlit as st
import pandas as pd
import uuid
from datetime import datetime
from collections import defaultdict, Counter
from supabase import create_client, Client

# Set the page title
st.set_page_config(page_title="AR Tennis")

# Supabase setup
supabase_url = st.secrets["supabase"]["supabase_url"]
supabase_key = st.secrets["supabase"]["supabase_key"]
supabase: Client = create_client(supabase_url, supabase_key)

# Table names
players_table_name = "players"
matches_table_name = "matches"

def load_players():
    try:
        response = supabase.table(players_table_name).select("name, profile_image_url, birthday").execute()
        df = pd.DataFrame(response.data)
        expected_columns = ["name", "profile_image_url", "birthday"]
        for col in expected_columns:
            if col not in df.columns:
                df[col] = ""
        return df
    except Exception as e:
        st.error(f"Error loading players: {str(e)}")
        return pd.DataFrame(columns=["name", "profile_image_url", "birthday"])

def save_players(players_df):
    try:
        expected_columns = [\"name\", \"profile_image_url\", \"birthday\"]
        players_df = players_df[expected_columns].copy()
        supabase.table(players_table_name).upsert(players_df.to_dict("records")).execute()
    except Exception as e:
        st.error(f"Error saving players: {str(e)}")

def load_matches():
    try:
        response = supabase.table(matches_table_name).select("*").execute()
        df = pd.DataFrame(response.data)
        expected_columns = ["match_id", "date", "match_type", "team1_player1", "team1_player2", "team2_player1", "team2_player2", "set1", "set2", "set3", "winner", "match_image_url"]
        for col in expected_columns:
            if col not in df.columns:
                df[col] = ""
        return df
    except Exception as e:
        st.error(f"Error loading matches: {str(e)}")
        return pd.DataFrame(columns=expected_columns)

def save_matches(df):
    try:
        df_to_save = df.copy()
        if 'date' in df_to_save.columns:
            df_to_save['date'] = pd.to_datetime(df_to_save['date'], errors='coerce')
            df_to_save = df_to_save.dropna(subset=['date'])
            df_to_save['date'] = df_to_save['date'].dt.strftime('%Y-%m-%d')
        supabase.table(matches_table_name).upsert(df_to_save.to_dict("records")).execute()
    except Exception as e:
        st.error(f"Error saving matches: {str(e)}")

def upload_image_to_supabase(file, file_name, image_type="match"):
    try:
        bucket = "profile" if image_type == "profile" else "ar"
        file_path = f"2ep_1/{file_name}" if image_type == "match" else file_name
        response = supabase.storage.from_(bucket).upload(
            file_path,
            file.read(),
            {"content-type": file.type}
        )
        if response is None or (isinstance(response, dict) and "error" in response):
            error_message = response.get("error", "Unknown error") if isinstance(response, dict) else "Upload failed"
            return ""
        public_url = supabase.storage.from_(bucket).get_public_url(file_path)
        if not public_url.startswith(f"https://vnolrqfkpptpljizzdvw.supabase.co/storage/v1/object/public/{bucket}/"):
             st.warning(f"Uploaded image URL does not match expected prefix. Got: {public_url}")
        return public_url
    except Exception as e:
        st.error(f"Error uploading image to bucket '{bucket}/{file_path}': {str(e)}")
        return ""

def tennis_scores():
    return ["6-0", "6-1", "6-2", "6-3", "6-4", "7-5", "7-6", "0-6", "1-6", "2-6", "3-6", "4-6", "5-7", "6-7"]

def get_quarter(month):
    if 1 <= month <= 3:
        return "Q1"
    elif 4 <= month <= 6:
        return "Q2"
    elif 7 <= month <= 9:
        return "Q3"
    else:
        return "Q4"

def generate_match_id(matches_df, match_date):
    year = match_date.year
    quarter = get_quarter(match_date.month)
    if not matches_df.empty and 'date' in matches_df.columns:
        matches_df['date'] = pd.to_datetime(matches_df['date'], errors='coerce')
        filtered_matches = matches_df[
            (matches_df['date'].dt.year == year) &
            (matches_df['date'].apply(lambda d: get_quarter(d.month) == quarter))
        ]
        serial_number = len(filtered_matches) + 1
    else:
        serial_number = 1
    return f"AR{quarter}{year}-{serial_number:02d}"

def get_player_trend(player, matches, max_matches=5):
    player_matches = matches[
        (matches['team1_player1'] == player) |
        (matches['team1_player2'] == player) |
        (matches['team2_player1'] == player) |
        (matches['team2_player2'] == player)
    ].copy()
    player_matches['date'] = pd.to_datetime(player_matches['date'], errors='coerce')
    player_matches = player_matches.sort_values(by='date', ascending=False)
    trend = []
    for _, row in player_matches.head(max_matches).iterrows():
        if row['match_type'] == 'Doubles':
            team1 = [row['team1_player1'], row['team1_player2']]
            team2 = [row['team2_player1'], row['team2_player2']]
        else:
            team1 = [row['team1_player1']]
            team2 = [row['team2_player1']]
        if player in team1 and row['winner'] == 'Team 1':
            trend.append('W')
        elif player in team2 and row['winner'] == 'Team 2':
            trend.append('W')
        elif row['winner'] != 'Tie':
            trend.append('L')
    return ' '.join(trend) if trend else 'No recent matches'

def display_player_insights(selected_player, players_df, matches_df, rank_df, partner_wins_data, key_prefix=""):
    if selected_player:
        player_info = players_df[players_df["name"] == selected_player].iloc[0]
        birthday = player_info.get("birthday", "Not set")
        profile_image = player_info.get("profile_image_url", "")
        trend = get_player_trend(selected_player, matches_df)
        cols = st.columns([1, 5])
        with cols[0]:
            if profile_image:
                try:
                    st.image(profile_image, width=100, caption="")
                except Exception as e:
                    st.error(f"Error displaying image for {selected_player}: {str(e)}")
            else:
                st.write("No image")
        with cols[1]:
            if selected_player in rank_df["Player"].values:
                player_data = rank_df[rank_df["Player"] == selected_player].iloc[0]
                st.markdown(f"""
                    **Rank**: {player_data["Rank"]}  
                    **Points**: {player_data["Points"]}  
                    **Win Percentage**: {player_data["Win %"]}%  
                    **Matches Played**: {int(player_data["Matches"])}  
                    **Wins**: {int(player_data["Wins"])}  
                    **Losses**: {int(player_data["Losses"])}  
                    **Game Diff Avg**: {player_data["Game Diff Avg"]:.2f}  
                    **Games Won**: {int(player_data["Games Won"])}  
                    **Birthday**: {birthday}  
                    **Partners Played With**: {dict(partner_wins_data[selected_player])}  
                    **Recent Trend**: {trend}  
                """)
                if partner_wins_data[selected_player]:
                    best_partner, best_wins = max(partner_wins_data[selected_player].items(), key=lambda x: x[1])
                    st.markdown(f"**Most Effective Partner**: {best_partner} ({best_wins} {'win' if best_wins == 1 else 'wins'})")
            else:
                st.markdown(f"No match data available for {selected_player}.")
                st.markdown(f"**Birthday**: {birthday}")
                st.markdown(f"**Partners Played With**: {dict(partner_wins_data[selected_player])}")
                st.markdown(f"**Recent Trend**: {trend}")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Offside&display=swap');
    html, body, [class*="st-"], h1, h2, h3, h4, h5, h6 {
        font-family: 'Offside', sans-serif !important;
    }
    .match-thumbnail-container img {
        width: 50px;
        height: 50px;
        object-fit: cover;
        cursor: pointer;
        border-radius: 50%;
    }
    .profile-thumbnail {
        width: 100px;
        height: 100px;
        object-fit: cover;
        border-radius: 50%;
        margin-right: 10px;
    }
    .ranking-profile-image {
        width: 40px;
        height: 40px;
        object-fit: cover;
        border-radius: 50%;
        margin-right: 10px;
        vertical-align: middle;
    }
    .rankings-table-container {
        width: 100%;
        background: #ffffff;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin-top: 0px !important;
        padding: 10px;
    }
    .rankings-table-scroll {
        max-height: 500px;
        overflow-y: auto;
    }
    .ranking-header-row {
        display: none;
    }
    .ranking-row {
        display: block;
        padding: 10px;
        margin-bottom: 10px;
        border: 1px solid #ddd;
        border-radius: 8px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .ranking-row:last-child {
        margin-bottom: 0;
    }
    .rank-col, .profile-col, .player-col, .points-col, .win-percent-col, .matches-col, .wins-col, .losses-col, .games-won-col, .game-diff-avg-col, .trend-col {
        width: 100%;
        text-align: left;
        padding: 2px 0;
        font-size: 1em;
        margin-bottom: 5px;
        word-break: break-word;
    }
    .rank-col {
        display: inline-block;
        white-space: nowrap;
        font-size: 1.3em;
        font-weight: bold;
        margin-right: 5px;
        color: #fff500;
    }
    .profile-col {
        text-align: left;
        margin-bottom: 10px;
        display: inline-block;
        vertical-align: middle;
    }
    .player-col {
        font-size: 1.3em;
        font-weight: bold;
        display: inline-block;
        flex-grow: 1;
        vertical-align: middle;
    }
    .rank-profile-player-group {
        display: flex;
        align-items: center;
        margin-bottom: 10px;
    }
    .rank-profile-player-group .rank-col {
        width: auto;
        margin-right: 10px;
    }
    .rank-profile-player-group .profile-col {
         width: auto;
         margin-right: 10px;
    }
    .points-col::before { content: "Points: "; font-weight: bold; color: #bbbbbb; }
    .win-percent-col::before { content: "Win %: "; font-weight: bold; color: #bbbbbb; }
    .matches-col::before { content: "Matches: "; font-weight: bold; color: #bbbbbb; }
    .wins-col::before { content: "Wins: "; font-weight: bold; color: #bbbbbb; }
    .losses-col::before { content: "Losses: "; font-weight: bold; color: #bbbbbb; }
    .games-won-col::before { content: "Games Won: "; font-weight: bold; color: #bbbbbb; }
    .game-diff-avg-col::before { content: "Game Diff Avg: "; font-weight: bold; color: #bbbbbb; }
    .trend-col::before { content: "Recent Trend: "; font-weight: bold; color: #bbbbbb; }
    .points-col, .win-percent-col, .matches-col, .wins-col, .losses-col, .games-won-col, .game-diff-avg-col, .trend-col {
        color: #fff500;
    }
    div.st-emotion-cache-1jm692n {
        margin-bottom: 0px !important;
        padding-bottom: 0px !important;
    }
    div.st-emotion-cache-1jm692n h3 {
        margin-bottom: 0px !important;
        padding-bottom: 0px !important;
        line-height: 1 !important;
    }
    .rankings-table-container > div {
        margin-top: 0 !important;
        padding-top: 0 !important;
    }
    .rankings-table-container > .rankings-table-scroll {
        margin-top: 0 !important;
        padding-top: 0 !important;
    }
    .stApp {
        padding-bottom: 80px;
    }
    .app-home-button {
        position: fixed;
        bottom: 0;
        left: 0;
        width: 100%;
        height: 60px;
        background-color: #161e80;
        color: #fff500;
        border: none;
        padding: 10px;
        text-align: center;
        font-size: 1.2em;
        font-weight: bold;
        cursor: pointer;
        z-index: 1000;
        border-top: 2px solid #fff500;
    }
    .app-icon-container {
        text-align: center;
        margin: 10px;
    }
    .app-icon {
        background-color: #161e80;
        border: 2px solid #fff500;
        border-radius: 10px;
        color: #fff500;
        padding: 20px;
        text-align: center;
        text-decoration: none;
        display: inline-block;
        font-size: 16px;
        margin: 4px 2px;
        cursor: pointer;
        width: 100%;
        height: 100px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        transition: transform 0.2s;
    }
    .app-icon:hover {
        transform: scale(1.05);
    }
    .app-icon-text {
        margin-top: 8px;
        font-weight: bold;
    }
    .st-emotion-cache-1jm692n {
        text-align: center;
    }
    div[data-testid="stForm"] > div > div > div[data-testid="stRadio"] > div {
        justify-content: center;
    }
    
    /* New styles for landing page buttons */
    .landing-button-container {
        display: flex;
        justify-content: center;
        margin-bottom: 10px;
    }
    .landing-button {
        width: 75px !important;
        height: 75px !important;
        background-color: #161e80;
        border: 2px solid #fff500;
        border-radius: 10px;
        color: #fff500;
        font-weight: bold;
        font-size: 1.2em;
        display: flex;
        align-items: center;
        justify-content: center;
        flex-direction: column;
        margin: 5px;
        transition: transform 0.2s;
    }
    .landing-button:hover {
        transform: scale(1.05);
    }
    </style>
""", unsafe_allow_html=True)

# Make the main image clickable to return to home
st.markdown(
    f"""
    <div style="cursor: pointer;" onclick="window.parent.postMessage({{ type: 'streamlit:setSessionState', state: {{ page: 'home' }} }}, '*')">
        <img src="https://raw.githubusercontent.com/mahadevbk/ar2/main/dubai.png" style="width: 100%; object-fit: contain;">
    </div>
    """,
    unsafe_allow_html=True
)

if 'players_df' not in st.session_state:
    st.session_state.players_df = load_players()
players_df = st.session_state.players_df
players = players_df["name"].dropna().tolist() if "name" in players_df.columns else []

if 'page' not in st.session_state:
    st.session_state.page = 'home'

matches = load_matches()
if not matches.empty and ("match_id" not in matches.columns or matches["match_id"].isnull().any()):
    matches['date'] = pd.to_datetime(matches['date'], errors='coerce')
    for i in matches.index:
        if pd.isna(matches.at[i, "match_id"]):
            match_date_for_id = matches.at[i, "date"] if pd.notna(matches.at[i, "date"]) else datetime.now()
            matches.at[i, "match_id"] = generate_match_id(matches, match_date_for_id)
    save_matches(matches)

def get_rank_df_and_partner_wins(players_df, matches):
    scores = defaultdict(float)
    wins = defaultdict(int)
    losses = defaultdict(int)
    matches_played = defaultdict(int)
    games_won = defaultdict(int)
    game_diff = defaultdict(int)
    partner_wins = defaultdict(lambda: defaultdict(int))
    for _, row in matches.iterrows():
        if row['match_type'] == 'Doubles':
            t1 = [row['team1_player1'], row['team1_player2']]
            t2 = [row['team2_player1'], row['team2_player2']]
        else:
            t1 = [row['team1_player1']]
            t2 = [row['team2_player1']]
        team1_total_games = sum(int(s.split('-')[0]) for s in [row['set1'], row['set2'], row['set3']] if s and '-' in s)
        team2_total_games = sum(int(s.split('-')[1]) for s in [row['set1'], row['set2'], row['set3']] if s and '-' in s)
        if row["winner"] == "Team 1":
            for p in t1: scores[p] += 3; wins[p] += 1; matches_played[p] += 1; game_diff[p] += team1_total_games - team2_total_games
            for p in t2: scores[p] += 1; losses[p] += 1; matches_played[p] += 1; game_diff[p] += team2_total_games - team1_total_games
        elif row["winner"] == "Team 2":
            for p in t2: scores[p] += 3; wins[p] += 1; matches_played[p] += 1; game_diff[p] += team2_total_games - team1_total_games
            for p in t1: scores[p] += 1; losses[p] += 1; matches_played[p] += 1; game_diff[p] += team1_total_games - team2_total_games
        else:
            for p in t1 + t2: scores[p] += 1.5; matches_played[p] += 1; game_diff[p] += team1_total_games - team2_total_games if p in t1 else team2_total_games - team1_total_games
        for set_score in [row['set1'], row['set2'], row['set3']]:
            if set_score and '-' in set_score:
                try:
                    team1_games, team2_games = map(int, set_score.split('-'))
                    for p in t1: games_won[p] += team1_games
                    for p in t2: games_won[p] += team2_games
                except ValueError:
                    continue
        if row['match_type'] == 'Doubles':
            if row["winner"] == "Team 1":
                partner_wins[row['team1_player1']][row['team1_player2']] += 1
                partner_wins[row['team1_player2']][row['team1_player1']] += 1
            elif row["winner"] == "Team 2":
                partner_wins[row['team2_player1']][row['team2_player2']] += 1
                partner_wins[row['team2_player2']][row['team2_player1']] += 1
    rank_data = []
    for player in scores:
        win_percentage = (wins[player] / matches_played[player] * 100) if matches_played[player] > 0 else 0
        game_diff_avg = (game_diff[player] / matches_played[player]) if matches_played[player] > 0 else 0
        profile_image = players_df[players_df["name"] == player]["profile_image_url"].iloc[0] if player in players_df["name"].values else ""
        player_trend = get_player_trend(player, matches)
        rank_data.append({
            "Rank": f"🏆 {len(rank_data) + 1}",
            "Profile": profile_image,
            "Player": player,
            "Points": scores[player],
            "Win %": round(win_percentage, 2),
            "Matches": matches_played[player],
            "Wins": wins[player],
            "Losses": losses[player],
            "Games Won": games_won[player],
            "Game Diff Avg": round(game_diff_avg, 2),
            "Recent Trend": player_trend
        })
    rank_df = pd.DataFrame(rank_data)
    if not rank_df.empty:
        rank_df = rank_df.sort_values(
            by=["Points", "Win %", "Game Diff Avg", "Games Won", "Player"],
            ascending=[False, False, False, False, True]
        ).reset_index(drop=True)
        rank_df["Rank"] = [f"🏆 {i}" for i in range(1, len(rank_df) + 1)]
    return rank_df, partner_wins

rank_df, partner_wins_data = get_rank_df_and_partner_wins(players_df, matches)

def landing_page():
    st.markdown("### Menu")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Rankings", key="btn_rankings", use_container_width=True):
            st.session_state.page = 'rankings'
            st.rerun()
    with col2:
        if st.button("Matches", key="btn_matches", use_container_width=True):
            st.session_state.page = 'matches'
            st.rerun()

    col3, col4 = st.columns(2)
    with col3:
        if st.button("Player Profile", key="btn_player_profile", use_container_width=True):
            st.session_state.page = 'player_profile'
            st.rerun()
    with col4:
        if st.button("Court Locations", key="btn_courts", use_container_width=True):
            st.session_state.page = 'court_locations'
            st.rerun()

    st.markdown("""
        <style>
        div[data-testid="stButton"] button {
            width: 75px !important;
            height: 75px !important;
            background-color: #161e80;
            border: 2px solid #fff500;
            border-radius: 10px;
            color: #fff500;
            font-weight: bold;
            font-size: 1.2em;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-direction: column;
            margin: 5px;
            transition: transform 0.2s;
        }
        div[data-testid="stButton"] button:hover {
            transform: scale(1.05);
        }
        </style>
    """, unsafe_allow_html=True)


def rankings_page(players_df, matches, rank_df, partner_wins_data):
    st.header("Rankings")
    view_mode = st.radio("Display View", ["Card View", "Table View"], horizontal=True, key="ranking_view_mode")
    current_date_formatted = datetime.now().strftime("%d/%m")
    st.subheader(f"Rankings as of {current_date_formatted}")
    if view_mode == "Table View":
        if not rank_df.empty:
            table_df = rank_df.drop(columns=['Profile', 'Recent Trend'])
            column_order = ["Rank", "Player", "Points", "Win %", "Matches", "Wins", "Losses", "Game Diff Avg", "Games Won"]
            table_df = table_df[column_order]
            st.dataframe(table_df, use_container_width=True, hide_index=True)
        else:
            st.info("No ranking data available. Please add players and matches.")
    else:
        st.markdown('<div class="rankings-table-container">', unsafe_allow_html=True)
        st.markdown('<div class="rankings-table-scroll">', unsafe_allow_html=True)
        if rank_df.empty:
            st.info("No ranking data available. Please add players and matches.")
        else:
            for index, row in rank_df.iterrows():
                profile_html = f'<img src="{row["Profile"]}" class="ranking-profile-image" alt="Profile">' if row["Profile"] else ''
                player_styled = f"<span style='font-weight:bold; color:#fff500;'>{row['Player']}</span>"
                points_value_styled = f"<span style='font-weight:bold; color:#fff500;'>{row['Points']:.1f}</span>"
                trend_value_styled = f"<span style='font-weight:bold; color:#fff500;'>{row['Recent Trend']}</span>"
                st.markdown(f"""
                <div class="ranking-row">
                    <div class="rank-profile-player-group">
                        <div class="rank-col">{row["Rank"]}</div>
                        <div class="profile-col">{profile_html}</div>
                        <div class="player-col">{player_styled}</div>
                    </div>
                    <div class="points-col">{points_value_styled}</div>
                    <div class="win-percent-col">{row["Win %"]:.1f}%</div>
                    <div class="matches-col">{int(row["Matches"])}</div>
                    <div class="wins-col">{int(row["Wins"])}</div>
                    <div class="losses-col">{int(row["Losses"])}</div>
                    <div class="game-diff-avg-col">{row["Game Diff Avg"]:.2f}</div>
                    <div class="games-won-col">{int(row["Games Won"])}</div>
                    <div class="trend-col">{trend_value_styled}</div>
                </div>
                """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    st.subheader("Player Insights")
    selected_player_rankings = st.selectbox("Select a player for insights", [""] + players, index=0, key="insights_player_rankings")
    if not rank_df.empty:
        display_player_insights(selected_player_rankings, players_df, matches, rank_df, partner_wins_data, key_prefix="rankings_")
    else:
        st.info("Player insights will be available once there is match data.")

def matches_page(players_df, matches):
    st.header("Matches")
    with st.expander("➕ Post New Match Result"):
        st.subheader("Enter Match Result")
        match_type_new = st.radio("Match Type", ["Doubles", "Singles"], horizontal=True, key="post_match_type_new")
        available_players = players.copy() if players else []
        if not available_players:
            st.warning("No players available. Please add players in the Player Profile tab.")
        else:
            if match_type_new == "Doubles":
                p1_new = st.selectbox("Team 1 - Player 1", [""] + available_players, key="t1p1_new_post")
                available_players_t1p2_new = [p for p in available_players if p != p1_new] if p1_new else available_players
                p2_new = st.selectbox("Team 1 - Player 2", [""] + available_players_t1p2_new, key="t1p2_new_post")
                available_players_t2p1_new = [p for p in available_players_t1p2_new if p != p2_new] if p2_new else available_players_t1p2_new
                p3_new = st.selectbox("Team 2 - Player 1", [""] + available_players_t2p1_new, key="t2p1_new_post")
                available_players_t2p2_new = [p for p in available_players_t1p2_new if p != p3_new] if p3_new else available_players_t1p2_new
                p4_new = st.selectbox("Team 2 - Player 2", [""] + available_players_t2p2_new, key="t2p2_new_post")
            else:
                p1_new = st.selectbox("Player 1", [""] + available_players, key="s1p1_new_post")
                available_players_p2_new = [p for p in available_players if p != p1_new] if p1_new else available_players
                p3_new = st.selectbox("Player 2", [""] + available_players_p2_new, key="s1p2_new_post")
                p2_new = ""
                p4_new = ""
            set1_new = st.selectbox("Set 1", tennis_scores(), index=4, key="set1_new_post")
            set2_new = st.selectbox("Set 2 (optional)", [""] + tennis_scores(), key="set2_new_post")
            set3_new = st.selectbox("Set 3 (optional)", [""] + tennis_scores(), key="set3_new_post")
            winner_new = st.radio("Winner", ["Team 1", "Team 2", "Tie"], key="winner_new_post")
            match_image_new = st.file_uploader("Upload Match Image (optional)", type=["jpg", "jpeg", "png", "gif", "bmp", "webp"], key="match_image_new_post")
            if st.button("Submit Match", key="submit_new_match_post"):
                if match_type_new == "Doubles" and not all([p1_new, p2_new, p3_new, p4_new]):
                    st.error("Please select all four players for a doubles match.")
                elif match_type_new == "Singles" and not all([p1_new, p3_new]):
                    st.error("Please select both players for a singles match.")
                else:
                    new_match_date = datetime.now()
                    match_id_new = generate_match_id(matches, new_match_date)
                    image_url_new = ""
                    if match_image_new:
                        image_url_new = upload_image_to_supabase(match_image_new, match_id_new, image_type="match")
                    new_match_entry = {
                        "match_id": match_id_new,
                        "date": new_match_date.strftime("%Y-%m-%d"),
                        "match_type": match_type_new,
                        "team1_player1": p1_new,
                        "team1_player2": p2_new,
                        "team2_player1": p3_new,
                        "team2_player2": p4_new,
                        "set1": set1_new,
                        "set2": set2_new,
                        "set3": set3_new,
                        "winner": winner_new,
                        "match_image_url": image_url_new
                    }
                    matches = pd.concat([matches, pd.DataFrame([new_match_entry])], ignore_index=True)
                    save_matches(matches)
                    st.success("Match submitted.")
                    st.rerun()
    st.markdown("---")
    st.subheader("Match History")
    match_filter = st.radio("Filter by Type", ["All", "Singles", "Doubles"], horizontal=True, key="match_history_filter")
    filtered_matches = matches.copy()
    if match_filter != "All":
        filtered_matches = filtered_matches[filtered_matches["match_type"] == match_filter]
    filtered_matches['date'] = pd.to_datetime(filtered_matches['date'], errors='coerce')
    filtered_matches = filtered_matches.sort_values(by='date', ascending=False).reset_index(drop=True)
    def format_match_label(row):
        score_parts = [f"<span style='font-weight:bold; color:#fff500;'>{row['set1']}</span>"]
        if row['set2']:
            score_parts.append(f"<span style='font-weight:bold; color:#fff500;'>{row['set2']}</span>")
        if row['set3']:
            score_parts.append(f"<span style='font-weight:bold; color:#fff500;'>{row['set3']}</span>")
        score = ", ".join(score_parts)
        date_str = row['date'].strftime('%Y-%m-%d')
        if row["match_type"] == "Singles":
            p1_styled = f"<span style='font-weight:bold; color:#fff500;'>{row['team1_player1']}</span>"
            p2_styled = f"<span style='font-weight:bold; color:#fff500;'>{row['team2_player1']}</span>"
            if row["winner"] == "Team 1":
                desc = f"{p1_styled} def. {p2_styled}"
            else:
                desc = f"{p2_styled} def. {p1_styled}"
        else:
            p1_styled = f"<span style='font-weight:bold; color:#fff500;'>{row['team1_player1']}</span>"
            p2_styled = f"<span style='font-weight:bold; color:#fff500;'>{row['team1_player2']}</span>"
            p3_styled = f"<span style='font-weight:bold; color:#fff500;'>{row['team2_player1']}</span>"
            p4_styled = f"<span style='font-weight:bold; color:#fff500;'>{row['team2_player2']}</span>"
            if row["winner"] == "Team 1":
                desc = f"{p1_styled} & {p2_styled} def. {p3_styled} & {p4_styled}"
            else:
                desc = f"{p3_styled} & {p4_styled} def. {p1_styled} & {p2_styled}"
        return f"{desc} | {score} | {date_str} | {row['match_id']}"
    if filtered_matches.empty:
        st.info("No matches found.")
    else:
        for _, row in filtered_matches.iterrows():
            match_label = format_match_label(row)
            cols = st.columns([1, 10])
            if row["match_image_url"]:
                with cols[0]:
                    try:
                        st.image(row["match_image_url"], width=50, caption="")
                    except Exception as e:
                        st.error(f"Error displaying match image: {str(e)}")
                with cols[1]:
                    st.markdown(f"- {match_label}", unsafe_allow_html=True)
            else:
                with cols[1]:
                    st.markdown(f"- {match_label}", unsafe_allow_html=True)
        st.markdown("<br><br><br><br><br><br><br><br><br><br>", unsafe_allow_html=True)
        st.markdown("### ✏️ Manage Existing Match")
        clean_match_options = []
        for _, row in filtered_matches.iterrows():
            score_plain = f"{row['set1']}"
            if row['set2']:
                score_plain += f", {row['set2']}"
            if row['set3']:
                score_plain += f", {row['set3']}"
            date_plain = row['date'].strftime('%Y-%m-%d')
            if row["match_type"] == "Singles":
                desc_plain = f"{row['team1_player1']} def. {row['team2_player1']}" if row["winner"] == "Team 1" else f"{row['team2_player1']} def. {row['team1_player1']}"
            else:
                desc_plain = f"{row['team1_player1']} & {row['team1_player2']} def. {row['team2_player1']} & {row['team2_player2']}" if row["winner"] == "Team 1" else f"{row['team2_player1']} & {row['team2_player2']} def. {row['team1_player1']} & {row['team1_player2']}"
            clean_match_options.append(f"{desc_plain} | {score_plain} | {date_plain} | {row['match_id']}")
        selected_match_to_edit = st.selectbox("Select a match to edit or delete", [""] + clean_match_options, key="select_match_to_edit")
        if selected_match_to_edit:
            selected_id = selected_match_to_edit.split(" | ")[-1]
            row = matches[matches["match_id"] == selected_id].iloc[0]
            idx = matches[matches["match_id"] == selected_id].index[0]
            current_date_dt = pd.to_datetime(row["date"])
            all_scores = [""] + tennis_scores()
            set1_index = all_scores.index(row["set1"]) if row["set1"] in all_scores else 0
            set2_index = all_scores.index(row["set2"]) if row["set2"] in all_scores else 0
            set3_index = all_scores.index(row["set3"]) if row["set3"] in all_scores else 0
            with st.expander("Edit Match Details"):
                date_edit = st.date_input("Match Date", value=current_date_dt.date(), key=f"edit_date_{selected_id}")
                match_type_edit = st.radio("Match Type", ["Doubles", "Singles"], index=0 if row["match_type"] == "Doubles" else 1, key=f"edit_match_type_{selected_id}")
                p1_edit = st.text_input("Team 1 - Player 1", value=row["team1_player1"], key=f"edit_t1p1_{selected_id}")
                p2_edit = st.text_input("Team 1 - Player 2", value=row["team1_player2"], key=f"edit_t1p2_{selected_id}")
                p3_edit = st.text_input("Team 2 - Player 1", value=row["team2_player1"], key=f"edit_t2p1_{selected_id}")
                p4_edit = st.text_input("Team 2 - Player 2", value=row["team2_player2"], key=f"edit_t2p2_{selected_id}")
                set1_edit = st.selectbox("Set 1", all_scores, index=set1_index, key=f"edit_set1_{selected_id}")
                set2_edit = st.selectbox("Set 2 (optional)", all_scores, index=set2_index, key=f"edit_set2_{selected_id}")
                set3_edit = st.selectbox("Set 3 (optional)", all_scores, index=set3_index, key=f"edit_set3_{selected_id}")
                winner_edit = st.selectbox("Winner", ["Team 1", "Team 2", "Tie"], index=["Team 1", "Team 2", "Tie"].index(row["winner"]), key=f"edit_winner_{selected_id}")
                match_image_edit = st.file_uploader("Update Match Image (optional)", type=["jpg", "jpeg", "png", "gif", "bmp", "webp"], key=f"edit_image_{selected_id}")
                if st.button("Save Changes", key=f"save_match_changes_{selected_id}"):
                    image_url_edit = row["match_image_url"]
                    if match_image_edit:
                        image_url_edit = upload_image_to_supabase(match_image_edit, selected_id, image_type="match")
                    matches.loc[idx] = {
                        "match_id": selected_id,
                        "date": date_edit,
                        "match_type": match_type_edit,
                        "team1_player1": p1_edit,
                        "team1_player2": p2_edit,
                        "team2_player1": p3_edit,
                        "team2_player2": p4_edit,
                        "set1": set1_edit,
                        "set2": set2_edit,
                        "set3": set3_edit,
                        "winner": winner_edit,
                        "match_image_url": image_url_edit
                    }
                    save_matches(matches)
                    st.success("Match updated.")
                    st.rerun()
            if st.button("🗑️ Delete This Match", key=f"delete_match_{selected_id}"):
                matches = matches[matches["match_id"] != selected_id].reset_index(drop=True)
                save_matches(matches)
                st.success("Match deleted.")
                st.rerun()

def player_profile_page(players_df, matches, rank_df, partner_wins_data):
    st.header("Player Profile")
    st.subheader("Player Insights")
    selected_player_profile_insights = st.selectbox("Select a player for insights", [""] + players, index=0, key="insights_player_profile")
    if not rank_df.empty:
        display_player_insights(selected_player_profile_insights, players_df, matches, rank_df, partner_wins_data, key_prefix="profile_")
    else:
        st.info("Player insights will be available once there is match data.")
    st.subheader("Manage & Edit Player Profiles")
    with st.expander("Add, Edit or Remove Player"):
        st.markdown("##### Add New Player")
        new_player = st.text_input("Player Name", key="new_player_input").strip()
        if st.button("Add Player", key="add_player_button"):
            if new_player:
                if new_player not in players:
                    new_player_data = {"name": new_player, "profile_image_url": "", "birthday": ""}
                    players_df = pd.concat([players_df, pd.DataFrame([new_player_data])], ignore_index=True)
                    players.append(new_player)
                    save_players(players_df)
                    st.session_state.players_df = load_players()
                    st.success(f"{new_player} added.")
                    st.rerun()
                else:
                    st.warning(f"{new_player} already exists.")
            else:
                st.warning("Please enter a player name to add.")
        st.markdown("---")
        st.markdown("##### Edit or Remove Existing Player")
        selected_player_manage = st.selectbox("Select Player", [""] + players, key="manage_player_select")
        if selected_player_manage:
            player_data = players_df[players_df["name"] == selected_player_manage].iloc[0]
            current_image = player_data.get("profile_image_url", "")
            current_birthday = player_data.get("birthday", "")
            st.markdown(f"**Current Profile for {selected_player_manage}**")
            if current_image:
                try:
                    st.image(current_image, width=100, caption="Current Image")
                except Exception as e:
                    st.error(f"Error displaying profile image: {str(e)}")
            else:
                st.write("No profile image set.")
            profile_image = st.file_uploader("Upload New Profile Image (optional)", type=["jpg", "jpeg", "png", "gif", "bmp", "webp"], key=f"profile_image_upload_{selected_player_manage}")
            default_day = 1
            default_month = 1
            if current_birthday and isinstance(current_birthday, str) and "-" in current_birthday:
                try:
                    day_str, month_str = current_birthday.split("-")
                    default_day = int(day_str)
                    default_month = int(month_str)
                except ValueError:
                    pass
            birthday_day = st.number_input("Birthday Day", min_value=1, max_value=31, value=default_day, key=f"birthday_day_{selected_player_manage}")
            birthday_month = st.number_input("Birthday Month", min_value=1, max_value=12, value=default_month, key=f"birthday_month_{selected_player_manage}")
            col_save, col_delete = st.columns(2)
            with col_save:
                if st.button("Save Profile Changes", key=f"save_profile_changes_{selected_player_manage}"):
                    image_url = current_image
                    if profile_image:
                        image_url = upload_image_to_supabase(profile_image, f"profile_{selected_player_manage}_{uuid.uuid4().hex[:6]}", image_type="profile")
                    players_df.loc[players_df["name"] == selected_player_manage, "profile_image_url"] = image_url
                    players_df.loc[players_df["name"] == selected_player_manage, "birthday"] = f"{birthday_day:02d}-{birthday_month:02d}"
                    save_players(players_df)
                    st.session_state.players_df = load_players()
                    st.success("Profile updated.")
                    st.rerun()
            with col_delete:
                if st.button("🗑️ Remove Player", key=f"remove_player_button_{selected_player_manage}"):
                    players_df = players_df[players_df["name"] != selected_player_manage].reset_index(drop=True)
                    players = [p for p in players if p != selected_player_manage]
                    save_players(players_df)
                    st.session_state.players_df = load_players()
                    st.success(f"{selected_player_manage} removed.")
                    st.rerun()

def court_locations_page():
    st.header("Court Locations")
    st.markdown("### Arabian Ranches Tennis Courts")
    st.markdown("- [Alvorado 1 & 2](https://maps.google.com/?q=25.041792,55.259258)")
    st.markdown("- [Palmera 2](https://maps.app.goo.gl/CHimjtqQeCfU1d3W6)")
    st.markdown("- [Palmera 4](https://maps.app.goo.gl/4nn1VzqMpgVkiZGN6)")
    st.markdown("- [Saheel](https://maps.app.goo.gl/a7qSvtHCtfgvJoxJ8)")
    st.markdown("- [Hattan](https://maps.app.goo.gl/fjGpeNzncyG1o34c7)")
    st.markdown("- [MLC Mirador La Colleccion](https://maps.app.goo.gl/n14VSDAVFZ1P1qEr6)")
    st.markdown("- [Al Mahra](https://maps.app.goo.gl/zVivadvUsD6yyL2Y9)")
    st.markdown("- [Mirador](https://maps.app.goo.gl/kVPVsJQ3FtMWxyKP8)")
    st.markdown("- [Reem 1](https://maps.app.goo.gl/qKswqmb9Lqsni5RD7)")
    st.markdown("- [Reem 2](https://maps.app.goo.gl/oFaUFQ9DRDMsVbMu5)")
    st.markdown("- [Reem 3](https://maps.app.goo.gl/o8z9pHo8tSqTbEL39)")
    st.markdown("- [Alma](https://maps.app.goo.gl/BZNfScABbzb3osJ18)")
    st.markdown("### Mira & Mira Oasis Tennis Courts")
    st.markdown("- [Mira 2](https://maps.app.goo.gl/JeVmwiuRboCnzhnb9)")
    st.markdown("- [Mira 4](https://maps.app.goo.gl/e1Vqv5MJXB1eusv6A)")
    st.markdown("- [Mira 5 A & B](https://maps.app.goo.gl/rWBj5JEUdw4LqJZb6)")
    st.markdown("- [Mira Oasis 1](https://maps.app.goo.gl/F9VYsFBwUCzvdJ2t8)")
    st.markdown("- [Mira Oasis 2](https://maps.app.goo.gl/ZNJteRu8aYVUy8sd9)")
    st.markdown("- [Mira Oasis 3 A & B](https://maps.app.goo.gl/ouXQGUxYSZSfaW1z9)")
    st.markdown("- [Mira Oasis 3 C](https://maps.app.goo.gl/kf7A9K7DoYm4PEPu8)")

if st.session_state.page == 'home':
    landing_page()
elif st.session_state.page == 'rankings':
    rankings_page(players_df, matches, rank_df, partner_wins_data)
elif st.session_state.page == 'matches':
    matches_page(players_df, matches)
elif st.session_state.page == 'player_profile':
    player_profile_page(players_df, matches, rank_df, partner_wins_data)
elif st.session_state.page == 'court_locations':
    court_locations_page()

if st.session_state.page != 'home':
    if st.button("🏠 Home", key="home_button", use_container_width=True):
        st.session_state.page = 'home'
        st.rerun()
    st.markdown(f"""
        <style>
            [data-testid="stButton"][key="home_button"] {{
                position: fixed;
                bottom: 10px;
                left: 10px;
                right: 10px;
                width: calc(100% - 20px);
                height: 60px;
                z-index: 999;
                padding-top: 10px;
                padding-bottom: 10px;
                background-color: #161e80;
                color: #fff500;
                border: 2px solid #fff500;
                border-radius: 10px;
                font-weight: bold;
                font-size: 1.2em;
            }}
        </style>
        """, unsafe_allow_html=True)

st.markdown("""
<div style='background-color: #161e80; padding: 1rem; border-left: 5px solid #fff500; border-radius: 0.5rem; color: white; margin-top: 20px;'>
Built with ❤️ using <a href='https://streamlit.io/' style='color: #ccff00;'>Streamlit</a> — free and open source.
<a href='https://devs-scripts.streamlit.app/' style='color: #ccff00;'>Other Scripts by dev</a> on Streamlit.
</div>
""", unsafe_allow_html=True)
