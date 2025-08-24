import streamlit as st
import pandas as pd
from datetime import datetime
import uuid

# Import functions from other modules
from config import setup_supabase_client
from data_manager import (
    load_players, load_matches, save_matches, delete_match_from_db,
    upload_image_to_supabase, save_players
)
from utils import (
    tennis_scores, generate_match_id, calculate_rankings
)
from ui import (
    apply_custom_css, display_player_insights, display_rankings_table,
    display_match_history, display_rankings_card_view, display_nerd_stuff,
    display_court_locations, display_backup_buttons, display_footer
)

# --- App Setup ---
st.set_page_config(page_title="AR Tennis")
apply_custom_css()
supabase = setup_supabase_client()

# --- Session state initialization ---
if 'players_df' not in st.session_state:
    st.session_state.players_df = pd.DataFrame()
if 'matches_df' not in st.session_state:
    st.session_state.matches_df = pd.DataFrame()
if 'form_key_suffix' not in st.session_state:
    st.session_state.form_key_suffix = 0

# --- Main App Logic ---
load_players(supabase)
load_matches(supabase)

players_df = st.session_state.players_df
matches = st.session_state.matches_df
players = sorted([p for p in players_df["name"].dropna().tolist() if p != "Visitor"]) if "name" in players_df.columns else []

# Generate missing match IDs if necessary
if not matches.empty and ("match_id" not in matches.columns or matches["match_id"].isnull().any()):
    matches['date'] = pd.to_datetime(matches['date'], errors='coerce')
    for i in matches.index:
        if pd.isna(matches.at[i, "match_id"]):
            match_date_for_id = matches.at[i, "date"] if pd.notna(matches.at[i, "date"]) else datetime.now()
            matches.at[i, "match_id"] = generate_match_id(matches, match_date_for_id)
    save_matches(supabase, matches)

st.image("krakow_tennis_league.jpeg", use_container_width=True)

tab_names = ["Rankings", "Matches", "Player Profile", "Court Locations"]
tabs = st.tabs(tab_names)

# --- Rankings Tab ---
with tabs[0]:
    st.header("Rankings")
    ranking_type = st.radio(
        "Select Ranking View",
        ["Combined", "Doubles", "Singles", "Nerd Stuff", "Table View"],
        horizontal=True,
        key="ranking_type_selector"
    )

    if ranking_type == "Table View":
        rank_df_combined, _ = calculate_rankings(matches, players_df)
        display_rankings_table(rank_df_combined, "Combined")

        doubles_matches = matches[matches['match_type'] == 'Doubles']
        rank_df_doubles, _ = calculate_rankings(doubles_matches, players_df)
        display_rankings_table(rank_df_doubles, "Doubles")

        singles_matches = matches[matches['match_type'] == 'Singles']
        rank_df_singles, _ = calculate_rankings(singles_matches, players_df)
        display_rankings_table(rank_df_singles, "Singles")

    elif ranking_type == "Nerd Stuff":
        if matches.empty or players_df.empty:
            st.info("No match data available to generate interesting stats.")
        else:
            rank_df, partner_stats = calculate_rankings(matches, players_df)
            display_nerd_stuff(rank_df, partner_stats, matches)

    else:
        title = ranking_type
        if ranking_type == "Doubles":
            filtered_matches = matches[matches['match_type'] == 'Doubles'].copy()
        elif ranking_type == "Singles":
            filtered_matches = matches[matches['match_type'] == 'Singles'].copy()
        else: # Combined
            filtered_matches = matches.copy()
            title = "Combined"

        rank_df, partner_stats = calculate_rankings(filtered_matches, players_df)
        display_rankings_card_view(rank_df, title)

        st.subheader("Player Insights")
        insights_key_suffix = ranking_type.lower()
        selected_player_rankings = st.selectbox(
            "Select a player for insights",
            [""] + players,
            index=0,
            key=f"insights_player_rankings_{insights_key_suffix}"
        )
        if selected_player_rankings:
            display_player_insights(selected_player_rankings, players_df, filtered_matches, rank_df, partner_stats, key_prefix=f"rankings_{insights_key_suffix}_")
        else:
            st.info("Player insights will be available once a player is selected.")

