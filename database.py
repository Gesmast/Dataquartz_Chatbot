import streamlit as st
from supabase import create_client

# --- 1. CONFIGURATION ---
# These are pulled from your .streamlit/secrets.toml
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

# --- 2. CONNECTION ---
@st.cache_resource
def get_db_client():
    """Initializes the Supabase client once and caches it."""
    return create_client(SUPABASE_URL, SUPABASE_KEY)

db = get_db_client()

# --- 3. HELPER FUNCTIONS ---

def create_new_session(title="Web Discussion"):
    """Creates a new session record and returns the UUID."""
    try:
        response = db.table("sessions").insert({"title": title}).execute()
        return response.data[0]['id']
    except Exception as e:
        st.error(f"Database Error (Session): {str(e)}")
        return None

def save_message(session_id, role, content):
    """Inserts a chat bubble into the messages table."""
    try:
        db.table("messages").insert({
            "session_id": session_id,
            "role": role,
            "content": content
        }).execute()
    except Exception as e:
        st.error(f"Database Error (Message): {str(e)}")

def get_chat_history(session_id):
    """Fetches all past messages for a session to maintain context."""
    try:
        response = db.table("messages").select("*").eq("session_id", session_id).order("created_at").execute()
        return response.data
    except Exception as e:
        st.error(f"Database Error (History): {str(e)}")
        return []
