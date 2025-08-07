import streamlit as st
import pandas as pd
import uuid
from datetime import datetime
from collections import defaultdict
from supabase import create_client, Client
import re
import urllib.parse

# Set the page title
st.set_page_config(page_title="AR Tennis")

# Custom CSS for a scenic background
st.markdown("""
<style>
.stApp {
  background: linear-gradient(to bottom, #07314f, #031827); /* New gradient background */
  background-size: cover;
  background-repeat: repeat;
  background-position: center;
  background-attachment: fixed;
  background-color: #031827; /* Fallback background color */
}

/* Apply the reversed gradient to the header/menu bar */
[data-testid="stHeader"] {
  background: linear-gradient(to top, #07314f, #035996) !important;
}

/* Standardize thumbnail styling across sections */
.profile-image {
    width: 50px;
    height: 50px;
    object-fit: cover;
    border-radius: 50%;
    margin-right: 10px;
    vertical-align: middle;
    transition: transform 0.2s;
}
.profile-image:hover {
    transform: scale(1.1);
}

@import url('https://fonts.googleapis.com/css2?family=Offside&display=swap');
html, body, [class*="st-"], h1, h2, h3, h4, h5, h6 {
    font-family: 'Offside', sans-serif !important;
}
/* Other styles */
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

/* Card layout for all screen sizes */
.ranking-header-row {
    display: none;
}
.ranking-row {
    display: block;
    padding: 10px;
    margin-bottom: 10px;
    border: 1px solid #696969;
    border-radius: 8px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}
.ranking-row:last-child {
    margin-bottom: 0;
}

/* Adjust individual columns for card layout */
.rank-col, .profile-col, .player-col, .points-col, .win-percent-col, .matches-col, .wins-col, .losses-col, .games-won-col, .game-diff-avg-col, .trend-col, .birthday-col, .partners-col, .best-partner-col {
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

/* Group Profile, Rank and Player together in a flex container */
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

/* Add labels for stats and apply new color to labels only */
.points-col::before { content: "Points: "; font-weight: bold; color: #bbbbbb; }
.win-percent-col::before { content: "Win %: "; font-weight: bold; color: #bbbbbb; }
.matches-col::before { content: "Matches: "; font-weight: bold; color: #bbbbbb; }
.wins-col::before { content: "Wins: "; font-weight: bold; color: #bbbbbb; }
.losses-col::before { content: "Losses: "; font-weight: bold; color: #bbbbbb; }
.games-won-col::before { content: "Games Won: "; font-weight: bold; color: #bbbbbb; }
.game-diff-avg-col::before { content: "Game Diff Avg: "; font-weight: bold; color: #bbbbbb; }
.trend-col::before { content: "Recent Trend: "; font-weight: bold; color: #bbbbbb; }
.birthday-col::before { content: "Birthday: "; font-weight: bold; color: #bbbbbb; }
.partners-col::before { content: " Partners Played With: "; font-weight: bold; color: #bbbbbb; }
.best-partner-col::before { content: "Most Effective Partner: "; font-weight: bold; color: #bbbbbb; }

/* Ensure the actual values are yellow. Applies to the text content within the div, not the ::before. */
.points-col, .win-percent-col, .matches-col, .wins-col, .losses-col, .games-won-col, .game-diff-avg-col, .trend-col, .birthday-col, .partners-col, .best-partner-col {
    color: #fff500;
}

/* Remove extra space below the subheader for "Rankings as of dd/mm" */
div.st-emotion-cache-1jm692n {
    margin-bottom: 0px !important;
    padding-bottom: 0px !important;
}
div.st-emotion-cache-1jm692n h3 {
    margin-bottom: 0px !important;
    padding-bottom: 0px !important;
    line-height: 1 !important;
}

/* Ensure no margin/padding on the immediate children of the rankings table container */
.rankings-table-container > div {
    margin-top: 0 !important;
    padding-top: 0 !important;
}
.rankings-table-container > .rankings-table-scroll {
    margin-top: 0 !important;
    padding-top: 0 !important;
}

/* Streamlit tabs for mobile responsiveness */
.stTabs [data-baseweb="tab-list"] {
    flex-wrap: wrap;
    gap: 5px;
}

.stTabs [data-baseweb="tab"] {
    flex: 1 0 auto;
    padding: 10px 0;
    font-size: 14px;
    text-align: center;
    margin: 2px;
}
</style>
""", unsafe_allow_html=True)

# Supabase setup
supabase_url = st.secrets["supabase"]["supabase_url"]
supabase_key = st.secrets["supabase"]["supabase_key"]
supabase: Client = create_client(supabase_url, supabase_key)

# Table names
players_table_name = "players"
matches_table_name = "matches"

# --- Session state initialization ---
if 'players_df' not in st.session_state:
    st.session_state.players_df = pd.DataFrame(columns=["name", "profile_image_url", "birthday"])
if 'matches_df' not in st.session_state:
    st.session_state.matches_df = pd.DataFrame(columns=["match_id", "date", "match_type", "team1_player1", "team1_player2", "team2_player1", "team2_player2", "set1", "set2", "set3", "winner", "match_image_url"])
if 'form_key_suffix' not in st.session_state:
    st.session_state.form_key_suffix = 0

# --- Functions ---
def load_players():
    try:
        response = supabase.table(players_table_name).select("name, profile_image_url, birthday").execute()
        df = pd.DataFrame(response.data)
        expected_columns = ["name", "profile_image_url", "birthday"]
        for col in expected_columns:
            if col not in df.columns:
                df[col] = ""
        st.session_state.players_df = df
    except Exception as e:
        st.error(f"Error loading players: {str(e)}")

def save_players(players_df):
    try:
        expected_columns = ["name", "profile_image_url", "birthday"]
        players_df = players_df[expected_columns].copy()
        supabase.table(players_table_name).upsert(players_df.to_dict("records")).execute()
    except Exception as e:
        st.error(f"Error saving players: {str(e)}")
      
def delete_player_from_db(player_name):
    try:
        supabase.table(players_table_name).delete().eq("name", player_name).execute()
    except Exception as e:
        st.error(f"Error deleting player from database: {str(e)}")

def load_matches():
    try:
        response = supabase.table(matches_table_name).select("*").execute()
        df = pd.DataFrame(response.data)
        expected_columns = ["match_id", "date", "match_type", "team1_player1", "team1_player2", "team2_player1", "team2_player2", "set1", "set2", "set3", "winner", "match_image_url"]
        for col in expected_columns:
            if col not in df.columns:
                df[col] = ""
        st.session_state.matches_df = df
    except Exception as e:
        st.error(f"Error loading matches: {str(e)}")

def save_matches(df):
    try:
        df_to_save = df.copy()
        if 'date' in df_to_save.columns:
            df_to_save['date'] = pd.to_datetime(df_to_save['date'], errors='coerce')
            df_to_save = df_to_save.dropna(subset=['date'])
            df_to_save['date'] = df_to_save['date'].dt.strftime('%Y-%m-%d %H:%M:%S')
        # Check for duplicate match_id values
        duplicates = df_to_save[df_to_save.duplicated(subset=['match_id'], keep=False)]
        if not duplicates.empty:
            st.warning(f"Found duplicate match_id values: {duplicates['match_id'].tolist()}")
            df_to_save = df_to_save.drop_duplicates(subset=['match_id'], keep='last')
        supabase.table(matches_table_name).upsert(df_to_save.to_dict("records")).execute()
    except Exception as e:
        st.error(f"Error saving matches: {str(e)}")

