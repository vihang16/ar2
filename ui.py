import streamlit as st
import pandas as pd
from datetime import datetime
import re
from collections import defaultdict
from utils import get_player_trend, generate_whatsapp_link, tennis_scores
from data_manager import delete_match_from_db, upload_image_to_supabase, save_matches, load_matches

def apply_custom_css():
    """Applies custom CSS styles to the Streamlit app."""
    st.markdown("""
    <style>
    .stApp {
      background: linear-gradient(to bottom, #07314f, #031827);
      background-size: cover;
      background-repeat: no-repeat;
      background-position: center;
      background-attachment: fixed;
    }
    [data-testid="stHeader"] {
      background: linear-gradient(to top, #07314f, #035996) !important;
    }
    .profile-image {
        width: 50px; height: 50px; object-fit: cover; border-radius: 50%;
        margin-right: 10px; vertical-align: middle; transition: transform 0.2s;
    }
    .profile-image:hover { transform: scale(1.1); }
    @import url('https://fonts.googleapis.com/css2?family=Offside&display=swap');
    html, body, [class*="st-"], h1, h2, h3, h4, h5, h6 {
        font-family: 'Offside', sans-serif !important;
    }
    /* Style for tabs to spread them out */
    div[data-testid="stTabs"] > div {
        display: flex;
        justify-content: space-around;
        width: 100%;
    }
    div[data-testid="stTabs"] button {
        flex: 1;
        text-align: center;
        padding: 10px;
        margin: 0 5px;
        font-size: 1.1em;
        color: #fff500;
        border-bottom: 2px solid transparent;
    }
    div[data-testid="stTabs"] button[aria-selected="true"] {
        border-bottom: 2px solid #fff500;
        font-weight: bold;
    }
    .rankings-table-container {
        width: 100%; background: rgba(255, 255, 255, 0.05); border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-top: 0px !important; padding: 10px;
        border: 1px solid #333;
    }
    .rankings-table-scroll { max-height: 600px; overflow-y: auto; }
    .ranking-row {
        display: block; padding: 10px; margin-bottom: 10px;
        border: 1px solid #696969; border-radius: 8px; background: rgba(0,0,0,0.2);
    }
    .rank-col, .profile-col, .player-col, .points-col, .win-percent-col, .matches-col, .wins-col, .losses-col, .games-won-col, .game-diff-avg-col, .trend-col, .birthday-col, .partners-col, .best-partner-col {
        width: 100%; text-align: left; padding: 2px 0; font-size: 1em; margin-bottom: 5px; word-break: break-word;
    }
    .rank-col { display: inline-block; font-size: 1.3em; font-weight: bold; margin-right: 5px; color: #fff500; }
    .profile-col { text-align: left; margin: 0 5px 0 0; display: inline-block; vertical-align: middle; }
    .player-col { font-size: 1.3em; font-weight: bold; display: inline-block; vertical-align: middle; margin-right: 5px; }
    .rank-profile-player-group { display: flex; align-items: center; justify-content: flex-start; margin-bottom: 10px; }
    .points-col::before, .win-percent-col::before, .matches-col::before, .wins-col::before, .losses-col::before, .games-won-col::before, .game-diff-avg-col::before, .trend-col::before, .birthday-col::before, .partners-col::before, .best-partner-col::before {
        font-weight: bold; color: #bbbbbb;
    }
    .points-col::before { content: "Points: "; }
    .win-percent-col::before { content: "Win %: "; }
    .matches-col::before { content: "Matches: "; }
    .wins-col::before { content: "Wins: "; }
    .losses-col::before { content: "Losses: "; }
    .games-won-col::before { content: "Games Won: "; }
    .game-diff-avg-col::before { content: "Game Diff Avg: "; }
    .trend-col::before { content: "Recent Trend: "; }
    .birthday-col::before { content: "Birthday: "; }
    .partners-col::before { content: "Partners Played With: "; }
    .best-partner-col::before { content: "Most Effective Partner: "; }
    .points-col, .win-percent-col, .matches-col, .wins-col, .losses-col, .games-won-col, .game-diff-avg-col, .trend-col, .birthday-col, .partners-col, .best-partner-col {
        color: #fff500;
    }
    .table-container {
        width: 100%; background: rgba(255, 255, 255, 0.05); border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1); padding: 10px; border: 1px solid #333;
    }
    .table-scroll { max-height: 600px; overflow-y: auto; }
    table {
        width: 100%; border-collapse: collapse; font-family: 'Offside', sans-serif;
    }
    th, td {
        padding: 8px; text-align: left; border-bottom: 1px solid #696969; color: #fff500;
    }
    th { background: rgba(0,0,0,0.2); font-weight: bold; color: #bbbbbb; }
    .table-profile-img { width: 40px; height: 40px; border-radius: 50%; vertical-align: middle; }
    </style>
    """, unsafe_allow_html=True)

