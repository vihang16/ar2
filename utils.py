import pandas as pd
from datetime import datetime
from collections import defaultdict
import urllib.parse
import streamlit as st

def tennis_scores():
    """Returns a list of valid tennis set scores."""
    return ["6-0", "6-1", "6-2", "6-3", "6-4", "7-5", "7-6", "0-6", "1-6", "2-6", "3-6", "4-6", "5-7", "6-7"]

def get_quarter(month: int) -> str:
    """Determines the financial quarter from a given month."""
    if 1 <= month <= 3: return "Q1"
    if 4 <= month <= 6: return "Q2"
    if 7 <= month <= 9: return "Q3"
    return "Q4"

def generate_match_id(matches_df: pd.DataFrame, match_datetime: datetime) -> str:
    """Generates a unique match ID based on the quarter and year."""
    year = match_datetime.year
    quarter = get_quarter(match_datetime.month)
    
    if not matches_df.empty and 'date' in matches_df.columns:
        matches_df['date'] = pd.to_datetime(matches_df['date'], errors='coerce')
        # Filter matches for the same year and quarter
        filtered_matches = matches_df[
            (matches_df['date'].dt.year == year) &
            (matches_df['date'].apply(lambda d: get_quarter(d.month) == quarter if pd.notna(d) else False))
        ]
        serial_number = len(filtered_matches) + 1
    else:
        serial_number = 1
        
    new_id = f"AR{quarter}{year}-{serial_number:02d}"
    
    # Ensure the ID is unique by incrementing the serial number if a collision occurs
    while not matches_df.empty and 'match_id' in matches_df.columns and new_id in matches_df['match_id'].values:
        serial_number += 1
        new_id = f"AR{quarter}{year}-{serial_number:02d}"
        
    return new_id

def get_player_trend(player: str, matches: pd.DataFrame, max_matches=5) -> str:
    """Calculates the recent match trend (W/L) for a player."""
    player_matches = matches[
        (matches['team1_player1'] == player) | (matches['team1_player2'] == player) |
        (matches['team2_player1'] == player) | (matches['team2_player2'] == player)
    ].copy()
    
    if player_matches.empty:
        return 'No recent matches'
        
    player_matches['date'] = pd.to_datetime(player_matches['date'], errors='coerce')
    player_matches = player_matches.sort_values(by='date', ascending=False)
    
    trend = []
    for _, row in player_matches.head(max_matches).iterrows():
        team1 = [row['team1_player1'], row.get('team1_player2')]
        team2 = [row['team2_player1'], row.get('team2_player2')]
        
        if (player in team1 and row['winner'] == 'Team 1') or \
           (player in team2 and row['winner'] == 'Team 2'):
            trend.append('W')
        elif row['winner'] != 'Tie':
            trend.append('L')
            
    return ' '.join(trend)

