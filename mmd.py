import streamlit as st
import pandas as pd
import uuid
from datetime import datetime
import gspread
from collections import defaultdict
from oauth2client.service_account import ServiceAccountCredentials

# Google Sheets setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_dict = st.secrets["gcp_service_account"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

SHEET_NAME = "RLTG Data"
players_sheet_name = "Mira Players"
matches_sheet_name = "Mira Matches"

spreadsheet = client.open(SHEET_NAME)

# Helper to get or create worksheet
def get_or_create_worksheet(spreadsheet, sheet_name):
    try:
        return spreadsheet.worksheet(sheet_name)
    except:
        return spreadsheet.add_worksheet(title=sheet_name, rows="1000", cols="20")

# Define sheet names
match_sheet_name = "Mira"
rank_sheet_name = "Mira Rankings"
stat_sheet_name = "Mira Stats"
bookings_sheet_name = "Mira Bookings"

match_sheet = get_or_create_worksheet(spreadsheet, match_sheet_name)
rank_sheet = get_or_create_worksheet(spreadsheet, rank_sheet_name)
stat_sheet = get_or_create_worksheet(spreadsheet, stat_sheet_name)
bookings_sheet = get_or_create_worksheet(spreadsheet, bookings_sheet_name)

# Sample player list (replace with your player source)
players = ["Player A", "Player B", "Player C", "Player D"]

# Booking court list
court_list = [
    "Mira 2", "Mira 4", "Mira 5 A", "Mira 5 B",
    "Mira Oasis 1", "Mira Oasis 2", "Mira Oasis 3 A", "Mira Oasis 3 B", "Mira Oasis 3C",
    "AR Palmera 2", "AR Palmera 4", "AR Alvorada 1", "AR Alvorada 2",
    "AR Mirador La Collecion", "AR Hattan", "AR Saheel", "AR Alma", "AR Al Mahra", "AR Mirador",
    "AR Reem 1", "AR Reem 2", "AR Reem 3", "Mudon Main (Rahat)", "Mudon Arabella", "Mudon Arabella 3",
    "AR2 Rosa", "AR2 Palma", "AR2 Fitness First"
]

time_slots = [f"{h}:00 {'AM' if h < 12 else 'PM'}" for h in range(6, 22)]

# Booking functions
def load_bookings():
    records = bookings_sheet.get_all_records()
    if not records:
        # Sheet is empty — initialize with required columns
        return pd.DataFrame(columns=["booking_id", "date", "time", "court", "players"])
    df = pd.DataFrame(records)
    if "booking_id" not in df.columns:
        df["booking_id"] = [f"BOOK-{i}" for i in range(len(df))]
    return df


def save_bookings(df):
    bookings_sheet.clear()
    bookings_sheet.update([df.columns.tolist()] + df.values.tolist())

st.set_page_config(page_title="Tennis App", layout="wide")
st.title("🎾 Mira Tennis Hub")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["Post Match", "Match Records", "Rankings", "Player Stats", "Game Bookings"])

with tab1:
    st.header("🏆 Post Match Results")
    player1 = st.selectbox("Select Player 1", players)
    player2 = st.selectbox("Select Player 2", players)
    match_date = st.date_input("Match Date")
    winner = st.selectbox("Winner", [player1, player2])
    score = st.text_input("Score")
    if st.button("Submit Match"):
        match_sheet.append_row([match_date.strftime("%Y-%m-%d"), player1, player2, winner, score])
        st.success("Match recorded!")

with tab2:
    st.header("📜 Match Records")
    match_data = pd.DataFrame(match_sheet.get_all_records())
    if not match_data.empty:
        st.dataframe(match_data)

with tab3:
    st.header("📈 Rankings")
    rank_data = pd.DataFrame(rank_sheet.get_all_records())
    if not rank_data.empty:
        st.dataframe(rank_data)

with tab4:
    st.header("📊 Player Stats")
    stat_data = pd.DataFrame(stat_sheet.get_all_records())
    if not stat_data.empty:
        st.dataframe(stat_data)

with tab5:
    st.header("🎾 Game Bookings")

    bookings = load_bookings()

    st.subheader("New Booking")
    selected_court = st.selectbox("Select Court", court_list)
    selected_date = st.date_input("Select Date")
    selected_time = st.selectbox("Select Time Slot", time_slots)
    selected_players = st.multiselect("Select Players", players)

    if st.button("Submit Booking"):
        if not selected_players:
            st.warning("Please select at least one player.")
        elif not bookings[(bookings['date'] == selected_date.strftime("%Y-%m-%d")) & (bookings['time'] == selected_time) & (bookings['court'] == selected_court)].empty:
            st.error("This time slot is already booked for the selected court.")
        else:
            new_booking = {
                "booking_id": f"BOOK-{datetime.now().strftime('%y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}",
                "date": selected_date.strftime("%Y-%m-%d"),
                "time": selected_time,
                "court": selected_court,
                "players": ", ".join(selected_players)
            }
            bookings = pd.concat([bookings, pd.DataFrame([new_booking])], ignore_index=True)
            save_bookings(bookings)
            st.success("Booking submitted.")
            st.rerun()

    st.subheader("📅 Manage Bookings")

    bookings["date"] = pd.to_datetime(bookings["date"], errors='coerce')
    bookings = bookings.sort_values(by=["date", "time"])
    bookings["Date"] = bookings["date"].dt.strftime("%d %b %Y")
    bookings["Players"] = bookings["players"]
    bookings_display = bookings[["Date", "time", "court", "Players", "booking_id"]]
    bookings_display.columns = ["Date", "Time", "Court", "Players", "Booking ID"]

    st.dataframe(bookings_display.style.hide(axis="index"), use_container_width=True)

    st.subheader("Edit/Delete Booking")
    booking_ids = bookings["booking_id"].dropna().tolist()
    selected_booking_id = st.selectbox("Select Booking ID", [""] + booking_ids)

    if selected_booking_id:
        row = bookings[bookings["booking_id"] == selected_booking_id].iloc[0]
        edit_court = st.selectbox("Edit Court", court_list, index=court_list.index(row["court"]))
        edit_date = st.date_input("Edit Date", row["date"])
        edit_time = st.selectbox("Edit Time", time_slots, index=time_slots.index(row["time"]))
        current_players = row["players"].split(", ")
        edit_players = st.multiselect("Edit Players", players, default=current_players)

        if st.button("Update Booking"):
            if not edit_players:
                st.warning("Select at least one player.")
            elif not bookings[(bookings['booking_id'] != selected_booking_id) & (bookings['date'] == edit_date.strftime("%Y-%m-%d")) & (bookings['time'] == edit_time) & (bookings['court'] == edit_court)].empty:
                st.error("This time slot is already booked for the selected court.")
            else:
                index = bookings[bookings["booking_id"] == selected_booking_id].index[0]
                bookings.at[index, "court"] = edit_court
                bookings.at[index, "date"] = edit_date.strftime("%Y-%m-%d")
                bookings.at[index, "time"] = edit_time
                bookings.at[index, "players"] = ", ".join(edit_players)
                save_bookings(bookings)
                st.success("Booking updated.")
                st.rerun()

        if st.button("Delete Booking"):
            bookings = bookings[bookings["booking_id"] != selected_booking_id]
            save_bookings(bookings)
            st.success("Booking deleted.")
            st.rerun()
