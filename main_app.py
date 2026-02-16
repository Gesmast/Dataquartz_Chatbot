import streamlit as st

# Automatically grab the IANA timezone string from the user's browser
detected_tz = st.context.timezone


# --- 1. ASSET LINKS (Direct from Supabase) ---
PAGE_ICON = "https://lrkawuwfwyrmezgrrbpp.supabase.co/storage/v1/object/public/Assets_DQ_Chatbot/62249_db-favicon%20(1).png"
DQ_LOGO = "https://lrkawuwfwyrmezgrrbpp.supabase.co/storage/v1/object/public/Assets_DQ_Chatbot/dq_logo_transparent.png"
BG_VIDEO = "https://lrkawuwfwyrmezgrrbpp.supabase.co/storage/v1/object/public/Assets_DQ_Chatbot/quartz_background.mp4"

# --- 2. CONFIG (MUST BE FIRST) ---
st.set_page_config(
    page_title="Dataquartz AI", 
    page_icon=PAGE_ICON, 
    layout="centered",
    initial_sidebar_state="collapsed" 
)

# --- 3. UI STYLING (CSS) ---
st.markdown(f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Electrolize&family=Inter:wght@400;700&display=swap');

        /* Hide Streamlit elements */
        [data-testid="stSidebar"], [data-testid="stSidebarNav"], button[kind="header"] {{
            display: none !important;
        }}

        .stApp {{
            background: transparent !important;
        }}

        /* Background Video */
        #bgVideo {{
            position: fixed; right: 0; bottom: 0;
            min-width: 100%; min-height: 100%;
            z-index: -1; object-fit: cover; 
            filter: brightness(0.25);
        }}
        
        /* Glassmorphism Content Box */
        .content-box {{
            background: rgba(255, 255, 255, 0.03);
            backdrop-filter: blur(20px);
            border-radius: 28px;
            padding: 40px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            text-align: center;
            margin-top: 10vh;
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.8);
        }}

        .electro-header {{
            font-family: 'Electrolize', sans-serif;
            font-size: 4rem;
            background: linear-gradient(90deg, #00FFFF, #9D00FF);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-weight: bold;
            letter-spacing: 5px;
            margin-bottom: 0;
        }}

        .sub-header {{
            font-family: 'Electrolize', sans-serif;
            color: rgba(255, 255, 255, 0.6);
            font-size: 1.1rem;
            text-transform: uppercase;
            letter-spacing: 2px;
            margin-top: 10px;
        }}

        /* Cyan/Purple Electro Buttons with Shine/Glow */
        div.stButton > button {{
            background: rgba(255, 255, 255, 0.05) !important;
            color: #F8F1F1 !important;
            /* The base outline */
            border: 1px solid rgba(0, 255, 255, 0.4) !important;
            border-radius: 12px !important;
            padding: 15px 25px !important;
            font-family: 'Electrolize', sans-serif !important;
            width: 100% !important;
            transition: all 0.4s ease !important;
            text-transform: uppercase;
            letter-spacing: 1.5px;
            /* The 'Shine' effect */
            box-shadow: 0 0 10px rgba(0, 255, 255, 0.1), inset 0 0 5px rgba(0, 255, 255, 0.1);
        }}

        div.stButton > button:hover {{
            background: linear-gradient(90deg, rgba(0, 255, 255, 0.1), rgba(157, 0, 255, 0.1)) !important;
            border-color: #00FFFF !important;
            /* Intense Glow on Hover */
            box-shadow: 0 0 20px rgba(0, 255, 255, 0.6), inset 0 0 10px rgba(0, 255, 255, 0.2) !important;
            transform: translateY(-3px);
            color: #ffffff !important;
        }}

        .website-link {{
            color: #00FFFF;
            text-decoration: none;
            font-family: 'Electrolize', sans-serif;
            transition: 0.3s;
        }}
        
        .website-link:hover {{
            text-shadow: 0 0 10px #00FFFF;
        }}
    </style>
    
    <video autoplay muted loop playsinline id="bgVideo">
        <source src="{BG_VIDEO}" type="video/mp4">
    </video>
""", unsafe_allow_html=True)

# --- 4. MAIN UI CONTENT ---
with st.container():
    # Centered Logo and Electro Header
    st.markdown(f"""
        <div class="content-box">
            <img src="{DQ_LOGO}" width="150" style="margin-bottom: 20px;">
            <div class="electro-header">DATAQUARTZ</div>
            <div class="sub-header">Intelligent AI Ecosystems</div>
            <hr style="border: 0; border-top: 1px solid rgba(255,255,255,0.1); margin: 30px 0;">
        </div>
    """, unsafe_allow_html=True)

    # Action Grid
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("<br>", unsafe_allow_html=True)
        # Main Action Button (The only link)
        if st.button("Explore Solutions"):
            st.markdown('<meta http-equiv="refresh" content="0;URL=\'https://dataquartz.com\'" />', unsafe_allow_html=True)
        
        # Static Text Label (No link)
        st.markdown(
            "<p style='text-align: center; color: rgba(255,255,255,0.5); font-family: Electrolize;'>"
            "Visit the dataquartz website"
            "</p>", 
            unsafe_allow_html=True
        )

    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Talk to AI Assistant"):
            st.switch_page("pages/1_💬_Chatbot.py")
        st.markdown("<p style='text-align: center; color: rgba(255,255,255,0.5); font-family: Electrolize;'>24/7 Intelligence</p>", unsafe_allow_html=True)
