import streamlit as st
from supabase import create_client, Client

def setup_supase_client():
    supabase_url = st.secrets["supabase"]["supabase_url"]
    supabase_key = st.secrets["supabase"]["supabase_key"]
    supabase: Client = create_client(supabase_url, supabase_key)
    return supabase