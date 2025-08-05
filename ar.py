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

/* ... rest of your custom CSS ... */
@import url('https://fonts.googleapis.com/css2?family=Offside&display=swap');
html, body, [class*="st-"], h1, h2, h3, h4, h5, h6 {
    font-family: 'Offside', sans-serif !important;
}
/* Other styles */
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
.partners-col::before { content: "Partners Played With: "; font-weight: bold; color: #bbbbbb; }
.best-partner-col::before { content: "Most Effective Partner: "; font-weight: bold; color: #bbbbbb; }

/* Ensure the actual values are white. Applies to the text content within the div, not the ::before. */
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
            # Ensure the 'date' column is in a consistent string format for Supabase
            df_to_save['date'] = pd.to_datetime(df_to_save['date'], errors='coerce')
            df_to_save = df_to_save.dropna(subset=['date'])
            df_to_save['date'] = df_to_save['date'].dt.strftime('%Y-%m-%d %H:%M:%S')
            
        supabase.table(matches_table_name).upsert(df_to_save.to_dict("records")).execute()
    except Exception as e:
        st.error(f"Error saving matches: {str(e)}")

def delete_match_from_db(match_id):
    try:
        supabase.table(matches_table_name).delete().eq("match_id", match_id).execute()
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

def display_player_insights(selected_players, players_df, matches_df, rank_df, partner_wins, key_prefix=""):
    # If selected_players is a single string, convert to a list for uniform handling
    if isinstance(selected_players, str):
        selected_players = [selected_players] if selected_players else []
    
    if not selected_players:
        st.info("No players selected or available for insights.")
        return

    # Sort players by name
    selected_players = sorted(selected_players)

    # Use the same container and scroll styling as rankings
    st.markdown('<div class="rankings-table-container">', unsafe_allow_html=True)
    st.markdown('<div class="rankings-table-scroll">', unsafe_allow_html=True)
    
    for selected_player in selected_players:
        # Fetch player information
        player_info = players_df[players_df["name"] == selected_player].iloc[0] if selected_player in players_df["name"].values else None
        if player_info is None:
            continue
        birthday = player_info.get("birthday", "Not set")
        profile_image = player_info.get("profile_image_url", "")
        trend = get_player_trend(selected_player, matches_df)
        
        # Prepare profile image HTML
        profile_html = f'<img src="{profile_image}" class="ranking-profile-image" alt="Profile">' if profile_image else ''
        
        # Style player name and values
        player_styled = f"<span style='font-weight:bold; color:#fff500;'>{selected_player}</span>"
        
        # Initialize default values for players without match data
        rank = "N/A"
        points = 0
        win_percent = 0.0
        matches = 0
        wins = 0
        losses = 0
        game_diff_avg = 0.0
        games_won = 0
        partners_list = "None"
        best_partner = "None"
        
        # If player has ranking data, populate the stats
        if selected_player in rank_df["Player"].values:
            player_data = rank_df[rank_df["Player"] == selected_player].iloc[0]
            rank = player_data["Rank"]
            points = player_data["Points"]
            win_percent = player_data["Win %"]
            matches = int(player_data["Matches"])
            wins = int(player_data["Wins"])
            losses = int(player_data["Losses"])
            game_diff_avg = player_data["Game Diff Avg"]
            games_won = int(player_data["Games Won"])
            
            # Partners and most effective partner
            if selected_player in partner_wins and partner_wins[selected_player]:
                partners_list = ', '.join([f'{p} ({item["wins"]} wins, GD Sum: {item["game_diff_sum"]:.2f})' for p, item in partner_wins[selected_player].items()])
                sorted_partners = sorted(
                    partner_wins[selected_player].items(),
                    key=lambda item: (item[1]['wins'], item[1]['game_diff_sum'] / item[1]['wins'] if item[1]['wins'] > 0 else 0),
                    reverse=True
                )
                best_partner_name = sorted_partners[0][0]
                best_wins = sorted_partners[0][1]['wins']
                best_partner = f"{best_partner_name} ({best_wins} {'win' if best_wins == 1 else 'wins'})"
        
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
        
        # Render the card using the same CSS classes as the rankings tab
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
    partner_wins = defaultdict(lambda: defaultdict(lambda: {'wins': 0, 'game_diff_sum': 0}))
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
        if row["winner"] == "Team 1":
            for p in t1:
                scores[p] += 3
                wins[p] += 1
                matches_played[p] += 1
                game_diff[p] += match_gd_avg
            for p in t2:
                scores[p] += 1
                losses[p] += 1
                matches_played[p] += 1
                game_diff[p] -= match_gd_avg
        elif row["winner"] == "Team 2":
            for p in t2:
                scores[p] += 3
                wins[p] += 1
                matches_played[p] += 1
                game_diff[p] -= match_gd_avg
            for p in t1:
                scores[p] += 1
                losses[p] += 1
                matches_played[p] += 1
                game_diff[p] += match_gd_avg
        else:
            for p in t1 + t2:
                scores[p] += 1.5
                matches_played[p] += 1
                game_diff[p] += match_gd_avg if p in t1 else -match_gd_avg
        for set_score in [row['set1'], row['set2'], row['set3']]:
            if set_score and '-' in set_score:
                try:
                    team1_games, team2_games = map(int, set_score.split('-'))
                    for p in t1:
                        games_won[p] += team1_games
                    for p in t2:
                        games_won[p] += team2_games
                except ValueError:
                    continue
        if row['match_type'] == 'Doubles':
            if row["winner"] == "Team 1":
                partner_wins[row['team1_player1']][row['team1_player2']]['wins'] += 1
                partner_wins[row['team1_player1']][row['team1_player2']]['game_diff_sum'] += match_gd_sum
                partner_wins[row['team1_player2']][row['team1_player1']]['wins'] += 1
                partner_wins[row['team1_player2']][row['team1_player1']]['game_diff_sum'] += match_gd_sum
            elif row["winner"] == "Team 2":
                partner_wins[row['team2_player1']][row['team2_player2']]['wins'] += 1
                partner_wins[row['team2_player1']][row['team2_player2']]['game_diff_sum'] += match_gd_sum
                partner_wins[row['team2_player2']][row['team2_player1']]['wins'] += 1
                partner_wins[row['team2_player2']][row['team2_player1']]['game_diff_sum'] += match_gd_sum
    rank_data = []
    players_df = st.session_state.players_df
    for player in scores:
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
    return rank_df, partner_wins
    
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

def display_rankings_table(df, title):
    if df.empty:
        st.info(f"No {title} ranking data available.")
        return
    
    st.subheader(f"{title} Player Rankings Table")
    # Drop the 'Profile' and 'Recent Trend' columns as they don't fit well in a simple table
    display_df = df.drop(columns=['Profile', 'Recent Trend'])
    st.dataframe(display_df, use_container_width=True, hide_index=True)

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
players = sorted(players_df["name"].dropna().tolist()) if "name" in players_df.columns else []

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
        rank_df, partner_wins = calculate_rankings(filtered_matches)
        st.subheader(f"Rankings as of {datetime.now().strftime('%d/%m')}")
        st.markdown('<div class="rankings-table-container">', unsafe_allow_html=True)
        st.markdown('<div class="rankings-table-scroll">', unsafe_allow_html=True)
        if rank_df.empty:
            st.info("No ranking data available for this view.")
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
        selected_player_rankings = st.selectbox("Select a player for insights", [""] + players, index=0, key="insights_player_rankings_doubles")
        if selected_player_rankings:
            display_player_insights(selected_player_rankings, players_df, filtered_matches, rank_df, partner_wins, key_prefix="rankings_doubles_")
        else:
            st.info("Player insights will be available once a player is selected.")
    elif ranking_type == "Singles":
        filtered_matches = matches[matches['match_type'] == 'Singles'].copy()
        rank_df, partner_wins = calculate_rankings(filtered_matches)
        current_date_formatted = datetime.now().strftime("%d/%m")
        st.subheader(f"Rankings as of {current_date_formatted}")
        st.markdown('<div class="rankings-table-container">', unsafe_allow_html=True)
        st.markdown('<div class="rankings-table-scroll">', unsafe_allow_html=True)
        if rank_df.empty:
            st.info("No ranking data available for this view.")
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
        selected_player_rankings = st.selectbox("Select a player for insights", [""] + players, index=0, key="insights_player_rankings_singles")
        if selected_player_rankings:
            display_player_insights(selected_player_rankings, players_df, filtered_matches, rank_df, partner_wins, key_prefix="rankings_singles_")
        else:
            st.info("Player insights will be available once a player is selected.")
    elif ranking_type == "Nerd Stuff":
        if matches.empty or players_df.empty:
            st.info("No match data available to generate interesting stats.")
        else:
            rank_df, partner_wins = calculate_rankings(matches)
            
            # Most Effective Partnership
            st.markdown("### 🤝 Most Effective Partnership")
            best_partner = None
            max_value = -1
            for player, partners in partner_wins.items():
                for partner, stats in partners.items():
                    if player < partner: # Avoid double counting
                        score = stats['wins'] + (stats['game_diff_sum'] / max(stats['wins'], 1))
                        if score > max_value:
                            max_value = score
                            best_partner = (player, partner, stats)

            if best_partner:
                p1, p2, stats = best_partner
                p1_styled = f"<span style='font-weight:bold; color:#fff500;'>{p1}</span>"
                p2_styled = f"<span style='font-weight:bold; color:#fff500;'>{p2}</span>"
                st.markdown(f"The most effective partnership is {p1_styled} and {p2_styled} with a combined score of wins and average game difference. They have **{stats['wins']}** wins and a total game difference of **{stats['game_diff_sum']:.2f}**.", unsafe_allow_html=True)
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
                                player_stats[p]['wins'] += 1
                                player_stats[p]['gd_sum'] += match_gd_sum
                                for partner in t1:
                                    if partner != p:
                                        player_stats[p]['partners'].add(partner)
                        elif row["winner"] == "Team 2":
                            for p in t2:
                                player_stats[p]['wins'] += 1
                                player_stats[p]['gd_sum'] += match_gd_sum
                                for partner in t2:
                                    if partner != p:
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
                                if p: cumulative_game_diff[p] += set_gd
                            for p in t2:
                                if p: cumulative_game_diff[p] -= set_gd
                        except ValueError:
                            continue

            if cumulative_game_diff:
                highest_gd_player, highest_gd_value = max(cumulative_game_diff.items(), key=lambda item: item[1])
                player_styled = f"<span style='font-weight:bold; color:#fff500;'>{highest_gd_player}</span>"
                
                # Updated line as per user's request
                st.markdown(f"{player_styled} has the highest cumulative game difference : <span style='font-weight:bold; color:#fff500;'>{highest_gd_value}</span>.", unsafe_allow_html=True)
            else:
                st.info("No match data available to calculate game difference.")

            st.markdown("---")

            # Other interesting stats
            if not rank_df.empty:
                # Player with the most wins
                st.markdown(f"### 👑 Player with the Most Wins")
                most_wins_player = rank_df.sort_values(by="Wins", ascending=False).iloc[0]
                player_styled = f"<span style='font-weight:bold; color:#fff500;'>{most_wins_player['Player']}</span>"
                st.markdown(f"{player_styled} holds the record for most wins with **{int(most_wins_player['Wins'])}** wins.", unsafe_allow_html=True)

                # ADDED DIVIDING LINE HERE
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
        rank_df, partner_wins = calculate_rankings(filtered_matches)
        current_date_formatted = datetime.now().strftime("%d/%m")
        st.subheader(f"Rankings as of {current_date_formatted}")
        st.markdown('<div class="rankings-table-container">', unsafe_allow_html=True)
        st.markdown('<div class="rankings-table-scroll">', unsafe_allow_html=True)
        if rank_df.empty:
            st.info("No ranking data available for this view.")
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
        selected_player_rankings = st.selectbox("Select a player for insights", [""] + players, index=0, key="insights_player_rankings_combined")
        if selected_player_rankings:
            display_player_insights(selected_player_rankings, players_df, filtered_matches, rank_df, partner_wins, key_prefix="rankings_combined_")
        else:
            st.info("Player insights will be available once a player is selected.")

with tabs[1]:
    st.header("Matches")
    with st.expander("➕ Post New Match Result"):
        st.subheader("Enter Match Result")
        match_type_new = st.radio("Match Type", ["Doubles", "Singles"], horizontal=True, key=f"post_match_type_new_{st.session_state.form_key_suffix}")
        available_players = sorted(players.copy() if players else [])
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
                        p3_new = st.selectbox("Team