def delete_match_from_db(match_id):
    try:
        supabase.table(matches_table_name).delete().eq("match_id", match_id).execute()
        # Remove the match from session state
        st.session_state.matches_df = st.session_state.matches_df[st.session_state.matches_df["match_id"] != match_id].reset_index(drop=True)
        save_matches(st.session_state.matches_df)  # Save to ensure consistency
    except Exception as e:
        st.error(f"Error deleting match from database: {str(e)}")

def upload_image_to_supabase(file, file_name, image_type="match"):
    try:
        bucket = "profile" if image_type == "profile" else "ar"
        file_path = f"2ep_1/{file_name}" if image_type == "match" else file_name
        response = supabase.storage.from_(bucket).upload(file_path, file.read(), {"content-type": file.type})
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

def generate_match_id(matches_df, match_datetime):
    year = match_datetime.year
    quarter = get_quarter(match_datetime.month)
    if not matches_df.empty and 'date' in matches_df.columns:
        matches_df['date'] = pd.to_datetime(matches_df['date'], errors='coerce')
        filtered_matches = matches_df[
            (matches_df['date'].dt.year == year) &
            (matches_df['date'].apply(lambda d: get_quarter(d.month) == quarter))
        ]
        serial_number = len(filtered_matches) + 1
        new_id = f"AR{quarter}{year}-{serial_number:02d}"
        # Ensure the ID is unique
        while new_id in matches_df['match_id'].values:
            serial_number += 1
            new_id = f"AR{quarter}{year}-{serial_number:02d}"
    else:
        serial_number = 1
        new_id = f"AR{quarter}{year}-{serial_number:02d}"
    return new_id

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

