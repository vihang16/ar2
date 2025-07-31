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
        expected_columns = ["name", "profile_image_url", "birthday"]
        players_df = players_df[expected_columns].copy()
        supabase.table(players_table_name).delete().neq("name", "").execute()
        supabase.table(players_table_name).insert(players_df.to_dict("records")).execute()
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
        supabase.table(matches_table_name).delete().neq("match_id", "").execute()
        supabase.table(matches_table_name).insert(df.to_dict("records")).execute()
    except Exception as e:
        st.error(f"Error saving matches: {str(e)}")

def upload_image_to_supabase(file, file_name, image_type="match"):
    try:
        bucket = "profile" if image_type == "profile" else "ar"
        # Debug: Log bucket and image type
        st.write(f"Debug: Attempting to upload {image_type} image to bucket '{bucket}'")
        
        # Check bucket existence only for 'ar' bucket (since 'profile' is confirmed to exist)
        if bucket == "ar":
            try:
                buckets = supabase.storage.list_buckets()
                bucket_names = [b["name"] for b in buckets]
                st.write(f"Debug: Available buckets: {bucket_names}")
                if bucket not in bucket_names:
                    st.error(f"Storage bucket '{bucket}' does not exist. Please create it in Supabase Storage.")
                    return ""
            except Exception as e:
                st.warning(f"Failed to list buckets: {str(e)}. Proceeding with upload to '{bucket}' as it worked for match images.")
        
        # Use folder for match images, root for profile images
        file_path = f"2ep_1/{file_name}" if image_type == "match" else file_name
        # Debug: Log file extension and path
        file_ext = file.name.split('.')[-1].lower()
        st.write(f"Debug: Uploading file with extension: {file_ext} to {bucket}/{file_path}")
        
        # Upload file
        response = supabase.storage.from_(bucket).upload(
            file_path, 
            file.read(), 
            {"content-type": file.type}
        )
        if response is None or isinstance(response, dict) and "error" in response:
            error_message = response.get("error", "Unknown error") if isinstance(response, dict) else "Upload failed"
            st.error(f"Failed to upload image to bucket '{bucket}/{file_path}': {error_message}")
            return ""
        
        # Get public URL
        public_url = supabase.storage.from_(bucket).get_public_url(file_path)
        # Validate URL structure
        expected_prefix = f"https://vnolrqfkpptpljizzdvw.supabase.co/storage/v1/object/public/{bucket}/"
        if not public_url.startswith(expected_prefix):
            st.warning(f"Uploaded image URL does not match expected prefix: {expected_prefix}. Got: {public_url}")
        st.write(f"Debug: Uploaded image URL: {public_url}")
        return public_url
    except Exception as e:
        st.error(f"Error uploading image to bucket '{bucket}/{file_path}': {str(e)}")
        return ""

def tennis_scores():
    return ["6-0", "6-1", "6-2", "6-3", "6-4", "7-5", "7-6", "0-6", "1-6", "2-6", "3-6", "4-6", "5-7", "6-7"]

