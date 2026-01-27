import sqlite3
import hashlib
from pathlib import Path
from datetime import datetime

# 1. SETUP PATH: Save the database in the root folder of your project
DB_PATH = Path(__file__).resolve().parent.parent / "dataquartz.db"

def init_db():
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    # --- USERS TABLE ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            role TEXT
        )
    """)

    # --- CHAT SESSIONS TABLE ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            title TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)

    # --- CHAT MESSAGES TABLE ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER,
            role TEXT,
            content TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(session_id) REFERENCES chat_sessions(id)
        )
    """)
    
    # --- SETTINGS TABLE ---
    cursor.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('personality', 'Professional and concise')")

    # --- BOOTSTRAP PERMANENT ADMIN ---
    # Check if the specific admin 'gesmast' already exists
    cursor.execute("SELECT * FROM users WHERE username = 'gesmast'")
    if not cursor.fetchone():
        admin_user = "gesmast"
        admin_pass = "Sans@2007"
        admin_role = "admin"
        cursor.execute('''
            INSERT INTO users (username, password, role) 
            VALUES (?, ?, ?)
        ''', (admin_user, hash_pass(admin_pass), admin_role))
        print(f"✅ Permanent admin '{admin_user}' created successfully.")
    
    conn.commit()
    conn.close()
def hash_pass(password):
    """The 'Shredder': Scrambles passwords using SHA-256 for security."""
    return hashlib.sha256(str.encode(password)).hexdigest()

def create_user(user, pwd, role):
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    try:
        # Explicitly name the columns you are inserting into
        c.execute('''
            INSERT INTO users (username, password, role) 
            VALUES (?, ?, ?)
        ''', (user, hash_pass(pwd), role))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        # This happens if the username already exists (UNIQUE constraint)
        return False
    finally:
        conn.close()
        
def verify_user(user, pwd):
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    # We now select both ID and ROLE
    c.execute('SELECT id, role FROM users WHERE username=? AND password=?', (user, hash_pass(pwd)))
    result = c.fetchone()
    conn.close()
    
    if result:
        return result[0], result[1] # Returns (1, "admin")
    return None, None # Returns None if verification fails

def save_message(user, role, text):
    """The Secretary: Logs a single chat message with a timestamp."""
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute('INSERT INTO chat_history VALUES (?,?,?,?)', (user, role, text, now))
    conn.commit()
    conn.close()

def get_history(user):
    """The Memory: Pulls all past conversations for a specific user."""
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    # We order by timestamp so the chat appears in the correct sequence
    c.execute('SELECT role, content FROM chat_history WHERE username=? ORDER BY timestamp ASC', (user,))
    data = c.fetchall()
    conn.close()
    # Formats the data for Streamlit's st.chat_message
    return [{"role": row[0], "content": row[1]} for row in data]

def create_new_session(user_id, title="New Chat"):
    """Creates a new chat session entry and returns its ID."""
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute('INSERT INTO chat_sessions (user_id, title) VALUES (?, ?)', (user_id, title))
    session_id = c.lastrowid # This gets the 'id' that was just created
    conn.commit()
    conn.close()
    return session_id

def get_user_sessions(user_id):
    """Retrieves all chat sessions for the sidebar list."""
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute('SELECT id, title FROM chat_sessions WHERE user_id=? ORDER BY created_at DESC', (user_id,))
    sessions = c.fetchall()
    conn.close()
    return sessions # List of (id, title)

def save_chat_message(session_id, role, content):
    """Saves a message to a specific chat session."""
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()

    c.execute('INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)', 
              (session_id, role, content))
    conn.commit()
    conn.close()

def get_chat_history(session_id):
    """Loads all messages for a specific session."""
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute('SELECT role, content FROM messages WHERE session_id=? ORDER BY timestamp ASC', (session_id,))
    rows = c.fetchall()
    conn.close()
    return [{"role": r[0], "content": r[1]} for r in rows]

def update_session_title(session_id, new_title):
    # Changed from hardcoded string to str(DB_PATH)
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE chat_sessions SET title = ? WHERE id = ?", (new_title, session_id))
        conn.commit()
    finally:
        conn.close()

def delete_session(session_id):
    # Changed from hardcoded string to str(DB_PATH)
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    try:
        # Note: Your table name in init_db is 'messages', fixed that here
        cursor.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        cursor.execute("DELETE FROM chat_sessions WHERE id = ?", (session_id,))
        conn.commit()
    finally:
        conn.close()