# --- Matches Tab ---
with tabs[1]:
    st.header("Matches")
    with st.expander("➕ Post New Match Result"):
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
                else: # Singles
                    p1_new = st.selectbox("Player 1", [""] + available_players, key=f"s1p1_new_post_{st.session_state.form_key_suffix}")
                    p3_new = st.selectbox("Player 2", [""] + available_players, key=f"s1p2_new_post_{st.session_state.form_key_suffix}")
                    p2_new, p4_new = "", ""

                set1_new = st.selectbox("Set 1 *", tennis_scores(), index=4, key=f"set1_new_post_{st.session_state.form_key_suffix}")
                set2_new = st.selectbox("Set 2 *" if match_type_new == "Doubles" else "Set 2 (optional)", [""] + tennis_scores(), key=f"set2_new_post_{st.session_state.form_key_suffix}")
                set3_new = st.selectbox("Set 3 (optional)", [""] + tennis_scores(), key=f"set3_new_post_{st.session_state.form_key_suffix}")
                winner_new = st.radio("Winner", ["Team 1", "Team 2", "Tie"], key=f"winner_new_post_{st.session_state.form_key_suffix}")
                match_image_new = st.file_uploader("Upload Match Image (optional)", type=["jpg", "jpeg", "png", "gif", "bmp", "webp"], key=f"match_image_new_post_{st.session_state.form_key_suffix}")
                st.markdown("*Required fields", unsafe_allow_html=True)
                submit_button = st.form_submit_button("Submit Match")

            if submit_button:
                selected_players_list = [p for p in [p1_new, p2_new, p3_new, p4_new] if p]
                if match_type_new == "Doubles" and "" in [p1_new, p2_new, p3_new, p4_new]:
                     st.error("Please select all players for a doubles match.")
                elif match_type_new == "Singles" and "" in [p1_new, p3_new]:
                    st.error("Please select all players for a singles match.")
                elif len(selected_players_list) != len(set(selected_players_list)):
                    st.error("Please select different players for each position.")
                elif not set1_new:
                    st.error("Set 1 score is required.")
                elif match_type_new == "Doubles" and not set2_new:
                    st.error("Set 2 score is required for doubles matches.")
                else:
                    new_match_date = datetime.now()
                    match_id_new = generate_match_id(st.session_state.matches_df, new_match_date)
                    image_url_new = upload_image_to_supabase(supabase, match_image_new, match_id_new, image_type="match") if match_image_new else ""

                    new_match_entry = {
                        "match_id": match_id_new, "date": new_match_date, "match_type": match_type_new,
                        "team1_player1": p1_new, "team1_player2": p2_new, "team2_player1": p3_new,
                        "team2_player2": p4_new, "set1": set1_new, "set2": set2_new, "set3": set3_new,
                        "winner": winner_new, "match_image_url": image_url_new
                    }
                    matches_to_save = pd.concat([st.session_state.matches_df, pd.DataFrame([new_match_entry])], ignore_index=True)
                    save_matches(supabase, matches_to_save)
                    load_matches(supabase)
                    st.success("Match submitted.")
                    st.session_state.form_key_suffix += 1
                    st.rerun()

    st.markdown("---")
    st.subheader("Match History")
    display_match_history(matches, supabase)

