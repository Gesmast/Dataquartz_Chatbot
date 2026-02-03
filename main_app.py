import streamlit as st
import base64
from io import BytesIO
from PIL import Image

# --- 1. CONFIG ---
# Retaining your custom icon logic
ICON_BASE64 = "iVBORw0KGgoAAAANSUhEUgAAABwAAAAcCAAAAABXZoBIAAAAtElEQVR4AcXLIQiDQBiG4bc3e2dxbWllxQ5Wo+3AYrt0IFy12m1XBPNh5xB7j9eD7QY7TsbAhYX5lP+Dl5+TFTnHdM2x9q9RTWY0qFfU1jbcBcnUABfXCXhscyMXr9fUpI53q8hCCSCDS3EmGgSTidPt0RLJGp8T5/r52Qn8LU6xx76M11c4HadZSNwVYBwFeQDgFhy70XS9zaUAFSSZDsPCm8clDee9zdqVY/pbVD/HQnGSJxdORxqCuJ3EAAAAAElFTkSuQmCC"

def get_page_icon():
    return Image.open(BytesIO(base64.b64decode(ICON_BASE64)))

st.set_page_config(
    page_title="Dataquartz AI", 
    page_icon=get_page_icon(), 
    layout="centered",
    initial_sidebar_state="collapsed" 
)

# --- 2. PERSISTENT VIDEO & MAROON THEME ---
if "bg_video_url" not in st.session_state:
    st.session_state.bg_video_url = "https://cdn.pixabay.com/video/2020/10/21/52991-472381398_large.mp4"

st.markdown(f"""
    <style>
        /* 1. UI HIDING (Sidebar & Header) */
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
            filter: brightness(0.3) saturate(1.1) hue-rotate(140deg);
        }}
        
        /* 3. CENTERED CONTENT BOX */
        .content-box {{
            background: rgba(0, 0, 0, 0.65);
            backdrop-filter: blur(20px);
            border-radius: 28px;
            padding: 40px;
            border: 1px solid #5E0B10;
            text-align: center;
            margin-top: 15vh;
        }}

        /* 4. MAROON BUTTONS */
        div.stButton > button {{
            background-color: #4A0404 !important;
            color: #F8F1F1 !important;
            border: 1px solid #800000 !important;
            border-radius: 12px !important;
            padding: 15px 25px !important;
            font-weight: 600 !important;
            width: 100% !important;
            transition: all 0.3s ease !important;
            text-transform: uppercase;
            letter-spacing: 1.5px;
            font-size: 1rem;
        }}

        div.stButton > button:hover {{
            background-color: #5E0B10 !important;
            border-color: #A01A22 !important;
            box-shadow: 0 0 20px rgba(128, 0, 0, 0.7);
            transform: translateY(-2px);
        }}

        .website-link {{
            color: #94a3b8;
            text-decoration: none;
            font-weight: 400;
            transition: color 0.3s;
        }}
        
        .website-link:hover {{
            color: #F8F1F1;
        }}
    </style>
    
    <video autoplay muted loop playsinline id="bgVideo">
        <source src="{st.session_state.bg_video_url}" type="video/mp4">
    </video>
    """, unsafe_allow_html=True)

# --- 3. MAIN UI CONTENT ---
with st.container():
    # Content Box Wrapper (via Markdown)
    st.markdown("""
        <div class="content-box">
            <h1 style='color: white; font-size: 3.8rem; margin-bottom: 0; font-weight: 700;'>Dataquartz</h1>
            <p style='color: #e2e8f0; font-size: 1.3rem; margin-top: 10px;'>Intelligent AI Ecosystems</p>
            <hr style='border: 0; border-top: 1px solid #5E0B10; margin: 30px 0;'>
        </div>
    """, unsafe_allow_html=True)

    # Columns for the two primary actions
    col1, col2 = st.columns(2)

    with col1:
        # Action 1: External Website
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Explore Solutions"):
            st.markdown('<meta http-equiv="refresh" content="0;URL=\'https://dataquartz.com\'" />', unsafe_allow_html=True)
        st.markdown("<p style='text-align: center;'><a href='https://dataquartz.com' class='website-link'>dataquartz.com</a></p>", unsafe_allow_html=True)

    with col2:
        # Action 2: Chatbot Page
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Talk to AI Assistant"):
            st.switch_page("pages/1_Chatbot.py")
        st.markdown("<p style='text-align: center; color: #94a3b8;'>Instant Support</p>", unsafe_allow_html=True)
