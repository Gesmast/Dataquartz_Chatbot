import streamlit as st
import asyncio
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.prebuilt import create_react_agent

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

async def get_agent():
    """Initializes the agent with all tools combined."""
    # The Adapter handles the conversion so LangGraph can 'read' FastMCP tools
    mcp_tools = await load_mcp_tools(cal_mcp)
    all_tools = [dataquartz_scraper_tool] + mcp_tools
    
    llm = ChatGroq(model="llama-3.3-70b-versatile", groq_api_key=st.secrets["GROQ_API_KEY"])
    
    # create_react_agent handles the tool-calling loop for you!
    return create_react_agent(llm, tools=all_tools, state_modifier=sys_p)

# Initialize Agent in Session State
if "agent" not in st.session_state:
    st.session_state.agent = asyncio.run(get_agent())

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