# --- Player Profile Tab ---
with tabs[2]:
    st.header("Player Profile")
    st.subheader("Manage & Edit Player Profiles")
    with st.expander("Add, Edit or Remove Player"):
        # Add new player
        st.markdown("##### Add New Player")
        new_player_name = st.text_input("Player Name", key="new_player_input").strip()
        if st.button("Add Player", key="add_player_button"):
            if new_player_name:
                if new_player_name.lower() == "visitor":
                    st.warning("The name 'Visitor' is reserved and cannot be added.")
                elif new_player_name in players:
                    st.warning(f"{new_player_name} already exists.")
                else:
                    new_player_data = {"name": new_player_name, "profile_image_url": "", "birthday": ""}
                    st.session_state.players_df = pd.concat([st.session_state.players_df, pd.DataFrame([new_player_data])], ignore_index=True)
                    save_players(supabase, st.session_state.players_df)
                    load_players(supabase)
                    st.success(f"{new_player_name} added.")
                    st.rerun()
            else:
                st.warning("Please enter a player name to add.")

        # Edit or Remove existing player
        st.markdown("---")
        st.markdown("##### Edit or Remove Existing Player")
        selected_player_manage = st.selectbox("Select Player", [""] + players, key="manage_player_select")
        if selected_player_manage:
            player_data = players_df[players_df["name"] == selected_player_manage].iloc[0]
            current_image = player_data.get("profile_image_url", "")
            current_birthday = player_data.get("birthday", "")

            st.markdown(f"**Current Profile for {selected_player_manage}**")
            if current_image:
                st.image(current_image, width=100)
            else:
                st.write("No profile image set.")

            profile_image_file = st.file_uploader("Upload New Profile Image (optional)", type=["jpg", "jpeg", "png", "gif", "bmp", "webp"], key=f"profile_image_upload_{selected_player_manage}")

            default_day, default_month = 1, 1
            if current_birthday and isinstance(current_birthday, str) and '-' in current_birthday:
                try:
                    day_str, month_str = current_birthday.split("-")
                    default_day, default_month = int(day_str), int(month_str)
                except (ValueError, IndexError):
                    pass

            birthday_day = st.number_input("Birthday Day", min_value=1, max_value=31, value=default_day, key=f"birthday_day_{selected_player_manage}")
            birthday_month = st.number_input("Birthday Month", min_value=1, max_value=12, value=default_month, key=f"birthday_month_{selected_player_manage}")

            col_save, col_delete = st.columns(2)
            with col_save:
                if st.button("Save Profile Changes", key=f"save_profile_changes_{selected_player_manage}"):
                    image_url = current_image
                    if profile_image_file:
                        image_url = upload_image_to_supabase(supabase, profile_image_file, f"profile_{selected_player_manage}_{uuid.uuid4().hex[:6]}", image_type="profile")

                    st.session_state.players_df.loc[st.session_state.players_df["name"] == selected_player_manage, "profile_image_url"] = image_url
                    st.session_state.players_df.loc[st.session_state.players_df["name"] == selected_player_manage, "birthday"] = f"{birthday_day:02d}-{birthday_month:02d}"
                    save_players(supabase, st.session_state.players_df)
                    load_players(supabase)
                    st.success("Profile updated.")
                    st.rerun()
            with col_delete:
                if st.button("🗑️ Remove Player", key=f"remove_player_button_{selected_player_manage}"):
                    if st.checkbox(f"Confirm deletion of {selected_player_manage}", key=f"confirm_delete_{selected_player_manage}"):
                        st.session_state.players_df = st.session_state.players_df[st.session_state.players_df["name"] != selected_player_manage].reset_index(drop=True)
                        save_players(supabase, st.session_state.players_df)
                        load_players(supabase)
                        st.success(f"{selected_player_manage} removed.")
                        st.rerun()

    st.markdown("---")
    st.subheader("Player Insights")
    rank_df_combined, partner_stats_combined = calculate_rankings(st.session_state.matches_df, players_df)
    if players:
        display_player_insights(players, players_df, st.session_state.matches_df, rank_df_combined, partner_stats_combined, key_prefix="profile_")
    else:
        st.info("No players available for insights. Please add players above.")

# --- Court Locations Tab ---
with tabs[3]:
    display_court_locations()

# --- Footer and Backup ---
st.markdown("---")
display_backup_buttons(matches, players_df)
display_footer()
