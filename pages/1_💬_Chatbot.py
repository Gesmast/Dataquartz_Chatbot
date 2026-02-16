import streamlit as st
import asyncio
from pathlib import Path
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage, AIMessage
from langchain_core.tools import StructuredTool

# Automatically grab the IANA timezone string from the user's browser
detected_tz = st.context.timezone

# --- PROJECT IMPORTS ---
from mcp_server import scrape_dataquartz 
from Calmcp import (
    get_available_slots, 
    create_cal_booking, 
    reschedule_cal_booking, 
    cancel_cal_booking, 
    get_booking_by_email
)
from database import create_new_session, save_message, get_chat_history

# --- 1. ASSETS & UI CONSTANTS ---
PAGE_ICON = "https://lrkawuwfwyrmezgrrbpp.supabase.co/storage/v1/object/public/Assets_DQ_Chatbot/62249_db-favicon%20(1).png"
DQ_LOGO = "https://lrkawuwfwyrmezgrrbpp.supabase.co/storage/v1/object/public/Assets_DQ_Chatbot/dq_logo_transparent.png"
AI_AVATAR = "https://lrkawuwfwyrmezgrrbpp.supabase.co/storage/v1/object/public/Assets_DQ_Chatbot/Gemini_Generated_Image_sinrf3sinrf3sinr.png"
USER_AVATAR = "https://lrkawuwfwyrmezgrrbpp.supabase.co/storage/v1/object/public/Assets_DQ_Chatbot/Untitled%20design%20(1).png"
BG_VIDEO = "https://lrkawuwfwyrmezgrrbpp.supabase.co/storage/v1/object/public/Assets_DQ_Chatbot/quartz_background.mp4"
SYSTEM_PROMPT_FILE = "prompts/SystemPrompt.txt"
LLM_MODEL = "llama-3.3-70b-versatile"

# --- 2. PAGE CONFIG & STYLING ---
st.set_page_config(page_title="Quartzy", page_icon=PAGE_ICON, layout="centered")

st.markdown(f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Electrolize&display=swap');
        .stApp, .stAppViewContainer, .stMain, [data-testid="stHeader"] {{ background: transparent !important; }}
        #bgVideo {{
            position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
            z-index: -1; object-fit: cover; filter: brightness(0.40); pointer-events: none;
        }}
        .electro-header {{
            font-family: 'Electrolize', sans-serif; font-size: 5rem;
            background: linear-gradient(90deg, #00FFFF, #9D00FF);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            text-align: center; font-weight: bold; letter-spacing: 5px; margin-top: -10px;
        }}
        .sub-header {{
            font-family: 'Electrolize', sans-serif; color: rgba(255, 255, 255, 0.7);
            text-align: center; font-size: 1rem; text-transform: uppercase; letter-spacing: 2px;
        }}
        .stChatMessage {{ 
            background: rgba(255, 255, 255, 0.07) !important; 
            backdrop-filter: blur(15px) !important;
            border-radius: 20px !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
            margin-bottom: 1rem;
        }}
        [data-testid="stSidebar"] {{ display: none !important; }}
    </style>
    <video autoplay muted loop playsinline id="bgVideo"><source src="{BG_VIDEO}" type="video/mp4"></video>
""", unsafe_allow_html=True)

def load_system_prompt() -> str:
    # 1. Start with the directory of the current script
    current_dir = Path(__file__).parent
    # 2. If this script is in the 'pages' subfolder, move up to the root
    if current_dir.name == "pages":
        root_dir = current_dir.parent
    else:
        root_dir = current_dir
    prompt_path = root_dir / "prompts" / "SystemPrompt.txt"

    if prompt_path.exists():
        return prompt_path.read_text(encoding='utf-8').strip()
    # Fallback if file is missing
    return "You are Quartzy, the official AI assistant of Dataquartz. Follow company rules."

# --- 4. INITIALIZATION ---
if "session_id" not in st.session_state:
    st.session_state.session_id = create_new_session("Web Discussion")
    st.session_state.messages = get_chat_history(st.session_state.session_id)

if "tools" not in st.session_state:
    st.session_state.tools = [
        StructuredTool.from_function(func=scrape_dataquartz, name="get_company_info", description="Search Dataquartz website."),
        StructuredTool.from_function(coroutine=get_available_slots, name="available_slots", description="Check Cal.com availability."),
        StructuredTool.from_function(coroutine=create_cal_booking, name="create_booking", description="Book meeting. Needs name, email, start_time."),
        StructuredTool.from_function(coroutine=reschedule_cal_booking, name="reschedule", description="Update booking. Needs booking_id, new_start_time."),
        StructuredTool.from_function(coroutine=cancel_cal_booking, name="cancel_booking", description="Delete booking. Needs booking_id."),
        StructuredTool.from_function(coroutine=get_booking_by_email, name="get_booking_via_email", description="Search guest ledger for bookings via email.")
    ]

# --- 5. UI BRANDING ---
st.markdown(f"""
    <div style="text-align: center; padding-top: 2rem;">
        <a href="/" target="_self"><img src="{DQ_LOGO}" width="140"></a>
        <div class="electro-header">CHAT</div>
        <div class="sub-header">Ask about Dataquartz</div>
    </div>
""", unsafe_allow_html=True)

# --- 6. CHAT LOGIC ---
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "system", 
            "content": f"The user's detected timezone is {detected_tz}. When booking, use this timezone."
        }
    ]

for msg in st.session_state.messages:
    if msg["role"] == "system":
        continue
    avatar = USER_AVATAR if msg["role"] == "user" else AI_AVATAR
    with st.chat_message(msg["role"], avatar=avatar):
        st.markdown(msg["content"])

if prompt := st.chat_input("How can I help you today?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    save_message(st.session_state.session_id, "user", prompt)
    with st.chat_message("user", avatar=USER_AVATAR):
        st.markdown(prompt)

    with st.chat_message("assistant", avatar=AI_AVATAR):
        with st.spinner(" "): 
            llm = ChatGroq(model=LLM_MODEL, groq_api_key=st.secrets["GROQ_API_KEY"])
            llm_with_tools = llm.bind_tools(st.session_state.tools)
            
            # Load instructions from your prompts/SystemPrompt.txt
            history = [SystemMessage(content=load_system_prompt())]
            for m in st.session_state.messages:
                role = HumanMessage if m["role"] == "user" else AIMessage
                history.append(role(content=m["content"]))

            # STEP 1: Process Request
            response = llm_with_tools.invoke(history)
            
            # STEP 2: Tool Routing
            if response.tool_calls:
                for tool_call in response.tool_calls:
                    t_name = tool_call["name"]
                    t_args = tool_call["args"]
                    
                    if t_name == "scrape_dataquartz":
                        observation = scrape_dataquartz(**t_args)
                    else:
                        selected_tool = next(t for t in st.session_state.tools if t.name == t_name)
                        if t_name == "create_cal_booking":
                            t_args["session_id"] = st.session_state.session_id
                        # Executing async MCP tools via sync bridge
                        observation = asyncio.run(selected_tool.ainvoke(t_args))

                # STEP 3: Generate Final Answer
                history.append(response)
                history.append(ToolMessage(content=str(observation), tool_call_id=tool_call["id"]))
                final_answer = llm.invoke(history).content
            else:
                final_answer = response.content

            st.markdown(final_answer)
            st.session_state.messages.append({"role": "assistant", "content": final_answer})
            save_message(st.session_state.session_id, "assistant", final_answer)