def display_rankings_card_view(rank_df, title):
    """Displays rankings in a responsive card layout."""
    st.subheader(f"{title} Rankings as of {datetime.now().strftime('%d/%m')}")
    st.markdown('<div class="rankings-table-container"><div class="rankings-table-scroll">', unsafe_allow_html=True)
    if rank_df.empty:
        st.info("No ranking data available for this view.")
    else:
        for _, row in rank_df.iterrows():
            profile_html = f'<a href="{row["Profile"]}" target="_blank"><img src="{row["Profile"]}" class="profile-image" alt="Profile"></a>' if row["Profile"] else ''
            player_styled = f"<span style='font-weight:bold; color:#fff500;'>{row['Player']}</span>"
            st.markdown(f"""
            <div class="ranking-row">
                <div class="rank-profile-player-group">
                    <div class="rank-col">{row["Rank"]}</div>
                    <div class="profile-col">{profile_html}</div>
                    <div class="player-col">{player_styled}</div>
                </div>
                <div class="points-col">{row['Points']:.1f}</div>
                <div class="win-percent-col">{row["Win %"]:.1f}%</div>
                <div class="matches-col">{int(row["Matches"])}</div>
                <div class="wins-col">{int(row["Wins"])}</div>
                <div class="losses-col">{int(row["Losses"])}</div>
                <div class="game-diff-avg-col">{row["Game Diff Avg"]:.2f}</div>
                <div class="games-won-col">{int(row["Games Won"])}</div>
                <div class="trend-col">{row['Recent Trend']}</div>
            </div>
            """, unsafe_allow_html=True)
    st.markdown('</div></div>', unsafe_allow_html=True)

def display_rankings_table(rank_df, title):
    """Displays rankings in a table format."""
    st.subheader(f"{title} Rankings as of {datetime.now().strftime('%d/%m')}")
    st.markdown('<div class="table-container"><div class="table-scroll">', unsafe_allow_html=True)
    if rank_df.empty:
        st.info("No ranking data available for this view.")
    else:
        table_html = '<table><thead><tr>'
        headers = ["Rank", "Profile", "Player", "Points", "Win %", "Matches", "Wins", "Losses", "Game Diff Avg", "Games Won", "Recent Trend"]
        for header in headers:
            table_html += f'<th>{header}</th>'
        table_html += '</tr></thead><tbody>'
        
        for _, row in rank_df.iterrows():
            profile_img = f'<a href="{row["Profile"]}" target="_blank"><img src="{row["Profile"]}" class="table-profile-img" alt="Profile"></a>' if row["Profile"] else ''
            table_html += '<tr>'
            table_html += f'<td>{row["Rank"]}</td>'
            table_html += f'<td>{profile_img}</td>'
            table_html += f'<td>{row["Player"]}</td>'
            table_html += f'<td>{row["Points"]:.1f}</td>'
            table_html += f'<td>{row["Win %"]:.1f}%</td>'
            table_html += f'<td>{int(row["Matches"])}</td>'
            table_html += f'<td>{int(row["Wins"])}</td>'
            table_html += f'<td>{int(row["Losses"])}</td>'
            table_html += f'<td>{row["Game Diff Avg"]:.2f}</td>'
            table_html += f'<td>{int(row["Games Won"])}</td>'
            table_html += f'<td>{row["Recent Trend"]}</td>'
            table_html += '</tr>'
        
        table_html += '</tbody></table>'
        st.markdown(table_html, unsafe_allow_html=True)
    st.markdown('</div></div>', unsafe_allow_html=True)

