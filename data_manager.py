import streamlit as st
import pandas as pd
from supabase import Client
from config import PLAYERS_TABLE, MATCHES_TABLE, PROFILE_BUCKET, MATCH_IMAGE_BUCKET
import io

def load_players(supabase: Client):
    """Loads player data from Supabase into session state."""
    try:
        response = supabase.table(PLAYERS_TABLE).select("name, profile_image_url, birthday").execute()
        df = pd.DataFrame(response.data)
        expected_columns = ["name", "profile_image_url", "birthday"]
        for col in expected_columns:
            if col not in df.columns:
                df[col] = ""
        st.session_state.players_df = df
    except Exception as e:
        st.error(f"Error loading players: {str(e)}")

def save_players(supabase: Client, players_df: pd.DataFrame):
    """Saves player data to Supabase."""
    try:
        expected_columns = ["name", "profile_image_url", "birthday"]
        players_df_to_save = players_df[expected_columns].copy()
        # Ensure no NaN values are sent to Supabase, replace with empty strings
        players_df_to_save.fillna("", inplace=True)
        supabase.table(PLAYERS_TABLE).upsert(players_df_to_save.to_dict("records"), on_conflict="name").execute()
    except Exception as e:
        st.error(f"Error saving players: {str(e)}")

def load_matches(supabase: Client):
    """Loads match data from Supabase into session state."""
    try:
        response = supabase.table(MATCHES_TABLE).select("*").execute()
        df = pd.DataFrame(response.data)
        expected_columns = ["match_id", "date", "match_type", "team1_player1", "team1_player2", "team2_player1", "team2_player2", "set1", "set2", "set3", "winner", "match_image_url"]
        for col in expected_columns:
            if col not in df.columns:
                df[col] = ""
        st.session_state.matches_df = df
    except Exception as e:
        st.error(f"Error loading matches: {str(e)}")

def save_matches(supabase: Client, df: pd.DataFrame):
    """Saves match data to Supabase."""
    try:
        df_to_save = df.copy()
        if 'date' in df_to_save.columns:
            # Coerce to datetime, then format, handling potential NaT values
            df_to_save['date'] = pd.to_datetime(df_to_save['date'], errors='coerce')
            df_to_save = df_to_save.dropna(subset=['date'])
            df_to_save['date'] = df_to_save['date'].dt.strftime('%Y-%m-%d %H:%M:%S')
        
        # Check for and handle duplicate match_id values before saving
        duplicates = df_to_save[df_to_save.duplicated(subset=['match_id'], keep=False)]
        if not duplicates.empty:
            st.warning(f"Found duplicate match_id values: {duplicates['match_id'].tolist()}. Keeping the last entry.")
            df_to_save = df_to_save.drop_duplicates(subset=['match_id'], keep='last')
        
        # Replace NaN with None (which becomes NULL in Supabase)
        df_to_save = df_to_save.where(pd.notnull(df_to_save), None)
        supabase.table(MATCHES_TABLE).upsert(df_to_save.to_dict("records"), on_conflict="match_id").execute()
    except Exception as e:
        st.error(f"Error saving matches: {str(e)}")

def delete_match_from_db(supabase: Client, match_id: str):
    """Deletes a match from the database and session state."""
    try:
        supabase.table(MATCHES_TABLE).delete().eq("match_id", match_id).execute()
        # Also remove from session state to update UI immediately
        st.session_state.matches_df = st.session_state.matches_df[st.session_state.matches_df["match_id"] != match_id].reset_index(drop=True)
    except Exception as e:
        st.error(f"Error deleting match from database: {str(e)}")

def upload_image_to_supabase(supabase: Client, file, file_name: str, image_type="match") -> str:
    """Uploads an image to the appropriate Supabase storage bucket."""
    if not file:
        return ""
    try:
        bucket = PROFILE_BUCKET if image_type == "profile" else MATCH_IMAGE_BUCKET
        file_path = f"2ep_1/{file_name}" if image_type == "match" else file_name
        
        # Read file into bytes
        file_bytes = file.getvalue()

        # Use upsert to handle existing files gracefully
        supabase.storage.from_(bucket).upload(file_path, file_bytes, {"content-type": file.type, "x-upsert": "true"})
        
        # Get the public URL
        public_url = supabase.storage.from_(bucket).get_public_url(file_path)
        
        return public_url
    except Exception as e:
        st.error(f"Error uploading image to bucket '{bucket}/{file_path}': {str(e)}")
        return ""
