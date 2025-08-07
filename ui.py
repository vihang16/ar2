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
    .profile-col { text-align: left; margin-bottom: 10px; display: inline-block; vertical-align: middle; }
    .player-col { font-size: 1.3em; font-weight: bold; display: inline-block; flex-grow: 1; vertical-align: middle; }
    .rank-profile-player-group { display: flex; align-items: center; margin-bottom: 10px; }
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
        # Create HTML table
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

def display_match_history(df, supabase):
    """Displays match history with options to edit or delete."""
    match_filter = st.radio("Filter by Type", ["All", "Singles", "Doubles"], horizontal=True, key="match_history_filter")
    filtered_matches = df.copy()
    if match_filter != "All":
        filtered_matches = filtered_matches[filtered_matches["match_type"] == match_filter]
    
    if 'date' in filtered_matches.columns:
        filtered_matches['date'] = pd.to_datetime(filtered_matches['date'], errors='coerce')
        filtered_matches = filtered_matches.sort_values(by='date', ascending=False).reset_index(drop=True)

    if filtered_matches.empty:
        st.info("No matches found.")
        return
        
    for index, row in filtered_matches.iterrows():
        def format_match_players(row):
            t1 = [p for p in [row['team1_player1'], row.get('team1_player2')] if p]
            t2 = [p for p in [row['team2_player1'], row.get('team2_player2')] if p]
            t1_str = " & ".join([f"<span style='font-weight:bold; color:#fff500;'>{p}</span>" for p in t1])
            t2_str = " & ".join([f"<span style='font-weight:bold; color:#fff500;'>{p}</span>" for p in t2])
            return f"{t1_str} vs {t2_str}" if row['winner'] == 'Tie' else (f"{t1_str} def. {t2_str}" if row['winner'] == 'Team 1' else f"{t2_str} def. {t1_str}")

        def format_scores(row):
            scores = [s for s in [row['set1'], row['set2'], row['set3']] if s]
            return ", ".join(scores)

        cols = st.columns([1, 8, 1])
        if row.get("match_image_url"):
            with cols[0]:
                st.image(row["match_image_url"], width=50)
        with cols[1]:
            st.markdown(f"{format_match_players(row)}", unsafe_allow_html=True)
            st.markdown(f"<span style='color: #bbbbbb;'>{format_scores(row)} on {pd.to_datetime(row['date']).strftime('%d %b %y')}</span>", unsafe_allow_html=True)
        with cols[2]:
            share_link = generate_whatsapp_link(row)
            st.markdown(f'<a href="{share_link}" target="_blank"><img src="https://upload.wikimedia.org/wikipedia/commons/6/6b/WhatsApp.svg" alt="Share" style="width:30px;"/></a>', unsafe_allow_html=True)
        st.markdown("<hr style='border-top: 1px solid #333;'>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader("✏️ Manage Existing Match")
    match_options = {f"{row['match_id']} | {pd.to_datetime(row['date']).strftime('%d %b %y')} - {row['team1_player1']} vs {row['team2_player1']}": row['match_id'] for _, row in filtered_matches.iterrows()}
    selected_match_label = st.selectbox("Select a match to edit or delete", [""] + list(match_options.keys()), key="select_match_to_edit")

    if selected_match_label:
        match_id = match_options[selected_match_label]
        row = df[df['match_id'] == match_id].iloc[0]
        idx = df[df['match_id'] == match_id].index[0]
        
        with st.expander("Edit Match Details", expanded=True):
            available_players = sorted(st.session_state.players_df["name"].dropna().tolist() + ["Visitor"])
            all_scores = [""] + tennis_scores()
            
            date_edit = st.date_input("Date", value=pd.to_datetime(row['date']).date(), key=f"date_edit_{match_id}")
            winner_edit = st.radio("Winner", ["Team 1", "Team 2", "Tie"], index=["Team 1", "Team 2", "Tie"].index(row['winner']), key=f"winner_edit_{match_id}", horizontal=True)
            set1_edit = st.selectbox("Set 1", all_scores, index=all_scores.index(row['set1']) if row['set1'] in all_scores else 0, key=f"s1_edit_{match_id}")
            set2_edit = st.selectbox("Set 2", all_scores, index=all_scores.index(row['set2']) if row['set2'] in all_scores else 0, key=f"s2_edit_{match_id}")
            set3_edit = st.selectbox("Set 3", all_scores, index=all_scores.index(row['set3']) if row['set3'] in all_scores else 0, key=f"s3_edit_{match_id}")

            if st.button("Save Changes", key=f"save_edit_{match_id}"):
                st.session_state.matches_df.loc[idx, 'date'] = pd.to_datetime(date_edit)
                st.session_state.matches_df.loc[idx, 'winner'] = winner_edit
                st.session_state.matches_df.loc[idx, 'set1'] = set1_edit
                st.session_state.matches_df.loc[idx, 'set2'] = set2_edit
                st.session_state.matches_df.loc[idx, 'set3'] = set3_edit
                save_matches(supabase, st.session_state.matches_df)
                st.success("Match updated.")
                st.rerun()

            if st.button("🗑️ Delete This Match", key=f"delete_edit_{match_id}"):
                delete_match_from_db(supabase, match_id)
                st.success("Match deleted.")
                st.rerun()

def display_nerd_stuff(rank_df, partner_stats, matches):
    """Displays various interesting statistics and insights."""
    st.markdown("### 🤝 Most Effective Partnership")
    # Placeholder for partnership logic
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

def display_court_locations():
    """Displays a list of tennis court locations with Google Maps links."""
    st.header("Court Locations")
    st.markdown("""
    ### Arabian Ranches Tennis Courts
    - [Alvorado 1 & 2](https://maps.google.com/?q=25.041792,55.259258)
    - [Palmera 2](https://maps.app.goo.gl/CHimjtqQeCfU1d3W6)
    - [Palmera 4](https://maps.app.goo.gl/4nn1VzqMpgVkiZGN6)
    - [Saheel](https://maps.app.goo.gl/a7qSvtHCtfgvJoxJ8)
    - [Hattan](https://maps.app.goo.gl/fjGpeNzncyG1o34c7)
    - [MLC Mirador La Colleccion](https://maps.app.goo.gl/n14VSDAVFZ1P1qEr6)
    - [Al Mahra](https://maps.app.goo.gl/zVivadvUsD6yyL2Y9)
    - [Mirador](https://maps.app.goo.gl/kVPVsJQ3FtMWxyKP8)
    - [Reem 1](https://maps.app.goo.gl/qKswqmb9Lqsni5RD7)
    - [Reem 2](https://maps.app.goo.gl/oFaUFQ9DRDMsVbMu5)
    - [Reem 3](https://maps.app.goo.gl/o8z9pHo8tSqTbEL39)
    - [Alma](https://maps.app.goo.gl/BZNfScABbzb3osJ18)
    ### Mira & Mira Oasis Tennis Courts
    - [Mira 2](https://maps.app.goo.gl/JeVmwiuRboCnzhnb9)
    - [Mira 4](https://maps.app.goo.gl/e1Vqv5MJXB1eusv6A)
    - [Mira 5 A & B](https://maps.app.goo.gl/rWBj5JEUdw4LqJZb6)
    - [Mira Oasis 1](https://maps.app.goo.gl/F9VYsFBwUCzvdJ2t8)
    - [Mira Oasis 2](https://maps.app.goo.gl/ZNJteRu8aYVUy8sd9)
    - [Mira Oasis 3 A & B](https://maps.app.goo.gl/ouXQGUxYSZSfaW1z9)
    - [Mira Oasis 3 C](https://maps.app.goo.gl/kf7A9K7DoYm4PEPu8)
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
