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
        response = supabase.table(players_table_name).select("name").execute()
        df = pd.DataFrame(response.data)
        return df["name"].dropna().tolist() if "name" in df.columns else []
    except Exception as e:
        st.error(f"Error loading players: {str(e)}")
        return []

def save_players(players):
    try:
        supabase.table(players_table_name).delete().neq("name", "").execute()
        data = [{"name": player} for player in players]
        supabase.table(players_table_name).insert(data).execute()
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

def upload_image_to_supabase(file, match_id):
    try:
        file_path = f"match_images/{match_id}_{file.name}"
        response = supabase.storage.from_("ar").upload(
            file_path, 
            file.read(), 
            {"content-type": file.type}
        )
        if response.status_code >= 400:
            st.error(f"Failed to upload image: {response.json()}")
            return ""
        public_url = supabase.storage.from_("ar").get_public_url(file_path)
        return public_url
    except Exception as e:
        st.error(f"Error uploading image: {str(e)}")
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
    </style>
""", unsafe_allow_html=True)

# Display dubai.png from local GitHub repository
st.image("dubai.png", width=800, caption="", use_column_width=False, cls="header-image")


st.title("AR Tennis Group 🎾")

players = load_players()
matches = load_matches()

if not matches.empty and ("match_id" not in matches.columns or matches["match_id"].isnull().any()):
    for i in matches.index:
        if pd.isna(matches.at[i, "match_id"]):
            matches.at[i, "match_id"] = f"AR2-{datetime.now().strftime('%y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}"
    save_matches(matches)

tab1, tab2, tab3 = st.tabs(["Post Match", "Match Records", "Rankings"])

# ----- POST MATCH -----
with tab1:
    st.header("Enter Match Result")
    match_type = st.radio("Match Type", ["Doubles", "Singles"], horizontal=True)
    available_players = players.copy()

    if match_type == "Doubles":
        p1 = st.selectbox("Team 1 - Player 1", available_players, key="t1p1")
        available_players.remove(p1)
        p2 = st.selectbox("Team 1 - Player 2", available_players, key="t1p2")
        available_players.remove(p2)
        p3 = st.selectbox("Team 2 - Player 1", available_players, key="t2p1")
        available_players.remove(p3)
        p4 = st.selectbox("Team 2 - Player 2", available_players, key="t2p2")
    else:
        p1 = st.selectbox("Player 1", available_players, key="s1p1")
        available_players.remove(p1)
        p3 = st.selectbox("Player 2", available_players, key="s1p2")
        p2 = ""
        p4 = ""

    set1 = st.selectbox("Set 1", tennis_scores(), index=4)
    set2 = st.selectbox("Set 2", tennis_scores(), index=4)
    set3 = st.selectbox("Set 3 (optional)", [""] + tennis_scores())
    winner = st.radio("Winner", ["Team 1", "Team 2", "Tie"])
    match_image = st.file_uploader("Upload Match Image (optional)", type=["jpg", "jpeg", "png"])

    if st.button("Submit Match"):
        match_id = f"AR2-{datetime.now().strftime('%y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}"
        image_url = ""
        if match_image:
            image_url = upload_image_to_supabase(match_image, match_id)
        
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
            cols = st.columns([1, 10])  # Two columns: one for thumbnail, one for label
            if row["match_image_url"]:
                with cols[0]:
                    st.image(row["match_image_url"], width=50, caption="")
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
            match_image = st.file_uploader("Update Match Image (optional)", type=["jpg", "jpeg", "png"], key=f"edit_image_{selected_id}")

            if st.button("Save Changes"):
                image_url = row["match_image_url"]
                if match_image:
                    image_url = upload_image_to_supabase(match_image, selected_id)
                
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

# ----- RANKINGS -----
with tab3:
    st.header("Player Rankings")
    scores = defaultdict(float)
    partners = defaultdict(list)
    for _, row in matches.iterrows():
        if row['match_type'] == 'Doubles':
            t1 = [row['team1_player1'], row['team1_player2']]
            t2 = [row['team2_player1'], row['team2_player2']]
        else:
            t1 = [row['team1_player1']]
            t2 = [row['team2_player1']]

        if row["winner"] == "Team 1":
            for p in t1: scores[p] += 3
            for p in t2: scores[p] += 1
        elif row["winner"] == "Team 2":
            for p in t2: scores[p] += 3
            for p in t1: scores[p] += 1
        else:
            for p in t1 + t2: scores[p] += 1.5

        if row['match_type'] == 'Doubles':
            partners[row['team1_player1']].append(row['team1_player2'])
            partners[row['team1_player2']].append(row['team1_player1'])
            partners[row['team2_player1']].append(row['team2_player2'])
            partners[row['team2_player2']].append(row['team2_player1'])

    rank_df = pd.DataFrame(scores.items(), columns=["Player", "Points"]).sort_values(by="Points", ascending=False).reset_index(drop=True)
    st.dataframe(rank_df, use_container_width=True)

    st.subheader("Player Insights")
    selected = st.selectbox("Select a player", players)
    if selected:
        st.markdown(f"**Partners Played With**: {dict(Counter(partners[selected]))}")
        if partners[selected]:
            best = Counter(partners[selected]).most_common(1)[0][0]
            st.markdown(f"**Most Frequent Partner**: {best}")

# ----- SIDEBAR -----
with st.sidebar:
    st.sidebar.title("Manage Players")
    new_player = st.text_input("Add Player").strip()
    if st.button("Add Player"):
        if new_player:
            if new_player not in players:
                players.append(new_player)
                save_players(players)
                st.success(f"{new_player} added.")
                st.rerun()
            else:
                st.warning(f"{new_player} already exists.")

    remove_player = st.selectbox("Remove Player", [""] + players)
    if st.button("Remove Selected Player"):
        if remove_player:
            players = [p for p in players if p != remove_player]
            save_players(players)
            st.success(f"{remove_player} removed.")
            st.rerun()

st.markdown("""
<div style='background-color: #292481; padding: 1rem; border-left: 5px solid #fff500; border-radius: 0.5rem; color: white;'>
Built with ❤️ using <a href='https://streamlit.io/' style='color: #fff500;'>Streamlit</a> — free and open source.
<a href='https://devs-scripts.streamlit.app/' style='color: #fff500;'>Other Scripts by dev</a> on Streamlit.
</div>
""", unsafe_allow_html=True)
