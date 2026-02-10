import streamlit as st
import asyncio
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage, AIMessage
from langchain_core.tools import Tool
from langchain_mcp_adapters.tools import load_mcp_tools

# 1. Internal Project Imports
from mcp_server import scrape_dataquartz
from database import create_new_session, save_message, get_chat_history
from Calmcp import mcp as cal_mcp  # Ensure the file is named Calmcp.py or change to calmcp

# --- 1. PAGE CONFIG ---
PAGE_ICON = "https://lrkawuwfwyrmezgrrbpp.supabase.co/storage/v1/object/public/Assets_DQ_Chatbot/62249_db-favicon%20(1).png"
st.set_page_config(page_title="Dataquartz AI", page_icon=PAGE_ICON, layout="centered")

# --- 2. ASSET CONSTANTS & CSS ---
DQ_LOGO = "https://lrkawuwfwyrmezgrrbpp.supabase.co/storage/v1/object/public/Assets_DQ_Chatbot/dq_logo_transparent.png"
AI_AVATAR = "https://lrkawuwfwyrmezgrrbpp.supabase.co/storage/v1/object/public/Assets_DQ_Chatbot/Gemini_Generated_Image_sinrf3sinrf3sinr.png"
USER_AVATAR = "https://lrkawuwfwyrmezgrrbpp.supabase.co/storage/v1/object/public/Assets_DQ_Chatbot/Untitled%20design%20(1).png"
BG_VIDEO = "https://lrkawuwfwyrmezgrrbpp.supabase.co/storage/v1/object/public/Assets_DQ_Chatbot/quartz_background.mp4"

# Define System Prompt (Missing in your snippet)
sys_p = "You are the Dataquartz AI assistant. Use the provided tools to search our website or book meetings."

st.markdown(f"""
    <style>
        .stApp {{ background: transparent !important; }}
        #bgVideo {{
            position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
            z-index: -1; object-fit: cover; filter: brightness(0.40); pointer-events: none;
        }}
    </style>
    <video autoplay muted loop playsinline id="bgVideo">
        <source src="{BG_VIDEO}" type="video/mp4">
    </video>
""", unsafe_allow_html=True)

# --- 3. TOOL DEFINITIONS ---
# Define manual tools FIRST so they exist when get_all_tools() is called
dataquartz_scraper_tool = Tool(
    name="scrape_dataquartz",
    func=scrape_dataquartz,
    description="Search the Dataquartz website for company information and services."
)

async def initialize_tools():
    """Converts MCP tools and merges with manual tools."""
    mcp_tools = await load_mcp_tools(cal_mcp)
    return [dataquartz_scraper_tool] + mcp_tools

# Wait for tools to load (fixes the "coroutine" concatenation error)
if "tools" not in st.session_state:
    st.session_state.tools = asyncio.run(initialize_tools())

# --- 4. SESSION & HISTORY ---
if "session_id" not in st.session_state:
    st.session_state.session_id = create_new_session("Web Discussion")
    st.session_state.messages = []

if not st.session_state.messages:
    db_history = get_chat_history(st.session_state.session_id)
    st.session_state.messages = [{"role": m['role'], "content": m['content']} for m in db_history]

# Display Branding
st.markdown(f'<div style="text-align: center;"><img src="{DQ_LOGO}" width="140"></div>', unsafe_allow_html=True)

# Display Messages
for msg in st.session_state.messages:
    with st.chat_message(msg["role"], avatar=USER_AVATAR if msg["role"] == "user" else AI_AVATAR):
        st.markdown(msg["content"])

# --- 5. CHAT LOGIC ---
if prompt := st.chat_input("Message Dataquartz AI..."):
    st.chat_message("user", avatar=USER_AVATAR).markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})
    save_message(st.session_state.session_id, "user", prompt)

    with st.chat_message("assistant", avatar=AI_AVATAR):
        llm = ChatGroq(model="llama-3.3-70b-versatile", groq_api_key=st.secrets["GROQ_API_KEY"])
        llm_with_tools = llm.bind_tools(st.session_state.tools)

        # Build message history
        history = [SystemMessage(content=sys_p)]
        for m in st.session_state.messages:
            history.append(HumanMessage(content=m["content"]) if m["role"] == "user" else AIMessage(content=m["content"]))

        ai_msg = llm_with_tools.invoke(history)
        
        if ai_msg.tool_calls:
            for tool_call in ai_msg.tool_calls:
                t_name = tool_call["name"]
                t_args = tool_call["args"]
                
                if t_name == "scrape_dataquartz":
                    observation = scrape_dataquartz(t_args.get("query", ""))
                else:
                    # Execute MCP tools via the server's call_tool method
                    if "session_id" in t_args:
                        t_args["session_id"] = st.session_state.session_id
                    observation = asyncio.run(cal_mcp.call_tool(t_name, t_args))
                
                history.append(ai_msg)
                history.append(ToolMessage(content=str(observation), tool_call_id=tool_call["id"]))
                final_response = llm.invoke(history)
                answer = final_response.content
        else:
            answer = ai_msg.content

        st.markdown(answer)
        st.session_state.messages.append({"role": "assistant", "content": answer})
        save_message(st.session_state.session_id, "assistant", answer)