def display_player_insights(selected_players, players_df, matches_df, rank_df, partner_stats, key_prefix=""):
    # If selected_players is a single string, convert to a list for uniform handling
    if isinstance(selected_players, str):
        selected_players = [selected_players] if selected_players else []

    # Exclude "Visitor" from selected players
    selected_players = [p for p in selected_players if p != "Visitor"]

    if not selected_players:
        st.info("No players selected or available for insights.")
        return

    # Radio buttons to toggle between Player Insights and Birthdays
    view_option = st.radio("Select View", ["Player Insights", "Birthdays"], horizontal=True, key=f"{key_prefix}view_selector")

    if view_option == "Birthdays":
        # Prepare birthday data, only including players with valid birthday entries
        birthday_data = []
        for player in selected_players:
            player_info = players_df[players_df["name"] == player].iloc[0] if player in players_df["name"].values else None
            if player_info is None:
                continue
            birthday = player_info.get("birthday", "")
            profile_image = player_info.get("profile_image_url", "")
            if birthday and re.match(r'^\d{2}-\d{2}$', birthday):
                try:
                    day, month = map(int, birthday.split("-"))
                    # Create a datetime object for sorting (use a fixed year for consistency)
                    birthday_dt = datetime.strptime(f"{day:02d}-{month:02d}-2000", "%d-%m-%Y")
                    birthday_formatted = birthday_dt.strftime("%d %b")
                    birthday_data.append({
                        "Player": player,
                        "Birthday": birthday_formatted,
                        "SortDate": birthday_dt,
                        "Profile": profile_image
                    })
                except ValueError:
                    continue

        if not birthday_data:
            st.info("No valid birthday data available for selected players.")
            return

        # Convert to DataFrame and sort by birthday
        birthday_df = pd.DataFrame(birthday_data)
        birthday_df = birthday_df.sort_values(by="SortDate").reset_index(drop=True)

        # Display birthdays in a card-like format
        st.markdown('<div class="rankings-table-container">', unsafe_allow_html=True)
        st.markdown('<div class="rankings-table-scroll">', unsafe_allow_html=True)
        for _, row in birthday_df.iterrows():
            profile_html = f'<a href="{row["Profile"]}" target="_blank"><img src="{row["Profile"]}" class="profile-image" alt="Profile"></a>' if row["Profile"] else ''
            player_styled = f"<span style='font-weight:bold; color:#fff500;'>{row['Player']}</span>"
            birthday_styled = f"<span style='font-weight:bold; color:#fff500;'>{row['Birthday']}</span>"
            st.markdown(f"""
            <div class="ranking-row">
                <div class="rank-profile-player-group">
                    <div class="profile-col">{profile_html}</div>
                    <div class="player-col">{player_styled}</div>
                </div>
                <div class="birthday-col">{birthday_styled}</div>
            </div>
            """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    else:  # Player Insights view
        # Filter players who have played at least one match, excluding "Visitor"
        active_players = []
        for player in selected_players:
            if player in rank_df["Player"].values and player != "Visitor":
                player_data = rank_df[rank_df["Player"] == player].iloc[0]
                if player_data["Matches"] > 0:
                    active_players.append(player)

        # Sort active players by name
        active_players = sorted(active_players)

        if not active_players:
            st.info("No players with matches played are available for insights.")
            return

        # Use the same container and scroll styling as rankings
        st.markdown('<div class="rankings-table-container">', unsafe_allow_html=True)
        st.markdown('<div class="rankings-table-scroll">', unsafe_allow_html=True)

        for selected_player in active_players:
            # Fetch player information
            player_info = players_df[players_df["name"] == selected_player].iloc[0] if selected_player in players_df["name"].values else None
            if player_info is None:
                continue
            birthday = player_info.get("birthday", "Not set")
            profile_image = player_info.get("profile_image_url", "")
            trend = get_player_trend(selected_player, matches_df)

            # Prepare profile image HTML with link to full image
            profile_html = f'<a href="{profile_image}" target="_blank"><img src="{profile_image}" class="profile-image" alt="Profile"></a>' if profile_image else ''

            # Style player name and values
            player_styled = f"<span style='font-weight:bold; color:#fff500;'>{selected_player}</span>"

            # Populate stats for players with match data
            player_data = rank_df[rank_df["Player"] == selected_player].iloc[0]
            rank = player_data["Rank"]
            points = player_data["Points"]
            win_percent = player_data["Win %"]
            matches = int(player_data["Matches"])
            wins = int(player_data["Wins"])
            losses = int(player_data["Losses"])
            game_diff_avg = player_data["Game Diff Avg"]
            games_won = int(player_data["Games Won"])

            # Partners and most effective partner, excluding "Visitor"
            partners_list = "None"
            best_partner = "None"
            if selected_player in partner_stats and partner_stats[selected_player]:
                partners_list = ', '.join([
                    f'{p} ({item["wins"]} wins, {item["losses"]} losses, {item["ties"]} ties, GD Sum: {item["game_diff_sum"]:.2f})'
                    for p, item in partner_stats[selected_player].items() if p != "Visitor"
                ])
                sorted_partners = sorted(
                    [(p, item) for p, item in partner_stats[selected_player].items() if p != "Visitor"],
                    key=lambda item: (
                        item[1]['wins'] / item[1]['matches'] if item[1]['matches'] > 0 else 0,  # Win percentage
                        item[1]['game_diff_sum'] / item[1]['matches'] if item[1]['matches'] > 0 else 0,  # Average game diff
                        item[1]['wins']
                    ),
                    reverse=True
                )
                if sorted_partners:
                    best_partner_name = sorted_partners[0][0]
                    best_stats = sorted_partners[0][1]
                    best_win_percent = (best_stats['wins'] / best_stats['matches'] * 100) if best_stats['matches'] > 0 else 0
                    best_partner = f"{best_partner_name} ({best_stats['wins']} {'win' if best_stats['wins'] == 1 else 'wins'}, {best_win_percent:.1f}% win rate)"

            # Style the values in yellow
            points_styled = f"<span style='font-weight:bold; color:#fff500;'>{points:.1f}</span>"
            win_percent_styled = f"<span style='font-weight:bold; color:#fff500;'>{win_percent:.1f}%</span>"
            matches_styled = f"<span style='font-weight:bold; color:#fff500;'>{matches}</span>"
            wins_styled = f"<span style='font-weight:bold; color:#fff500;'>{wins}</span>"
            losses_styled = f"<span style='font-weight:bold; color:#fff500;'>{losses}</span>"
            game_diff_avg_styled = f"<span style='font-weight:bold; color:#fff500;'>{game_diff_avg:.2f}</span>"
            games_won_styled = f"<span style='font-weight:bold; color:#fff500;'>{games_won}</span>"
            birthday_styled = f"<span style='font-weight:bold; color:#fff500;'>{birthday}</span>"
            partners_styled = f"<span style='font-weight:bold; color:#fff500;'>{partners_list}</span>"
            best_partner_styled = f"<span style='font-weight:bold; color:#fff500;'>{best_partner}</span>"
            trend_styled = f"<span style='font-weight:bold; color:#fff500;'>{trend}</span>"

            # Render the card
            st.markdown(f"""
            <div class="ranking-row">
                <div class="rank-profile-player-group">
                    <div class="rank-col">{rank}</div>
                    <div class="profile-col">{profile_html}</div>
                    <div class="player-col">{player_styled}</div>
                </div>
                <div class="points-col">{points_styled}</div>
                <div class="win-percent-col">{win_percent_styled}</div>
                <div class="matches-col">{matches_styled}</div>
                <div class="wins-col">{wins_styled}</div>
                <div class="losses-col">{losses_styled}</div>
                <div class="game-diff-avg-col">{game_diff_avg_styled}</div>
                <div class="games-won-col">{games_won_styled}</div>
                <div class="birthday-col">{birthday_styled}</div>
                <div class="partners-col">{partners_styled}</div>
                <div class="best-partner-col">{best_partner_styled}</div>
                <div class="trend-col">{trend_styled}</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

def calculate_rankings(matches_to_rank):
    scores = defaultdict(float)
    wins = defaultdict(int)
    losses = defaultdict(int)
    matches_played = defaultdict(int)
    games_won = defaultdict(int)
    game_diff = defaultdict(float)
    partner_stats = defaultdict(lambda: defaultdict(lambda: {'wins': 0, 'losses': 0, 'ties': 0, 'matches': 0, 'game_diff_sum': 0}))

    for _, row in matches_to_rank.iterrows():
        if row['match_type'] == 'Doubles':
            t1 = [row['team1_player1'], row['team1_player2']]
            t2 = [row['team2_player1'], row['team2_player2']]
        else:
            t1 = [row['team1_player1']]
            t2 = [row['team2_player1']]
        
        team1_total_games = 0
        team2_total_games = 0
        match_gd_sum = 0
        set_count = 0
        for set_score in [row['set1'], row['set2'], row['set3']]:
            if set_score and '-' in set_score:
                try:
                    team1_games, team2_games = map(int, set_score.split('-'))
                    team1_total_games += team1_games
                    team2_total_games += team2_games
                    match_gd_sum += team1_games - team2_games
                    set_count += 1
                except ValueError:
                    continue
        match_gd_avg = match_gd_sum / set_count if set_count > 0 else 0

        # Update individual player stats for non-Visitor players
        if row["winner"] == "Team 1":
            for p in t1:
                if p != "Visitor":
                    scores[p] += 3
                    wins[p] += 1
                    matches_played[p] += 1
                    game_diff[p] += match_gd_avg
            for p in t2:
                if p != "Visitor":
                    scores[p] += 1
                    losses[p] += 1
                    matches_played[p] += 1
                    game_diff[p] -= match_gd_avg
        elif row["winner"] == "Team 2":
            for p in t2:
                if p != "Visitor":
                    scores[p] += 3
                    wins[p] += 1
                    matches_played[p] += 1
                    game_diff[p] -= match_gd_avg
            for p in t1:
                if p != "Visitor":
                    scores[p] += 1
                    losses[p] += 1
                    matches_played[p] += 1
                    game_diff[p] += match_gd_avg
        else:  # Tie
            for p in t1 + t2:
                if p != "Visitor":
                    scores[p] += 1.5
                    matches_played[p] += 1
                    game_diff[p] += match_gd_avg if p in t1 else -match_gd_avg

        # Update games won
        for set_score in [row['set1'], row['set2'], row['set3']]:
            if set_score and '-' in set_score:
                try:
                    team1_games, team2_games = map(int, set_score.split('-'))
                    for p in t1:
                        if p != "Visitor":
                            games_won[p] += team1_games
                    for p in t2:
                        if p != "Visitor":
                            games_won[p] += team2_games
                except ValueError:
                    continue

        # Update partner stats for doubles matches
        if row['match_type'] == 'Doubles':
            for p1 in t1:
                for p2 in t1:
                    if p1 != p2 and p1 != "Visitor" and p2 != "Visitor":
                        partner_stats[p1][p2]['matches'] += 1
                        partner_stats[p1][p2]['game_diff_sum'] += match_gd_sum
                        if row["winner"] == "Team 1":
                            partner_stats[p1][p2]['wins'] += 1
                        elif row["winner"] == "Team 2":
                            partner_stats[p1][p2]['losses'] += 1
                        else:
                            partner_stats[p1][p2]['ties'] += 1
            for p1 in t2:
                for p2 in t2:
                    if p1 != p2 and p1 != "Visitor" and p2 != "Visitor":
                        partner_stats[p1][p2]['matches'] += 1
                        partner_stats[p1][p2]['game_diff_sum'] -= match_gd_sum  # Reverse for losing team
                        if row["winner"] == "Team 2":
                            partner_stats[p1][p2]['wins'] += 1
                        elif row["winner"] == "Team 1":
                            partner_stats[p1][p2]['losses'] += 1
                        else:
                            partner_stats[p1][p2]['ties'] += 1

    rank_data = []
    players_df = st.session_state.players_df
    for player in scores:
        if player == "Visitor":
            continue  # Skip Visitor in rankings
        win_percentage = (wins[player] / matches_played[player] * 100) if matches_played[player] > 0 else 0
        game_diff_avg = (game_diff[player] / matches_played[player]) if matches_played[player] > 0 else 0
        profile_image = players_df[players_df["name"] == player]["profile_image_url"].iloc[0] if player in players_df["name"].values else ""
        player_trend = get_player_trend(player, matches_to_rank)
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

    return rank_df, partner_stats

def display_rankings_table(rank_df, title):
    if rank_df.empty:
        st.info(f"No {title} ranking data available.")
        return
    display_df = rank_df[["Rank", "Player", "Points", "Win %", "Matches", "Wins", "Losses", "Games Won", "Game Diff Avg", "Recent Trend"]].copy()
    display_df["Points"] = display_df["Points"].map("{:.1f}".format)
    display_df["Win %"] = display_df["Win %"].map("{:.1f}%".format)
    display_df["Game Diff Avg"] = display_df["Game Diff Avg"].map("{:.2f}".format)
    display_df["Matches"] = display_df["Matches"].astype(int)
    display_df["Wins"] = display_df["Wins"].astype(int)
    display_df["Losses"] = display_df["Losses"].astype(int)
    display_df["Games Won"] = display_df["Games Won"].astype(int)
    st.subheader(f"{title} Rankings")
    st.dataframe(display_df, hide_index=True, height=300)

def display_match_table(df, title):
    if df.empty:
        st.info(f"No {title} match data available.")
        return

    table_df = df.copy()

    # Create a formatted Match column
    def format_match_info(row):
        scores = [s for s in [row['set1'], row['set2'], row['set3']] if s]
        scores_str = ", ".join(scores)

        if row['match_type'] == 'Doubles':
            players = f"{row['team1_player1']} & {row['team1_player2']} vs. {row['team2_player1']} & {row['team2_player2']}"
        else:
            players = f"{row['team1_player1']} vs. {row['team2_player1']}"

        return f"{players} ({scores_str})"

    table_df['Match Details'] = table_df.apply(format_match_info, axis=1)

    # Select and rename columns for display
    display_df = table_df[['date', 'Match Details', 'match_image_url']].copy()
    display_df.rename(columns={
        'date': 'Date',
        'match_image_url': 'Image URL'
    }, inplace=True)

    # Format the date column as dd MMM yy
    display_df['Date'] = pd.to_datetime(display_df['Date']).dt.strftime('%d %b %y')

    st.dataframe(display_df, height=300)

def generate_whatsapp_link(row):
    # Determine the winner and loser(s) based on the match type and winner
    if row["match_type"] == "Singles":
        if row["winner"] == "Team 1":
            winner_str = f"{row['team1_player1']}"
            loser_str = f"{row['team2_player1']}"
        else:
            winner_str = f"{row['team2_player1']}"
            loser_str = f"{row['team1_player1']}"
    else: # Doubles
        if row["winner"] == "Team 1":
            winner_str = f"{row['team1_player1']} & {row['team1_player2']}"
            loser_str = f"{row['team2_player1']} & {row['team2_player2']}"
        else:
            winner_str = f"{row['team2_player1']} & {row['team2_player2']}"
            loser_str = f"{row['team1_player1']} & {row['team1_player2']}"

    # Format scores with bolding and date
    scores_list = [f'*{s.replace("-", ":")}*' for s in [row['set1'], row['set2'], row['set3']] if s]
    scores_str = " ".join(scores_list)
    date_str = row['date'].strftime('%d %b %y')

    # Create the text to be shared
    share_text = f"*{winner_str} def. {loser_str}*\nSet scores {scores_str} on {date_str}"

    # URL-encode the text
    encoded_text = urllib.parse.quote(share_text)

    return f"https://api.whatsapp.com/send/?text={encoded_text}&type=custom_url&app_absent=0"

# --- Main App Logic ---
load_players()
load_matches()

players_df = st.session_state.players_df
matches = st.session_state.matches_df
players = sorted([p for p in players_df["name"].dropna().tolist() if p != "Visitor"]) if "name" in players_df.columns else []

if not matches.empty and ("match_id" not in matches.columns or matches["match_id"].isnull().any()):
    matches['date'] = pd.to_datetime(matches['date'], errors='coerce')
    for i in matches.index:
        if pd.isna(matches.at[i, "match_id"]):
            match_date_for_id = matches.at[i, "date"] if pd.notna(matches.at[i, "date"]) else datetime.now()
            matches.at[i, "match_id"] = generate_match_id(matches, match_date_for_id)
    save_matches(matches)

st.image("https://raw.githubusercontent.com/mahadevbk/ar2/main/dubai.png", use_container_width=True)

tab_names = ["Rankings", "Matches", "Player Profile", "Court Locations"]

tabs = st.tabs(tab_names)

with tabs[0]:
    st.header("Rankings")
    ranking_type = st.radio("Select Ranking View", ["Combined", "Doubles", "Singles", "Nerd Stuff", "Table View"], horizontal=True, key="ranking_type_selector")
    if ranking_type == "Doubles":
        filtered_matches = matches[matches['match_type'] == 'Doubles'].copy()
        rank_df, partner_stats = calculate_rankings(filtered_matches)
        st.subheader(f"Rankings as of {datetime.now().strftime('%d/%m')}")
        st.markdown('<div class="rankings-table-container">', unsafe_allow_html=True)
        st.markdown('<div class="rankings-table-scroll">', unsafe_allow_html=True)
        if rank_df.empty:
            st.info("No ranking data available for this view.")
        else:
            for index, row in rank_df.iterrows():
                profile_html = f'<a href="{row["Profile"]}" target="_blank"><img src="{row["Profile"]}" class="profile-image" alt="Profile"></a>' if row["Profile"] else ''
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
        selected_player_rankings = st.selectbox("Select a player for insights", [""] + players, index=0, key="insights_player_rankings_doubles")
        if selected_player_rankings:
            display_player_insights(selected_player_rankings, players_df, filtered_matches, rank_df, partner_stats, key_prefix="rankings_doubles_")
        else:
            st.info("Player insights will be available once a player is selected.")
    elif ranking_type == "Singles":
        filtered_matches = matches[matches['match_type'] == 'Singles'].copy()
        rank_df, partner_stats = calculate_rankings(filtered_matches)
        current_date_formatted = datetime.now().strftime("%d/%m")
        st.subheader(f"Rankings as of {current_date_formatted}")
        st.markdown('<div class="rankings-table-container">', unsafe_allow_html=True)
        st.markdown('<div class="rankings-table-scroll">', unsafe_allow_html=True)
        if rank_df.empty:
            st.info("No ranking data available for this view.")
        else:
            for index, row in rank_df.iterrows():
                profile_html = f'<a href="{row["Profile"]}" target="_blank"><img src="{row["Profile"]}" class="profile-image" alt="Profile"></a>' if row["Profile"] else ''
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
        selected_player_rankings = st.selectbox("Select a player for insights", [""] + players, index=0, key="insights_player_rankings_singles")
        if selected_player_rankings:
            display_player_insights(selected_player_rankings, players_df, filtered_matches, rank_df, partner_stats, key_prefix="rankings_singles_")
        else:
            st.info("Player insights will be available once a player is selected.")
    elif ranking_type == "Nerd Stuff":
        if matches.empty or players_df.empty:
            st.info("No match data available to generate interesting stats.")
        else:
            rank_df, partner_stats = calculate_rankings(matches)

            # Most Effective Partnership
            st.markdown("### 🤝 Most Effective Partnership")
            best_partner = None
            max_value = -1
            for player, partners in partner_stats.items():
                if player == "Visitor":
                    continue
                for partner, stats in partners.items():
                    if partner == "Visitor" or player < partner:  # Avoid double counting
                        win_rate = stats['wins'] / stats['matches'] if stats['matches'] > 0 else 0
                        avg_game_diff = stats['game_diff_sum'] / stats['matches'] if stats['matches'] > 0 else 0
                        score = win_rate + (avg_game_diff / 10)  # Adjust weight of game diff
                        if score > max_value:
                            max_value = score
                            best_partner = (player, partner, stats)

            if best_partner:
                p1, p2, stats = best_partner
                p1_styled = f"<span style='font-weight:bold; color:#fff500;'>{p1}</span>"
                p2_styled = f"<span style='font-weight:bold; color:#fff500;'>{p2}</span>"
                win_rate = (stats['wins'] / stats['matches'] * 100) if stats['matches'] > 0 else 0
                st.markdown(f"The most effective partnership is {p1_styled} and {p2_styled} with **{stats['wins']}** wins, **{stats['losses']}** losses, and a total game difference of **{stats['game_diff_sum']:.2f}** (win rate: {win_rate:.1f}%).", unsafe_allow_html=True)
            else:
                st.info("No doubles matches have been played to determine the most effective partnership.")

            st.markdown("---")

            # Best Player to Partner With
            st.markdown("### 🥇 Best Player to Partner With")
            player_stats = defaultdict(lambda: {'wins': 0, 'gd_sum': 0, 'partners': set()})
            for _, row in matches.iterrows():
                if row['match_type'] == 'Doubles':
                    t1 = [row['team1_player1'], row['team1_player2']]
                    t2 = [row['team2_player1'], row['team2_player2']]

                    match_gd_sum = 0
                    set_count = 0
                    for set_score in [row['set1'], row['set2'], row['set3']]:
                        if set_score and '-' in set_score:
                            try:
                                team1_games, team2_games = map(int, set_score.split('-'))
                                match_gd_sum += team1_games - team2_games
                                set_count += 1
                            except ValueError:
                                continue

                    if set_count > 0:
                        if row["winner"] == "Team 1":
                            for p in t1:
                                if p != "Visitor":
                                    player_stats[p]['wins'] += 1
                                    player_stats[p]['gd_sum'] += match_gd_sum
                                    for partner in t1:
                                        if partner != p and partner != "Visitor":
                                            player_stats[p]['partners'].add(partner)
                        elif row["winner"] == "Team 2":
                            for p in t2:
                                if p != "Visitor":
                                    player_stats[p]['wins'] += 1
                                    player_stats[p]['gd_sum'] += match_gd_sum
                                    for partner in t2:
                                        if partner != p and partner != "Visitor":
                                            player_stats[p]['partners'].add(partner)

            if player_stats:
                best_partner_candidate = None
                max_score = -1

                wins_list = [stats['wins'] for stats in player_stats.values()]
                gd_list = [stats['gd_sum'] for stats in player_stats.values()]
                partners_list = [len(stats['partners']) for stats in player_stats.values()]

                max_wins = max(wins_list) if wins_list else 1
                max_gd = max(gd_list) if gd_list else 1
                max_partners = max(partners_list) if partners_list else 1

                for player, stats in player_stats.items():
                    # Normalize scores and create a composite score
                    normalized_wins = stats['wins'] / max_wins
                    normalized_gd = stats['gd_sum'] / max_gd
                    normalized_partners = len(stats['partners']) / max_partners

                    composite_score = normalized_wins + normalized_gd + normalized_partners

                    if composite_score > max_score:
                        max_score = composite_score
                        best_partner_candidate = (player, stats)

                if best_partner_candidate:
                    player_name, stats = best_partner_candidate
                    player_styled = f"<span style='font-weight:bold; color:#fff500;'>{player_name}</span>"
                    st.markdown(f"The best player to partner with is {player_styled} based on their high number of wins, game difference sum, and variety of partners. They have:", unsafe_allow_html=True)
                    st.markdown(f"- **Total Wins**: {stats['wins']}")
                    st.markdown(f"- **Total Game Difference**: {stats['gd_sum']:.2f}")
                    st.markdown(f"- **Unique Partners Played With**: {len(stats['partners'])}")
                else:
                    st.info("Not enough data to determine the best player to partner with.")
            else:
                st.info("No doubles matches have been recorded yet.")

            st.markdown("---")

            # Most Frequent Player
            st.markdown("### 🏟️ Most Frequent Player")
            if not rank_df.empty:
                most_frequent_player = rank_df.sort_values(by="Matches", ascending=False).iloc[0]
                player_styled = f"<span style='font-weight:bold; color:#fff500;'>{most_frequent_player['Player']}</span>"
                st.markdown(f"{player_styled} has played the most matches, with a total of **{int(most_frequent_player['Matches'])}** matches played.", unsafe_allow_html=True)
            else:
                st.info("No match data available to determine the most frequent player.")

            st.markdown("---")

            # Player with highest Game Difference
            st.markdown("### 📈 Player with highest Game Difference")
            cumulative_game_diff = defaultdict(int)
            for _, row in matches.iterrows():
                t1 = [row['team1_player1'], row['team1_player2']] if row['match_type'] == 'Doubles' else [row['team1_player1']]
                t2 = [row['team2_player1'], row['team2_player2']] if row['match_type'] == 'Doubles' else [row['team2_player1']]
                for set_score in [row['set1'], row['set2'], row['set3']]:
                    if set_score and '-' in set_score:
                        try:
                            team1_games, team2_games = map(int, set_score.split('-'))
                            set_gd = team1_games - team2_games
                            for p in t1:
                                if p != "Visitor":
                                    cumulative_game_diff[p] += set_gd
                            for p in t2:
                                if p != "Visitor":
                                    cumulative_game_diff[p] -= set_gd
                        except ValueError:
                            continue

            if cumulative_game_diff:
                highest_gd_player, highest_gd_value = max(cumulative_game_diff.items(), key=lambda item: item[1])
                player_styled = f"<span style='font-weight:bold; color:#fff500;'>{highest_gd_player}</span>"
                st.markdown(f"{player_styled} has the highest cumulative game difference: <span style='font-weight:bold; color:#fff500;'>{highest_gd_value}</span>.", unsafe_allow_html=True)
            else:
                st.info("No match data available to calculate game difference.")

            st.markdown("---")

            # Player with the most wins
            st.markdown(f"### 👑 Player with the Most Wins")
            most_wins_player = rank_df.sort_values(by="Wins", ascending=False).iloc[0]
            player_styled = f"<span style='font-weight:bold; color:#fff500;'>{most_wins_player['Player']}</span>"
            st.markdown(f"{player_styled} holds the record for most wins with **{int(most_wins_player['Wins'])}** wins.", unsafe_allow_html=True)

            st.markdown("---") 

            # Player with the highest win percentage (minimum 5 matches)
            st.markdown(f"### 🔥 Highest Win Percentage (Min. 5 Matches)")
            eligible_players = rank_df[rank_df['Matches'] >= 5].sort_values(by="Win %", ascending=False)
            if not eligible_players.empty:
                highest_win_percent_player = eligible_players.iloc[0]
                player_styled = f"<span style='font-weight:bold; color:#fff500;'>{highest_win_percent_player['Player']}</span>"
                st.markdown(f"{player_styled} has the highest win percentage at **{highest_win_percent_player['Win %']:.2f}%**.", unsafe_allow_html=True)
            else:
                st.info("No players have played enough matches to calculate a meaningful win percentage.")

            st.markdown("---")
            with st.expander("Process being used for Rankings" , expanded=False, icon="➡️"):
                st.markdown("""
                ### Ranking System Overview
                - **Points**: Players earn 3 points for a win, 1 point for a loss, and 1.5 points for a tie.
                - **Win Percentage**: Calculated as (Wins / Matches Played) * 100.
                - **Game Difference Average**: The average difference in games won vs. lost per match.
                - **Games Won**: Total games won across all sets.
                - **Ranking Criteria**: Players are ranked by Points (highest first), then by Win Percentage, Game Difference Average, Games Won, and finally alphabetically by name.
                - **Matches Included**: All matches, including those with a 'Visitor', contribute to AR players' stats, but 'Visitor' is excluded from rankings and insights.

                Detailed Ranking Logic at https://github.com/mahadevbk/ar2/blob/main/ar_ranking_logic.pdf
                
                """)

    elif ranking_type == "Table View":
        # Calculate combined rankings
        rank_df_combined, _ = calculate_rankings(matches)
        display_rankings_table(rank_df_combined, "Combined")

        # Calculate doubles rankings
        doubles_matches = matches[matches['match_type'] == 'Doubles']
        rank_df_doubles, _ = calculate_rankings(doubles_matches)
        display_rankings_table(rank_df_doubles, "Doubles")

        # Calculate singles rankings
        singles_matches = matches[matches['match_type'] == 'Singles']
        rank_df_singles, _ = calculate_rankings(singles_matches)
        display_rankings_table(rank_df_singles, "Singles")
    else: # Combined view
        filtered_matches = matches.copy()
        rank_df, partner_stats = calculate_rankings(filtered_matches)
        current_date_formatted = datetime.now().strftime("%d/%m")
        st.subheader(f"Rankings as of {current_date_formatted}")
        st.markdown('<div class="rankings-table-container">', unsafe_allow_html=True)
        st.markdown('<div class="rankings-table-scroll">', unsafe_allow_html=True)
        if rank_df.empty:
            st.info("No ranking data available for this view.")
        else:
            for index, row in rank_df.iterrows():
                profile_html = f'<a href="{row["Profile"]}" target="_blank"><img src="{row["Profile"]}" class="profile-image" alt="Profile"></a>' if row["Profile"] else ''
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
        selected_player_rankings = st.selectbox("Select a player for insights", [""] + players, index=0, key="insights_player_rankings_combined")
        if selected_player_rankings:
            display_player_insights(selected_player_rankings, players_df, filtered_matches, rank_df, partner_stats, key_prefix="rankings_combined_")
        else:
            st.info("Player insights will be available once a player is selected.")

with tabs[1]:
    st.header("Matches")
    with st.expander("➕ Post New Match Result", expanded=False, icon="➡️"):
        st.subheader("Enter Match Result")
        match_type_new = st.radio("Match Type", ["Doubles", "Singles"], horizontal=True, key=f"post_match_type_new_{st.session_state.form_key_suffix}")
        available_players = sorted(players.copy() + ["Visitor"] if players else ["Visitor"])
        if not available_players:
            st.warning("No players available. Please add players in the Player Profile tab.")
        else:
            with st.form(key=f"new_match_form_{st.session_state.form_key_suffix}"):
                if match_type_new == "Doubles":
                    col1, col2 = st.columns(2)
                    with col1:
                        p1_new = st.selectbox("Team 1 - Player 1", [""] + available_players, key=f"t1p1_new_post_{st.session_state.form_key_suffix}")
                        p2_new = st.selectbox("Team 1 - Player 2", [""] + available_players, key=f"t1p2_new_post_{st.session_state.form_key_suffix}")
                    with col2:
                        p3_new = st.selectbox("Team 2 - Player 1", [""] + available_players, key=f"t2p1_new_post_{st.session_state.form_key_suffix}")
                        p4_new = st.selectbox("Team 2 - Player 2", [""] + available_players, key=f"t2p2_new_post_{st.session_state.form_key_suffix}")
                else:
                    p1_new = st.selectbox("Player 1", [""] + available_players, key=f"s1p1_new_post_{st.session_state.form_key_suffix}")
                    p3_new = st.selectbox("Player 2", [""] + available_players, key=f"s1p2_new_post_{st.session_state.form_key_suffix}")
                    p2_new = ""
                    p4_new = ""
                set1_new = st.selectbox("Set 1 *", tennis_scores(), index=4, key=f"set1_new_post_{st.session_state.form_key_suffix}")
                set2_new = st.selectbox("Set 2 *" if match_type_new == "Doubles" else "Set 2 (optional)", [""] + tennis_scores(), key=f"set2_new_post_{st.session_state.form_key_suffix}")
                set3_new = st.selectbox("Set 3 (optional)", [""] + tennis_scores(), key=f"set3_new_post_{st.session_state.form_key_suffix}")
                winner_new = st.radio("Winner", ["Team 1", "Team 2", "Tie"], key=f"winner_new_post_{st.session_state.form_key_suffix}")
                match_image_new = st.file_uploader("Upload Match Image (optional)", type=["jpg", "jpeg", "png", "gif", "bmp", "webp"], key=f"match_image_new_post_{st.session_state.form_key_suffix}")
                st.markdown("*Required fields", unsafe_allow_html=True)
                submit_button = st.form_submit_button("Submit Match")
            if submit_button:
                selected_players = [p1_new, p2_new, p3_new, p4_new] if match_type_new == "Doubles" else [p1_new, p3_new]
                if "" in selected_players:
                    st.error("Please select all players.")
                elif len(selected_players) != len(set(selected_players)):
                    st.error("Please select different players for each position.")
                elif not set1_new:
                    st.error("Set 1 score is required.")
                elif match_type_new == "Doubles" and not set2_new:
                    st.error("Set 2 score is required for doubles matches.")
                else:
                    new_match_date = datetime.now()
                    match_id_new = generate_match_id(st.session_state.matches_df, new_match_date)
                    image_url_new = ""
                    if match_image_new:
                        image_url_new = upload_image_to_supabase(match_image_new, match_id_new, image_type="match")
                    new_match_entry = {
                        "match_id": match_id_new,
                        "date": new_match_date,
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
                    matches_to_save = pd.concat([st.session_state.matches_df, pd.DataFrame([new_match_entry])], ignore_index=True)
                    save_matches(matches_to_save)
                    load_matches()  # Reload data from DB
                    st.success("Match submitted.")
                    st.session_state.form_key_suffix += 1
                    st.rerun()

    st.markdown("---")
    st.subheader("Match History")
    match_filter = st.radio("Filter by Type", ["All", "Singles", "Doubles"], horizontal=True, key="match_history_filter")
    filtered_matches = st.session_state.matches_df.copy()
    if match_filter != "All":
        filtered_matches = filtered_matches[filtered_matches["match_type"] == match_filter]
    filtered_matches['date'] = pd.to_datetime(filtered_matches['date'], errors='coerce')
    filtered_matches = filtered_matches.sort_values(by='date', ascending=False).reset_index(drop=True)
    def format_match_players(row):
        if row["match_type"] == "Singles":
            p1_styled = f"<span style='font-weight:bold; color:#fff500;'>{row['team1_player1']}</span>"
            p2_styled = f"<span style='font-weight:bold; color:#fff500;'>{row['team2_player1']}</span>"
            if row["winner"] == "Team 1":
                return f"{p1_styled} def. {p2_styled}"
            else:
                return f"{p2_styled} def. {p1_styled}"
        else:
            p1_styled = f"<span style='font-weight:bold; color:#fff500;'>{row['team1_player1']}</span>"
            p2_styled = f"<span style='font-weight:bold; color:#fff500;'>{row['team1_player2']}</span>"
            p3_styled = f"<span style='font-weight:bold; color:#fff500;'>{row['team2_player1']}</span>"
            p4_styled = f"<span style='font-weight:bold; color:#fff500;'>{row['team2_player2']}</span>"
            if row["winner"] == "Team 1":
                return f"{p1_styled} & {p2_styled} def. {p3_styled} & {p4_styled}"
            else:
                return f"{p3_styled} & {p4_styled} def. {p1_styled} & {p2_styled}"
    def format_match_scores_and_date(row):
        score_parts_plain = [s for s in [row['set1'], row['set2'], row['set3']] if s]
        score_text = ", ".join(score_parts_plain)
        target_width = 30
        padding_spaces = " " * (target_width - len(score_text))
        score_parts_html = [f"<span style='font-weight:bold; color:#fff500;'>{s}</span>" for s in score_parts_plain]
        score_html = ", ".join(score_parts_html)
        date_str = row['date'].strftime('%d %b %y')
        return f"<div style='font-family: monospace; white-space: pre;'>{score_html}{padding_spaces}{date_str}</div>"
    if filtered_matches.empty:
        st.info("No matches found.")
    else:
        for index, row in filtered_matches.iterrows():
            cols = st.columns([1, 8, 1])
            if row["match_image_url"]:
                with cols[0]:
                    try:
                        st.image(row["match_image_url"], width=50, caption="")
                    except Exception as e:
                        st.error(f"Error displaying match image: {str(e)}")
            with cols[1]:
                st.markdown(f"{format_match_players(row)}", unsafe_allow_html=True)
                st.markdown(format_match_scores_and_date(row), unsafe_allow_html=True)
            with cols[2]:
                share_link = generate_whatsapp_link(row)
                st.markdown(f'<a href="{share_link}" target="_blank" style="text-decoration:none; color:#ffffff;"><img src="https://upload.wikimedia.org/wikipedia/commons/6/6b/WhatsApp.svg" alt="WhatsApp Share" style="width:30px;height:30px;"/></a>', unsafe_allow_html=True)
            st.markdown("<hr style='border-top: 1px solid #333333; margin: 10px 0;'>", unsafe_allow_html=True)

    st.markdown("<br><br><br><br><br><br><br><br><br><br>", unsafe_allow_html=True)
    st.subheader("✏️ Manage Existing Match")
    clean_match_options = []
    for _, row in filtered_matches.iterrows():
        score_plain = f"{row['set1']}"
        if row['set2']:
            score_plain += f", {row['set2']}"
        if row['set3']:
            score_plain += f", {row['set3']}"
        date_plain = row['date'].strftime('%d %b %y %H:%M')
        if row["match_type"] == "Singles":
            desc_plain = f"{row['team1_player1']} def. {row['team2_player1']}" if row["winner"] == "Team 1" else f"{row['team2_player1']} def. {row['team1_player1']}"
        else:
            desc_plain = f"{row['team1_player1']} & {row['team1_player2']} def. {row['team2_player1']} & {row['team2_player2']}" if row["winner"] == "Team 1" else f"{row['team2_player1']} & {row['team2_player2']} def. {row['team1_player1']} & {row['team1_player2']}"
        clean_match_options.append(f"{desc_plain} | {score_plain} | {date_plain} | {row['match_id']}")
    selected_match_to_edit = st.selectbox("Select a match to edit or delete", [""] + clean_match_options, key="select_match_to_edit")
    if selected_match_to_edit:
        selected_id = selected_match_to_edit.split(" | ")[-1]
        row = st.session_state.matches_df[st.session_state.matches_df["match_id"] == selected_id].iloc[0]
        idx = st.session_state.matches_df[st.session_state.matches_df["match_id"] == selected_id].index[0]
        current_date_dt = pd.to_datetime(row["date"])
        all_scores = [""] + tennis_scores()
        set1_index = all_scores.index(row["set1"]) if row["set1"] in all_scores else 0
        set2_index = all_scores.index(row["set2"]) if row["set2"] in all_scores else 0
        set3_index = all_scores.index(row["set3"]) if row["set3"] in all_scores else 0
        with st.expander("Edit Match Details"):
            date_edit = st.date_input("Match Date", value=current_date_dt.date(), key=f"edit_date_{selected_id}")
            time_edit = st.time_input("Match Time", value=current_date_dt.time(), key=f"edit_time_{selected_id}")
            match_type_edit = st.radio("Match Type", ["Doubles", "Singles"], index=0 if row["match_type"] == "Doubles" else 1, key=f"edit_match_type_{selected_id}")
            p1_edit = st.selectbox("Team 1 - Player 1", [""] + available_players, index=available_players.index(row["team1_player1"]) + 1 if row["team1_player1"] in available_players else 0, key=f"edit_t1p1_{selected_id}")
            p2_edit = st.selectbox("Team 1 - Player 2", [""] + available_players, index=available_players.index(row["team1_player2"]) + 1 if row["team1_player2"] in available_players else 0, key=f"edit_t1p2_{selected_id}")
            p3_edit = st.selectbox("Team 2 - Player 1", [""] + available_players, index=available_players.index(row["team2_player1"]) + 1 if row["team2_player1"] in available_players else 0, key=f"edit_t2p1_{selected_id}")
            p4_edit = st.selectbox("Team 2 - Player 2", [""] + available_players, index=available_players.index(row["team2_player2"]) + 1 if row["team2_player2"] in available_players else 0, key=f"edit_t2p2_{selected_id}")
            set1_edit = st.selectbox("Set 1", all_scores, index=set1_index, key=f"edit_set1_{selected_id}")
            set2_edit = st.selectbox("Set 2 (optional)", all_scores, index=set2_index, key=f"edit_set2_{selected_id}")
            set3_edit = st.selectbox("Set 3 (optional)", all_scores, index=set3_index, key=f"edit_set3_{selected_id}")
            winner_edit = st.selectbox("Winner", ["Team 1", "Team 2", "Tie"], index=["Team 1", "Team 2", "Tie"].index(row["winner"]), key=f"edit_winner_{selected_id}")
            match_image_edit = st.file_uploader("Update Match Image (optional)", type=["jpg", "jpeg", "png", "gif", "bmp", "webp"], key=f"edit_image_{selected_id}")
            if st.button("Save Changes", key=f"save_match_changes_{selected_id}"):
                image_url_edit = row["match_image_url"]
                if match_image_edit:
                    image_url_edit = upload_image_to_supabase(match_image_edit, selected_id, image_type="match")
                combined_datetime = datetime.combine(date_edit, time_edit)
                st.session_state.matches_df.loc[idx] = {
                    "match_id": selected_id,
                    "date": combined_datetime,
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
                save_matches(st.session_state.matches_df)
                load_matches()
                st.success("Match updated.")
                st.rerun()
        if st.button("🗑️ Delete This Match", key=f"delete_match_{selected_id}"):
            delete_match_from_db(selected_id)
            load_matches()
            st.success("Match deleted.")
            st.rerun()

# Player Profile tab
with tabs[2]:
    st.header("Player Profile")
    st.subheader("Manage & Edit Player Profiles")
    with st.expander("Add, Edit or Remove Player", expanded=False, icon="➡️"):
        st.markdown("##### Add New Player")
        new_player = st.text_input("Player Name", key="new_player_input").strip()
        if st.button("Add Player", key="add_player_button"):
            if new_player:
                if new_player.lower() == "visitor":
                    st.warning("The name 'Visitor' is reserved and cannot be added.")
                elif new_player in st.session_state.players_df["name"].tolist():
                    st.warning(f"{new_player} already exists.")
                else:
                    new_player_data = {"name": new_player, "profile_image_url": "", "birthday": ""}
                    st.session_state.players_df = pd.concat([st.session_state.players_df, pd.DataFrame([new_player_data])], ignore_index=True)
                    save_players(st.session_state.players_df)
                    load_players()
                    st.success(f"{new_player} added.")
                    st.rerun()
            else:
                st.warning("Please enter a player name to add.")
        st.markdown("---")
        st.markdown("##### Edit or Remove Existing Player")
        players = sorted([p for p in st.session_state.players_df["name"].dropna().tolist() if p != "Visitor"]) if "name" in st.session_state.players_df.columns else []
        if not players:
            st.info("No players available. Add a new player to begin.")
        else:
            selected_player_manage = st.selectbox("Select Player", [""] + players, key="manage_player_select")
            if selected_player_manage:
                player_data = st.session_state.players_df[st.session_state.players_df["name"] == selected_player_manage].iloc[0]
                current_image = player_data.get("profile_image_url", "")
                current_birthday = player_data.get("birthday", "")
                st.markdown(f"**Current Profile for {selected_player_manage}**")
                if current_image:
                    st.image(current_image, width=100)
                else:
                    st.write("No profile image set.")
                profile_image = st.file_uploader("Upload New Profile Image (optional)", type=["jpg", "jpeg", "png", "gif", "bmp", "webp"], key=f"profile_image_upload_{selected_player_manage}")
                default_day = 1
                default_month = 1
                if current_birthday and isinstance(current_birthday, str) and re.match(r'^\d{2}-\d{2}$', current_birthday):
                    try:
                        day_str, month_str = current_birthday.split("-")
                        default_day = int(day_str)
                        default_month = int(month_str)
                    except (ValueError, IndexError):
                        pass
                birthday_day = st.number_input("Birthday Day", min_value=1, max_value=31, value=default_day, key=f"birthday_day_{selected_player_manage}")
                birthday_month = st.number_input("Birthday Month", min_value=1, max_value=12, value=default_month, key=f"birthday_month_{selected_player_manage}")
                col_save, col_delete = st.columns(2)
                with col_save:
                    if st.button("Save Profile Changes", key=f"save_profile_changes_{selected_player_manage}"):
                        image_url = current_image
                        if profile_image:
                            image_url = upload_image_to_supabase(profile_image, f"profile_{selected_player_manage}_{uuid.uuid4().hex[:6]}", image_type="profile")
                        st.session_state.players_df.loc[st.session_state.players_df["name"] == selected_player_manage, "profile_image_url"] = image_url
                        st.session_state.players_df.loc[st.session_state.players_df["name"] == selected_player_manage, "birthday"] = f"{birthday_day:02d}-{birthday_month:02d}"
                        save_players(st.session_state.players_df)
                        load_players()
                        st.success(f"Profile for {selected_player_manage} updated.")
                        st.rerun()
                with col_delete:
                    if st.button("Remove Player", key=f"remove_player_{selected_player_manage}"):
                        if selected_player_manage.lower() == "visitor":
                            st.warning("The 'Visitor' player cannot be removed.")
                        else:
                            # Check for associated matches
                            if st.session_state.matches_df[
                                (st.session_state.matches_df["team1_player1"] == selected_player_manage) |
                                (st.session_state.matches_df["team1_player2"] == selected_player_manage) |
                                (st.session_state.matches_df["team2_player1"] == selected_player_manage) |
                                (st.session_state.matches_df["team2_player2"] == selected_player_manage)
                            ].shape[0] > 0:
                                st.warning(f"Cannot delete {selected_player_manage} because they have associated matches. Delete their matches first.")
                            else:
                                delete_player_from_db(selected_player_manage)
                                st.session_state.players_df = st.session_state.players_df[st.session_state.players_df["name"] != selected_player_manage].reset_index(drop=True)
                                save_players(st.session_state.players_df)
                                load_players()
                                st.success(f"{selected_player_manage} removed.")
                                st.rerun()
    st.markdown("---")
    st.subheader("Player Insights")
    rank_df_combined, partner_stats_combined = calculate_rankings(st.session_state.matches_df)
    if players:
        display_player_insights(players, st.session_state.players_df, st.session_state.matches_df, rank_df_combined, partner_stats_combined, key_prefix="profile_")
    else:
        st.info("No players available for insights. Please add players above.")

with tabs[3]:
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
  
st.markdown("---")
st.subheader("Manual Backup")
col_match_backup, col_player_backup = st.columns(2)
with col_match_backup:
    if not st.session_state.matches_df.empty:
        csv_matches = st.session_state.matches_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download Matches Data as CSV",
            data=csv_matches,
            file_name=f'ar_tennis_matches_backup_{datetime.now().strftime("%Y-%m-%d")}.csv',
            mime='text/csv',
            help="Download a complete backup of all match records as a CSV file."
        )
    else:
        st.info("No match data available to download.")
with col_player_backup:
    if not st.session_state.players_df.empty:
        csv_players = st.session_state.players_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download Players Data as CSV",
            data=csv_players,
            file_name=f'ar_tennis_players_backup_{datetime.now().strftime("%Y-%m-%d")}.csv',
            mime='text/csv',
            help="Download a complete backup of all player records as a CSV file."
        )
    else:
        st.info("No player data available to download.")
st.markdown("""
<div style='background-color: #0d5384; padding: 1rem; border-left: 5px solid #fff500; border-radius: 0.5rem; color: white;'>
Built with ❤️ using <a href='https://streamlit.io/' style='color: #ccff00;'>Streamlit</a> — free and open source.
<a href='https://devs-scripts.streamlit.app/' style='color: #ccff00;'>Other Scripts by dev</a> on Streamlit.
</div>
""", unsafe_allow_html=True)
