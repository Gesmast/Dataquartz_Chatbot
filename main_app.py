import streamlit as st
import base64
from io import BytesIO
from PIL import Image
from components.database import init_db, create_user, verify_user

# --- 1. CONFIG & DB INIT ---
init_db()

ICON_BASE64 = "iVBORw0KGgoAAAANSUhEUgAAABwAAAAcCAAAAABXZoBIAAAAtElEQVR4AcXLIQiDQBiG4bc3e2dxbWllxQ5Wo+3AYrt0IFy12m1XBPNh5xB7j9eD7QY7TsbAhYX5lP+Dl5+TFTnHdM2x9q9RTWY0qFfU1jbcBcnUABfXCXhscyMXr9fUpI53q8hCCSCDS3EmGgSTidPt0RLJGp8T5/r52Qn8LU6xx76M11c4HadZSNwVYBwFeQDgFhy70XS9zaUAFSSZDsPCm8clDee9zdqVY/pbVD/HQnGSJxdORxqCuJ3EAAAAAElFTkSuQmCC"

def get_page_icon():
    return Image.open(BytesIO(base64.b64decode(ICON_BASE64)))

st.set_page_config(
    page_title="Dataquartz AI", 
    page_icon=get_page_icon(), 
    layout="centered",
    initial_sidebar_state="collapsed" 
)

# --- 2. THE PERSISTENT VIDEO LOGIC ---
if "bg_video_url" not in st.session_state:
    st.session_state.bg_video_url = "https://cdn.pixabay.com/video/2020/10/21/52991-472381398_large.mp4"

# Create a placeholder that stays put during reruns
video_placeholder = st.empty()

with video_placeholder.container():
    st.markdown(f"""
    <style>
        /* 1. UI HIDING */
        [data-testid="stSidebar"], [data-testid="stSidebarNav"], button[kind="header"] {{
            display: none !important;
        }}

        .stApp {{
            background: transparent !important;
        }}
        
        .main {{
            background: linear-gradient(180deg, #000000 0%, #2D080A 100%) !important;
        }}

        /* 2. BACKGROUND VIDEO POSITIONING */
        #bgVideo {{
            position: fixed; 
            right: 0; 
            bottom: 0;
            min-width: 100%; 
            min-height: 100%;
            z-index: -1; 
            object-fit: cover; 
            filter: brightness(0.4) saturate(1.3) hue-rotate(140deg);
        }}
        
        /* 3. THE AUTH BOX */
        .stTabs {{
            background: rgba(0, 0, 0, 0.6);
            backdrop-filter: blur(15px);
            border-radius: 24px;
            padding: 30px;
            border: 1px solid #5E0B10;
        }}

        /* 4. DARK MAROON BUTTON BARS */
        div.stButton > button {{
            background-color: #4A0404 !important;
            color: #F8F1F1 !important;
            border: 1px solid #800000 !important;
            border-radius: 12px !important;
            padding: 12px 20px !important;
            font-weight: 600 !important;
            width: 100% !important;
            transition: all 0.3s ease !important;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}

        div.stButton > button:hover {{
            background-color: #5E0B10 !important;
            border-color: #A01A22 !important;
            box-shadow: 0 0 15px rgba(128, 0, 0, 0.6);
            transform: translateY(-1px);
        }}

        div.stButton > button:active {{
            transform: translateY(1px);
            background-color: #2D080A !important;
        }}

        .stButton {{
            margin-top: 20px;
        }}
    </style>
    
    <video autoplay muted loop playsinline id="bgVideo">
        <source src="{st.session_state.bg_video_url}" type="video/mp4">
    </video>
    """, unsafe_allow_html=True)

# --- 3. SESSION STATE ---
if "user" not in st.session_state: 
    st.session_state.user = None

# --- 4. THE UI LOGIC (Login/Register) ---
# Wrapping this in a container helps prevent the page from jumping when the video re-renders
main_container = st.container()

with main_container:
    if st.session_state.user is None:
        st.markdown("<h1 style='text-align: center; color: white; font-size: 3.5rem; margin-bottom: 0;'>Dataquartz</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #94a3b8; font-size: 1.2rem;'>Begin your AI journey</p>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        
        tab1, tab2 = st.tabs(["Secure Login", "Create Profile"])
        
        with tab1:
            u = st.text_input("Username", placeholder="User ID", key="l_u")
            p = st.text_input("Password", type="password", placeholder="••••••••", key="l_p")
            if st.button("Access Portal", use_container_width=True):
                user_id, role = verify_user(u, p)
                if user_id:
                    st.session_state.user = {"id": user_id, "username": u, "role": role}
                    st.rerun()
                else:
                    st.error("Access Denied")
                    
        with tab2:
            nu = st.text_input("Choose Username", key="r_u")
            np = st.text_input("Create Password", type="password", key="r_p")
            if st.button("Register", use_container_width=True):
                if nu and np:
                    if create_user(nu, np, "user"):
                        user_id, role = verify_user(nu, np)
                        if user_id:
                            st.session_state.user = {"id": user_id, "username": nu, "role": role}
                            st.rerun()
                    else:
                        st.error("❌ Username already registered.")

    else:
        # REDIRECTION
        if st.session_state.user['role'] == "admin":
            st.switch_page("pages/2_⚙️_Admin_Panel.py")
        else:
            st.switch_page("pages/1_💬_Chatbot.py")