# Custom CSS
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Offside&display=swap');
    html, body, [class*="st-"], h1, h2, h3, h4, h5, h6 {
        font-family: 'Offside', sans-serif !important;
    }
    .thumbnail {
        width: 50px;
        height: 50px;
        object-fit: cover;
        cursor: pointer;
        border-radius: 5px;
    }
    .profile-thumbnail {
        width: 50px;
        height: 50px;
        object-fit: cover;
        border-radius: 50%;
        margin-right: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# Display dubai.png from local GitHub repository
st.image("https://raw.githubusercontent.com/mahadevbk/ar2/main/dubai.png", use_container_width=True)

# Initialize players_df in session state
if 'players_df' not in st.session_state:
    st.session_state.players_df = load_players()
players_df = st.session_state.players_df
players = players_df["name"].dropna().tolist() if "name" in players_df.columns else []
matches = load_matches()

if not matches.empty and ("match_id" not in matches.columns or matches["match_id"].isnull().any()):
    for i in matches.index:
        if pd.isna(matches.at[i, "match_id"]):
            matches.at[i, "match_id"] = f"AR2-{datetime.now().strftime('%y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}"
    save_matches(matches)

# Reordered tabs: Rankings, Match Records, Post Match, Player Profile, Court Locations
tab3, tab2, tab1, tab5, tab4 = st.tabs(["Rankings", "Match Records", "Post Match", "Player Profile", "Court Locations"])

# ----- RANKINGS -----
with tab3:
    st.header("Player Rankings")
    
    scores = defaultdict(float)
    wins = defaultdict(int)
    losses = defaultdict(int)
    matches_played = defaultdict(int)
    games_won = defaultdict(int)
    partner_wins = defaultdict(lambda: defaultdict(int))

    for _, row in matches.iterrows():
        if row['match_type'] == 'Doubles':
            t1 = [row['team1_player1'], row['team1_player2']]
            t2 = [row['team2_player1'], row['team2_player2']]
        else:
            t1 = [row['team1_player1']]
            t2 = [row['team2_player1']]

        if row["winner"] == "Team 1":
            for p in t1:
                scores[p] += 3
                wins[p] += 1
                matches_played[p] += 1
            for p in t2:
                scores[p] += 1
                losses[p] += 1
                matches_played[p] += 1
        elif row["winner"] == "Team 2":
            for p in t2:
                scores[p] += 3
                wins[p] += 1
                matches_played[p] += 1
            for p in t1:
                scores[p] += 1
                losses[p] += 1
                matches_played[p] += 1
        else:
            for p in t1 + t2:
                scores[p] += 1.5
                matches_played[p] += 1

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
                partner_wins[row['team1_player1']][row['team1_player2']] += 1
                partner_wins[row['team1_player2']][row['team1_player1']] += 1
            elif row["winner"] == "Team 2":
                partner_wins[row['team2_player1']][row['team2_player2']] += 1
                partner_wins[row['team2_player2']][row['team2_player1']] += 1

    rank_data = []
    for player in scores:
        win_percentage = (wins[player] / matches_played[player] * 100) if matches_played[player] > 0 else 0
        profile_image = players_df[players_df["name"] == player]["profile_image_url"].iloc[0] if player in players_df["name"].values else ""
        rank_data.append({
            "Player": player,
            "Profile Image": profile_image,
            "Points": scores[player],
            "Win Percentage": round(win_percentage, 2),
            "Matches Played": matches_played[player],
            "Wins": wins[player],
            "Losses": losses[player],
            "Games Won": games_won[player]
        })

    rank_df = pd.DataFrame(rank_data)
    rank_df = rank_df.sort_values(
        by=["Points", "Win Percentage", "Games Won", "Player"],
        ascending=[False, False, False, True]
    ).reset_index(drop=True)
    
    rank_df.insert(0, "Rank", [f"🏆 {i}" for i in range(1, len(rank_df) + 1)])
    
    st.dataframe(
        rank_df[["Rank", "Profile Image", "Player", "Points", "Win Percentage", "Matches Played", "Wins", "Losses", "Games Won"]],
        use_container_width=True,
        hide_index=True,
        column_config={
            "Rank": st.column_config.TextColumn("Rank", help="Player ranking with trophy icon"),
            "Profile Image": st.column_config.ImageColumn("Profile", width="small"),
            "Player": st.column_config.TextColumn("Player", help="Player name"),
            "Points": st.column_config.NumberColumn("Points", format="%.1f"),
            "Win Percentage": st.column_config.NumberColumn("Win Percentage", format="%.2f%%"),
            "Matches Played": st.column_config.NumberColumn("Matches Played", format="%d"),
            "Wins": st.column_config.NumberColumn("Wins", format="%d"),
            "Losses": st.column_config.NumberColumn("Losses", format="%d"),
            "Games Won": st.column_config.NumberColumn("Games Won", format="%d")
        },
        column_order=["Rank", "Profile Image", "Player", "Points", "Win Percentage", "Matches Played", "Wins", "Losses", "Games Won"]
    )

    # Player Insights
    st.subheader("Player Insights")
    selected = st.selectbox("Select a player", players)
    if selected:
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

        if selected in rank_df["Player"].values:
            player_data = rank_df[rank_df["Player"] == selected].iloc[0]
            trend = get_player_trend(selected, matches)
            player_info = players_df[players_df["name"] == selected].iloc[0]
            birthday = player_info.get("birthday", "Not set")
            profile_image = player_info.get("profile_image_url", "")
            
            cols = st.columns([1, 5])
            with cols[0]:
                if profile_image:
                    try:
                        st.image(profile_image, width=50, caption="")
                    except Exception as e:
                        st.error(f"Error displaying image for {selected}: {str(e)}")
                else:
                    st.write("No image")
            with cols[1]:
                st.markdown(f"""
                    **Rank**: {player_data["Rank"]}  
                    **Points**: {player_data["Points"]}  
                    **Win Percentage**: {player_data["Win Percentage"]}%  
                    **Matches Played**: {int(player_data["Matches Played"])}  
                    **Wins**: {int(player_data["Wins"])}  
                    **Losses**: {int(player_data["Losses"])}  
                    **Games Won**: {int(player_data["Games Won"])}  
                    **Birthday**: {birthday}  
                    **Partners Played With**: {dict(partner_wins[selected])}  
                    **Recent Trend**: {trend}  
                """)
                if partner_wins[selected]:
                    best_partner, best_wins = max(partner_wins[selected].items(), key=lambda x: x[1])
                    st.markdown(f"**Most Effective Partner**: {best_partner} ({best_wins} {'win' if best_wins == 1 else 'wins'})")
        else:
            trend = get_player_trend(selected, matches)
            player_info = players_df[players_df["name"] == selected].iloc[0]
            birthday = player_info.get("birthday", "Not set")
            profile_image = player_info.get("profile_image_url", "")
            cols = st.columns([1, 5])
            with cols[0]:
                if profile_image:
                    try:
                        st.image(profile_image, width=50, caption="")
                    except Exception as e:
                        st.error(f"Error displaying image for {selected}: {str(e)}")
                else:
                    st.write("No image")
            with cols[1]:
                st.markdown(f"No match data available for {selected}.")  
                st.markdown(f"**Birthday**: {birthday}")
                st.markdown(f"**Partners Played With**: {dict(partner_wins[selected])}")
                st.markdown(f"**Recent Trend**: {trend}")

# ----- MATCH RECORDS -----
with tab2:
    st.header("Match History")
    match_filter = st.radio("Filter by Type", ["All", "Singles", "Doubles"], horizontal=True)
    filtered_matches = matches.copy()
    if match_filter != "All":
        filtered_matches = filtered_matches[filtered_matches["match_type"] == match_filter]

    def format_match_label(row):
        score = f"{row['set1']}, {row['set2']}" + (f", {row['set3']}" if row['set3'] else "")
        if row["match_type"] == "Singles":
            desc = f"{row['date']} | {row['team1_player1']} def. {row['team2_player1']}" if row["winner"] == "Team 1" else f"{row['date']} | {row['team2_player1']} def. {row['team1_player1']}"
        else:
            desc = f"{row['date']} | {row['team1_player1']} & {row['team1_player2']} def. {row['team2_player1']} & {row['team2_player2']}" if row["winner"] == "Team 1" else f"{row['date']} | {row['team2_player1']} & {row['team2_player2']} def. {row['team1_player1']} & {row['team1_player2']}"
        return f"{desc} | {score} | {row['match_id']}"

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
                    st.markdown(f"- {match_label}")
            else:
                with cols[1]:
                    st.markdown(f"- {match_label}")
        
        st.markdown("<br><br><br><br><br><br><br><br><br><br>", unsafe_allow_html=True)
        st.markdown("### ✏️ Manage Match")
        match_options = filtered_matches.apply(format_match_label, axis=1).tolist()
        selected = st.selectbox("Select a match to edit or delete", match_options)
        selected_id = selected.split(" | ")[-1]
        row = matches[matches["match_id"] == selected_id].iloc[0]
        idx = matches[matches["match_id"] == selected_id].index[0]

        with st.expander("Edit Match"):
            match_type = st.radio("Match Type", ["Doubles", "Singles"], index=0 if row["match_type"] == "Doubles" else 1)
            p1 = st.text_input("Team 1 - Player 1", value=row["team1_player1"])
            p2 = st.text_input("Team 1 - Player 2", value=row["team1_player2"])
            p3 = st.text_input("Team 2 - Player 1", value=row["team2_player1"])
            p4 = st.text_input("Team 2 - Player 2", value=row["team2_player2"])
            set1 = st.text_input("Set 1", value=row["set1"])
            set2 = st.text_input("Set 2", value=row["set2"])
            set3 = st.text_input("Set 3", value=row["set3"])
            winner = st.selectbox("Winner", ["Team 1", "Team 2", "Tie"], index=["Team 1", "Team 2", "Tie"].index(row["winner"]))
            match_image = st.file_uploader("Update Match Image (optional)", type=["jpg", "jpeg", "png", "gif", "bmp", "webp"], key=f"edit_image_{selected_id}")

            if st.button("Save Changes"):
                image_url = row["match_image_url"]
                if match_image:
                    image_url = upload_image_to_supabase(match_image, selected_id, image_type="match")
                
                matches.loc[idx] = {
                    "match_id": selected_id,
                    "date": row["date"],
                    "match_type": match_type,
                    "team1_player1": p1,
                    "team1_player2": p2,
                    "team2_player1": p3,
                    "team2_player2": p4,
                    "set1": set1,
                    "set2": set2,
                    "set3": set3,
                    "winner": winner,
                    "match_image_url": image_url
                }
                save_matches(matches)
                st.success("Match updated.")
                st.rerun()

        if st.button("🗑️ Delete This Match"):
            matches = matches[matches["match_id"] != selected_id].reset_index(drop=True)
            save_matches(matches)
            st.success("Match deleted.")
            st.rerun()

# ----- POST MATCH -----
with tab1:
    st.header("Enter Match Result")
    match_type = st.radio("Match Type", ["Doubles", "Singles"], horizontal=True)
    available_players = players.copy() if players else []

    if not available_players:
        st.warning("No players available. Please add players in the sidebar.")
    else:
        if match_type == "Doubles":
            p1 = st.selectbox("Team 1 - Player 1", [""] + available_players, key="t1p1")
            available_players_t1p2 = [p for p in available_players if p != p1] if p1 else available_players
            p2 = st.selectbox("Team 1 - Player 2", [""] + available_players_t1p2, key="t1p2")
            available_players_t2p1 = [p for p in available_players_t1p2 if p != p2] if p2 else available_players_t1p2
            p3 = st.selectbox("Team 2 - Player 1", [""] + available_players_t2p1, key="t2p1")
            available_players_t2p2 = [p for p in available_players_t1p2 if p != p3] if p3 else available_players_t1p2
            p4 = st.selectbox("Team 2 - Player 2", [""] + available_players_t2p2, key="t2p2")
        else:
            p1 = st.selectbox("Player 1", [""] + available_players, key="s1p1")
            available_players_p2 = [p for p in available_players if p != p1] if p1 else available_players
            p3 = st.selectbox("Player 2", [""] + available_players_p2, key="s1p2")
            p2 = ""
            p4 = ""

        set1 = st.selectbox("Set 1", tennis_scores(), index=4)
        set2 = st.selectbox("Set 2", tennis_scores(), index=4)
        set3 = st.selectbox("Set 3 (optional)", [""] + tennis_scores())
        winner = st.radio("Winner", ["Team 1", "Team 2", "Tie"])
        match_image = st.file_uploader("Upload Match Image (optional)", type=["jpg", "jpeg", "png", "gif", "bmp", "webp"], key="match_image")

        if st.button("Submit Match"):
            if match_type == "Doubles" and not all([p1, p2, p3, p4]):
                st.error("Please select all four players for a doubles match.")
            elif match_type == "Singles" and not all([p1, p3]):
                st.error("Please select both players for a singles match.")
            else:
                match_id = f"AR2-{datetime.now().strftime('%y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}"
                image_url = ""
                if match_image:
                    image_url = upload_image_to_supabase(match_image, match_id, image_type="match")
                
                new_match = {
                    "match_id": match_id,
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "match_type": match_type,
                    "team1_player1": p1,
                    "team1_player2": p2,
                    "team2_player1": p3,
                    "team2_player2": p4,
                    "set1": set1,
                    "set2": set2,
                    "set3": set3,
                    "winner": winner,
                    "match_image_url": image_url
                }
                matches = pd.concat([matches, pd.DataFrame([new_match])], ignore_index=True)
                save_matches(matches)
                st.success("Match submitted.")
                st.rerun()

# ----- PLAYER PROFILE -----
with tab5:
    st.header("Player Profile")
    selected_player = st.selectbox("Select Player", [""] + players, key="profile_player")
    
    if selected_player:
        player_data = players_df[players_df["name"] == selected_player].iloc[0]
        current_image = player_data.get("profile_image_url", "")
        current_birthday = player_data.get("birthday", "")
        
        st.subheader(f"Profile for {selected_player}")
        if current_image:
            try:
                st.image(current_image, width=100, caption="Current Profile Image")
            except Exception as e:
                st.error(f"Error displaying profile image: {str(e)}")
        else:
            st.write("No profile image set.")
        
        with st.expander("Edit Profile"):
            profile_image = st.file_uploader("Upload New Profile Image (optional)", type=["jpg", "jpeg", "png", "gif", "bmp", "webp"], key=f"profile_image_{selected_player}")
            birthday_day = st.number_input("Birthday Day", min_value=1, max_value=31, value=int(current_birthday.split("-")[0]) if current_birthday else 1, key=f"birthday_day_{selected_player}")
            birthday_month = st.number_input("Birthday Month", min_value=1, max_value=12, value=int(current_birthday.split("-")[1]) if current_birthday else 1, key=f"birthday_month_{selected_player}")
            
            if st.button("Save Profile Changes", key=f"save_profile_{selected_player}"):
                image_url = current_image
                if profile_image:
                    image_url = upload_image_to_supabase(profile_image, f"profile_{selected_player}_{uuid.uuid4().hex[:6]}", image_type="profile")
                
                players_df.loc[players_df["name"] == selected_player, "profile_image_url"] = image_url
                players_df.loc[players_df["name"] == selected_player, "birthday"] = f"{birthday_day:02d}-{birthday_month:02d}"
                save_players(players_df)
                st.session_state.players_df = load_players()  # Refresh players_df
                st.success("Profile updated.")
                st.rerun()

# ----- COURT LOCATIONS -----
with tab4:
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

# ----- SIDEBAR -----
with st.sidebar:
    st.sidebar.title("Manage Players")
    new_player = st.text_input("Add Player").strip()
    if st.button("Add Player"):
        if new_player:
            if new_player not in players:
                new_player_data = {"name": new_player, "profile_image_url": "", "birthday": ""}
                players_df = pd.concat([players_df, pd.DataFrame([new_player_data])], ignore_index=True)
                players.append(new_player)
                save_players(players_df)
                st.session_state.players_df = load_players()  # Refresh players_df
                st.success(f"{new_player} added.")
                st.rerun()
            else:
                st.warning(f"{new_player} already exists.")

    remove_player = st.selectbox("Remove Player", [""] + players)
    if st.button("Remove Selected Player"):
        if remove_player:
            players_df = players_df[players_df["name"] != remove_player].reset_index(drop=True)
            players = [p for p in players if p != remove_player]
            save_players(players_df)
            st.session_state.players_df = load_players()  # Refresh players_df
            st.success(f"{remove_player} removed.")
            st.rerun()

st.markdown("""
<div style='background-color: #161e80; padding: 1rem; border-left: 5px solid #fff500; border-radius: 0.5rem; color: white;'>
Built with ❤️ using <a href='https://streamlit.io/' style='color: #ccff00;'>Streamlit</a> — free and open source.
<a href='https://devs-scripts.streamlit.app/' style='color: #ccff00;'>Other Scripts by dev</a> on Streamlit.
</div>
""", unsafe_allow_html=True)
