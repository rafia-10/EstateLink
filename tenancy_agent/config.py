"""Configuration for Supabase connection"""
import os

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://gmqbqiaiusnjndyvbecn.supabase.co/rest/v1")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdtcWJxaWFpdXNuam5keXZiZWNuIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjI1NzQ3NTIsImV4cCI6MjA3ODE1MDc1Mn0.P_-4K4WDmrNBFYN_RsLfnpLyqN5yC24FiEbg1qXuvo0")

SUPABASE_HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}
