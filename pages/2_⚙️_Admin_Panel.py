import streamlit as st
import sqlite3
import os
import base64
import PyPDF2 # For text extraction
from io import BytesIO
from pathlib import Path
from reportlab.pdfgen import canvas # For saving edits back to PDF
from reportlab.lib.pagesizes import letter
from components.company_rag import CompanyKnowledgeBase

# --- 1. PAGE SETUP & SECURITY ---
st.set_page_config(page_title="Dataquartz Admin", layout="wide")

if "user" not in st.session_state or st.session_state.user.get('role') != 'admin':
    st.error("🚫 Access Denied.")
    if st.button("Return to Home"): st.switch_page("main_app.py")
    st.stop()

# --- 2. MAROON THEME STYLING ---
st.markdown("""
    <style>
        [data-testid="stSidebarNav"] { display: none !important; }
        .stApp { background: linear-gradient(180deg, #000000 0%, #2D080A 100%) !important; color: white; }
        [data-testid="stSidebar"] { background-color: #000000 !important; border-right: 1px solid #4a0404; }
        .stTabs [data-baseweb="tab-list"] { background-color: rgba(0,0,0,0.3); padding: 10px; border-radius: 15px; }
        .stTabs [aria-selected="true"] { color: #ff4b4b !important; border-bottom-color: #5E0B10 !important; }
        div[data-testid="stExpander"] { background: rgba(255, 255, 255, 0.05); border: 1px solid #4a0404; }
        /* Style for the Edit Area */
        .stTextArea textarea { background-color: #1a1a1a !important; color: #ffffff !important; border: 1px solid #5E0B10 !important; }
    </style>
""", unsafe_allow_html=True)

# --- 3. DATABASE & UTILS ---
def get_db_connection():
    return sqlite3.connect("dataquartz.db")

def get_indexed_files():
    kb_path = Path("knowledge_base")
    if not kb_path.exists(): return []
    return [f.name for f in kb_path.glob("*.pdf")]

def extract_text_from_pdf(file_path):
    """Helper to extract text for the editor."""
    text = ""
    try:
        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                text += page.extract_text() + "\n"
    except Exception as e:
        st.error(f"Error reading PDF: {e}")
    return text

def save_text_to_pdf(text, filename):
    """Saves edited text back to a PDF file on disk."""
    filepath = Path("knowledge_base") / filename
    c = canvas.Canvas(str(filepath), pagesize=letter)
    width, height = letter
    textobject = c.beginText(50, height - 50)
    textobject.setFont("Helvetica", 10)
    
    # Simple line wrapping
    for line in text.split('\n'):
        if textobject.getY() < 50: # New page if bottom reached
            c.drawText(textobject)
            c.showPage()
            textobject = c.beginText(50, height - 50)
            textobject.setFont("Helvetica", 10)
        textobject.textLine(line)
    
    c.drawText(textobject)
    c.save()

# --- SETTINGS HELPERS (Omitted update_setting/get_setting for brevity, keep yours) ---
def update_setting(key, value):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()

def get_setting(key, default):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
    res = cursor.fetchone()
    conn.close()
    return res[0] if res else default

# --- 4. SIDEBAR NAVIGATION ---
with st.sidebar:
    st.image("https://dataquartz.com/wp-content/uploads/2024/02/dq_logo_transparent.png", width=200)
    st.title("Admin Portal")
    st.write(f"Logged in: **{st.session_state.user['username']}**")
    st.divider()
    if st.button("Switch to Chatbot", use_container_width=True): st.switch_page("pages/1_💬_Chatbot.py")
    if st.button("Logout", use_container_width=True, type="primary"):
        st.session_state.user = None
        st.switch_page("main_app.py")

# --- 5. MAIN UI TABS ---
st.title("Dataquartz Admin Panel")
tab1, tab2, tab3 = st.tabs(["AI Persona", "User Management", "Knowledge Base"])

# --- TAB 1 & 2 (Keep your existing User Management and Persona code here) ---
with tab1:
    st.header("Personality Settings")
    current_persona = get_setting("personality", "Professional and concise")
    new_persona = st.text_area("Define System Prompt:", value=current_persona, height=200)
    if st.button("Save Personality", type="primary"):
        update_setting("personality", new_persona)
        st.success("AI Persona updated!")

