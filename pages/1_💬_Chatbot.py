import os
import streamlit as st
from langchain_groq import ChatGroq
from mcp_server import search_dataquartz

# --- 1. PAGE CONFIG ---
st.set_page_config(page_title="Dataquartz AI", layout="centered")

# --- 2. THE FOUR PILLARS UI (CSS) ---
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;700&display=swap');

        /* Pillar 4: Geometry & Typography */
        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
            letter-spacing: 0.02em;
        }

        /* Pillar 2 & 3: Palette & Luminescent Accents (Orbital Glows) */
        .stApp {
            background-color: #0B0B0B !important;
            background-image: 
                radial-gradient(circle at 20% 30%, rgba(0, 255, 255, 0.05) 0%, transparent 40%),
                radial-gradient(circle at 80% 70%, rgba(157, 0, 255, 0.07) 0%, transparent 40%) !important;
            color: #F8F1F1;
        }

        /* Pillar 1: Glassmorphism & Light-Leak Borders */
        .stChatMessage { 
            background: rgba(255, 255, 255, 0.03) !important; 
            backdrop-filter: blur(15px) !important;
            border-radius: 16px !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.8) !important;
            margin-bottom: 20px;
        }

        /* Gradient Text for Headers */
        h1, h2, h3 {
            background: linear-gradient(90deg, #00FFFF, #9D00FF);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-weight: 700 !important;
        }

        /* Hide Sidebar Elements */
        [data-testid="stSidebar"], [data-testid="stSidebarNav"] { display: none !important; }

        #bgVideo {
            position: fixed; right: 0; bottom: 0;
            min-width: 100%; min-height: 100%;
            z-index: -2; object-fit: cover; 
            filter: brightness(0.2);
        }

        .logo-container { text-align: center; padding: 2rem 0; }
        .logo-container img { width: 180px; transition: 0.4s; }
        .logo-container img:hover { filter: drop-shadow(0 0 15px rgba(0, 255, 255, 0.5)); transform: scale(1.02); }
    </style>
    
    <video autoplay muted loop playsinline id="bgVideo">
        <source src="https://cdn.pixabay.com/video/2020/10/21/52991-472381398_large.mp4" type="video/mp4">
    </video>
""", unsafe_allow_html=True)

# --- 3. THE BRAND LINK ---
st.markdown("""
    <div class="logo-container">
        <a href="https://dataquartz.com" target="_blank">
            <img src="https://dataquartz.com/wp-content/uploads/2024/02/dq_logo_transparent.png">
        </a>
    </div>
""", unsafe_allow_html=True)

# --- 4. CHAT LOGIC ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# User Input
if prompt := st.chat_input("Ask about Dataquartz..."):
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        with st.spinner(" "): # Cleaner minimalist spinner
            # 1. Scraping Tool
            context = search_dataquartz(prompt)
            
            # 2. LLM Call
            llm = ChatGroq(model="llama3-70b-8192", groq_api_key=st.secrets["GROQ_API_KEY"])
            
            # 3. Reading System Prompt from GitHub-mirrored folder
            with open("prompts/SystemPrompt.txt", "r") as f:
                sys_p = f.read()

            full_p = f"{sys_p}\n\nSITE CONTEXT:\n{context}\n\nQUESTION: {prompt}"
            response = llm.invoke(full_p)
            
            st.markdown(response.content)
            st.session_state.messages.append({"role": "assistant", "content": response.content})
