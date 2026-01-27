import streamlit as st
import components.database as db
from components.company_rag import CompanyKnowledgeBase
import PyPDF2
from io import BytesIO

# ==========================================
# 1. SECURITY CHECK (GATES)
# ==========================================
# Kick out anyone not logged in before loading any heavy logic
if "user" not in st.session_state or st.session_state.user is None:
    st.warning("⚠️ Session expired. Redirecting to Login...")
    st.switch_page("main_app.py")
    st.stop()

# ==========================================
# 2. PAGE & UI CONFIGURATION
# ==========================================
st.set_page_config(page_title="Dataquartz Chat", layout="wide")

# Persistent Background & CSS logic to prevent vanishing on rerun
bg_placeholder = st.empty()
with bg_placeholder.container():
    st.markdown(f"""
        <style>
            [data-testid="stSidebarNav"] {{ display: none !important; }}    
            .stApp {{ background: transparent !important; color: #F8F1F1; }}
            .main {{ background: linear-gradient(180deg, #000000 0%, #2D080A 100%) !important; }}
            
            #bgVideo {{
                position: fixed; right: 0; bottom: 0;
                min-width: 100%; min-height: 100%;
                z-index: -1; object-fit: cover; 
                filter: brightness(0.3) saturate(1.2) hue-rotate(140deg);
            }}

            [data-testid="stSidebar"] {{ background-color: #000000 !important; border-right: 1px solid #4a0404; }}

            /* Animated Maroon Buttons */
            div.stButton > button {{
                background-color: #5E0B10 !important;
                color: white !important;
                border: none !important;
                position: relative; z-index: 1;
                overflow: hidden; border-radius: 8px !important;
                transition: all 0.3s ease;
            }}

            div.stButton > button::before {{
                content: ''; position: absolute;
                top: -50%; left: -50%; width: 200%; height: 200%;
                background: conic-gradient(transparent, #A01A22, transparent 30%);
                animation: rotate 4s linear infinite; z-index: -1;
            }}
            
            div.stButton > button::after {{
                content: ''; position: absolute; inset: 2px;
                background: #5E0B10; border-radius: 6px; z-index: -1;
            }}

            @keyframes rotate {{ 100% {{ transform: rotate(360deg); }} }}

            .stChatMessage {{ 
                background: rgba(45, 8, 10, 0.6) !important; 
                backdrop-filter: blur(12px);
                border-radius: 15px !important;
                border: 1px solid #800000 !important;
            }}
        </style>
        
        <video autoplay muted loop playsinline id="bgVideo">
            <source src="https://cdn.pixabay.com/video/2020/10/21/52991-472381398_large.mp4" type="video/mp4">
        </video>
    """, unsafe_allow_html=True)

# ==========================================
# 3. HELPER FUNCTIONS
# ==========================================
def extract_pdf_text(uploaded_file):
    """Converts uploaded PDF bytes into a single string of text."""
    try:
        pdf_reader = PyPDF2.PdfReader(BytesIO(uploaded_file.read()))
        return "\n".join([page.extract_text() for page in pdf_reader.pages if page.extract_text()])
    except Exception:
        return ""

# ==========================================
# 4. CORE LOGIC INITIALIZATION
# ==========================================
user_data = st.session_state.user
rag = CompanyKnowledgeBase() # Initialize the RAG engine

if "temp_pdf_text" not in st.session_state:
    st.session_state.temp_pdf_text = ""