def display_player_insights(selected_players, players_df, matches_df, rank_df, partner_stats, key_prefix=""):
    """Displays detailed insights for selected players or their birthdays."""
    if isinstance(selected_players, str):
        selected_players = [selected_players] if selected_players else []
    selected_players = [p for p in selected_players if p != "Visitor"]

    if not selected_players:
        st.info("No players selected or available for insights.")
        return

    view_option = st.radio("Select View", ["Player Insights", "Birthdays"], horizontal=True, key=f"{key_prefix}view_selector")

    st.markdown('<div class="rankings-table-container"><div class="rankings-table-scroll">', unsafe_allow_html=True)

    if view_option == "Birthdays":
        birthday_data = []
        for player_name in selected_players:
            player_info = players_df[players_df["name"] == player_name]
            if not player_info.empty:
                player_info = player_info.iloc[0]
                birthday = player_info.get("birthday", "")
                if birthday and re.match(r'^\d{2}-\d{2}$', birthday):
                    try:
                        day, month = map(int, birthday.split("-"))
                        birthday_data.append({
                            "Player": player_name,
                            "Birthday": datetime(2000, month, day).strftime("%d %b"),
                            "SortDate": datetime(2000, month, day),
                            "Profile": player_info.get("profile_image_url", "")
                        })
                    except ValueError:
                        continue
        if not birthday_data:
            st.info("No valid birthday data available for selected players.")
        else:
            birthday_df = pd.DataFrame(birthday_data).sort_values(by="SortDate")
            for _, row in birthday_df.iterrows():
                profile_html = f'<a href="{row["Profile"]}" target="_blank"><img src="{row["Profile"]}" class="profile-image"></a>' if row["Profile"] else ''
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
    else:
        for player_name in selected_players:
            rank_info = rank_df[rank_df["Player"] == player_name]
            if rank_info.empty:
                st.info(f"No ranking data available for {player_name}.")
                continue
            rank_info = rank_info.iloc[0]
            profile_html = f'<a href="{rank_info["Profile"]}" target="_blank"><img src="{rank_info["Profile"]}" class="profile-image"></a>' if rank_info["Profile"] else ''
            player_styled = f"<span style='font-weight:bold; color:#fff500;'>{player_name}</span>"
            st.markdown(f"""
            <div class="ranking-row">
                <div class="rank-profile-player-group">
                    <div class="rank-col">{rank_info["Rank"]}</div>
                    <div class="profile-col">{profile_html}</div>
                    <div class="player-col">{player_styled}</div>
                </div>
                <div class="points-col">{rank_info['Points']:.1f}</div>
                <div class="win-percent-col">{rank_info["Win %"]:.1f}%</div>
                <div class="matches-col">{int(rank_info["Matches"])}</div>
                <div class="wins-col">{int(rank_info["Wins"])}</div>
                <div class="losses-col">{int(rank_info["Losses"])}</div>
                <div class="game-diff-avg-col">{rank_info["Game Diff Avg"]:.2f}</div>
                <div class="games-won-col">{int(rank_info["Games Won"])}</div>
                <div class="trend-col">{rank_info['Recent Trend']}</div>
                <div class="partners-col">{', '.join([p for p in partner_stats[player_name].keys()])}</div>
                <div class="best-partner-col">{max(partner_stats[player_name].items(), key=lambda x: x[1]['wins'] / x[1]['matches'] if x[1]['matches'] > 0 else 0)[0] if partner_stats[player_name] else 'None'}</div>
            </div>
            """, unsafe_allow_html=True)
    st.markdown('</div></div>', unsafe_allow_html=True)

