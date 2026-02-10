import streamlit as st
import asyncio
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage

from langgraph.prebuilt import create_react_agent
from langchain_core.tools import StructuredTool

# Project Imports
from mcp_server import scrape_dataquartz
from database import create_new_session, save_message, get_chat_history
from Calmcp import mcp as cal_mcp 
from langchain_core.tools import Tool

# --- UI & ASSETS (Truncated for brevity, keep your existing CSS/Logo code here) ---
sys_p = "You are the Dataquartz AI assistant. Use the provided tools to search the website or book meetings."

# --- 1. TOOL & AGENT SETUP ---
dataquartz_scraper_tool = Tool(
    name="scrape_dataquartz",
    func=scrape_dataquartz,
    description="Search the Dataquartz website for company information and services."
)

def get_cal_tools():
    """Manually wraps FastMCP functions into LangChain tools."""
    # We create a LangChain tool for each function in your Calmcp.py
    # Replace 'get_available_slots' with your actual function names
    from Calmcp import get_available_slots, create_cal_booking 

    cal_slots_tool = StructuredTool.from_function(
        coroutine=get_available_slots,
        name="get_available_slots",
        description="Finds open booking times for a specific date (YYYY-MM-DD)."
    )

    cal_booking_tool = StructuredTool.from_function(
        coroutine=create_cal_booking,
        name="create_cal_booking",
        description="Books a meeting. Requires email, name, and start_time."
    )

    return [cal_slots_tool, cal_booking_tool]

# Initialize Agent in Session State
if "tools" not in st.session_state:
    manual_cal_tools = get_cal_tools()
    st.session_state.tools = [dataquartz_scraper_tool] + manual_cal_tools
    
# --- 2. CHAT HISTORY & UI ---
if "session_id" not in st.session_state:
    st.session_state.session_id = create_new_session("Web Discussion")
    st.session_state.messages = []

# Display existing messages...
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# --- 3. THE SIMPLIFIED CHAT LOOP ---
if prompt := st.chat_input("Message Dataquartz AI..."):
    # Save & Display User Message
    st.session_state.messages.append({"role": "user", "content": prompt})
    save_message(st.session_state.session_id, "user", prompt)
    with st.chat_message("user"):
        st.markdown(prompt)

    # Run Agent
    with st.chat_message("assistant"):
        with st.spinner("Consulting tools..."):
            # We pass the message history to the agent
            inputs = {"messages": [HumanMessage(content=prompt)]}
            
            # Use asyncio.run to bridge the sync/async gap
            result = asyncio.run(st.session_state.agent.ainvoke(inputs))
            
            # The last message in the result is the AI's final answer
            answer = result["messages"][-1].content
            st.markdown(answer)
            
            # Save Assistant Message
            st.session_state.messages.append({"role": "assistant", "content": answer})
            save_message(st.session_state.session_id, "assistant", answer)