with tab2:
    st.header("User Management")
    
    # A. Create New Admin Form
    with st.expander("➕ Create New Admin Account"):
        new_u = st.text_input("New Admin Username")
        new_p = st.text_input("New Admin Password", type="password")
        
        if st.button("Register Admin"):
            if new_u and new_p:
                try:
                    conn = get_db_connection()
                    conn.execute(
                        "INSERT INTO users (username, password, role) VALUES (?, ?, 'admin')", 
                        (new_u, new_p)
                    )
                    conn.commit()
                    st.success(f"Admin {new_u} created!")
                except Exception as e:
                    st.error("Username already exists.")
                finally:
                    conn.close()

    st.divider()

    # B. Search and List Users
    search_u = st.text_input("🔍 Search Users", placeholder="Enter username...")
    
    conn = get_db_connection()
    query = "SELECT id, username, role FROM users"
    if search_u:
        query += f" WHERE username LIKE '%{search_u}%'"
    users = conn.execute(query).fetchall()

    for u_id, u_name, u_role in users:
        with st.container():
            col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
            col1.write(f"👤 {u_name}")
            col2.info(f"{u_role}")

            # Only show controls if the user isn't the one currently logged in
            if u_name != st.session_state.user['username']:
                # Promote/Demote logic
                new_role = "admin" if u_role == 'user' else "user"
                label = "🔼 Promote" if u_role == 'user' else "🔽 Demote"
                
                if col3.button(label, key=f"role_{u_id}", use_container_width=True):
                    conn.execute("UPDATE users SET role = ? WHERE id = ?", (new_role, u_id))
                    conn.commit()
                    st.rerun()

                # Secure Deletion with Confirmation
                if col4.button("🗑️ Delete", key=f"del_{u_id}", type="primary", use_container_width=True):
                    st.session_state[f"confirm_del_{u_id}"] = True

                # Conditional Confirmation UI
                if st.session_state.get(f"confirm_del_{u_id}"):
                    st.warning(f"Confirm deletion of {u_name}?")
                    c1, c2 = st.columns(2)
                    if c1.button("✅ YES", key=f"y_{u_id}", use_container_width=True):
                        conn.execute("DELETE FROM users WHERE id = ?", (u_id,))
                        conn.commit()
                        del st.session_state[f"confirm_del_{u_id}"]
                        st.rerun()
                    if c2.button("❌ NO", key=f"n_{u_id}", use_container_width=True):
                        del st.session_state[f"confirm_del_{u_id}"]
                        st.rerun()
        st.divider()
    
    conn.close()
    
# --- TAB 3: KNOWLEDGE BASE (Enhanced with View/Edit) ---
with tab3:
    st.header("KB Manager")
    rag = CompanyKnowledgeBase()
    
    uploaded_files = st.file_uploader("Upload PDFs", type=["pdf"], accept_multiple_files=True)
    existing_files = get_indexed_files()

    if st.button("Process & Index Documents", type="primary"):
        if uploaded_files:
            kb_path = Path("knowledge_base")
            kb_path.mkdir(exist_ok=True)
            new_files_to_index = []
            for f in uploaded_files:
                if f.name in existing_files:
                    st.toast(f"⚠️ {f.name} already exists.", icon="🚫")
                else:
                    with open(kb_path / f.name, "wb") as save_file:
                        save_file.write(f.getbuffer())
                    new_files_to_index.append(f.name)
            
            if new_files_to_index:
                with st.status("Updating AI Index...", expanded=True) as status:
                    if rag.index_documents():
                        rag.update_manifest()
                        status.update(label="Index Synced!", state="complete")
                        st.rerun()
        else:
            st.warning("Please upload files first.")

    st.divider()
    
    st.subheader("Current Knowledge Base")
    for file_name in existing_files:
        with st.container():
            c1, c2, c3, c4 = st.columns([2, 0.8, 0.8, 0.8])
            c1.write(f"📄 {file_name}")
            
            # 1. VIEW (Embedded Iframe)
            if c2.button(" View", key=f"view_{file_name}", use_container_width=True):
                st.session_state.viewing_pdf = file_name

            # 2. EDIT (Text Area Toggle)
            if c3.button("Edit", key=f"edit_{file_name}", use_container_width=True):
                st.session_state.editing_pdf = file_name

            # 3. REMOVE
            if c4.button("Remove", key=f"kb_del_{file_name}", use_container_width=True):
                os.remove(Path("knowledge_base") / file_name)
                # Purge from RAG index
                rag.index_documents()
                st.rerun()

            # --- DYNAMIC VIEWING AREA ---
            if st.session_state.get("viewing_pdf") == file_name:
                with st.expander(f"Viewing: {file_name}", expanded=True):
                    with open(Path("knowledge_base") / file_name, "rb") as f:
                        base64_pdf = base64.b64encode(f.read()).decode('utf-8')
                    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="500" type="application/pdf"></iframe>'
                    st.markdown(pdf_display, unsafe_allow_html=True)
                    if st.button("Close Preview", key=f"close_v_{file_name}"):
                        st.session_state.viewing_pdf = None
                        st.rerun()

            # --- DYNAMIC EDITING AREA ---
            if st.session_state.get("editing_pdf") == file_name:
                with st.expander(f"Editing Content: {file_name}", expanded=True):
                    current_text = extract_text_from_pdf(Path("knowledge_base") / file_name)
                    new_text = st.text_area("Edit Text Content:", value=current_text, height=300, key=f"txt_{file_name}")
                    
                    ec1, ec2 = st.columns(2)
                    if ec1.button("Save & Re-index", key=f"save_{file_name}", use_container_width=True):
                        save_text_to_pdf(new_text, file_name)
                        with st.spinner("AI is relearning..."):
                            rag.index_documents() # Critical: Update the RAG with new text
                        st.success("Changes saved and AI updated!")
                        st.session_state.editing_pdf = None
                        st.rerun()
                    if ec2.button("Cancel", key=f"cancel_{file_name}", use_container_width=True):
                        st.session_state.editing_pdf = None
                        st.rerun()