def calculate_head_to_head(matches_df):
    """Calculates head-to-head records between players."""
    head_to_head = defaultdict(lambda: defaultdict(lambda: {'wins': 0, 'losses': 0, 'ties': 0, 'matches': 0}))
    for _, row in matches_df.iterrows():
        team1 = [p for p in [row['team1_player1'], row.get('team1_player2')] if p and p != "Visitor"]
        team2 = [p for p in [row['team2_player1'], row.get('team2_player2')] if p and p != "Visitor"]
        
        for p1 in team1:
            for p2 in team2:
                head_to_head[p1][p2]['matches'] += 1
                head_to_head[p2][p1]['matches'] += 1
                if row['winner'] == "Team 1":
                    head_to_head[p1][p2]['wins'] += 1
                    head_to_head[p2][p1]['losses'] += 1
                elif row['winner'] == "Team 2":
                    head_to_head[p1][p2]['losses'] += 1
                    head_to_head[p2][p1]['wins'] += 1
                else:
                    head_to_head[p1][p2]['ties'] += 1
                    head_to_head[p2][p1]['ties'] += 1
    return head_to_head

def calculate_set_win_percentage(matches_df):
    """Calculates the percentage of sets won by each player."""
    set_wins = defaultdict(int)
    total_sets = defaultdict(int)
    for _, row in matches_df.iterrows():
        team1 = [p for p in [row['team1_player1'], row.get('team1_player2')] if p and p != "Visitor"]
        team2 = [p for p in [row['team2_player1'], row.get('team2_player2')] if p and p != "Visitor"]
        for set_score in [row['set1'], row['set2'], row['set3']]:
            if isinstance(set_score, str) and '-' in set_score:
                try:
                    g1, g2 = map(int, set_score.split('-'))
                    total_sets_played = 1
                    for p in team1:
                        total_sets[p] += total_sets_played
                        if g1 > g2:
                            set_wins[p] += 1
                    for p in team2:
                        total_sets[p] += total_sets_played
                        if g2 > g1:
                            set_wins[p] += 1
                except ValueError:
                    continue
    set_win_pct = {p: (set_wins[p] / total_sets[p] * 100) if total_sets[p] > 0 else 0 for p in set_wins}
    return set_win_pct

def calculate_win_streak(matches_df):
    """Calculates the longest current win streak for each player."""
    win_streaks = defaultdict(int)
    current_streak = defaultdict(int)
    matches_df = matches_df.sort_values(by='date', ascending=False)
    for _, row in matches_df.iterrows():
        team1 = [p for p in [row['team1_player1'], row.get('team1_player2')] if p and p != "Visitor"]
        team2 = [p for p in [row['team2_player1'], row.get('team2_player2')] if p and p != "Visitor"]
        for p in team1 + team2:
            if p not in current_streak:  # Only count streaks that haven't been broken
                if row['winner'] == "Team 1" and p in team1:
                    current_streak[p] += 1
                elif row['winner'] == "Team 2" and p in team2:
                    current_streak[p] += 1
                elif row['winner'] == "Tie":
                    continue
                else:
                    current_streak[p] = 0
                win_streaks[p] = max(win_streaks[p], current_streak[p])
    return win_streaks

def calculate_opponent_adjusted_points(matches_df, rank_df):
    """Calculates points adjusted for opponent strength."""
    adjusted_points = defaultdict(float)
    rank_dict = rank_df.set_index('Player')['Points'].to_dict()
    for _, row in matches_df.iterrows():
        team1 = [p for p in [row['team1_player1'], row.get('team1_player2')] if p and p != "Visitor"]
        team2 = [p for p in [row['team2_player1'], row.get('team2_player2')] if p and p != "Visitor"]
        team1_points = sum(rank_dict.get(p, 0) for p in team1) / len(team1) if team1 else 0
        team2_points = sum(rank_dict.get(p, 0) for p in team2) / len(team2) if team2 else 0
        for p in team1:
            if row['winner'] == "Team 1":
                adjusted_points[p] += 3 * (team2_points / 10)  # Scale by opponent strength
            elif row['winner'] == "Team 2":
                adjusted_points[p] += 1 * (team2_points / 10)
            else:
                adjusted_points[p] += 1.5 * (team2_points / 10)
        for p in team2:
            if row['winner'] == "Team 2":
                adjusted_points[p] += 3 * (team1_points / 10)
            elif row['winner'] == "Team 1":
                adjusted_points[p] += 1 * (team1_points / 10)
            else:
                adjusted_points[p] += 1.5 * (team1_points / 10)
    return adjusted_points

