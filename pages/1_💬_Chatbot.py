import streamlit as st
import asyncio
import threading
from contextlib import AsyncExitStack
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.prebuilt import create_react_agent
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage

# Project Imports
from database import create_new_session, save_message, get_chat_history

# --- 1. ASSETS & UI CONSTANTS ---
PAGE_ICON = "https://lrkawuwfwyrmezgrrbpp.supabase.co/storage/v1/object/public/Assets_DQ_Chatbot/62249_db-favicon%20(1).png"
DQ_LOGO = "https://lrkawuwfwyrmezgrrbpp.supabase.co/storage/v1/object/public/Assets_DQ_Chatbot/dq_logo_transparent.png"
AI_AVATAR = "https://lrkawuwfwyrmezgrrbpp.supabase.co/storage/v1/object/public/Assets_DQ_Chatbot/Gemini_Generated_Image_sinrf3sinrf3sinr.png"
USER_AVATAR = "https://lrkawuwfwyrmezgrrbpp.supabase.co/storage/v1/object/public/Assets_DQ_Chatbot/Untitled%20design%20(1).png"
BG_VIDEO = "https://lrkawuwfwyrmezgrrbpp.supabase.co/storage/v1/object/public/Assets_DQ_Chatbot/quartz_background.mp4"
SYSTEM_PROMPT_FILE = "SystemPrompt.txt"
LLM_MODEL = "llama-3.3-70b-versatile"

# --- 2. THE BACKGROUND LOOP MANAGER (THE BRAIN) ---
class AsyncAppCore:
    def __init__(self):
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        self.exit_stack = AsyncExitStack()
        self.tools = []

    def _run_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def run_coro(self, coro):
        future = asyncio.run_coroutine_threadsafe(coro, self.loop)
        return future.result()

    async def _setup_servers(self):
        # Local Server Configurations (Scraper and Calendar)
        server_configs = [
            StdioServerParameters(command="python", args=["mcp_server.py"]),
            StdioServerParameters(command="python", args=["Calmcp.py"])
        ]
        for config in server_configs:
            read, write = await self.exit_stack.enter_async_context(stdio_client(config))
            session = await self.exit_stack.enter_async_context(ClientSession(read, write))
            await session.initialize()
            mcp_tools = await load_mcp_tools(session)
            self.tools.extend(mcp_tools)
        return self.tools

# --- 3. PAGE CONFIG & STYLING ---
st.set_page_config(page_title="Dataquartz AI", page_icon=PAGE_ICON, layout="centered")

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

# --- 4. INITIALIZATION ---
def load_system_prompt() -> str:
    prompt_path = Path(__file__).parent / SYSTEM_PROMPT_FILE
    return prompt_path.read_text(encoding='utf-8').strip() if prompt_path.exists() else "You are Dataquartz AI."

if "core" not in st.session_state:
    core = AsyncAppCore()
    with st.spinner(" "): # Hidden spinner to keep UI clean
        all_tools = core.run_coro(core._setup_servers())
        llm = ChatGroq(model=LLM_MODEL, temperature=0, groq_api_key=st.secrets["GROQ_API_KEY"])
        st.session_state.agent = create_react_agent(llm, tools=all_tools, state_modifier=load_system_prompt())
        st.session_state.core = core

if "session_id" not in st.session_state:
    st.session_state.session_id = create_new_session("Web Discussion")
    st.session_state.messages = get_chat_history(st.session_state.session_id)

# --- 5. UI BRANDING ---
st.markdown(f"""
    <div style="text-align: center; padding-top: 2rem;">
        <a href="/" target="_self"><img src="{DQ_LOGO}" width="140"></a>
        <div class="electro-header">CHAT</div>
        <div class="sub-header">Ask about Dataquartz</div>
    </div>
""", unsafe_allow_html=True)

# --- 6. CHAT DISPLAY & LOGIC ---
for msg in st.session_state.messages:
    avatar = USER_AVATAR if msg["role"] == "user" else AI_AVATAR
    with st.chat_message(msg["role"], avatar=avatar):
        st.markdown(msg["content"])

if prompt := st.chat_input("Message Dataquartz AI..."):
    # User Input
    st.session_state.messages.append({"role": "user", "content": prompt})
    save_message(st.session_state.session_id, "user", prompt)
    with st.chat_message("user", avatar=USER_AVATAR):
        st.markdown(prompt)

    # Assistant Response
    with st.chat_message("assistant", avatar=AI_AVATAR):
        with st.spinner(" "): 
            try:
                # Run the Agent through the Background Thread
                result = st.session_state.core.run_coro(
                    st.session_state.agent.ainvoke({"messages": [HumanMessage(content=prompt)]})
                )
                answer = result["messages"][-1].content
                st.markdown(answer)
                
                # Persistence
                st.session_state.messages.append({"role": "assistant", "content": answer})
                save_message(st.session_state.session_id, "assistant", answer)
            except Exception as e:
                st.error(f"System Offline: {e}")
