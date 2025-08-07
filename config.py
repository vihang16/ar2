import streamlit as st
from supabase import create_client, Client

# Table names
PLAYERS_TABLE = "players"
MATCHES_TABLE = "matches"
PROFILE_BUCKET = "profile"
MATCH_IMAGE_BUCKET = "ar"

def setup_supabase_client() -> Client:
    """
    Initializes and returns a Supabase client using secrets.
    """
    try:
        supabase_url = st.secrets["supabase"]["supabase_url"]
        supabase_key = st.secrets["supabase"]["supabase_key"]
        return create_client(supabase_url, supabase_key)
    except Exception as e:
        st.error(f"Error connecting to Supabase: {e}")
        st.stop()