def display_nerd_stuff(rank_df, partner_stats, matches):
    """Displays various interesting statistics and insights."""
    st.markdown("### 🤝 Most Effective Partnership")
    best_partnership = None
    max_win_rate = 0
    for player1 in partner_stats:
        for player2, stats in partner_stats[player1].items():
            if stats['matches'] > 0:
                win_rate = stats['wins'] / stats['matches']
                if win_rate > max_win_rate:
                    max_win_rate = win_rate
                    best_partnership = (player1, player2, stats)
    if best_partnership:
        p1, p2, stats = best_partnership
        st.markdown(f"**{p1} & {p2}**: {stats['wins']} wins, {stats['losses']} losses, {stats['ties']} ties, Win %: {max_win_rate*100:.1f}%")
    else:
        st.info("No partnership data available.")
    
    st.markdown("---")
    st.markdown("### 🥇 Best Player to Partner With")
    best_partner = None
    max_avg_win_rate = 0
    for player in partner_stats:
        total_matches = sum(stats['matches'] for stats in partner_stats[player].values())
        total_wins = sum(stats['wins'] for stats in partner_stats[player].values())
        if total_matches > 0:
            avg_win_rate = total_wins / total_matches
            if avg_win_rate > max_avg_win_rate:
                max_avg_win_rate = avg_win_rate
                best_partner = player
    if best_partner:
        st.markdown(f"**{best_partner}**: Average Win %: {max_avg_win_rate*100:.1f}%")
    else:
        st.info("No partner data available.")

    st.markdown("---")
    st.markdown("### 🤼 Head-to-Head Records")
    head_to_head = calculate_head_to_head(matches)
    h2h_data = []
    for p1 in head_to_head:
        for p2, stats in head_to_head[p1].items():
            if stats['matches'] > 0 and p1 < p2:  # Avoid duplicates
                h2h_data.append({
                    "Players": f"{p1} vs {p2}",
                    "Matches": stats['matches'],
                    "Wins1": stats['wins'],
                    "Wins2": head_to_head[p2][p1]['wins'],
                    "Ties": stats['ties']
                })
    if h2h_data:
        st.markdown('<div class="rankings-table-container"><div class="rankings-table-scroll">', unsafe_allow_html=True)
        for record in sorted(h2h_data, key=lambda x: x['Matches'], reverse=True)[:5]:  # Top 5 rivalries
            st.markdown(f"""
            <div class="ranking-row">
                <div class="player-col">{record['Players']}</div>
                <div class="matches-col">{record['Matches']} matches</div>
                <div class="wins-col">{record['Wins1']} - {record['Wins2']}</div>
                <div class="ties-col">Ties: {record['Ties']}</div>
            </div>
            """, unsafe_allow_html=True)
        st.markdown('</div></div>', unsafe_allow_html=True)
    else:
        st.info("No head-to-head data available.")

    st.markdown("---")
    st.markdown("### 🎾 Set Win Percentage")
    set_win_pct = calculate_set_win_percentage(matches)
    if set_win_pct:
        set_win_data = [
            {"Player": p, "Set Win %": pct} for p, pct in set_win_pct.items()
        ]
        set_win_df = pd.DataFrame(set_win_data).sort_values(by="Set Win %", ascending=False)
        st.markdown('<div class="rankings-table-container"><div class="rankings-table-scroll">', unsafe_allow_html=True)
        for _, row in set_win_df.head(5).iterrows():  # Top 5
            st.markdown(f"""
            <div class="ranking-row">
                <div class="player-col">{row['Player']}</div>
                <div class="win-percent-col">{row['Set Win %']:.1f}%</div>
            </div>
            """, unsafe_allow_html=True)
        st.markdown('</div></div>', unsafe_allow_html=True)
    else:
        st.info("No set win data available.")

    st.markdown("---")
    st.markdown("### 🔥 Longest Win Streak")
    win_streaks = calculate_win_streak(matches)
    if win_streaks:
        streak_data = [
            {"Player": p, "Win Streak": streak} for p, streak in win_streaks.items() if streak > 0
        ]
        streak_df = pd.DataFrame(streak_data).sort_values(by="Win Streak", ascending=False)
        if not streak_df.empty:
            st.markdown('<div class="rankings-table-container"><div class="rankings-table-scroll">', unsafe_allow_html=True)
            for _, row in streak_df.head(5).iterrows():  # Top 5
                st.markdown(f"""
                <div class="ranking-row">
                    <div class="player-col">{row['Player']}</div>
                    <div class="wins-col">{row['Win Streak']} matches</div>
                </div>
                """, unsafe_allow_html=True)
            st.markdown('</div></div>', unsafe_allow_html=True)
        else:
            st.info("No current win streaks.")
    else:
        st.info("No win streak data available.")

    st.markdown("---")
    st.markdown("### 🏅 Opponent-Adjusted Points")
    adjusted_points = calculate_opponent_adjusted_points(matches, rank_df)
    if adjusted_points:
        adj_points_data = [
            {"Player": p, "Adjusted Points": points} for p, points in adjusted_points.items()
        ]
        adj_points_df = pd.DataFrame(adj_points_data).sort_values(by="Adjusted Points", ascending=False)
        st.markdown('<div class="rankings-table-container"><div class="rankings-table-scroll">', unsafe_allow_html=True)
        for _, row in adj_points_df.head(5).iterrows():  # Top 5
            st.markdown(f"""
            <div class="ranking-row">
                <div class="player-col">{row['Player']}</div>
                <div class="points-col">{row['Adjusted Points']:.1f}</div>
            </div>
            """, unsafe_allow_html=True)
        st.markdown('</div></div>', unsafe_allow_html=True)
    else:
        st.info("No opponent-adjusted points data available.")

