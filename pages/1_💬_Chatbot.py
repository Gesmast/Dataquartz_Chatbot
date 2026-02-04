import streamlit as st
from langchain_groq import ChatGroq
from mcp_server import scrape_dataquartz
from database import create_new_session, save_message, get_chat_history

# --- 1. PAGE CONFIG ---
PAGE_ICON = "https://lrkawuwfwyrmezgrrbpp.supabase.co/storage/v1/object/public/Assets_DQ_Chatbot/62249_db-favicon%20(1).png"
st.set_page_config(
    page_title="Dataquartz AI", 
    page_icon=PAGE_ICON,
    layout="centered"
)

# --- 2. ASSET CONSTANTS ---
DQ_LOGO = "https://lrkawuwfwyrmezgrrbpp.supabase.co/storage/v1/object/public/Assets_DQ_Chatbot/dq_logo_transparent.png"
AI_AVATAR = "https://lrkawuwfwyrmezgrrbpp.supabase.co/storage/v1/object/public/Assets_DQ_Chatbot/Gemini_Generated_Image_sinrf3sinrf3sinr.png"
USER_AVATAR = "https://lrkawuwfwyrmezgrrbpp.supabase.co/storage/v1/object/public/Assets_DQ_Chatbot/Untitled%20design%20(1).png"
BG_VIDEO = "https://lrkawuwfwyrmezgrrbpp.supabase.co/storage/v1/object/public/Assets_DQ_Chatbot/quartz_background.mp4"

# --- 3. UI STYLING (CSS) ---
st.markdown(f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Electrolize&display=swap');

        .stApp, .stAppViewContainer, .stMain, [data-testid="stHeader"] {{
            background: transparent !important;
        }}

        #bgVideo {{
            position: fixed; top: 0; left: 0;
            width: 100vw; height: 100vh;
            z-index: -1; object-fit: cover;
            filter: brightness(0.40); /* Increased from 0.25 to 0.40 for better visibility */
            pointer-events: none;
        }}

        .electro-header {{
            font-family: 'Electrolize', sans-serif;
            font-size: 5rem;
            background: linear-gradient(90deg, #00FFFF, #9D00FF);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            text-align: center;
            font-weight: bold;
            letter-spacing: 5px;
            margin-top: -10px;
        }}

        .sub-header {{
            font-family: 'Electrolize', sans-serif;
            color: rgba(255, 255, 255, 0.7);
            text-align: center;
            font-size: 1rem;
            text-transform: uppercase;
            letter-spacing: 2px;
        }}

        .stChatMessage {{ 
            background: rgba(255, 255, 255, 0.07) !important; /* Slightly more opaque to contrast with brighter video */
            backdrop-filter: blur(15px) !important;
            border-radius: 20px !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
            margin-bottom: 1rem;
        }}

        /* Logo Hover Effect */
        .logo-link img {{
            transition: transform 0.3s ease, filter 0.3s ease;
        }}
        .logo-link img:hover {{
            transform: scale(1.05);
            filter: drop-shadow(0 0 10px rgba(0, 255, 255, 0.5));
        }}

        [data-testid="stSidebar"] {{ display: none !important; }}
    </style>

    <video autoplay muted loop playsinline id="bgVideo">
        <source src="{BG_VIDEO}" type="video/mp4">
    </video>
""", unsafe_allow_html=True)

# --- 4. CENTERED BRANDING ---
# Logo now clicks through to the main app (home)
st.markdown(f"""
    <div style="text-align: center; padding-top: 2rem;">
        <a href="/" target="_self" class="logo-link">
            <img src="{DQ_LOGO}" width="140">
        </a>
        <div class="electro-header">CHAT</div>
        <div class="sub-header">Ask about Dataquartz</div>
    </div>
""", unsafe_allow_html=True)

# --- 5. SESSION & HISTORY ---
if "session_id" not in st.session_state:
    st.session_state.session_id = create_new_session("Web Discussion")
    st.session_state.messages = []

if not st.session_state.messages:
    db_history = get_chat_history(st.session_state.session_id)
    st.session_state.messages = [{"role": m['role'], "content": m['content']} for m in db_history]

for msg in st.session_state.messages:
    current_avatar = USER_AVATAR if msg["role"] == "user" else AI_AVATAR
    with st.chat_message(msg["role"], avatar=current_avatar):
        st.markdown(msg["content"])

# --- 6. CHAT LOGIC ---
if prompt := st.chat_input("Message Dataquartz AI..."):
    with st.chat_message("user", avatar=USER_AVATAR):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})
    save_message(st.session_state.session_id, "user", prompt)

    with st.chat_message("assistant", avatar=AI_AVATAR):
        with st.spinner(" "): 
            context = scrape_dataquartz(prompt)
            llm = ChatGroq(model="llama-3.3-70b-versatile", groq_api_key=st.secrets["GROQ_API_KEY"])
            
            try:
                with open("prompts/SystemPrompt.txt", "r") as f:
                    sys_p = f.read()
            except FileNotFoundError:
                sys_p = "Professional Dataquartz assistant."

            full_prompt = f"{sys_p}\\n\\nSITE CONTEXT:\\n{context}\\n\\nQUESTION: {prompt}"
            response = llm.invoke(full_prompt)
            answer = response.content
            
            st.markdown(answer)
            st.session_state.messages.append({"role": "assistant", "content": answer})
            save_message(st.session_state.session_id, "assistant", answer)
            
