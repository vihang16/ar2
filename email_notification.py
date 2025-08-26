import streamlit as st
from supabase import create_client
import smtplib, ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- Supabase setup ---
SUPABASE_URL = st.secrets['supabase']["supabase_url"]
SUPABASE_KEY = st.secrets['supabase']["supabase_key"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- Email setup ---
EMAIL_USER = st.secrets['supabase']["EMAIL_USER"]
EMAIL_PASS = st.secrets['supabase']["EMAIL_PASSWORD"]
EMAIL_TO   = st.secrets['supabase']["EMAIL_TO"]

def send_email(subject, body):
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ssl.create_default_context()) as server:
            server.login(EMAIL_USER, EMAIL_PASS)
            server.sendmail(EMAIL_USER, EMAIL_TO, msg.as_string())
            st.success("SMTP connection succsfully")
    except Exception as e:
        st.error(f"SMTP failed: {e}")

    msg = MIMEMultipart()
    msg["From"] = EMAIL_USER
    msg["To"] = EMAIL_TO
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))
    print(f"triggering email:{EMAIL_USER}")
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL_USER, EMAIL_PASS)
        server.sendmail(EMAIL_USER, EMAIL_TO, msg.as_string())

# --- Realtime subscription ---
def handle_change(payload):
    change_type = payload["eventType"]
    table = payload["table"]
    record = payload["new"]
    print(f"even triggered:{change_type}")
    subject = f"DB Change: {change_type} on {table}"
    body = f"Table: {table}\nEvent: {change_type}\nRecord: {record}"
    send_email(subject, body)