def display_court_locations():
    """Displays a list of tennis court locations with Google Maps links."""
    st.header("Court Locations")
    st.markdown("""
    ### Krakow Tennis Courts
    - [Korty Dąbski](https://maps.app.goo.gl/c1eNLt3dpf1Y6Vnw6)  
    - [KATenis - korty Olszai](https://maps.app.goo.gl/qAQdJETTpM6sSr1N6) 
    - [Czyżyny Sports Center"](https://maps.app.goo.gl/8pfHMGTqZRCFtWSz6) 
    - [Korty ziemne (Centrum tenisowe PK)](https://maps.app.goo.gl/uciZTXWYkcAXMFTL9) 
    - [Krakowski Klub Tenisowy Olsza](https://maps.app.goo.gl/D91Lsu63aQWnhKm9A)        
    """)

def display_backup_buttons(matches_df, players_df):
    """Provides download buttons for backing up data."""
    st.subheader("Manual Backup")
    col1, col2 = st.columns(2)
    with col1:
        if not matches_df.empty:
            csv_matches = matches_df.to_csv(index=False).encode('utf-8')
            st.download_button("Download Matches Data", csv_matches, f'ar_tennis_matches_backup_{datetime.now().strftime("%Y-%m-%d")}.csv', 'text/csv')
    with col2:
        if not players_df.empty:
            csv_players = players_df.to_csv(index=False).encode('utf-8')
            st.download_button("Download Players Data", csv_players, f'ar_tennis_players_backup_{datetime.now().strftime("%Y-%m-%d")}.csv', 'text/csv')

def display_footer():
    """Displays the footer section of the app."""
    st.markdown("""
    <div style='background-color: #0d5384; padding: 1rem; border-left: 5px solid #fff500; border-radius: 0.5rem; color: white; margin-top: 2rem;'>
    Built with ❤️ using <a href='https://streamlit.io/' style='color: #ccff00;'>Streamlit</a>.
    <a href='https://devs-scripts.streamlit.app/' style='color: #ccff00;'>Other Scripts by dev</a>.
    </div>
    """, unsafe_allow_html=True)
