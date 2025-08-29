import pandas as pd
from setup_supabase import setup_supase_client
import streamlit as st

supabase =  setup_supase_client()

def load_locations():
    response = supabase.table("location").select("*").execute()
    return pd.DataFrame(response.data)

def add_court():
    st.markdown("### Add New Location")
    new_location = st.text_input("Location Name", key="new_location_name_input").strip()
    new_location_url = st.text_input("Goole Map URL", key="new_google_map_url_input").strip()
    if st.button("Add location", key="add_location_button"):
        if new_location and new_location_url:
            new_location_data = {"name": new_location, "google_map_url": new_location_url}
            st.session_state.players_df = pd.concat([st.session_state.players_df, pd.DataFrame([new_location_data])], ignore_index=True)
            save_location(new_location_data)
        else:
            st.warning("location name or google map url can not be empty")

def save_location(location_data):
    supabase.table("location")\
    .insert(location_data)\
    .execute()
    st.success("New location added successfully")
    load_locations()