def calculate_rankings(matches_to_rank: pd.DataFrame, players_df: pd.DataFrame):
    """Calculates player rankings and partnership statistics from match data."""
    scores = defaultdict(float)
    wins = defaultdict(int)
    losses = defaultdict(int)
    matches_played = defaultdict(int)
    games_won = defaultdict(int)
    game_diff = defaultdict(float)
    partner_stats = defaultdict(lambda: defaultdict(lambda: {'wins': 0, 'losses': 0, 'ties': 0, 'matches': 0, 'game_diff_sum': 0}))

    for _, row in matches_to_rank.iterrows():
        t1 = [row['team1_player1']]
        if row['match_type'] == 'Doubles' and row['team1_player2']: t1.append(row['team1_player2'])
        t2 = [row['team2_player1']]
        if row['match_type'] == 'Doubles' and row['team2_player2']: t2.append(row['team2_player2'])
        
        team1_total_games, team2_total_games, set_count = 0, 0, 0
        match_gd_sum = 0
        for set_score in [row['set1'], row['set2'], row['set3']]:
            if isinstance(set_score, str) and '-' in set_score:
                try:
                    g1, g2 = map(int, set_score.split('-'))
                    team1_total_games += g1
                    team2_total_games += g2
                    match_gd_sum += g1 - g2
                    set_count += 1
                except ValueError:
                    continue
        
        match_gd_avg = match_gd_sum / set_count if set_count > 0 else 0

        # Update individual player stats
        if row["winner"] == "Team 1":
            for p in t1:
                if p != "Visitor": scores[p] += 3; wins[p] += 1; game_diff[p] += match_gd_avg
            for p in t2:
                if p != "Visitor": scores[p] += 1; losses[p] += 1; game_diff[p] -= match_gd_avg
        elif row["winner"] == "Team 2":
            for p in t2:
                if p != "Visitor": scores[p] += 3; wins[p] += 1; game_diff[p] -= match_gd_avg
            for p in t1:
                if p != "Visitor": scores[p] += 1; losses[p] += 1; game_diff[p] += match_gd_avg
        else:  # Tie
            for p in t1 + t2:
                if p != "Visitor": scores[p] += 1.5

        # Update matches played and games won for all non-visitor players
        for p in t1:
            if p != "Visitor": matches_played[p] += 1; games_won[p] += team1_total_games
        for p in t2:
            if p != "Visitor": matches_played[p] += 1; games_won[p] += team2_total_games

        # Update partner stats for doubles matches
        if row['match_type'] == 'Doubles':
            for p1 in t1:
                for p2 in t1:
                    if p1 != p2 and p1 != "Visitor" and p2 != "Visitor":
                        partner_stats[p1][p2]['matches'] += 1
                        partner_stats[p1][p2]['game_diff_sum'] += match_gd_sum
                        if row["winner"] == "Team 1": partner_stats[p1][p2]['wins'] += 1
                        elif row["winner"] == "Team 2": partner_stats[p1][p2]['losses'] += 1
                        else: partner_stats[p1][p2]['ties'] += 1
            for p1 in t2:
                for p2 in t2:
                    if p1 != p2 and p1 != "Visitor" and p2 != "Visitor":
                        partner_stats[p1][p2]['matches'] += 1
                        partner_stats[p1][p2]['game_diff_sum'] -= match_gd_sum
                        if row["winner"] == "Team 2": partner_stats[p1][p2]['wins'] += 1
                        elif row["winner"] == "Team 1": partner_stats[p1][p2]['losses'] += 1
                        else: partner_stats[p1][p2]['ties'] += 1

    rank_data = []
    for player in scores:
        if player == "Visitor": continue
        win_percentage = (wins[player] / matches_played[player] * 100) if matches_played[player] > 0 else 0
        game_diff_avg = (game_diff[player] / matches_played[player]) if matches_played[player] > 0 else 0
        profile_image = players_df.loc[players_df["name"] == player, "profile_image_url"].iloc[0] if player in players_df["name"].values else ""
        
        rank_data.append({
            "Player": player, "Points": scores[player], "Win %": win_percentage,
            "Matches": matches_played[player], "Wins": wins[player], "Losses": losses[player],
            "Games Won": games_won[player], "Game Diff Avg": game_diff_avg,
            "Profile": profile_image, "Recent Trend": get_player_trend(player, matches_to_rank)
        })

    rank_df = pd.DataFrame(rank_data)
    if not rank_df.empty:
        rank_df = rank_df.sort_values(
            by=["Points", "Win %", "Game Diff Avg", "Games Won", "Player"],
            ascending=[False, False, False, False, True]
        ).reset_index(drop=True)
        rank_df["Rank"] = [f"🏆 {i}" for i in range(1, len(rank_df) + 1)]

    return rank_df, partner_stats

def generate_whatsapp_link(row: pd.Series) -> str:
    """Generates a WhatsApp share link for a match result."""
    if row["winner"] == "Team 1":
        winner_players = [p for p in [row['team1_player1'], row.get('team1_player2')] if p]
        loser_players = [p for p in [row['team2_player1'], row.get('team2_player2')] if p]
    else: # Team 2 wins or Tie
        winner_players = [p for p in [row['team2_player1'], row.get('team2_player2')] if p]
        loser_players = [p for p in [row['team1_player1'], row.get('team1_player2')] if p]

    winner_str = " & ".join(winner_players)
    loser_str = " & ".join(loser_players)
    
    scores_list = [f'*{s.replace("-", ":")}*' for s in [row['set1'], row['set2'], row['set3']] if s]
    scores_str = " ".join(scores_list)
    date_str = pd.to_datetime(row['date']).strftime('%d %b %y')

    share_text = f"*{winner_str} def. {loser_str}*\nSet scores {scores_str} on {date_str}"
    encoded_text = urllib.parse.quote(share_text)
    
    return f"https://api.whatsapp.com/send/?text={encoded_text}&type=custom_url&app_absent=0"
