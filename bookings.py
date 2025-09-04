
import pandas as pd
from datetime import datetime, timedelta, timezone
from setup_supabase import setup_supase_client

supabase =  setup_supase_client()

def load_upcoming_bookings():
    today = datetime.now(timezone.utc).date()
    three_days_later = today + timedelta(days=3)
    today_str = today.isoformat()
    three_days_str = three_days_later.isoformat()
    response = supabase.table("bookings").select("*") \
    .gte("date", today_str) \
    .lte("date", three_days_str) \
    .execute()
    return pd.DataFrame(response.data)

def load_all_bookings():
    today = datetime.now(timezone.utc).date()
    three_days_later = today + timedelta(days=3)
    today_str = today.isoformat()
    three_days_str = three_days_later.isoformat()
    response = supabase.table("bookings").select("*") \
    .gte("date", today_str) \
    .execute()
    return pd.DataFrame(response.data)