# ==========================================
# 5. SIDEBAR (HISTORY & ACCOUNT)
# ==========================================
with st.sidebar:
    st.image("https://dataquartz.com/wp-content/uploads/2024/02/dq_logo_transparent.png", width=200)

    # Admin Guarded Navigation
    if user_data.get('role') == "admin":
        st.markdown("<p style='color: #A01A22; font-weight: bold; margin-bottom: 5px;'>ADMIN ACCESS</p>", unsafe_allow_html=True)
        if st.button("Open Admin Panel", use_container_width=True):
            st.switch_page("pages/2_⚙️_Admin_Panel.py")
        st.divider()
    
    # Account Settings
    with st.expander(f"Account: {user_data['username']}", expanded=False):
        st.write(f"Role: `{user_data['role']}`")
        if st.button("Logout", use_container_width=True):
            st.session_state.user = None
            st.rerun()

    # New Chat Initialization
    if st.button("＋ New Chat", use_container_width=True):
        new_id = db.create_new_session(user_data['id'], title="New Discussion")
        st.session_state.current_session_id = new_id
        st.session_state.messages = []
        st.session_state.temp_pdf_text = ""
        st.rerun()
    
    st.divider()
    st.title("Chat History")
    
    # Chat History Search & Listing
    search_query = st.text_input("🔍 Search", placeholder="Filter...", label_visibility="collapsed")
    user_sessions = db.get_user_sessions(user_data['id'])
    
    if search_query:
        user_sessions = [s for s in user_sessions if search_query.lower() in s[1].lower()]

    for s_id, title in user_sessions:
        col_link, col_menu = st.columns([0.85, 0.15])
        
        # Click to load existing chat
        if col_link.button(f"💬 {title[:20]}", key=f"btn_{s_id}", use_container_width=True):
            st.session_state.current_session_id = s_id
            st.session_state.messages = db.get_chat_history(s_id)
            st.rerun()
        
        # Popover for Rename/Delete
        with col_menu.popover("⋮"):
            new_name = st.text_input("Rename", value=title, key=f"rename_{s_id}")
            if st.button("Save", key=f"save_{s_id}"):
                db.update_session_title(s_id, new_name)
                st.rerun()
            
            if st.button("🗑️ Delete", key=f"del_{s_id}", type="primary"):
                db.delete_session(s_id)
                if st.session_state.get("current_session_id") == s_id:
                    st.session_state.current_session_id = None
                st.rerun()

# ==========================================
# 6. MAIN CHAT INTERFACE
# ==========================================
# Ensure a session is always selected
if st.session_state.get("current_session_id") is None:
    if user_sessions:
        st.session_state.current_session_id = user_sessions[0][0]
        st.session_state.messages = db.get_chat_history(st.session_state.current_session_id)
    else:
        st.session_state.current_session_id = db.create_new_session(user_data['id'])
        st.session_state.messages = []

st.title("Dataquartz Chat")

# Welcome message for empty chats
if not st.session_state.messages:
    st.markdown(f"""
        <div style="background-color: rgba(94, 11, 16, 0.2); border: 1px solid #5E0B10; padding: 20px; border-radius: 10px;">
            <h3 style="color: #A01A22;">Hi {user_data['username']}! 👋</h3>
            <p>Ask about Dataquartz or upload a PDF to analyze documents.</p>
        </div>
    """, unsafe_allow_html=True)

# Render Chat History from State
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ==========================================
# 7. INPUT HANDLING & AI RESPONSE
# ==========================================
prompt_payload = st.chat_input("Ask about Dataquartz...", accept_file="multiple", file_type=["pdf"])

if prompt_payload:
    user_text = prompt_payload.text
    uploaded_files = prompt_payload.files 
    
    # Process PDF attachments
    if uploaded_files:
        new_pdf_content = ""
        for f in uploaded_files:
            new_pdf_content += f"\n--- {f.name} ---\n{extract_pdf_text(f)}"
        st.session_state.temp_pdf_text = new_pdf_content
        st.info(f"📁 {len(uploaded_files)} files added to session memory.")

    # Auto-generate Title for new chats
    if not st.session_state.messages:
        title_trigger = user_text if user_text else "Document Analysis"
        res = rag.llm.invoke(f"Create a 3-word title for: {title_trigger}")
        db.update_session_title(st.session_state.current_session_id, res.content.strip().replace('"', ''))
    
    # Save & Display User Message
    display_text = user_text if user_text else f"📎 Attached {len(uploaded_files)} files"
    st.chat_message("user").markdown(display_text)
    db.save_chat_message(st.session_state.current_session_id, "user", display_text)
    st.session_state.messages.append({"role": "user", "content": display_text})

    # AI RESPONSE GENERATION
    with st.chat_message("assistant"):
        with st.spinner("Analyzing context..."):
            result = rag.query(
                user_question=user_text or "Summarize these documents.",
                extra_context=st.session_state.temp_pdf_text,
                history=st.session_state.messages
            )
            
            answer = result["answer"]
            st.markdown(answer)
            
            # Display Sources if RAG used the Vector Store
            if result.get('used_kb') and result['sources']:
                st.markdown("---")
                for src in set(result['sources']):
                    st.caption(f"🧷 Source: {src}")

    # Save AI response to DB
    db.save_chat_message(st.session_state.current_session_id, "assistant", answer)
    st.session_state.messages.append({"role": "assistant", "content": answer})