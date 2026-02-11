import streamlit as st
import asyncio
import nest_asyncio
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent
from langchain_mcp_adapters.tools import load_mcp_tools
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Project Imports
from database import create_new_session, save_message, get_chat_history
from Calmcp import get_available_slots, create_cal_booking 
from langchain_core.tools import StructuredTool

# 1. FIX: Patch the event loop for Streamlit
nest_asyncio.apply()

# --- CONFIGURATION ---
LLM_MODEL = "llama-3.3-70b-versatile"
SYS_PROMPT = "You are the Dataquartz AI assistant. Use the MCP tools to search the website and the Cal tools to book meetings."

# --- TOOL SETUP ---
def get_manual_tools():
    """Wraps local sync/async functions into LangChain tools."""
    return [
        StructuredTool.from_function(
            coroutine=get_available_slots,
            name="get_available_slots",
            description="Finds open booking times for a specific date (YYYY-MM-DD)."
        ),
        StructuredTool.from_function(
            coroutine=create_cal_booking,
            name="create_cal_booking",
            description="Books a meeting. Requires email, name, and start_time."
        )
    ]

async def initialize_agent():
    """Connects to MCP server and initializes the ReAct agent."""
    # 1. Define your MCP Server parameters (adjust command/args to your RAG server)
    server_params = StdioServerParameters(
        command="python",
        args=["mcp_server.py"], # This is your Company RAG/Scraper MCP
    )
    
    # 2. Connect to MCP and load tools
    # Note: In a production app, you'd manage this session lifecycle more strictly
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            mcp_tools = await load_mcp_tools(session)
            
            # 3. Combine with manual Cal tools
            all_tools = mcp_tools + get_manual_tools()
            
            # 4. Initialize LLM & Agent
            llm = ChatGroq(model=LLM_MODEL, temperature=0)
            return create_react_agent(llm, tools=all_tools, state_modifier=SYS_PROMPT)

# --- SESSION STATE INITIALIZATION ---
if "agent" not in st.session_state:
    with st.spinner("Connecting to Knowledge Base MCP..."):
        # We run the async initializer in the background
        st.session_state.agent = asyncio.run(initialize_agent())

if "session_id" not in st.session_state:
    st.session_state.session_id = create_new_session("Web Discussion")
    st.session_state.messages = get_chat_history(st.session_state.session_id)

# --- UI RENDERING ---
st.title("Dataquartz AI")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# --- CHAT LOGIC ---
if prompt := st.chat_input("How can I help you today?"):
    # 1. User Message
    st.session_state.messages.append({"role": "user", "content": prompt})
    save_message(st.session_state.session_id, "user", prompt)
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. Agent Execution
    with st.chat_message("assistant"):
        with st.spinner("Searching Knowledge Base..."):
            # Prepare inputs
            inputs = {"messages": [HumanMessage(content=prompt)]}
            
            # Bridge Sync to Async
            # We use the agent created during initialization
            result = asyncio.run(st.session_state.agent.ainvoke(inputs))
            
            answer = result["messages"][-1].content
            st.markdown(answer)
            
            # 3. Save History
            st.session_state.messages.append({"role": "assistant", "content": answer})
            save_message(st.session_state.session_id, "assistant", answer)
